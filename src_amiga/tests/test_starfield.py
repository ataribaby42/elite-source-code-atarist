"""Execute the native BBC/C64-style starfield on MC68000 and MC68020.

Optional dependency: unicorn==2.1.4. No emulator or game build dependency.
"""
from pathlib import Path
import math
import re
import struct
import subprocess
import tempfile
import unittest

from test_raster import BACKGROUND, GUARD, SCREEN, OTHER, paint, routine

try:
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_PROT_READ, UC_PROT_EXEC
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_D0,
        UC_M68K_REG_PC, UC_M68K_REG_SR)
except ImportError:
    Uc = None

ROOT = Path(__file__).resolve().parents[1]
CODE, STOP, VARIABLES, COLOUR, STACK = 0x10000, 0x1000, 0x30000, 0x32000, 0x90000
UNIT = 65536


@unittest.skipIf(Uc is None, 'optional starfield tests require unicorn==2.1.4')
class StarfieldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dust = (ROOT / 'asm/dust.m68').read_text()
        graphics = (ROOT / 'asm/graphics.m68').read_text()
        maths = (ROOT / 'asm/maths.m68').read_text()
        names = re.findall(r'^\s*q_subr (\w+)', dust, re.M)
        constants = ['dust_front', 'dust_store', 'dust_len', 'no_dust', 'dust_used',
                     'dust_motion', 'dust_step', 'dust_speed', 'dust_plane_sin',
                     'dust_plane_cos', 'dust_vertical_sin', 'dust_vertical_cos',
                     'dust_x', 'dust_y', 'dust_z', 'view', 'speed', 'max_speed',
                     'roll_sin', 'roll_cos', 'climb_sin', 'climb_cos', 'retro_count',
                     'retro_life', 'dust_type', 'dust_size', 'dust_ctr', 'latch',
                     'max_len', 'witch_space', 'scr_base', 'colour_ptr', 'random_seed']
        assembly = ('amiga_implementation equ 1\namiga_workspace_implementation equ 1\n'
                    'fileio_implementation equ 1\n\tinclude "common.def"\n'
                    '\tinclude "macros.m68"\n\tinclude "raster.inc"\n')
        assembly += dust[dust.index('    rsset 0'):dust.index('    q_module dust')]
        assembly += re.search(r'^outcodes macro.*?^\s*endm', graphics, re.M | re.S).group(0) + '\n'
        assembly += '\torg $10000\n\tdc.l ' + ','.join(names + constants) + '\n'
        assembly += '\n'.join(routine(dust, name) for name in names)
        assembly += '\n'.join(routine(graphics, name) for name in
                              ['dot_to_addr', 'c_plotxy', 'plotxy', 'mask_plot'])
        assembly += '\n'.join(routine(maths, name) for name in ['random', 'rand'])
        assembly += '\nset_colour:\n\trts\nmult_by_320:\n\tdc.w '
        assembly += ','.join(str(y * 320) for y in range(200)) + '\n'
        assembly += graphics[graphics.index('\tq_global bit_masks'):graphics.index('clip_list:')]
        (ROOT / 'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='test-starfield-', dir=ROOT / 'build') as temporary:
            folder = Path(temporary)
            path, binary = folder / 'starfield.s', folder / 'starfield.bin'
            path.write_text(assembly)
            result = subprocess.run([str(ROOT.parent / 'tools/vasmm68k_mot.exe'),
                '-m68000', '-Fbin', '-no-opt', '-align', '-allmp', '-spaces', '-nocase',
                '-I' + str(ROOT / 'asm'), '-o', str(binary), str(path)],
                cwd=folder, capture_output=True, text=True)
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)
            cls.code = binary.read_bytes()
        cls.symbols = dict(zip(names + constants,
                              struct.unpack_from('>' + 'I' * (len(names) + len(constants)), cls.code)))

    def prepare(self, view=0, speed=0, roll=0, pitch=0, retro=False,
                screen=SCREEN, model=None):
        self.cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(model or UC_CPU_M68K_M68000)
        self.cpu.mem_map(0, 0x100000)
        self.cpu.mem_write(CODE, self.code)
        self.cpu.mem_protect(CODE, (len(self.code)+4095)//4096*4096, UC_PROT_READ | UC_PROT_EXEC)
        self.cpu.mem_write(GUARD, BACKGROUND)
        self.cpu.mem_write(COLOUR, b'\xff' * 16)
        for name, value in [('scr_base', screen), ('colour_ptr', COLOUR), ('random_seed', 0x347ac9)]:
            self.variable(name, value, 4)
        self.variable('view', view)
        self.variable('speed', speed)
        self.variable('retro_count', self.symbols['retro_life'] if retro else 0)
        self.angles(roll, pitch)
        self.call('setup_dust')
        self.star = VARIABLES + self.symbols['dust_front'] + view * self.symbols['dust_store']
        self.cpu.reg_write(UC_M68K_REG_A5, self.star)

    def variable(self, name, value, size=2):
        self.cpu.mem_write(VARIABLES + self.symbols[name],
                           int(value & ((1 << (size*8))-1)).to_bytes(size, 'big'))

    def angles(self, roll, pitch):
        for name, angle in [('roll', roll), ('climb', pitch)]:
            self.variable(name + '_sin', round(math.sin(angle) * (1 << 24)), 4)
            self.variable(name + '_cos', round(math.cos(angle) * (1 << 24)), 4)

    def call(self, name):
        self.cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        self.cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.cpu.reg_write(UC_M68K_REG_A7, STACK-4)
        self.cpu.mem_write(STACK-4, struct.pack('>I', STOP))
        self.cpu.emu_start(self.symbols[name], STOP, count=1000000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC), STOP, name)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7), STACK, name)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A6), VARIABLES, name)

    def set_star(self, x, y, z, address=None):
        self.cpu.mem_write(address or self.star,
                           struct.pack('>iiH', round(x*UNIT), round(y*UNIT), round(z*256)))

    def get_star(self, address=None):
        return struct.unpack('>iiH', self.cpu.mem_read(address or self.star, 10))

    def assert_visible(self, address=None):
        x, y, z = self.get_star(address)
        self.assertTrue(-128 <= x//UNIT <= 127, x/UNIT)
        self.assertTrue(-56 <= y//UNIT <= 55, y/UNIT)
        self.assertTrue(8*256 <= z <= 65535, z/256)

    def test_front_and_rear_follow_bbc_depth_and_radial_laws(self):
        for view, sign in ((0, 1), (1, -1)):
            for speed in (1, 11, 22):
                for depth in (40, 80, 150):
                    with self.subTest(view=view, speed=speed, depth=depth):
                        self.prepare(view, speed)
                        self.set_star(-40.25, 10.5, depth)
                        before = self.get_star()
                        self.call('update_dust')
                        q = (speed*64 // depth) | 1
                        self.assertEqual(self.get_star(), (
                            before[0] + sign*(-40)*q*256,
                            before[1] + sign*10*q*256,
                            before[2] - sign*speed*64))

    def test_radial_motion_is_symmetric_across_the_centre(self):
        for view in (0, 1):
            self.prepare(view, speed=11)
            self.set_star(40.25, 10.5, 80)
            self.call('update_dust')
            positive = self.get_star()
            self.set_star(-40.25, -10.5, 80)
            self.call('update_dust')
            negative = self.get_star()
            self.assertEqual(negative, (-positive[0], -positive[1], positive[2]))

    def test_sideways_speed_depends_on_depth_and_view(self):
        for view, direction in ((2, -1), (3, 1)):
            for depth in (8, 40, 200, 255):
                self.prepare(view, speed=22)
                self.set_star(0.25, 3.5, depth)
                self.call('update_dust')
                self.assertEqual(self.get_star(), (
                    UNIT//4 + direction*(22*2048//depth)*256, 7*UNIT//2, depth*256))

    def test_stopped_stars_keep_all_subpixel_coordinates(self):
        for view in range(4):
            self.prepare(view)
            self.set_star(-40.25, 10.5, 80)
            before = self.get_star()
            for _ in range(40):
                self.call('update_dust')
            self.assertEqual(self.get_star(), before)

    def test_front_respawns_far_and_rear_respawns_on_borders(self):
        for view in (0, 1):
            self.prepare(view, speed=22)
            for _ in range(80):
                self.set_star(15, 5, 16 if view == 0 else 159)
                self.call('update_dust')
                self.assert_visible()
                x, y, z = self.get_star()
                if view == 0:
                    self.assertGreaterEqual(z, 144*256)
                    self.assertGreaterEqual(abs(x//UNIT), 8)
                    self.assertGreaterEqual(abs(y//UNIT), 4)
                else:
                    self.assertTrue(x//UNIT in (-128, 127) or y//UNIT in (-56, 55))
                    self.assertTrue(10*256 <= z <= 137*256)

    def test_side_respawns_at_incoming_edges_including_retros(self):
        for view in (2, 3):
            for retro in (False, True):
                self.prepare(view, speed=22, retro=retro)
                for x, y in ((-129, 0), (128, 0), (0, -57), (0, 56)):
                    self.set_star(x, y, 80)
                    self.call('update_dust')
                    self.assert_visible()
                    actual_x, actual_y, _ = self.get_star()
                    if x:
                        self.assertEqual(actual_x//UNIT, 127 if (view ^ retro) == 2 else -128)
                    else:
                        self.assertEqual(actual_y//UNIT, 55 if y < 0 else -56)

    def test_retros_reverse_translation_without_reversing_steering(self):
        for view in range(4):
            self.prepare(view, speed=22, roll=0.005, pitch=-0.003)
            offsets = ['dust_plane_sin', 'dust_plane_cos', 'dust_vertical_sin', 'dust_vertical_cos']
            angles = [bytes(self.cpu.mem_read(VARIABLES+self.symbols[name], 2)) for name in offsets]
            self.variable('retro_count', self.symbols['retro_life'])
            self.call('setup_dust')
            self.assertEqual(int.from_bytes(self.cpu.mem_read(
                VARIABLES+self.symbols['dust_motion'], 2), 'big'), view ^ 1)
            self.assertEqual(angles, [bytes(self.cpu.mem_read(
                VARIABLES+self.symbols[name], 2)) for name in offsets])

    def test_rotation_tracks_the_512_pixel_object_projection(self):
        for view in range(4):
            for roll, pitch in ((0.015, 0), (0, -0.015), (0.005, -0.007)):
                for x, y in ((0, 0), (-90, 30), (80, -20)):
                    with self.subTest(view=view, angles=(roll, pitch), point=(x, y)):
                        self.prepare(view, roll=roll, pitch=pitch)
                        self.set_star(x, y, 80)
                        self.call('rotate_dust')
                        plane = [roll, -roll, -pitch, pitch][view]
                        vertical = [-pitch, pitch, -roll, roll][view]
                        u = x*math.cos(plane) - y*math.sin(plane)
                        v = x*math.sin(plane) + y*math.cos(plane)
                        denominator = math.cos(vertical) - v*math.sin(vertical)/512
                        expected_x = u/denominator
                        expected_y = (v*math.cos(vertical) + 512*math.sin(vertical))/denominator
                        actual_x, actual_y, _ = self.get_star()
                        self.assertAlmostEqual(actual_x/UNIT, expected_x, delta=0.1)
                        self.assertAlmostEqual(actual_y/UNIT, expected_y, delta=0.1)

    def test_slow_pitch_accumulates_fractional_pixels_in_both_directions(self):
        for pitch in (-0.0005, 0.0005):
            self.prepare(pitch=pitch)
            self.set_star(0, 0, 80)
            for _ in range(12):
                self.call('rotate_dust')
            _, y, _ = self.get_star()
            self.assertGreater(abs(y), 2*UNIT)
            self.assertEqual(y > 0, pitch < 0)

    def test_every_depth_draws_exactly_one_pixel(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for screen in (SCREEN, OTHER):
                for depth in (8, 79, 80, 143, 144, 255):
                    for x, y in ((0, 0), (-128, 55), (127, -56), (-129, 0), (128, 0)):
                        self.prepare(screen=screen, model=model)
                        self.set_star(x, y, depth)
                        self.call('plot_dust')
                        expected = bytearray(BACKGROUND)
                        if -128 <= x <= 127:
                            paint(expected, [(x+160, 63-y)], (65535,)*4, screen)
                        self.assertEqual(self.cpu.mem_read(GUARD, len(BACKGROUND)), expected)

    def test_complete_cloud_stays_inside_viewport_during_flight_and_turns(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.prepare(speed=22, model=model)
            self.call('init_dust')
            start = VARIABLES + self.symbols['dust_front']
            for view in range(4):
                self.variable('view', view)
                for frame in range(100):
                    self.angles(0.008*math.sin(frame/9), 0.006*math.cos(frame/11))
                    self.cpu.mem_write(GUARD, BACKGROUND)
                    self.call('draw_dust')
                    for star in range(self.symbols['no_dust']):
                        address = start+view*self.symbols['dust_store']+star*self.symbols['dust_len']
                        self.assert_visible(address)
                    # Only the viewport may change, on either CPU model.
                    actual = bytearray(self.cpu.mem_read(GUARD, len(BACKGROUND)))
                    paint(actual, ((x, y) for y in range(8, 120) for x in range(32, 288)), (0,)*4)
                    expected = bytearray(BACKGROUND)
                    paint(expected, ((x, y) for y in range(8, 120) for x in range(32, 288)), (0,)*4)
                    self.assertEqual(actual, expected)

    def test_witchspace_and_coloured_trail_lifecycle(self):
        self.prepare(speed=22)
        self.call('init_dust')
        start = VARIABLES+self.symbols['dust_front']
        before = bytes(self.cpu.mem_read(start, 4*self.symbols['dust_store']))
        self.variable('witch_space', 1)
        self.call('draw_dust')
        self.assertEqual(self.cpu.mem_read(start, len(before)), before)
        self.assertEqual(self.cpu.mem_read(GUARD, len(BACKGROUND)), BACKGROUND)
        self.variable('witch_space', 0)
        for name, value in [('dust_type', 2), ('dust_size', 3), ('dust_ctr', 1),
                            ('latch', 10), ('max_len', 8)]:
            self.variable(name, value)
        self.call('dust_cloud')
        self.assertEqual(int.from_bytes(self.cpu.mem_read(
            VARIABLES+self.symbols['dust_size'], 2), 'big'), 4)
        for star in range(self.symbols['no_dust']):
            self.assert_visible(start+star*self.symbols['dust_len'])


if __name__ == '__main__':
    unittest.main()
