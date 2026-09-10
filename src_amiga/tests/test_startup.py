"""Execute native title loading and display startup on an emulated MC68000.

OS calls are stubbed; this does not emulate Copper timing or AmigaDOS.
Optional dependency: unicorn==2.1.4, as used by the raster tests.
"""
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import unittest

try:
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
    from unicorn.m68k_const import (UC_CPU_M68K_M68000,
        UC_M68K_REG_A1, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_D0,
        UC_M68K_REG_D1, UC_M68K_REG_D2, UC_M68K_REG_PC, UC_M68K_REG_SR)
except ImportError:
    Uc = None

ROOT = Path(__file__).resolve().parents[1]
CODE, STOP, EXEC, VARIABLES, STACK = 0x10000, 0x1000, 0x20000, 0x30000, 0x90000
SCREEN, OTHER = 0x4f020, 0x57020


def routine(source, name):
    return re.search(r'^\s*q_subr ' + name + r'(?:,global)?\s*\n(.*?)'
                     r'(?=^\s*q_subr |\Z)', source, re.M | re.S).group(0)


def decode_title(data):
    """Elite DEGAS packets contain count+1 literals or 1-count repeats."""
    result = bytearray()
    pos = 34
    while len(result) < 32000:
        count = struct.unpack_from('b', data, pos)[0]
        pos += 1
        if count >= 0:
            result.extend(data[pos:pos + count + 1])
            pos += count + 1
        else:
            result.extend(data[pos:pos + 1] * (1 - count))
            pos += 1
    if len(result) != 32000:
        raise ValueError('Title packets exceed the screen')
    return bytes(result)


