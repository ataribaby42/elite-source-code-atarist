"""Check full viewport coverage and clipping in the actual MC68000 routines.

The optional CPU tests require unicorn==2.1.4.
"""
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from test_raster import BACKGROUND, GUARD, SCREEN, OTHER, paint, pixels, routine

try:
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_M68K_REG_A0,
        UC_M68K_REG_A3, UC_M68K_REG_A4, UC_M68K_REG_A5, UC_M68K_REG_A6,
        UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_PC, UC_M68K_REG_SR)
except ImportError:
    Uc = None

CODE, STOP, VARIABLES, COLOUR, NODES, STACK = 0x10000, 0x1000, 0x30000, 0x32000, 0x68000, 0x90000
SOLID = (65535,) * 4


def assemble(assembly, symbols):
    (ROOT / 'build').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='test-viewport-', dir=ROOT / 'build') as temporary:
        directory = Path(temporary)
        source, binary = directory / 'viewport.s', directory / 'viewport.bin'
        source.write_text(assembly)
        result = subprocess.run([
            str(ROOT.parent / 'tools/vasmm68k_mot.exe'), '-m68000', '-Fbin',
            '-no-opt', '-align', '-allmp', '-spaces', '-nocase',
            '-I' + str(ROOT / 'asm'), '-o', str(binary), str(source)],
            cwd=directory, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        code = binary.read_bytes()
    return code, dict(zip(symbols, struct.unpack_from('>' + 'I' * len(symbols), code)))


def preamble():
    return 'amiga_implementation equ 1\namiga_workspace_implementation equ 1\n' \
           'fileio_implementation equ 1\n\tinclude "common.def"\n' \
           '\tinclude "macros.m68"\n\tinclude "raster.inc"\n'


def variable_block(source, name):
    return re.search(r'^\s*q_vars ' + name + r'.*?^\s*q_end_vars ' + name,
                     source, re.M | re.S).group(0) + '\n'


def circle_pixels(cx, cy, radius, flare):
    """Filled midpoint circle, clipped after optional one-pixel sun flares."""
    x, y, error = 0, radius, 3 - 2 * radius
    points = set()
    while x <= y:
        for half_width, offset in ((y, x), (x, y)):
            for row in {cy - offset, cy + offset}:
                if -56 <= row <= 55:
                    points.update((column + 160, 63 - row) for column in
                                  range(max(-128, cx - half_width - flare),
                                        min(127, cx + half_width + flare) + 1))
        if error < 0:
            error += 4 * x + 6
        else:
            error += 4 * (x - y) + 10
            y -= 1
        x += 1
    return points


@unittest.skipIf(Uc is None, 'optional viewport tests require unicorn==2.1.4')
class ViewportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT / 'asm/graphics.m68').read_text()
        names = ['dot_to_addr', 'clear_image', 'c_line', 'line', 'horiz_line',
                 'vert_line', 'mask_plot', 'circle', 'circle_plotxy', 'circle_horiz',
                 'solid_polygon', 'c_solid_polygon', 'clip_edge', 'output_intersect',
                 'output_vertex', 'add_vertex', 'intersect_top', 'intersect_bottom',
                 'intersect_left', 'intersect_right']
        constants = ['scr_base', 'colour_ptr', 'flyback', 'sun_flare', 'flare', 'flare_count',
                     'poly_min_y', 'poly_max_y', 'poly_x', 'poly_y', 'top_ptr',
                     'node_len', 'nflags', 'scr_x', 'scr_y', 'prev', 'next', 'clip_panel',
                     'edge_masks', 'random_value']
        assembly = preamble() + 'max_vert equ 15\n'
        assembly += variable_block(source, 'graphics')
        assembly += re.search(r'^outcodes macro.*?^\s*endm', source, re.M | re.S).group(0) + '\n'
        assembly += '\torg $10000\n\tdc.l ' + ','.join(names + constants) + '\n'
        assembly += '\n'.join(routine(source, name) for name in names)
        assembly += source[source.index('\tq_global bit_masks'):]
        # RANDOM's documented scratch registers are D0 and D1.
        assembly += ('\nrandom:\n\tmove.l random_value(pc),d0\n\tmoveq #-1,d1\n\trts\n'
                     'random_value:\n\tdc.l -1\namiga_poll:\n\trts\n'
                     'left_arm equ $70000\nright_arm equ $71000\nmult_by_320:\n\tdc.w ')
        assembly += ','.join(str(y * 320) for y in range(200)) + '\n'
        cls.code, cls.symbols = assemble(assembly, names + constants)

    def setUp(self):
        self.cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(UC_CPU_M68K_M68000)
        self.cpu.mem_map(0, 0x100000)
        self.cpu.mem_write(CODE, self.code)

    def word(self, address, value):
        self.cpu.mem_write(address, struct.pack('>H', value & 65535))

    def long(self, address, value):
        self.cpu.mem_write(address, struct.pack('>I', value & 0xffffffff))

    def prepare(self, screen=SCREEN, sun=False, flare=True):
        self.cpu.mem_write(GUARD, BACKGROUND)
        self.cpu.mem_write(VARIABLES, bytes(0x2000))
        self.cpu.mem_write(COLOUR, b'\xff' * 16)
        for name, value in [('scr_base', screen), ('colour_ptr', COLOUR)]:
            self.long(VARIABLES + self.symbols[name], value)
        for name, value in [('flyback', 1), ('sun_flare', int(sun)),
                            ('flare', 65535 if flare else 0), ('flare_count', 1)]:
            self.word(VARIABLES + self.symbols[name], value)
        self.long(self.symbols['random_value'], 0xffffffff if flare else 0)
        self.cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        self.cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.cpu.reg_write(UC_M68K_REG_A4, self.symbols['edge_masks'])

    def call(self, name, registers=()):
        self.cpu.reg_write(UC_M68K_REG_A7, STACK - 4)
        self.long(STACK - 4, STOP)
        for index, value in enumerate(registers):
            self.cpu.reg_write(UC_M68K_REG_D0 + index, value & 0xffffffff)
        self.cpu.emu_start(self.symbols[name], STOP, count=2000000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC), STOP)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7), STACK)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A6), VARIABLES)
        return self.cpu.mem_read(GUARD, len(BACKGROUND))

    def expected(self, points, screen=SCREEN):
        expected = bytearray(BACKGROUND)
        paint(expected, points, SOLID, screen)
        return expected

    def test_clipped_lines_reach_all_four_edges(self):
        cases = [(-1000, y, 1000, y, (32, 63-y, 287, 63-y)) for y in (-56, 0, 55)]
        cases += [(x, -1000, x, 1000, (x+160, 8, x+160, 119)) for x in (-128, 0, 127)]
        cases += [(x, y, x, y, (x+160, 63-y, x+160, 63-y))
                  for x in (-128, 127) for y in (-56, 55)]
        for screen in (SCREEN, OTHER):
            for x0, y0, x1, y1, expected_line in cases:
                for reverse in (False, True):
                    line = (x1, y1, x0, y0) if reverse else (x0, y0, x1, y1)
                    with self.subTest(screen=screen, line=line):
                        self.prepare(screen)
                        self.assertEqual(self.call('c_line', line),
                                         self.expected(pixels(*expected_line), screen))

    def test_clipped_solid_polygon_fills_the_whole_viewport(self):
        for screen in (SCREEN, OTHER):
            self.prepare(screen)
            coords = [(-1000, 500), (1000, 500), (1000, -500), (-1000, -500)]
            for index, (x, y) in enumerate(coords):
                address = NODES + index * self.symbols['node_len']
                for name, value in [('scr_x', x), ('scr_y', y),
                                    ('nflags', ((1 if x < -128 else 2) |
                                                (4 if y < -56 else 8)) << 8)]:
                    self.word(address + self.symbols[name], value)
                for name, neighbor in [('prev', (index-1) % 4), ('next', (index+1) % 4)]:
                    self.long(address + self.symbols[name],
                              NODES + neighbor * self.symbols['node_len'])
            self.word(VARIABLES + self.symbols['poly_min_y'], -500)
            self.word(VARIABLES + self.symbols['poly_max_y'], 500)
            self.word(VARIABLES + self.symbols['clip_panel'], 0x0f00)
            self.long(VARIABLES + self.symbols['top_ptr'], NODES)
            self.cpu.reg_write(UC_M68K_REG_A4, NODES)
            self.cpu.reg_write(UC_M68K_REG_A3, NODES + 3 * self.symbols['node_len'])
            self.assertEqual(self.call('c_solid_polygon'),
                             self.expected(((x, y) for y in range(8, 120)
                                            for x in range(32, 288)), screen))

    def test_planets_and_sun_match_clipped_circle_reference(self):
        cases = [(0, 0, 300), (-200, 0, 150), (200, 0, 150), (0, 100, 120),
                 (0, -100, 120), (-129, 0, 0), (128, 0, 0), (-500, 0, 20),
                 (500, 0, 20), (-128, 55, 12), (127, -56, 12)]
        for screen in (SCREEN, OTHER):
            for sun, flare in ((False, False), (True, False), (True, True)):
                for x, y, radius in cases:
                    with self.subTest(screen=screen, sun=sun, flare=flare, circle=(x, y, radius)):
                        self.prepare(screen, sun, flare)
                        self.assertEqual(self.call('circle', (0, 0, 0, 0, 0, x, y, radius)),
                                         self.expected(circle_pixels(x, y, radius, int(sun and flare)), screen))

    def test_circle_spans_clip_after_flare_without_touching_cockpit(self):
        spans = [(-1000, 1000), (-128, -128), (127, 127), (-129, -129),
                 (128, 128), (-500, -200), (200, 500), (-128, 40000), (-40000, 127)]
        for sun, flare in ((False, False), (True, False), (True, True)):
            for left, right in spans:
                with self.subTest(sun=sun, flare=flare, span=(left, right)):
                    self.prepare(sun=sun, flare=flare)
                    grow = int(sun and flare)
                    points = ((x+160, 63) for x in range(max(-128, left-grow),
                                                         min(127, right+grow)+1))
                    self.assertEqual(self.call('circle_horiz', (right, 0, left)),
                                     self.expected(points))

    def test_circle_plot_preserves_large_horizontal_ends_on_both_rows(self):
        for center, offset in ((20000, 20100), (-20000, 20100)):
            for sun in (False, True):
                self.prepare(sun=sun)
                self.word(VARIABLES + self.symbols['poly_x'], center)
                self.word(VARIABLES + self.symbols['poly_y'], 0)
                points = ((x+160, 63-y) for y in (-5, 5) for x in
                          range(max(-128, center-offset-int(sun)),
                                min(127, center+offset+int(sun))+1))
                self.assertEqual(self.call('circle_plotxy', (0, 0, 0, 0, 0, offset, 5)),
                                 self.expected(points))


if __name__ == '__main__':
    unittest.main()
