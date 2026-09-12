"""Execute the native file layer with stubbed DOS services on an MC68000.

Real floppy changes and DOS requesters also require emulator testing.
"""
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import unittest

try:
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
    from unicorn import m68k_const as reg
except ImportError:
    Uc = None

ROOT = Path(__file__).resolve().parents[1]
CODE, STOP, EXEC, DOS, PROCESS, STRING, BUFFER, STACK = (
    0x10000, 0x1000, 0x20000, 0x22000, 0x30000, 0x40000, 0x41000, 0x90000)


@unittest.skipIf(Uc is None, 'optional file tests require unicorn==2.1.4')
class FileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory(prefix='test-fileio-', dir=ROOT/'build') as tmp:
            tmp = Path(tmp)
            source = (ROOT/'asm/fileio.m68').read_text()
            source = re.sub(r'^\s*(?:xref|section)\b[^\n]*', '', source, flags=re.M)
            names = ('file_init file_shutdown commander_open commander_create file_open '
                     'file_close file_first file_next active_files directory_lock '
                     'commander_directory commander_path').split()
            source = ('amiga_implementation equ 1\namiga_workspace_implementation equ 1\n org $10000\n dc.l '
                      + ','.join(names) + '\n' + source + f'\n ds.b 16\ndos_base: dc.l ${DOS:x}\n')
            (tmp/'fileio.s').write_text(source)
            result = subprocess.run([str(ROOT.parent/'tools/vasmm68k_mot.exe'),
                '-m68000', '-Fbin', '-no-opt', '-align', '-allmp', '-spaces', '-nocase',
                '-I'+str(ROOT/'asm'), '-o', str(tmp/'fileio.bin'), str(tmp/'fileio.s')],
                cwd=tmp, capture_output=True, text=True)
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)
            cls.code = (tmp/'fileio.bin').read_bytes()
            cls.symbols = dict(zip(names, struct.unpack_from('>'+'I'*len(names), cls.code)))

    def setUp(self):
        self.cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(reg.UC_CPU_M68K_M68000)
        self.cpu.mem_map(0, 0x100000)
        self.cpu.mem_write(CODE, self.code)
        self.put(4, EXEC)
        self.put(PROCESS+184, 0x12345678)
        self.handlers = {'': 0x51000, 'DF0:': 0x51000}
        self.calls = []
        self.open_result = 0x30001  # BPTR deliberately exceeds a TOS word handle.
        self.names = ['TOM.CDR']
        for base, offsets in [(EXEC, [-294]), (DOS, [-174, -30, -36, -84, -90, -102, -108])]:
            for offset in offsets:
                address = base+offset
                self.cpu.mem_write(address, b'\x4e\x75')
                self.cpu.hook_add(UC_HOOK_CODE, self.service, begin=address, end=address)

    def put(self, address, value):
        self.cpu.mem_write(address, struct.pack('>I', value))

    def get(self, address):
        return struct.unpack('>I', self.cpu.mem_read(address, 4))[0]

    def string(self, address):
        return bytes(self.cpu.mem_read(address, 256)).split(b'\0')[0].decode('ascii')

    def service(self, cpu, address, size, data):
        d1, d2 = [cpu.reg_read(getattr(reg, 'UC_M68K_REG_'+n)) for n in ('D1', 'D2')]
        if address == EXEC-294:
            self.assertEqual(cpu.reg_read(reg.UC_M68K_REG_A1), 0)
            value = PROCESS
        else:
            offset = address-DOS
            if offset == -174:
                value = self.handlers.get(self.string(d1), 0)
            elif offset == -30:
                self.calls.append(('open', self.string(d1), d2))
                value = self.open_result
            elif offset == -36:
                self.calls.append(('close', d1))
                value = 1
            elif offset == -84:
                self.calls.append(('lock', self.string(d1), d2))
                value = 0x30002
            elif offset == -90:
                self.calls.append(('unlock', d1))
                value = 1
            elif offset == -102:
                value = 1
            elif offset == -108:
                value = int(bool(self.names))
                if value:
                    self.put(d2+4, 0xfffffffd)
                    cpu.mem_write(d2+8, self.names.pop(0).encode()+b'\0')
            else:
                raise AssertionError(offset)
        # Exercise preservation even when OS volatile registers are overwritten.
        for n in ('D1', 'A0', 'A1'):
            cpu.reg_write(getattr(reg, 'UC_M68K_REG_'+n), 0xdeadbeef)
        cpu.reg_write(reg.UC_M68K_REG_D0, value)

    def call(self, name, d1=None):
        cpu = self.cpu
        cpu.reg_write(reg.UC_M68K_REG_SR, 0x2000)
        saved = {}
        for i, n in enumerate([f'D{i}' for i in range(1, 8)]+[f'A{i}' for i in range(7)]):
            value = (d1 if n == 'D1' and d1 is not None else 0x70000+i*16)
            saved[n] = value
            cpu.reg_write(getattr(reg, 'UC_M68K_REG_'+n), value)
        cpu.reg_write(reg.UC_M68K_REG_A7, STACK-4)
        self.put(STACK-4, STOP)
        cpu.emu_start(self.symbols[name], STOP, count=100000)
        self.assertEqual(cpu.reg_read(reg.UC_M68K_REG_PC), STOP)
        self.assertEqual(cpu.reg_read(reg.UC_M68K_REG_A7), STACK)
        for n, value in saved.items():
            self.assertEqual(cpu.reg_read(getattr(reg, 'UC_M68K_REG_'+n)), value, n)
        return cpu.reg_read(reg.UC_M68K_REG_D0)

    def filename(self, name):
        self.cpu.mem_write(STRING, name.encode()+b'\0')
        return STRING

    def test_each_startup_floppy_follows_its_physical_drive(self):
        for drive in range(4):
            with self.subTest(drive=drive):
                self.handlers = {'': 0x51000, **{f'DF{i}:': 0x51000 if i == drive else 0x52000+i*4 for i in range(4)}}
                self.call('file_init')
                self.assertEqual(self.get(PROCESS+184), 0xffffffff)
                self.assertEqual(self.call('commander_open', self.filename('TOM.CDR')), 0x30001)
                self.assertEqual(self.calls[-1], ('open', f'DF{drive}:TOM.CDR', 1005))
                self.call('file_close', 0x30001)
                self.assertEqual(self.calls[-1], ('close', 0x30001))
                self.call('file_shutdown')
                self.assertEqual(self.get(PROCESS+184), 0x12345678)

    def test_hard_disk_keeps_current_directory(self):
        self.handlers = {'': 0x53000, 'DF0:': 0x51000}
        self.call('file_init')
        self.assertEqual(self.get(self.symbols['commander_directory']), 0)
        self.call('commander_create', self.filename('TOM.CDR'))
        self.assertEqual(self.calls[-1], ('open', 'TOM.CDR', 1006))
        self.call('file_first', BUFFER)
        self.assertEqual(self.calls[-1], ('lock', '', 0xfffffffe))

    def test_assets_stay_relative_and_maximum_commander_name_fits(self):
        self.call('file_init')
        self.call('file_open', self.filename('BITMAPS.IMG'))
        self.assertEqual(self.calls[-1], ('open', 'BITMAPS.IMG', 1005))
        end = self.symbols['commander_path']+18
        self.cpu.mem_write(end, b'GUARD')
        self.call('commander_create', self.filename('ABCDEFGH.CDR'))
        self.assertEqual(self.calls[-1], ('open', 'DF0:ABCDEFGH.CDR', 1006))
        self.assertEqual(self.cpu.mem_read(end, 5), b'GUARD')

    def test_catalog_and_load_use_same_inserted_drive_and_release_lock(self):
        self.call('file_init')
        self.assertEqual(self.call('file_first', BUFFER), 0)
        self.assertEqual(self.calls[-1], ('lock', 'DF0:', 0xfffffffe))
        self.assertEqual(self.string(BUFFER), 'TOM.CDR')
        self.call('commander_open', BUFFER)
        self.assertEqual(self.calls[-1], ('open', 'DF0:TOM.CDR', 1005))
        self.assertEqual(self.call('file_next'), (-49)&0xffffffff)
        self.assertEqual(self.calls[-1], ('unlock', 0x30002))
        self.assertEqual(self.get(self.symbols['directory_lock']), 0)

    def test_missing_file_returns_without_consuming_handle_slot(self):
        self.call('file_init')
        self.open_result = 0
        self.assertEqual(self.call('commander_open', self.filename('MISSING.CDR')), (-33)&0xffffffff)
        self.assertEqual(self.cpu.mem_read(self.symbols['active_files'], 32), b'\0'*32)


if __name__ == '__main__':
    unittest.main()
