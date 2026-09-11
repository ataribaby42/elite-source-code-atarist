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
        UC_M68K_REG_A0, UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_D0,
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
        init = (ROOT / 'asm/init.m68').read_text()
        rotate = (ROOT / 'asm/rotate.m68').read_text()
        data = (ROOT / 'asm/data.m68').read_text()
        main = (ROOT / 'asm/main.m68').read_text(encoding='utf-8')
        flight = (ROOT / 'asm/flight.m68').read_text(encoding='utf-8')
        names = re.findall(r'^\s*q_subr (\w+)', dust, re.M)
        reset_names = ['reset_system', 'set_roll_angles', 'set_climb_angles', 'get_trig']
        control_names = ['lock_controls', 'torus', 'torus_drive', 'attack', 'damping', 'finish_space_skip']
        constants = ['dust_front', 'dust_store', 'dust_len', 'no_dust', 'dust_used',
                     'dust_motion', 'dust_step', 'dust_plane_sin',
                     'dust_plane_cos', 'dust_vertical_sin', 'dust_vertical_cos',
                     'dust_x', 'dust_y', 'dust_z', 'view', 'speed', 'max_speed',
                     'roll_sin', 'roll_cos', 'climb_sin', 'climb_cos', 'retro_count',
                     'retro_life', 'dust_type', 'dust_size', 'dust_ctr', 'latch',
                     'max_len', 'witch_space', 'scr_base', 'colour_ptr', 'random_seed',
                     'roll_angle', 'climb_angle', 'controls_locked', 'torus_on', 'torus_ctr',
                     'stop_skip', 'planet_range', 'sun_range', 'torus_planet', 'torus_sun',
                     'mission', 'splanet', 'govern', 'f_roll', 'f_climb']
        assembly = ('amiga_implementation equ 1\namiga_workspace_implementation equ 1\n'
                    'fileio_implementation equ 1\n\tinclude "common.def"\n'
                    '\tinclude "macros.m68"\n\tinclude "raster.inc"\n')
        assembly += dust[dust.index('    rsset 0'):dust.index('    q_module dust')]
        assembly += flight[flight.index('\tq_vars flight'):flight.index('\tq_module flight')]
        for name in ('torus_dur', 'torus_speed'):
            assembly += re.search(r'^'+name+r': equ[^\n]*\n', flight, re.M).group(0)
        assembly += re.search(r'^outcodes macro.*?^\s*endm', graphics, re.M | re.S).group(0) + '\n'
        assembly += '\torg $10000\n\tdc.l ' + ','.join(names + reset_names + control_names + constants) + '\n'
        assembly += '\n'.join(routine(dust, name) for name in names)
        assembly += '\n'.join(routine(graphics, name) for name in
                              ['dot_to_addr', 'c_plotxy', 'plotxy', 'mask_plot'])
        assembly += '\n'.join(routine(maths, name) for name in ['random', 'rand'])
        assembly += routine(init, 'reset_system')
        assembly += re.search(r'^reset_table:\s*\n(?:\s*dc\.w[^\n]*\n)+', init, re.M).group(0)
        assembly += '\n'.join(routine(rotate, name) for name in reset_names[1:])
        assembly += re.search(r'\tq_global trig_table\s*\n(?:\s*dc\.l[^\n]*\n)+', data).group(0)
        assembly += routine(main, 'lock_controls')
        assembly += '\n'.join(routine(flight, name) for name in control_names[1:-1])
        # Execute the frame's actual deferred torus-stop block.
        assembly += '\nfinish_space_skip:\n' + re.search(
            r'\ttst stop_skip\(a6\).*?^q_main_m68_17:', main, re.M | re.S).group(0) + '\n\trts\n'
        assembly += '\nquiet:\ncheck_inflight:\nbeep:\ndisp_message:\nfx:\npirate_attack:\n\trts\n'
        assembly += '\ntext7:\ntext8:\ntext10:\n\tdc.w 0\n'
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
        cls.symbols = dict(zip(names + reset_names + control_names + constants,
                              struct.unpack_from('>' + 'I' * (len(names) + len(reset_names) + len(control_names) + len(constants)), cls.code)))

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


    def test_control_lock_resets_cached_rotation_without_clobbering_registers(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for roll, pitch in ((40, 0), (-40, 0), (0, 20), (0, -20), (40, -20), (0, 0)):
                with self.subTest(cpu=model, roll=roll, pitch=pitch):
                    self.prepare(model=model)
                    for name, angle in (('roll', roll), ('climb', pitch)):
                        self.variable(name + '_angle', angle)
                        self.call('set_' + name + '_angles')
                    self.variable('f_roll', 0xffff)
                    self.variable('f_climb', 0xffff)
                    registers = {UC_M68K_REG_D0+i: 0x12340000+i for i in range(8)}
                    registers.update({UC_M68K_REG_A0+i: 0x80000+i*16 for i in range(6)})
                    for register, value in registers.items():
                        self.cpu.reg_write(register, value)
                    self.call('lock_controls')
                    for register, value in registers.items():
                        self.assertEqual(self.cpu.reg_read(register), value)
                    for name in ('roll', 'climb'):
                        for suffix, size, expected in (('_angle', 2, 0), ('_sin', 4, 0),
                                                      ('_cos', 4, 1 << 24)):
                            actual = self.cpu.mem_read(VARIABLES+self.symbols[name+suffix], size)
                            self.assertEqual(int.from_bytes(actual, 'big'), expected, name+suffix)
                    for flag in ('f_roll', 'f_climb'):
                        self.assertEqual(self.cpu.mem_read(VARIABLES+self.symbols[flag], 2), b'\0\0')

    def test_torus_entry_and_all_exits_match_neutral_starfield_in_every_view(self):
        def flight(model, view, roll, pitch, exit_kind):
            self.prepare(view, speed=self.symbols['max_speed'], model=model)
            self.call('init_dust')
            for name, angle in (('roll', roll), ('climb', pitch)):
                self.variable(name+'_angle', angle)
                self.call('set_'+name+'_angles')
            self.variable('planet_range', self.symbols['torus_planet']+100000, 4)
            self.variable('sun_range', self.symbols['torus_sun']+200000, 4)
            self.cpu.mem_write(VARIABLES+self.symbols['splanet']+self.symbols['govern'], b'\0\7')
            self.call('torus')
            self.assertEqual(self.cpu.mem_read(VARIABLES+self.symbols['torus_on'], 2), b'\xff\x00')
            states = []
            start = VARIABLES+self.symbols['dust_front']

            def frame():
                self.cpu.mem_write(GUARD, BACKGROUND)
                self.call('dust_cloud')
                states.append(bytes(self.cpu.mem_read(start, 4*self.symbols['dust_store'])))

            for _ in range(4):
                self.call('torus_drive')
                self.call('finish_space_skip')
                frame()
            if exit_kind == 'manual':
                # J again: force a stop, with a valid government and a known
                # non-attack RNG result (1), without stubbing the drive logic.
                self.variable('random_seed', 0x02000000, 4)
                self.call('torus')
            elif exit_kind == 'mass_lock':
                self.variable('planet_range', self.symbols['torus_planet']+100, 4)
            else:
                self.variable('mission', 0x21)
                self.variable('torus_ctr', 1)
            self.call('torus_drive')
            self.call('finish_space_skip')
            for name in ('torus_on', 'controls_locked', 'dust_type', 'roll_angle', 'climb_angle'):
                self.assertEqual(self.cpu.mem_read(VARIABLES+self.symbols[name], 2), b'\0\0', name)
            self.assertEqual(int.from_bytes(self.cpu.mem_read(
                VARIABLES+self.symbols['speed'], 2), 'big'), self.symbols['max_speed'])
            for _ in range(12):
                self.call('damping')
                frame()
            return states

        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for view in range(4):
                for exit_kind in ('manual', 'mass_lock', 'attack'):
                    neutral = flight(model, view, 0, 0, exit_kind)
                    for roll, pitch in ((40, 0), (0, -20), (40, 20), (-40, -20)):
                        with self.subTest(cpu=model, view=view, exit=exit_kind, roll=roll, pitch=pitch):
                            self.assertTrue(flight(model, view, roll, pitch, exit_kind) == neutral,
                                            'Starfield differs from an initially neutral warp')

    def test_front_and_rear_follow_bbc_depth_and_radial_laws(self):
        for view, sign in ((0, 1), (1, -1)):
            for speed in (0, 1, 11, 21, 22):
                for depth in (40, 80, 150):
                    with self.subTest(view=view, speed=speed, depth=depth):
                        self.prepare(view, speed)
                        self.set_star(-40.25, 10.5, depth)
                        before = self.get_star()
                        self.call('update_dust')
                        step = 64 + speed*2048//22
                        q = (step // depth) | 1
                        self.assertEqual(self.get_star(), (
                            before[0] + sign*(-40)*q*256,
                            before[1] + sign*10*q*256,
                            before[2] - sign*step))

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
                    UNIT//4 + direction*(33*2048//depth)*256, 7*UNIT//2, depth*256))

    def test_zero_throttle_keeps_slow_drift_in_every_view(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for view in range(4):
                with self.subTest(cpu=model, view=view):
                    self.prepare(view, speed=0, model=model)
                    self.set_star(-40.25, 10.5, 80)
                    before = self.get_star()
                    for _ in range(40):
                        self.call('update_dust')
                        self.assert_visible()
                    x, y, z = self.get_star()
                    dx = x - before[0]
                    self.assertGreater(abs(dx), UNIT)
                    self.assertLess(abs(dx), 12*UNIT)
                    self.assertEqual(dx < 0, view in (0, 2))
                    if view < 2:
                        self.assertEqual(z - before[2], (-1 if view == 0 else 1)*40*64)
                        self.assertEqual(y > before[1], view == 0)
                    else:
                        self.assertEqual((y, z), before[1:])
                    self.assertEqual(self.cpu.mem_read(VARIABLES+self.symbols['speed'], 2),
                                     b'\x00\x00')

    def test_throttle_curve_is_gradual_and_clamped_in_every_view(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for view in range(4):
                with self.subTest(cpu=model, view=view):
                    self.prepare(view, model=model)
                    rates = []
                    for speed in range(23):
                        self.variable('speed', speed)
                        self.call('setup_dust')
                        rates.append(int.from_bytes(self.cpu.mem_read(
                            VARIABLES+self.symbols['dust_step'], 2), 'big'))
                    self.assertEqual(rates[0], 64)
                    self.assertEqual(rates[-1], 22*64*3//2)
                    increments = [b-a for a, b in zip(rates, rates[1:])]
                    self.assertGreater(min(increments), 0)
                    self.assertLessEqual(max(increments)-min(increments), 1)
                    for speed in (23, 32767, 65535):
                        self.variable('speed', speed)
                        self.call('setup_dust')
                        self.assertEqual(int.from_bytes(self.cpu.mem_read(
                            VARIABLES+self.symbols['dust_step'], 2), 'big'), rates[-1])

    def test_full_speed_scales_translation_including_retros(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for view in range(4):
                for retro in (False, True):
                    with self.subTest(cpu=model, view=view, retro=retro):
                        self.prepare(view, speed=22, retro=retro, model=model)
                        motion = view ^ retro
                        self.set_star(40, 10, 128)
                        self.call('update_dust')
                        x, y, z = self.get_star()
                        if motion < 2:
                            sign = 1 if motion == 0 else -1
                            # Depth travel is exactly 150% of the former 22*64.
                            self.assertEqual(z-128*256, -sign*22*64*3//2)
                            self.assertEqual(x > 40*UNIT, sign > 0)
                        else:
                            # At this depth the old side speed was 1.375 px.
                            sign = -1 if motion == 2 else 1
                            self.assertEqual(x-40*UNIT, sign*11*UNIT*3//16)
                            self.assertEqual((y, z), (10*UNIT, 128*256))

    def test_coloured_jump_trails_keep_their_translation_rate(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for view in range(4):
                for kind in (1, 2):
                    for speed in (0, 11, 22):
                        with self.subTest(cpu=model, view=view, kind=kind, speed=speed):
                            self.prepare(view, speed=speed, model=model)
                            self.variable('dust_type', kind)
                            self.call('setup_dust')
                            self.set_star(40, 10, 80)
                            self.call('update_dust')
                            x, y, z = self.get_star()
                            if view < 2:
                                sign = 1 if view == 0 else -1
                                self.assertEqual((x, y, z), (
                                    40*UNIT+sign*40*256, 10*UNIT+sign*10*256,
                                    80*256-sign*128))
                            else:
                                sign = -1 if view == 2 else 1
                                self.assertEqual((x, y, z), (
                                    40*UNIT+sign*(4096//80)*256, 10*UNIT, 80*256))

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

    def test_rear_vertical_recycling_preserves_overshoot_and_spreads_stars(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            # Retros also use rearward translation in the front view.
            for view, retro in ((1, False), (0, True)):
                self.prepare(view, speed=22, retro=retro, model=model)
                for x in (-129, 0, 128):
                    for y in (-91.5, -57, -56.25, 56, 56.75, 91.5):
                        with self.subTest(cpu=model, view=view, x=x, y=y):
                            xs = []
                            for _ in range(40):
                                self.set_star(x, y, 80)
                                self.call('update_dust')
                                self.assert_visible()
                                actual_x, actual_y, depth = self.get_star()
                                xs.append(actual_x//UNIT)
                                self.assertEqual(actual_y, round(
                                    (y + (112 if y < 0 else -112))*UNIT))
                                self.assertTrue(10*256 <= depth <= 137*256)
                            self.assertLess(min(xs), -80)
                            self.assertGreater(max(xs), 80)
                            self.assertGreater(len(set(xs)), 25)
                for y in (-10000, 10000):
                    self.set_star(0, y, 80)
                    self.call('update_dust')
                    self.assert_visible()

    def test_steady_rear_pitch_does_not_accumulate_edge_columns(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for speed in (0, 11, 22):
                for degrees in (-4, -1, -0.25, 0.25, 1, 4):
                    for seed in (0x347ac9, 1, 0xa5f013):
                        with self.subTest(cpu=model, speed=speed, pitch=degrees, seed=seed):
                            self.prepare(view=1, speed=speed,
                                         pitch=math.radians(degrees), model=model)
                            self.variable('random_seed', seed, 4)
                            self.call('init_dust')
                            start = VARIABLES+self.symbols['dust_front']+self.symbols['dust_store']
                            edge_counts, row_peaks = [], []
                            for frame in range(600):
                                self.call('draw_dust')
                                stars = list(struct.iter_unpack('>iiH', self.cpu.mem_read(
                                    start, self.symbols['dust_store'])))
                                for x, y, z in stars:
                                    self.assertTrue(-128 <= x//UNIT <= 127)
                                    self.assertTrue(-56 <= y//UNIT <= 55)
                                    self.assertTrue(8*256 <= z <= 65535)
                                if frame >= 100:
                                    edge_counts.append(sum(x//UNIT < -124 or x//UNIT >= 124
                                                           for x, y, z in stars))
                                    ys = [y//UNIT for x, y, z in stars]
                                    row_peaks.append(max(ys.count(y) for y in ys))
                            # These eight edge columns previously held more than
                            # six of the fifteen stars at full pitch and low speed.
                            self.assertLess(sum(edge_counts)/len(edge_counts), 1.6)
                            # Keeping fractional overshoot must not replace the
                            # vertical columns with synchronized horizontal rows.
                            self.assertLess(sum(row_peaks)/len(row_peaks), 3.5)

    def test_forward_depth_underflow_respawns_instead_of_wrapping(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.prepare(speed=22, model=model)
            for depth in (8, 8.125, 8.25, 16, 24):
                with self.subTest(cpu=model, depth=depth):
                    self.set_star(40, 10, depth)
                    self.call('update_dust')
                    self.assert_visible()
                    self.assertGreaterEqual(self.get_star()[2], 144*256)

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

    def test_vertical_side_recycling_preserves_subpixel_overshoot(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for view in (2, 3):
                for retro in (False, True):
                    self.prepare(view, speed=22, retro=retro, model=model)
                    for y in (-91.5, -57, -56.25, 56, 56.75, 91.5):
                        with self.subTest(cpu=model, view=view, retro=retro, y=y):
                            self.set_star(0, y, 80)
                            self.call('update_dust')
                            self.assert_visible()
                            _, actual_y, _ = self.get_star()
                            self.assertEqual(actual_y, round((y + (112 if y < 0 else -112))*UNIT))
                    # Projection failure sentinels or invalid coordinates must
                    # still recover inside the viewport after a single update.
                    for y in (-10000, 10000):
                        self.set_star(0, y, 80)
                        self.call('update_dust')
                        self.assert_visible()

    def test_steady_side_roll_does_not_synchronize_stars_into_rows(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for view in (2, 3):
                for roll in (-math.radians(4), math.radians(4)):
                    for speed in (0, 22):
                        with self.subTest(cpu=model, view=view, roll=roll, speed=speed):
                            self.prepare(view, speed=speed, roll=roll, model=model)
                            self.call('init_dust')
                            start = VARIABLES + self.symbols['dust_front'] + view*self.symbols['dust_store']
                            unique_rows = []
                            for frame in range(600):
                                self.call('draw_dust')
                                if frame >= 100:
                                    rows = [self.get_star(start+i*self.symbols['dust_len'])[1]//UNIT
                                            for i in range(self.symbols['no_dust'])]
                                    unique_rows.append(len(set(rows)))
                            # A 15-star cloud previously collapsed to about four
                            # rows at full roll. Allow incidental alignments.
                            self.assertGreater(sum(unique_rows)/len(unique_rows),
                                               self.symbols['no_dust']*0.75)

    def test_system_reset_initializes_trigonometry_before_first_control_input(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for stale in (0, 1234567):
                self.prepare(model=model)
                for name in ('roll_sin', 'roll_cos', 'climb_sin', 'climb_cos'):
                    self.variable(name, stale, 4)
                self.variable('roll_angle', 10)
                self.variable('climb_angle', -10)
                self.call('reset_system')
                for axis in ('roll', 'climb'):
                    angle = self.cpu.mem_read(VARIABLES+self.symbols[axis+'_angle'], 2)
                    trig = self.cpu.mem_read(VARIABLES+self.symbols[axis+'_sin'], 8)
                    self.assertEqual(angle, b'\0\0')
                    self.assertEqual(trig, struct.pack('>ii', 0, 1 << 24))

    def test_first_side_view_after_launch_keeps_the_cloud_spread_out(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for view in (2, 3):
                self.prepare(view=view, model=model)
                # Match a cold start: INIT_DUST runs with zeroed trig caches,
                # RESET_SYSTEM runs at launch, then launch sets roll to +10.
                for name in ('roll_sin', 'roll_cos', 'climb_sin', 'climb_cos'):
                    self.variable(name, 0, 4)
                self.call('init_dust')
                self.call('reset_system')
                self.variable('roll_angle', 10)
                self.call('set_roll_angles')
                start = VARIABLES + self.symbols['dust_front'] + view*self.symbols['dust_store']
                for frame in range(30):
                    # The original launch spin decays by one unit per frame.
                    self.variable('roll_angle', max(0, 10-frame))
                    self.call('set_roll_angles')
                    self.call('draw_dust')
                    stars = [self.get_star(start+i*self.symbols['dust_len'])
                             for i in range(self.symbols['no_dust'])]
                    self.assertGreater(max(s[0] for s in stars)-min(s[0] for s in stars), 100*UNIT)
                    self.assertGreater(max(s[1] for s in stars)-min(s[1] for s in stars), 40*UNIT)

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
