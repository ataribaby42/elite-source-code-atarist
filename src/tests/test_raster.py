"""Execute the Atari MC68000 raster routines against a pixel reference.

Optional test dependency: unicorn==2.1.4. The game build does not need it.
"""
from pathlib import Path
import random
import re
import struct
import subprocess
import tempfile
import unittest

try:
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_M68K_REG_A0,
        UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D7,
        UC_M68K_REG_PC, UC_M68K_REG_SR)
except ImportError:
    Uc = None

ROOT = Path(__file__).resolve().parents[1]
CODE, STOP, VARIABLES, STACK = 0x10000, 0x1000, 0x30000, 0x90000
# Two screen buffers, with guard bytes before and after them.
SCREEN, OTHER, GUARD = 0x40000, 0x48000, 0x3ffe0
BACKGROUND = random.Random(68000).randbytes(0x10100)
COLOUR = 0x32000


def routine(source, name):
    return re.search(r'^\s*q_subr ' + name + r'(?:,global)?\s*\n(.*?)'
                     r'(?=^\s*q_subr |\Z)', source, re.M | re.S).group(0)


def pixels(x0, y0, x1, y1):
    """Inclusive Bresenham endpoints, with the game's half-error tie rule."""
    if y1 < y0:
        x0, y0, x1, y1 = x1, y1, x0, y0
    dx, dy = abs(x1 - x0), y1 - y0
    step = 1 if x1 >= x0 else -1
    major, minor = max(dx, dy), min(dx, dy)
    error = major // 2
    for _ in range(major + 1):
        yield x0, y0
        if dx >= dy:
            x0 += step
        else:
            y0 += 1
        error -= minor
        if error < 0:
            error += major
            if dx >= dy:
                y0 += 1
            else:
                x0 += step