@unittest.skipIf(Uc is None, 'optional startup tests require unicorn==2.1.4')
class StartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / 'build').mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix='test-startup-', dir=ROOT / 'build')
        cls.addClassCleanup(cls.temp.cleanup)
        directory = Path(cls.temp.name)
        system = (ROOT / 'asm/system.m68').read_text()
        # Flatten the real system module into a test image; external services
        # are replaced below, while all display/input startup code stays intact.
        system = re.sub(r'^\s*(?:xref|section)\b[^\n]*', '', system, flags=re.M)
        init = (ROOT / 'asm/init.m68').read_text()
        graphics = (ROOT / 'asm/graphics.m68').read_text()
        names = ['show_title', 'amiga_install', 'amiga_start_display', 'amiga_vblank',
                 'palette', 'copper', 'copper_planes', 'display_front', 'display_pending',
                 'ready', 'amiga_active', 'frclock', 'exec_base', 'vblank_server',
                 'file_open', 'file_read', 'file_close', 'game_ticks', 'var_size']
        assembly = ('amiga_workspace_implementation equ 1\nfileio_implementation equ 1\n'
                    '\torg $10000\n\tdc.l ' + ','.join(names) + '\n' + system)
        assembly += re.search(r'^load_file macro.*?^\s*endm', init, re.M | re.S).group(0)
        assembly += '\n' + routine(init, 'show_title') + routine(init, 'read_file')
        assembly += routine(graphics, 'draw_screen')
        assembly += ('\nelite:\nquiet:\nkey_change:\nfile_open:\nfile_read:\nfile_close:\n'
                     '\trts\nvblank:\n\taddq.l #1,game_ticks\n\trts\n'
                     'game_ticks: dc.l 0\nactive_files: dcb.l 8,0\ndirectory_lock: dc.l 0\n'
                     'title_file: dc.b "title.pc1",0\n'
                     f'vars equ ${VARIABLES:x}\namiga_primary equ ${SCREEN:x}\n'
                     f'other_screen equ ${OTHER:x}\n')
        # Each file service needs its own hook address.
        assembly = assembly.replace('file_open:\nfile_read:\nfile_close:',
                                    'file_open:\n\trts\nfile_read:\n\trts\nfile_close:')
        source, binary = directory / 'startup.s', directory / 'startup.bin'
        source.write_text(assembly)
        result = subprocess.run([str(ROOT.parent / 'tools/vasmm68k_mot.exe'),
            '-m68000', '-Fbin', '-no-opt', '-align', '-allmp', '-spaces', '-nocase',
            '-I' + str(ROOT / 'asm'), '-o', str(binary), str(source)],
            cwd=directory, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.code = binary.read_bytes()
        cls.symbols = dict(zip(names, struct.unpack_from('>' + 'I' * len(names), cls.code)))
        cls.title = (ROOT / 'assets/TITLE.PC1').read_bytes()

    def setUp(self):
        self.cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(UC_CPU_M68K_M68000)
        self.cpu.mem_map(0, 0x100000)
        self.cpu.mem_map(0xbfe000, 0x1000)
        self.cpu.mem_map(0xdff000, 0x1000)
        self.cpu.mem_write(CODE, self.code)
        self.write_long('exec_base', EXEC)
        self.calls = []
        self.file_data = self.title
        self.read_error = False
        for offset in (-168, -330, -294, -444, -456):
            address = EXEC + offset
            self.cpu.mem_write(address, b'\x4e\x75')
            self.cpu.hook_add(UC_HOOK_CODE, self.os_call, begin=address, end=address)
        for name in ('file_open', 'file_read', 'file_close'):
            address = self.symbols[name]
            self.cpu.hook_add(UC_HOOK_CODE, self.file_call, begin=address, end=address)

    def os_call(self, cpu, address, size, user_data):
        offset = address - EXEC
        self.calls.append(offset)
        if offset == -168:
            self.assertEqual(cpu.reg_read(UC_M68K_REG_D0), 5)
            self.assertEqual(cpu.reg_read(UC_M68K_REG_A1), self.symbols['vblank_server'])
        cpu.reg_write(UC_M68K_REG_D0, {-330: 3, -294: 0x40000}.get(offset, 0))

    def file_call(self, cpu, address, size, user_data):
        if address == self.symbols['file_open']:
            filename = cpu.mem_read(cpu.reg_read(UC_M68K_REG_D1), 10)
            self.assertEqual(filename, b'title.pc1\0')
            value = -33 if self.file_data is None else 0x12345
        elif address == self.symbols['file_read']:
            value = -36 if self.read_error else len(self.file_data)
            if not self.read_error and self.file_data:
                cpu.mem_write(cpu.reg_read(UC_M68K_REG_D2), self.file_data)
        else:
            value = 0
        cpu.reg_write(UC_M68K_REG_D0, value & 0xffffffff)

    def write_long(self, name, value):
        self.cpu.mem_write(self.symbols[name], struct.pack('>I', value))

    def read_long(self, name):
        return struct.unpack('>I', self.cpu.mem_read(self.symbols[name], 4))[0]

    def run_code(self, name):
        self.cpu.reg_write(UC_M68K_REG_SR, 0x2000)
        self.cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.cpu.reg_write(UC_M68K_REG_A7, STACK - 4)
        self.cpu.mem_write(STACK - 4, struct.pack('>I', STOP))
        self.cpu.emu_start(self.symbols[name], STOP, count=300000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC), STOP)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7), STACK)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A6), VARIABLES)

    def test_title_pixels_palette_and_display_survive_disk_buffer_reuse(self):
        self.cpu.mem_write(SCREEN - 32, b'\xa5' * (32768 + 32))
        game_vars = b'\xa5' * self.symbols['var_size']
        self.cpu.mem_write(VARIABLES, game_vars)
        self.run_code('show_title')
        expected = decode_title(self.title)
        self.assertEqual(self.cpu.mem_read(SCREEN, 32000), expected)
        self.assertEqual(self.cpu.mem_read(SCREEN - 32, 32), b'\xa5' * 32)
        self.assertEqual(self.cpu.mem_read(SCREEN + 32000, 768), b'\xa5' * 768)
        palette = struct.pack('>16H', *(2 * (word & 0x777) for word in
                                      struct.unpack_from('>16H', self.title, 2)))
        self.assertEqual(self.cpu.mem_read(self.symbols['palette'], 32), palette)
        self.cpu.mem_write(OTHER, b'\x5a' * 32768)
        self.run_code('amiga_vblank')
        self.assertEqual(self.cpu.mem_read(0xdff180, 32), palette)
        for plane in range(4):
            words = struct.unpack('>4H', self.cpu.mem_read(self.symbols['copper_planes'] + plane * 8, 8))
            self.assertEqual(words[1] << 16 | words[3], SCREEN + plane * 40)
        self.assertEqual(self.cpu.mem_read(SCREEN, 32000), expected)
        self.assertEqual(self.cpu.mem_read(VARIABLES, len(game_vars)), game_vars)
        self.assertEqual(self.read_long('game_ticks'), 0)
        self.assertEqual(self.read_long('frclock'), 1)

    def test_game_handoff_installs_one_server_and_preserves_frame_swapping(self):
        self.run_code('show_title')
        self.run_code('amiga_install')
        self.assertEqual(self.calls.count(-168), 1)
        self.write_long('display_pending', OTHER)
        self.cpu.mem_write(self.symbols['ready'], b'\xff\xff')
        self.run_code('amiga_vblank')
        self.assertEqual(self.read_long('game_ticks'), 1)
        self.assertEqual(self.read_long('display_front'), OTHER)
        self.assertEqual(self.cpu.mem_read(self.symbols['ready'], 2), b'\0\0')

    def test_missing_short_invalid_or_unreadable_title_allows_game_start(self):
        for data, read_error in [(None, False), (b'', False), (b'\x80\0', False),
                                 (b'\0' * 34, False), (self.title, True)]:
            with self.subTest(data_bytes=None if data is None else len(data), read_error=read_error):
                self.setUp()
                self.file_data, self.read_error = data, read_error
                self.run_code('show_title')
                self.assertEqual(self.calls, [])
                self.run_code('amiga_install')
                self.assertEqual(self.calls.count(-168), 1)
                self.run_code('amiga_vblank')
                self.assertEqual(self.read_long('game_ticks'), 1)


if __name__ == '__main__':
    unittest.main()
