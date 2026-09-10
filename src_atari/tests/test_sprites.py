"""Check real Atari sprite code and assets on MC68000/MC68020 with read-only code.

Unicorn does not model an instruction cache. Write protection verifies that
sprite drawing never patches executable instructions and needs no cache flush.
Optional dependency: unicorn==2.1.4.
"""
from pathlib import Path
import random
import re
import struct
import subprocess
import tempfile
import unittest

try:
    from unicorn import (Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN,
                         UC_PROT_READ, UC_PROT_EXEC)
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_A4, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_PC, UC_M68K_REG_SR)
except ImportError:
    Uc = None

ROOT = Path(__file__).resolve().parents[1]
CODE, STOP, VARIABLES, RECORD, DATA, SAVE, STACK = 0x10000, 0x1000, 0x30000, 0x38000, 0x40000, 0x45000, 0x90000
SCREEN, OTHER, GUARD = 0x4f020, 0x57020, 0x4f000
BACKGROUND = random.Random(68020).randbytes(0x10100)


def routine(source, name):
    return re.search(r'^\s*q_subr ' + name + r'(?:,global)?\s*\n(.*?)'
                     r'(?=^\s*q_subr |\Z)', source, re.M | re.S).group(0)


def paint(buffer, data, x, y, screen, clip):
    width, height = struct.unpack_from('>2H', data)
    left, right, top, bottom = clip
    for sy in range(height):
        for sx in range(width * 16):
            dx, dy = x + sx, y + sy
            if not (left <= dx <= right and top <= dy <= bottom):
                continue
            words = struct.unpack_from('>5H', data, 4 + (sy * width + sx // 16) * 10)
            source_mask, dest_mask = 0x8000 >> (sx & 15), 0x80 >> (dx & 7)
            for plane in range(4):
                offset = screen - GUARD + dy * 160 + (dx // 16) * 8 + plane * 2 + (dx & 15) // 8
                if not words[0] & source_mask:
                    buffer[offset] &= 255 ^ dest_mask
                if words[plane + 1] & source_mask:
                    buffer[offset] |= dest_mask


@unittest.skipIf(Uc is None, 'optional sprite tests require unicorn==2.1.4')
class SpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / 'build').mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix='test-sprites-', dir=ROOT / 'build')
        cls.addClassCleanup(cls.temp.cleanup)
        directory = Path(cls.temp.name)
        source = (ROOT / 'asm/sprites.m68').read_text()
        source = re.sub(r'^\s*xref[^\n]*', '', source, flags=re.M)
        source = source.replace('\tq_module sprites', '')
        names = ['draw_sprite', 'remove_sprite', 'scr_base', 'sp_flags', 'sp_xpos',
                 'data_ptr', 'buffer_ptr', 'clip_left', 'var_size', 'bit_on', 'bit_digits',
                 'empty_defn', 'installed_defn', 'active_defn', 'locked_defn', 'icon_draw_data']
        assembly = '\torg $10000\n\tdc.l ' + ','.join(names) + '\n'
        assembly += source + '\n' + routine((ROOT / 'asm/graphics.m68').read_text(), 'dot_to_addr')
        assembly += '\nmult_by_320:\n\tdc.w ' + ','.join(str(y * 320) for y in range(200)) + '\n'
        cockpit = (ROOT / 'asm/cockpit.m68').read_text()
        assembly += cockpit[cockpit.index('* Missile - not installed.'):cockpit.index('* Laser sight information.')]
        options = (ROOT / 'asm/options.m68').read_text()
        assembly += '\tinclude "bitlist.m68"\nicon_y equ text_top+8\n'
        assembly += options[options.index('icon_draw_data:'):options.index('* Highlight coordinate table.')]
        path, binary = directory / 'sprites.s', directory / 'sprites.bin'
        path.write_text(assembly)
        result = subprocess.run([str(ROOT.parent / 'tools/vasmm68k_mot.exe'),
            '-m68000', '-Fbin', '-no-opt', '-align', '-allmp', '-spaces', '-nocase',
            '-I' + str(ROOT / 'asm'), '-o', str(binary), str(path)],
            cwd=directory, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.code = binary.read_bytes()
        cls.symbols = dict(zip(names, struct.unpack_from('>' + 'I' * len(names), cls.code)))

    def start_cpu(self, model):
        self.cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(model)
        self.cpu.mem_map(0, 0x100000)
        self.cpu.mem_write(CODE, self.code)
        self.cpu.mem_protect(CODE, 0x10000, UC_PROT_READ | UC_PROT_EXEC)

    def asset(self, index):
        bank = (ROOT / 'assets/BITMAPS.IMG').read_bytes()
        offset = struct.unpack_from('>I', bank, index * 4)[0]
        width, height = struct.unpack_from('>2H', bank, offset)
        data = bytearray(struct.pack('>2H', width, height))
        for column in range(width * height):
            planes = struct.unpack_from('>4H', bank, offset + 4 + column * 8)
            data.extend(struct.pack('>5H', 0xffff ^ (planes[0] | planes[1] | planes[2] | planes[3]), *planes))
        return bytes(data)

    def missile(self, name):
        return self.code[self.symbols[name] - CODE:self.symbols[name] - CODE + 64]

    def run_code(self, name):
        self.cpu.reg_write(UC_M68K_REG_SR, 0x2000)
        self.cpu.reg_write(UC_M68K_REG_A4, RECORD)
        self.cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.cpu.reg_write(UC_M68K_REG_A7, STACK - 4)
        self.cpu.mem_write(STACK - 4, struct.pack('>I', STOP))
        self.cpu.emu_start(self.symbols[name], STOP, count=1000000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC), STOP)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7), STACK)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A6), VARIABLES)

    def check_sprite(self, data, x, y, screen=SCREEN, clip=(0, 319, 0, 199), save=False):
        self.cpu.mem_write(GUARD, BACKGROUND)
        self.cpu.mem_write(VARIABLES, bytes(self.symbols['var_size']))
        self.cpu.mem_write(RECORD, bytes(64))
        self.cpu.mem_write(DATA, data)
        self.cpu.mem_write(VARIABLES + self.symbols['scr_base'], struct.pack('>I', screen))
        for name, value in [('data_ptr', DATA), ('buffer_ptr', SAVE)]:
            self.cpu.mem_write(RECORD + self.symbols[name], struct.pack('>I', value))
        self.cpu.mem_write(RECORD + self.symbols['sp_flags'], struct.pack('>H', (1 | (0 if save else 8)) << 8))
        self.cpu.mem_write(RECORD + self.symbols['sp_xpos'], struct.pack('>hh', x, y))
        self.cpu.mem_write(RECORD + self.symbols['clip_left'], struct.pack('>4h', *clip))
        expected = bytearray(BACKGROUND)
        paint(expected, data, x, y, screen, clip)
        self.run_code('draw_sprite')
        self.assertEqual(self.cpu.mem_read(GUARD, len(BACKGROUND)), expected)
        if save:
            self.run_code('remove_sprite')
            self.assertEqual(self.cpu.mem_read(GUARD, len(BACKGROUND)), BACKGROUND)

    def test_options_and_missiles_at_their_actual_positions_with_read_only_code(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.start_cpu(model)
            offset = self.symbols['icon_draw_data'] - CODE
            while True:
                index = struct.unpack_from('>h', self.code, offset)[0]
                if index < 0:
                    break
                index, x, y = struct.unpack_from('>3h', self.code, offset)
                with self.subTest(model=model, bitmap=index, x=x, y=y):
                    self.check_sprite(self.asset(index), x, y)
                offset += 6
            for name in ('empty_defn', 'installed_defn', 'active_defn', 'locked_defn'):
                for x in (43, 59, 75, 91):
                    with self.subTest(model=model, missile=name, x=x):
                        self.check_sprite(self.missile(name), x, 186)

    def test_all_shifts_both_screens_and_background_restore(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.start_cpu(model)
            for index in (self.symbols['bit_on'], self.symbols['bit_digits'] + 1):
                for shift in range(16):
                    for screen in (SCREEN, OTHER):
                        with self.subTest(model=model, bitmap=index, shift=shift, screen=screen):
                            self.check_sprite(self.asset(index), 112 + shift, 89, screen, save=True)

    def test_clipped_sprites_all_shifts_edges_and_background_restore(self):
        clip = (80, 129, 80, 99)
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.start_cpu(model)
            for shift in range(16):
                for x, y in [(48 + shift, 76), (112 + shift, 92), (48 + shift, 90),
                             (80 + shift, 75), (80 + shift, 92), (-64 + shift, 80)]:
                    with self.subTest(model=model, x=x, y=y):
                        self.check_sprite(self.asset(self.symbols['bit_on']), x, y, clip=clip, save=True)


if __name__ == '__main__':
    unittest.main()