def paint(buffer, points, colour, screen=SCREEN):
    for x, y in points:
        mask = 0x80 >> (x & 7)
        for plane in range(4):
            offset = screen - GUARD + y * 160 + (x // 16) * 8 + plane * 2 + (x & 15) // 8
            if colour[plane] & (0x8000 >> (x & 15)):
                buffer[offset] |= mask
            else:
                buffer[offset] &= 255 ^ mask


@unittest.skipIf(Uc is None, 'optional raster tests require unicorn==2.1.4')
class RasterTests(unittest.TestCase):
    source_dir = ROOT / 'asm'

    @classmethod
    def setUpClass(cls):
        (ROOT / 'build').mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix='test-raster-', dir=ROOT / 'build')
        cls.addClassCleanup(cls.temp.cleanup)
        directory = Path(cls.temp.name)
        source = (cls.source_dir / 'graphics.m68').read_text()
        names = ['dot_to_addr', 'clear_image', 'line', 'horiz_line', 'vert_line', 'mask_plot']
        constants = ['scr_base', 'colour_ptr', 'flyback', 'frame_count', 'next_record']
        assembly = '\tinclude "common.def"\n\tinclude "macros.m68"\n\torg $10000\n'
        assembly += '\tdc.l ' + ','.join(names + constants) + '\n'
        assembly += '\n'.join(routine(source, name) for name in names)
        assembly += source[source.index('\tq_global bit_masks'):source.index('clip_list:')]
        assembly += '\nmult_by_320:\n\tdc.w ' + ','.join(str(y * 320) for y in range(200)) + '\n'
        path, binary = directory / 'raster.s', directory / 'raster.bin'
        path.write_text(assembly)
        command = [str(ROOT.parent / 'tools/vasmm68k_mot.exe'), '-m68000', '-Fbin',
                   '-no-opt', '-align', '-allmp', '-spaces', '-nocase',
                   '-I' + str(directory), '-I' + str(ROOT / 'asm'),
                   '-o', str(binary), str(path)]
        result = subprocess.run(command, cwd=directory, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.code = binary.read_bytes()
        values = struct.unpack_from('>' + 'I' * (len(names) + len(constants)), cls.code)
        cls.symbols = dict(zip(names + constants, values))
        vector = (ROOT / 'asm/vector.m68').read_text().split('panel_colours:', 1)[1]
        cls.colours = [tuple(int(word, 16) for word in row) for row in
                       re.findall(r'dc.w \$(\w{4}),\$(\w{4}),\$(\w{4}),\$(\w{4})', vector)]
        cls.colours += [tuple(0xffff if col & (1 << p) else 0 for p in range(4))
                        for col in range(16)]

    def setUp(self):
        self.cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(UC_CPU_M68K_M68000)
        self.cpu.mem_map(0, 0x100000)
        self.cpu.mem_write(CODE, self.code)

    def run_routine(self, name, registers=(), colour=(0, 0, 0, 0), screen=SCREEN, flyback=1):
        cpu = self.cpu
        cpu.mem_write(GUARD, BACKGROUND)
        cpu.mem_write(VARIABLES, bytes(0x2000))
        cpu.mem_write(COLOUR, struct.pack('>4H', *colour))
        for symbol, value in [('scr_base', screen), ('colour_ptr', COLOUR)]:
            cpu.mem_write(VARIABLES + self.symbols[symbol], struct.pack('>I', value))
        cpu.mem_write(VARIABLES + self.symbols['flyback'], struct.pack('>H', flyback))
        cpu.mem_write(VARIABLES + self.symbols['frame_count'], struct.pack('>H', 7))
        cpu.mem_write(VARIABLES + self.symbols['next_record'], struct.pack('>I', 0x12345678))
        cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        for register in range(UC_M68K_REG_A0, UC_M68K_REG_D7 + 1):
            cpu.reg_write(register, 0x5a5a0000 + register)
        cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        cpu.reg_write(UC_M68K_REG_A7, STACK - 4)
        cpu.mem_write(STACK - 4, struct.pack('>I', STOP))
        for index, value in enumerate(registers):
            cpu.reg_write(UC_M68K_REG_D0 + index, value)
        cpu.emu_start(self.symbols[name], STOP, count=1000000)
        self.assertEqual(cpu.reg_read(UC_M68K_REG_PC), STOP, 'routine did not return')
        self.assertEqual(cpu.reg_read(UC_M68K_REG_A7), STACK, 'unbalanced stack')
        self.assertEqual(cpu.reg_read(UC_M68K_REG_A6), VARIABLES)
        self.assertEqual(cpu.reg_read(UC_M68K_REG_A0 + 5), 0x5a5a0006)
        if name == 'line':
            self.assertEqual(cpu.reg_read(UC_M68K_REG_D7), 0x5a5a0010)
            self.assertEqual(cpu.reg_read(UC_M68K_REG_A0 + 4), 0x5a5a0005)
        if name == 'clear_image':
            for index in range(2, 5):
                self.assertEqual(cpu.reg_read(UC_M68K_REG_A0 + index), 0x5a5a0001 + index)
        return cpu.mem_read(GUARD, len(BACKGROUND))

    def test_clear_changes_only_the_viewport(self):
        for screen in (SCREEN, OTHER):
            with self.subTest(screen=screen):
                expected = bytearray(BACKGROUND)
                paint(expected, ((x, y) for y in range(8, 120) for x in range(32, 288)),
                      (0, 0, 0, 0), screen)
                self.assertEqual(self.run_routine('clear_image', screen=screen), expected)
                for symbol, length in [('frame_count', 2), ('next_record', 4)]:
                    self.assertEqual(self.cpu.mem_read(VARIABLES + self.symbols[symbol], length),
                                     bytes(length))
                self.assertEqual(self.cpu.mem_read(VARIABLES + self.symbols['flyback'], 2), b'\0\1')

    def test_clear_waits_for_flyback(self):
        visits = []

        def signal_flyback(cpu, address, size, data):
            visits.append(address)
            self.assertEqual(cpu.mem_read(GUARD, len(BACKGROUND)), BACKGROUND)
            self.assertEqual(cpu.mem_read(VARIABLES + self.symbols['frame_count'], 2), b'\0\7')
            self.assertEqual(cpu.mem_read(VARIABLES + self.symbols['next_record'], 4),
                             bytes.fromhex('12345678'))
            if len(visits) == 3:
                cpu.mem_write(VARIABLES + self.symbols['flyback'], b'\0\1')

        entry = self.symbols['clear_image']
        hook = self.cpu.hook_add(UC_HOOK_CODE, signal_flyback, begin=entry, end=entry)
        self.addCleanup(self.cpu.hook_del, hook)
        expected = bytearray(BACKGROUND)
        paint(expected, ((x, y) for y in range(8, 120) for x in range(32, 288)), (0, 0, 0, 0))
        self.assertEqual(self.run_routine('clear_image', flyback=0), expected)
        self.assertEqual(len(visits), 3)

    def test_all_line_directions_colours_and_word_edges(self):
        cases = [(32, 8, 287, 23), (287, 8, 32, 23), (15, 0, 16, 199),
                 (16, 0, 15, 199), (0, 0, 199, 199), (319, 0, 120, 199),
                 (15, 9, 16, 10), (16, 9, 15, 10), (0, 199, 319, 199),
                 (3, 8, 301, 8), (15, 0, 15, 199), (16, 0, 16, 199),
                 (319, 199, 319, 199), (0, 0, 0, 0), (1, 9, 14, 9)]
        cases += [(c, d, a, b) for a, b, c, d in cases]
        for colour in self.colours:
            for case in cases:
                with self.subTest(colour=colour, line=case):
                    expected = bytearray(BACKGROUND)
                    paint(expected, pixels(*case), colour)
                    self.assertEqual(self.run_routine('line', case, colour), expected)

    def test_horizontal_masks_at_every_bit_offset(self):
        colours = [(0, 0, 0, 0), (65535, 65535, 65535, 65535),
                   (0x5555, 0xaaaa, 0x1234, 0x8765), (0xaaaa, 0x5555, 0xf00f, 0x0ff0),
                   (65535, 0, 65535, 0), (0, 65535, 0, 65535)]
        for colour in colours:
            for x in range(16):
                for width in (1, 2, 15, 16, 17, 31, 32, 33):
                    y = 199 if x & 1 else 0
                    case = (x, y, x + width - 1, y)
                    with self.subTest(colour=colour, line=case):
                        expected = bytearray(BACKGROUND)
                        paint(expected, pixels(*case), colour)
                        self.assertEqual(self.run_routine('line', case, colour), expected)

    def test_random_lines_on_both_buffers(self):
        rng = random.Random(0x68000)
        for _ in range(300):
            case = (rng.randrange(320), rng.randrange(200),
                    rng.randrange(320), rng.randrange(200))
            colour = tuple(rng.randrange(65536) for _ in range(4))
            screen = rng.choice([SCREEN, OTHER])
            expected = bytearray(BACKGROUND)
            paint(expected, pixels(*case), colour, screen)
            self.assertEqual(self.run_routine('line', case, colour, screen), expected)


if __name__ == '__main__':
    unittest.main()
