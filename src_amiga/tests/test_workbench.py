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
                 'workbench_message', 'active_files', 'directory_lock',
                 'instance_port', 'instance_name', 'instance_owned',
                 'amiga_install', 'input_request']
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

    def exercise(self, model, workbench, fail=None, args=1, old_directory=0x1111,
                 shared=None, contender=None):
        if shared is None:
            shared = {'port': 0}
        busy = shared['port'] != 0
        initial_port = shared['port']
        depth = 0
        cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        cpu.ctl_set_cpu_model(model)
        cpu.mem_map(0, 0x100000)
        cpu.mem_map(0xdff000, 0x1000)
        cpu.mem_write(0xdff000, b'\xa5' * 0x1000)
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
            nonlocal current, depth
            a1 = cpu.reg_read(UC_M68K_REG_A1)
            if address == EXEC - 294:
                value = PROCESS
                events.append('FindTask')
            elif address in (EXEC - 384, EXEC - 372):
                self.assertEqual(cpu.reg_read(UC_M68K_REG_A0), PROCESS + 92)
                events.append('WaitPort' if address == EXEC - 384 else 'GetMsg')
                value = MESSAGE
            elif address == EXEC - 552:
                self.assertEqual(depth, 0, 'Do not block with task switching forbidden')
                self.assertEqual(shared['port'], self.symbols['instance_port'])
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
                depth += 1
                value = 0
            elif address == EXEC - 138:
                events.append('Permit')
                self.assertGreater(depth, 0)
                depth -= 1
                value = 0
            elif address == EXEC - 390:
                self.assertEqual(depth, 1)
                self.assertEqual(a1, self.symbols['instance_name'])
                self.assertEqual(bytes(cpu.mem_read(a1, 19)).split(b'\0')[0], b'Elite.Native.Amiga')
                events.append('FindPort')
                value = shared['port']
            elif address == EXEC - 354:
                self.assertEqual(depth, 1)
                self.assertEqual(shared['port'], 0, 'Two owners must never be published')
                self.assertEqual(a1, self.symbols['instance_port'])
                self.assertEqual(cpu.mem_read(a1 + 8, 2), b'\x04\0')
                self.assertEqual(cpu.mem_read(a1 + 14, 6), b'\x02\0\0\0\0\0')
                shared['port'] = a1
                events.append('AddPort')
                value = 0
            elif address == EXEC - 360:
                self.assertEqual(depth, 1)
                self.assertFalse(busy, 'A rejected launch must not release another owner')
                self.assertEqual(a1, shared['port'])
                shared['port'] = 0
                events.append('RemPort')
                value = 0
            elif address == EXEC - 378:
                self.assertEqual(depth, 1)
                self.assertEqual(a1, MESSAGE)
                events.append('ReplyMsg')
                value = 0
            elif address == GFX - 222:
                self.assertEqual(shared['port'], self.symbols['instance_port'])
                events.append(('LoadView', a1))
                value = 0
            elif address == EXEC - 330:
                events.append('AllocSignal')
                value = 0xffffffff if fail == 'signal' else 3
            elif address == EXEC - 336:
                events.append('FreeSignal')
                value = 0
            elif address == EXEC - 444:
                events.append('OpenDevice')
                value = 1 if fail == 'input.device' else 0
            elif address == EXEC - 450:
                events.append('CloseDevice')
                value = 0
            elif address == EXEC - 456:
                events.append('DoIO')
                cpu.mem_write(self.symbols['input_request'] + 31, b'\x01')
                value = 0
            else:
                events.append('WaitTOF')
                value = 0
            cpu.reg_write(UC_M68K_REG_D0, value)
        for base, offsets in [(EXEC, (-294, -384, -372, -552, -414, -132, -138,
                                     -390, -354, -360, -378, -330, -336, -444, -450, -456)),
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
            if name == 'elite':
                if contender:
                    contender(shared)
                if fail in ('signal', 'input.device', 'input.handler'):
                    cpu.reg_write(UC_M68K_REG_PC, self.symbols['amiga_install'])
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
        self.assertEqual(shared['port'], initial_port)
        self.assertEqual(cpu.mem_read(self.symbols['instance_owned'], 2), b'\0\0')
        self.assertEqual(depth, 1 if workbench else 0)
        if workbench:
            self.assertEqual(events.count('ReplyMsg'), 1)
            self.assertEqual(events[-2:], ['Forbid', 'ReplyMsg'])
            self.assertLess(events.index('WaitPort'), events.index('GetMsg'))
        else:
            self.assertNotIn('WaitPort', events)
            self.assertNotIn('ReplyMsg', events)
            self.assertFalse(any(isinstance(e, tuple) and e[0] == 'CurrentDir' for e in events))
        if busy:
            self.assertEqual(cpu.mem_read(0xdff000, 0x1000), b'\xa5' * 0x1000)
            self.assertEqual(events, (['FindTask', 'WaitPort', 'GetMsg'] if workbench else ['FindTask'])
                + ['Forbid', 'FindPort', 'Permit'] + (['Forbid', 'ReplyMsg'] if workbench else []))
            return events
        self.assertEqual(events.count('AddPort'), 1)
        self.assertEqual(events.count('RemPort'), 1)
        self.assertLess(events.index('AddPort'), events.index(('Open', 'dos.library')))
        self.assertLess(events.index('file_shutdown'), events.index('RemPort'))
        self.assertEqual('elite' in events, fail not in ('dos.library', 'graphics.library'))
        if fail != 'dos.library':
            self.assertIn(('Close', DOS), events)
            self.assertLess(events.index(('Close', DOS)), events.index('RemPort'))
        if fail not in ('dos.library', 'graphics.library'):
            self.assertIn(('LoadView', 0x123456), events)
            self.assertIn(('Close', GFX), events)
            self.assertLess(events.index(('Close', GFX)), events.index('RemPort'))
        if fail in ('input.device', 'input.handler'):
            self.assertIn('FreeSignal', events)
        if fail == 'input.handler':
            self.assertIn('CloseDevice', events)
        if workbench and args and fail != 'dos.library':
            self.assertLess(events.index(('CurrentDir', old_directory)), events.index(('Close', DOS)))
        return events

    def test_entry_exit_and_failure_cleanup(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for wb in (False, True):
                for fail in (None, 'dos.library', 'graphics.library', 'signal',
                             'input.device', 'input.handler'):
                    with self.subTest(cpu=model, workbench=wb, failure=fail):
                        self.exercise(model, wb, fail)

    def test_workbench_with_no_arguments_or_original_root_directory(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.exercise(model, True, args=0)
            self.exercise(model, True, old_directory=0)

    def test_duplicate_start_does_not_touch_the_running_game(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for wb in (False, True):
                with self.subTest(cpu=model, workbench=wb):
                    self.exercise(model, wb, shared={'port': 0x88000})

    def test_overlapping_launches_and_restart_after_release(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for first_wb in (False, True):
                shared = {'port': 0}
                def contenders(state):
                    for second_wb in (False, True):
                        for _ in range(3):
                            self.exercise(model, second_wb, shared=state)
                with self.subTest(cpu=model, first_workbench=first_wb):
                    self.exercise(model, first_wb, shared=shared, contender=contenders)
                    self.assertEqual(shared['port'], 0)
                    self.exercise(model, not first_wb, shared=shared)


if __name__ == '__main__':
    unittest.main()
