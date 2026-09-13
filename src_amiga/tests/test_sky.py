"""Execute the real distant-star renderer, comparing tree culling to all stars.

Optional dependency: unicorn==2.1.4. No changes to the game random sequence.
"""
from pathlib import Path
import math
import random
import re
import struct
import unittest

from test_raster import BACKGROUND, GUARD, SCREEN, OTHER, paint, routine
from test_viewport import assemble, preamble

try:
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_PROT_READ, UC_PROT_EXEC, UC_HOOK_CODE
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_D0, UC_M68K_REG_A0, UC_M68K_REG_A6, UC_M68K_REG_A7,
        UC_M68K_REG_PC, UC_M68K_REG_SR)
except ImportError:
    Uc = None

ROOT = Path(__file__).resolve().parents[1]
CODE, STOP, VARIABLES, COLOUR, STACK = 0x10000, 0x1000, 0x30000, 0x3c000, 0x90000
Q = 1 << 24


def multiply(a, b):
    return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def rotation(roll, pitch):
    cr, sr, cp, sp = math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch)
    return multiply([[1, 0, 0], [0, cp, -sp], [0, sp, cp]],
                    [[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])


@unittest.skipIf(Uc is None, 'optional sky tests require unicorn==2.1.4')
class SkyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sky = (ROOT/'asm/sky.m68').read_text()
        graphics = (ROOT/'asm/graphics.m68').read_text()
        names = ['init_sky', 'advance_sky', 'draw_sky', 'sky_make_matrix', 'sky_project',
                 'sky_project_star', 'sky_multiply', 'sky_normalise', 'sky_catalogue',
                 'sky_catalogue_end', 'sky_basis', 'sky_matrix', 'sky_pixels', 'sky_count',
                 'sky_dirty', 'sky_view', 'sky_turns', 'sky_vars', 'sky_used', 'sky_vsize',
                 'sky_capacity', 'sky_enabled', 'set_sky_enabled', 'view', 'witch_space', 'roll_angle', 'climb_angle',
                 'roll_sin', 'roll_cos', 'climb_sin', 'climb_cos', 'speed', 'dust_type',
                 'random_seed', 'scr_base', 'colour_ptr']
        asm = preamble() + sky[sky.index('sky_capacity:'):sky.index('    q_module sky')]
        asm += re.search(r'^outcodes macro.*?^\s*endm', graphics, re.M | re.S).group(0) + '\n'
        asm += '\torg $10000\n\tdc.l ' + ','.join(names) + '\n'
        asm += sky[sky.index('    q_subr init_sky'):]
        asm += '\nreturn: set *\n\trts\n'
        asm += '\n'.join(routine(graphics, n) for n in
                         ['dot_to_addr', 'c_plotxy', 'plotxy', 'mask_plot'])
        asm += '\nset_colour:\n\trts\nmult_by_320:\n\tdc.w '
        asm += ','.join(str(y*320) for y in range(200)) + '\n'
        asm += graphics[graphics.index('\tq_global bit_masks'):graphics.index('clip_list:')]
        cls.code, cls.sym = assemble(asm, names)
        cls.points = []
        pos = cls.sym['sky_catalogue']-CODE
        end = cls.sym['sky_catalogue_end']-CODE
        while pos < end:
            skip = struct.unpack_from('>h', cls.code, pos+10)[0]
            pos += 12
            if skip < 0:
                for offset in range(0, -skip, 6):
                    cls.points.append(struct.unpack_from('>3h', cls.code, pos+offset))
                pos -= skip
        assert len(cls.points) == 1024

    def prepare(self, model=UC_CPU_M68K_M68000 if Uc else 0, screen=SCREEN):
        self.cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(model)
        self.cpu.mem_map(0, 0x100000)
        self.cpu.mem_write(CODE, self.code)
        self.cpu.mem_protect(CODE, (len(self.code)+4095)//4096*4096, UC_PROT_READ | UC_PROT_EXEC)
        self.cpu.mem_write(GUARD, BACKGROUND)
        self.cpu.mem_write(COLOUR, b'\xff'*16)
        self.put('scr_base', screen, 4)
        self.put('colour_ptr', COLOUR, 4)
        self.put('random_seed', 0x187abc13, 4)
        self.call('init_sky')
        self.screen = screen

    def put(self, name, value, size=2):
        self.cpu.mem_write(VARIABLES+self.sym[name], (value & ((1 << (size*8))-1)).to_bytes(size, 'big'))

    def get(self, name, size=2):
        return int.from_bytes(self.cpu.mem_read(VARIABLES+self.sym[name], size), 'big')

    def call(self, name):
        self.cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        self.cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.cpu.reg_write(UC_M68K_REG_A7, STACK-4)
        self.cpu.mem_write(STACK-4, struct.pack('>I', STOP))
        self.cpu.emu_start(self.sym[name], STOP, count=300000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC), STOP, name)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7), STACK, name)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A6), VARIABLES, name)

    def basis(self, matrix):
        self.cpu.mem_write(VARIABLES+self.sym['sky_basis'],
                           struct.pack('>9i', *(round(v*Q) for row in matrix for v in row)))
        self.put('sky_dirty', 0xffff)

    def read_basis(self):
        values = struct.unpack('>9i', self.cpu.mem_read(VARIABLES+self.sym['sky_basis'], 36))
        return [[values[r*3+c]/Q for c in range(3)] for r in range(3)]

    def angles(self, roll, pitch):
        for axis, value in [('roll', roll), ('climb', pitch)]:
            self.put(axis+'_angle', 1 if value else 0)
            self.put(axis+'_sin', round(math.sin(value)*Q), 4)
            self.put(axis+'_cos', round(math.cos(value)*Q), 4)

    def points_on_screen(self):
        count = self.get('sky_count')
        self.assertLessEqual(count, self.sym['sky_capacity'])
        values = struct.unpack('>'+'h'*count*2,
                               self.cpu.mem_read(VARIABLES+self.sym['sky_pixels'], count*4))
        return list(zip(values[::2], values[1::2]))

    def reference(self):
        values = struct.unpack('>9h', self.cpu.mem_read(VARIABLES+self.sym['sky_matrix'], 18))
        rows = [values[i:i+3] for i in range(0, 9, 3)]
        pixels = []
        for p in self.points:
            x, y, z = [sum(a*b for a, b in zip(row, p)) >> 14 for row in rows]
            if z <= 0:
                continue
            x, y = math.trunc(x*512/z), math.trunc(y*512/z)
            if -128 <= x <= 127 and -56 <= y <= 55:
                pixels.append((x, y))
        return pixels

    def test_culling_matches_full_catalogue_in_all_views_and_random_orientations(self):
        rng = random.Random(4510)
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.prepare(model)
            self.assertLessEqual(self.sym['sky_used'], self.sym['sky_vsize']*2)
            for i in range(160):
                self.basis(multiply(rotation(rng.uniform(-math.pi, math.pi), rng.uniform(-math.pi, math.pi)),
                                    rotation(rng.uniform(-math.pi, math.pi), rng.uniform(-math.pi, math.pi))))
                self.put('view', i % 4)
                self.call('draw_sky')
                self.assertCountEqual(self.points_on_screen(), self.reference(), (model, i))
            self.assertEqual(self.get('random_seed', 4), 0x187abc13)

    def test_white_single_pixels_clipping_and_guarded_screens(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for screen in (SCREEN, OTHER):
                self.prepare(model, screen)
                for view in range(4):
                    self.cpu.mem_write(GUARD, BACKGROUND)
                    self.put('view', view)
                    self.call('draw_sky')
                    expected = bytearray(BACKGROUND)
                    paint(expected, ((x+160, 63-y) for x, y in self.reference()), (65535,)*4, screen)
                    self.assertEqual(bytes(self.cpu.mem_read(GUARD, len(BACKGROUND))), expected)

    def test_translation_and_warp_do_not_move_sky_and_cache_avoids_projection(self):
        self.prepare()
        self.call('draw_sky')
        pixels = self.points_on_screen()
        calls = []
        hook = self.cpu.hook_add(UC_HOOK_CODE, lambda cpu, a, size, data: calls.append(a),
                                 begin=self.sym['sky_project'], end=self.sym['sky_project'])
        for speed in (0, 1, 11, 22, 1000):
            self.put('speed', speed)
            self.put('dust_type', speed & 1)
            self.call('advance_sky')
            self.call('draw_sky')
            self.assertEqual(self.points_on_screen(), pixels)
        self.assertFalse(calls)
        self.cpu.hook_del(hook)
        self.put('witch_space', 1)
        self.cpu.mem_write(GUARD, BACKGROUND)
        self.call('draw_sky')
        self.assertEqual(bytes(self.cpu.mem_read(GUARD, len(BACKGROUND))), BACKGROUND)

    def test_rotation_matches_world_order_and_survives_long_turns(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.prepare(model)
            roll, pitch = math.radians(1.6), math.radians(-0.8)
            self.angles(roll, pitch)
            self.call('advance_sky')
            expected = rotation(roll, pitch)
            for actual_row, expected_row in zip(self.read_basis(), expected):
                for actual, target in zip(actual_row, expected_row):
                    self.assertAlmostEqual(actual, target, delta=2e-7)
            for i in range(32768):
                self.call('advance_sky')
            matrix = self.read_basis()
            for i in range(3):
                for j in range(3):
                    self.assertAlmostEqual(sum(a*b for a, b in zip(matrix[i], matrix[j])),
                                           int(i == j), delta=0.0005)
            self.angles(0, 0)
            before = self.read_basis()
            self.call('advance_sky')
            self.assertEqual(before, self.read_basis())

    def test_full_turn_and_view_roundtrip_restore_constellations(self):
        self.prepare()
        self.call('draw_sky')
        original = self.points_on_screen()
        for view in (1, 2, 3, 0):
            self.put('view', view)
            self.call('draw_sky')
        self.assertEqual(self.points_on_screen(), original)
        self.angles(math.tau/720, 0)
        for i in range(720):
            self.call('advance_sky')
        self.call('draw_sky')
        self.assertEqual(len(self.points_on_screen()), len(original))
        for point in original:
            self.assertTrue(any(max(abs(a-b) for a, b in zip(point, p)) <= 1
                                for p in self.points_on_screen()))

    def test_toggle_skips_all_sky_work_and_restarts_only_when_reenabled(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.prepare(model)
            self.assertEqual(self.get('sky_enabled'), 1)
            self.angles(0.04, -0.02)
            self.call('advance_sky')
            self.call('draw_sky')
            start = VARIABLES+self.sym['sky_vars']
            size = self.sym['sky_vsize']*2
            rotated = bytes(self.cpu.mem_read(start, size))
            self.cpu.reg_write(UC_M68K_REG_D0, 1)
            self.call('set_sky_enabled')
            self.assertEqual(bytes(self.cpu.mem_read(start, size)), rotated)
            self.cpu.reg_write(UC_M68K_REG_D0, 0)
            self.call('set_sky_enabled')
            self.assertEqual(self.get('sky_enabled'), 0)
            disabled = bytes(self.cpu.mem_read(start, size))
            self.cpu.mem_write(GUARD, BACKGROUND)
            instructions = []
            hook = self.cpu.hook_add(UC_HOOK_CODE,
                lambda cpu, address, size, data: instructions.append(address))
            for view in range(4):
                self.put('view', view)
                for name in ('advance_sky', 'draw_sky'):
                    instructions.clear()
                    self.call(name)
                    self.assertTrue(instructions)
                    self.assertLessEqual(len(instructions), 3, (model, name))
                    self.assertTrue(all(self.sym[name] <= pc < self.sym[name]+8 for pc in instructions))
                    self.assertEqual(bytes(self.cpu.mem_read(start, size)), disabled)
                    self.assertEqual(bytes(self.cpu.mem_read(GUARD, len(BACKGROUND))), BACKGROUND)
            self.cpu.hook_del(hook)
            self.assertEqual(self.get('random_seed', 4), 0x187abc13)
            self.cpu.reg_write(UC_M68K_REG_D0, 1)
            self.call('set_sky_enabled')
            self.assertEqual(self.get('sky_enabled'), 1)
            self.assertEqual(self.read_basis(), [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
            self.assertEqual(self.get('sky_count'), 0)
            self.assertEqual(self.get('sky_view'), 65535)
            self.assertNotEqual(self.get('sky_dirty'), 0)
            self.call('draw_sky')
            self.assertCountEqual(self.points_on_screen(), self.reference())
            self.assertTrue(self.points_on_screen())

    def test_misjump_hides_sky_even_when_toggled_on(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.prepare(model)
            self.put('witch_space', 1)
            for enabled in (0, 1):
                self.cpu.reg_write(UC_M68K_REG_D0, enabled)
                self.call('set_sky_enabled')
                for view in range(4):
                    self.put('view', view)
                    self.call('draw_sky')
                    self.assertEqual(bytes(self.cpu.mem_read(GUARD, len(BACKGROUND))), BACKGROUND)
            self.put('witch_space', 0)
            self.call('draw_sky')
            self.assertNotEqual(bytes(self.cpu.mem_read(GUARD, len(BACKGROUND))), BACKGROUND)

    def test_public_routines_preserve_registers_and_private_workspace(self):
        self.prepare()
        self.angles(0.04, -0.02)
        for name in ('init_sky', 'set_sky_enabled', 'advance_sky', 'draw_sky'):
            regs = [UC_M68K_REG_D0+i for i in range(8)] + [UC_M68K_REG_A0+i for i in range(6)]
            values = {reg: 0x12345670+i for i, reg in enumerate(regs)}
            for reg, value in values.items():
                self.cpu.reg_write(reg, value)
            start = VARIABLES+self.sym['sky_vars']
            self.cpu.mem_write(start-16, b'\xa5'*16)
            self.cpu.mem_write(start+self.sym['sky_vsize']*2, b'\x5a'*16)
            self.call(name)
            for reg, value in values.items():
                self.assertEqual(self.cpu.reg_read(reg), value, (name, reg))
            self.assertEqual(bytes(self.cpu.mem_read(start-16, 16)), b'\xa5'*16)
            self.assertEqual(bytes(self.cpu.mem_read(start+self.sym['sky_vsize']*2, 16)), b'\x5a'*16)


if __name__ == '__main__':
    unittest.main()
