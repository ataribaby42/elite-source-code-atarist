"""Execute CLI/Workbench entry and exit, including failures, on 68k CPUs.

Exec, DOS and graphics services are stubbed; real Workbench checks are separate.
"""
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import unittest

try:
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
    from unicorn.m68k_const import *
except ImportError:
    Uc = None

ROOT = Path(__file__).resolve().parents[1]
CODE, STOP, EXEC, DOS, GFX = 0x10000, 0x1000, 0x70000, 0x72000, 0x74000
PROCESS, MESSAGE, ARGS, STACK = 0x76000, 0x77000, 0x77100, 0x90000


@unittest.skipIf(Uc is None, 'optional Workbench tests require unicorn')
class WorkbenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test-workbench-', dir=ROOT / 'build')
        cls.addClassCleanup(cls.temp.cleanup)
        directory = Path(cls.temp.name)
        system = (ROOT / 'asm/system.m68').read_text()
        system = re.sub(r'^\s*(?:xref|section)\b[^\n]*', '', system, flags=re.M)
        names = ['amiga_entry', 'elite', 'file_init', 'file_shutdown', 'quiet',
                 'workbench_message', 'active_files', 'directory_lock']
        stubs = '\n'.join(name + ':\n rts' for name in
                           ('elite', 'file_init', 'file_shutdown', 'quiet', 'vblank', 'key_change'))
        assembly = ('amiga_workspace_implementation equ 1\nfileio_implementation equ 1\n'
                    ' org $10000\n dc.l ' + ','.join(names) + '\n' + system + '\n' + stubs +
                    '\nactive_files: dcb.l 8,0\ndirectory_lock: dc.l 0\n'
                    'vars equ $30000\namiga_primary equ $40000\nother_screen equ $48000\n')
        source, binary = directory / 'start.s', directory / 'start.bin'
        source.write_text(assembly)
        result = subprocess.run([str(ROOT.parent / 'tools/vasmm68k_mot.exe'), '-m68000',
            '-Fbin', '-no-opt', '-align', '-allmp', '-spaces', '-nocase',
            '-I' + str(ROOT / 'asm'), '-o', str(binary), str(source)],
            cwd=directory, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.code = binary.read_bytes()
        cls.symbols = dict(zip(names, struct.unpack_from('>' + 'I' * len(names), cls.code)))

    def exercise(self, model, workbench, fail=None, args=1, old_directory=0x1111):
        cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        cpu.ctl_set_cpu_model(model)
        cpu.mem_map(0, 0x100000)
        cpu.mem_map(0xdff000, 0x1000)
        cpu.mem_write(CODE, self.code)
        def long(address, value):
            cpu.mem_write(address, struct.pack('>I', value))
        long(4, EXEC)
        long(PROCESS + 172, 0 if workbench else 0x1234)
        long(MESSAGE + 28, args)
        long(MESSAGE + 36, ARGS)
        long(ARGS, 0x2222)
        long(GFX + 34, 0x123456)
        long(GFX + 38, 0x654321)
        current = old_directory
        events = []
        def service(cpu, address, size, userdata):
            nonlocal current
            a1 = cpu.reg_read(UC_M68K_REG_A1)
            if address == EXEC - 294:
                value = PROCESS
                events.append('FindTask')
            elif address in (EXEC - 384, EXEC - 372):
                self.assertEqual(cpu.reg_read(UC_M68K_REG_A0), PROCESS + 92)
                events.append('WaitPort' if address == EXEC - 384 else 'GetMsg')
                value = MESSAGE
            elif address == EXEC - 552:
                name = bytes(cpu.mem_read(a1, 32)).split(b'\0')[0].decode()
                events.append(('Open', name))
                value = 0 if name == fail else {'dos.library': DOS, 'graphics.library': GFX}[name]
            elif address == DOS - 126:
                target = cpu.reg_read(UC_M68K_REG_D1)
                events.append(('CurrentDir', target))
                value, current = current, target
            elif address == EXEC - 414:
                events.append(('Close', a1))
                value = 0
            elif address == EXEC - 132:
                events.append('Forbid')
                value = 0
            elif address == EXEC - 378:
                self.assertEqual(a1, MESSAGE)
                events.append('ReplyMsg')
                value = 0
            elif address == GFX - 222:
                events.append(('LoadView', a1))
                value = 0
            else:
                events.append('WaitTOF')
                value = 0
            cpu.reg_write(UC_M68K_REG_D0, value)
        for base, offsets in [(EXEC, (-294, -384, -372, -552, -414, -132, -378)),
                              (DOS, (-126,)), (GFX, (-222, -270))]:
            for offset in offsets:
                address = base + offset
                cpu.mem_write(address, b'\x4e\x75')
                cpu.hook_add(UC_HOOK_CODE, service, begin=address, end=address)
        def game(cpu, address, size, userdata):
            name = next(n for n in ('elite', 'file_init', 'file_shutdown', 'quiet')
                        if self.symbols[n] == address)
            events.append(name)
            if name in ('file_init', 'elite'):
                self.assertEqual(current, 0x2222 if workbench and args else old_directory)
        for name in ('elite', 'file_init', 'file_shutdown', 'quiet'):
            address = self.symbols[name]
            cpu.hook_add(UC_HOOK_CODE, game, begin=address, end=address)
        registers = [UC_M68K_REG_D2, UC_M68K_REG_D3, UC_M68K_REG_D4, UC_M68K_REG_D5,
                     UC_M68K_REG_D6, UC_M68K_REG_D7, UC_M68K_REG_A2, UC_M68K_REG_A3,
                     UC_M68K_REG_A4, UC_M68K_REG_A5, UC_M68K_REG_A6]
        for i, register in enumerate(registers):
            cpu.reg_write(register, 0xabc000 + i)
        cpu.reg_write(UC_M68K_REG_SR, 0x2000)
        cpu.reg_write(UC_M68K_REG_A7, STACK - 4)
        long(STACK - 4, STOP)
        cpu.emu_start(self.symbols['amiga_entry'], STOP, count=10000)
        self.assertEqual(cpu.reg_read(UC_M68K_REG_PC), STOP)
        self.assertEqual(cpu.reg_read(UC_M68K_REG_A7), STACK)
        self.assertEqual(cpu.reg_read(UC_M68K_REG_D0), 0)
        for i, register in enumerate(registers):
            self.assertEqual(cpu.reg_read(register), 0xabc000 + i)
        self.assertEqual(current, old_directory)
        if workbench:
            self.assertEqual(events.count('ReplyMsg'), 1)
            self.assertEqual(events[-2:], ['Forbid', 'ReplyMsg'])
            self.assertLess(events.index('WaitPort'), events.index('GetMsg'))
        else:
            self.assertNotIn('WaitPort', events)
            self.assertNotIn('ReplyMsg', events)
            self.assertFalse(any(isinstance(e, tuple) and e[0] == 'CurrentDir' for e in events))
        self.assertEqual('elite' in events, fail is None)
        if fail != 'dos.library':
            self.assertIn(('Close', DOS), events)
        if fail is None:
            self.assertIn(('LoadView', 0x123456), events)
            self.assertIn(('Close', GFX), events)
        if workbench and args and fail != 'dos.library':
            self.assertLess(events.index(('CurrentDir', old_directory)), events.index(('Close', DOS)))

    def test_entry_exit_and_failure_cleanup(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for wb in (False, True):
                for fail in (None, 'dos.library', 'graphics.library'):
                    with self.subTest(cpu=model, workbench=wb, failure=fail):
                        self.exercise(model, wb, fail)

    def test_workbench_with_no_arguments_or_original_root_directory(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.exercise(model, True, args=0)
            self.exercise(model, True, old_directory=0)


if __name__ == '__main__':
    unittest.main()
