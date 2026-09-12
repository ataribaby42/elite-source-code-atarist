"""Execute the real TOS launcher, loader and relocation on MC68000/MC68020.

GEMDOS/XBIOS calls are simulated; these tests do not emulate an HDD driver.
Run build_atari.bat first so the linked game and relocation records are present.
"""
import itertools
import re
import struct
import unittest

import test_port
from test_port import Uc
from build import ROOT, ORIGIN, LOADER_ORIGIN, relocation_offsets, relocate_image

if Uc is not None:
    from unicorn import UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_A7, UC_M68K_REG_SR, UC_M68K_REG_PC, UC_M68K_REG_D0)


@unittest.skipIf(Uc is None, 'optional startup execution requires unicorn==2.1.4')
class BootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build = ROOT / 'build'
        if not (build / 'game-relocations.bin').is_file():
            raise unittest.SkipTest('Run build_atari.bat before linked-game startup tests')
        cls.config = (build / 'boot-config.inc').read_text()
        cls.values = {name: int(value[1:], 16) if value.startswith('$') else int(value)
                      for name, value in re.findall(r'(\w+) equ (\$?[0-9a-f]+)', cls.config)}
        cls.stream = (build / 'game-relocations.bin').read_bytes()
        game = ROOT.parent / 'output_atari/ELITE'
        cls.files = {name: (game / name).read_bytes()
                     for name in ('LOADER.IMG', 'TITLE.PC1', 'ELITE.IMG')}
        cls.offsets = relocation_offsets(struct.pack('>I', len(cls.stream)) + cls.stream,
                                         len(cls.files['ELITE.IMG']))
        cls.launchers = {}
        for automatic in (False, True):
            cls.launchers[automatic] = test_port.PortTests().assemble(
                ('auto_start equ 1\n' if automatic else '') + (ROOT/'asm/boot.s').read_text(),
                {'boot-config.inc': cls.config, 'game-relocations.bin': cls.stream})

    def execute(self, model, basepage, top, screen, automatic=False,
                short_file=None, bad_open=None, corrupt=False):
        code = self.launchers[automatic]
        text = basepage + 0x100
        delta = max(0, (text + len(code) - LOADER_ORIGIN + 32767) // 32768 * 32768)
        entry = ORIGIN + delta
        end = self.values['required_ram'] + delta
        cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        cpu.ctl_set_cpu_model(model)
        ram = max(top, screen + 32768, 0x100000)
        ram = (ram + 4095) & -4096
        cpu.mem_map(0, ram)
        cpu.mem_write(0, bytes([0xa5]) * ram)
        cpu.mem_write(text, code)
        cpu.mem_write(basepage, struct.pack('>II', basepage, top))
        cpu.mem_write(top-124, struct.pack('>I', basepage))
        cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        cpu.reg_write(UC_M68K_REG_A7, top-128)
        cpu.mem_write(0x484, b'\x07')  # conterm, key click may be disabled by loader
        low_before = bytes(cpu.mem_read(0, basepage))
        directory = '\\AUTO' if automatic else '\\ELITE'
        handles, opened, errors, reads, screens = {}, [], [], [], []
        game_on_disk = bytearray(self.files['ELITE.IMG'])
        if corrupt:
            # An unrelated modified byte must still fail the game's original check.
            game_on_disk[self.values['checksum_start_offset'] + 100] ^= 1

        def trap(machine, address, size, user):
            opcode = bytes(machine.mem_read(address, 2))
            if opcode not in (b'\x4e\x41', b'\x4e\x4e'):
                return
            stack = machine.reg_read(UC_M68K_REG_A7)
            def number(offset, length):
                return int.from_bytes(machine.mem_read(stack+offset, length), 'big')
            def string(pointer):
                return bytes(machine.mem_read(pointer, 160)).split(b'\0', 1)[0].decode()
            op, result = number(0, 2), 0
            nonlocal directory
            if opcode == b'\x4e\x4e':
                if op == 2: result = screens[-1] if screens else screen
                elif op == 5:
                    self.assertEqual(number(2, 4), number(6, 4))
                    self.assertEqual(number(10, 2), 0)
                    screens.append(number(2, 4))
                elif op not in (6, 21): self.fail(f'Unexpected XBIOS call {op}')
            elif op == 0x20: result = 1  # already supervisor, as in AUTO execution
            elif op == 0x3b: directory = string(number(2, 4))
            elif op == 0x3d:
                self.assertEqual(directory, '\\' if automatic else '\\ELITE')
                name = string(number(2, 4)).upper()
                opened.append(name)
                if name == bad_open: result = -33
                else:
                    self.assertIn(name, self.files)
                    result = 5 + len(handles)
                    handles[result] = name
            elif op == 0x3f:
                name = handles[number(2, 2)]
                count, destination = number(4, 4), number(8, 4)
                data = bytes(game_on_disk) if name == 'ELITE.IMG' else self.files[name]
                self.assertEqual(count, len(data), 'Reads must be bounded to the reserved buffer')
                if name == short_file: data = data[:-1]
                self.assertGreaterEqual(destination, text + len(code))
                self.assertLessEqual(destination + len(data), end)
                machine.mem_write(destination, data)
                reads.append((name, destination, len(data)))
                result = len(data)
            elif op == 0x3e: self.assertIn(number(2, 2), handles)
            elif op == 9: errors.append(string(number(2, 4)))
            elif op == 7: pass
            elif op == 0x4c:
                self.assertEqual(number(2, 2), 1)
                machine.emu_stop()
                return
            else: self.fail(f'Unexpected GEMDOS call {op:#x}')
            machine.reg_write(UC_M68K_REG_D0, result & 0xffffffff)
            machine.reg_write(UC_M68K_REG_PC, address + 2)

        cpu.hook_add(UC_HOOK_CODE, trap)
        cpu.emu_start(text, entry, count=3000000)
        reached = cpu.reg_read(UC_M68K_REG_PC) == entry
        low_after = bytearray(cpu.mem_read(0, basepage))
        low_after[0x484] = low_before[0x484]  # sole intentional system-variable write
        self.assertEqual(bytes(low_after), low_before, 'Memory below the TPA was overwritten')
        if reached:
            self.assertFalse(errors)
            expected = bytearray(relocate_image(game_on_disk, self.offsets, delta))
            if self.values['patch_checksum']:
                start = self.values['checksum_start_offset']
                stop = start + self.values['checksum_length']
                patch = self.values['checksum_patch_offset']
                change = sum(expected[start:stop]) - sum(game_on_disk[start:stop])
                value = (int.from_bytes(expected[patch:patch+2], 'big') + change) & 0xffff
                expected[patch:patch+2] = struct.pack('>H', value)
                self.assertEqual(value == sum(expected[start:stop]) & 0xffff, not corrupt)
            self.assertEqual(bytes(cpu.mem_read(entry, len(expected))), bytes(expected))
            self.assertEqual(opened, ['LOADER.IMG', 'TITLE.PC1', 'ELITE.IMG'])
            self.assertEqual(screens[0] % 32768, 0)
            self.assertTrue(screens[0]+32768 <= basepage or screens[0] >= top
                            or end <= screens[0] <= top-4096-32768)
        else:
            self.assertTrue(errors, 'Launcher stalled without reaching the game or an error')
        return reached, errors, opened

    def test_boots_above_resident_programs_and_on_plain_512k(self):
        cases = ((0xf0f8, 0x78000, 0x78000),
                 (0x15000, 0xf8000, 0xf8000),
                 (0x31000, 0xf8000, 0xf8000),
                 (0x71234, 0xf8000, 0xf8000),
                 (0x112340, 0x3f8000, 0x3f8000),
                 (0x15000, 0xf8000, 0xf8300))
        for model, automatic, args in itertools.product(
                (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020), (False, True), cases):
            with self.subTest(cpu=model, automatic=automatic, memory=args):
                self.assertTrue(self.execute(model, *args, automatic=automatic)[0])

    def test_real_shortage_and_file_errors_fail_safely(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            reached, errors, opened = self.execute(model, 0x31000, 0x78000, 0x78000)
            self.assertFalse(reached)
            self.assertIn('Not enough free ST RAM', errors[0])
            self.assertEqual(opened, [])
            for name in self.files:
                for fault in ('short_file', 'bad_open'):
                    with self.subTest(cpu=model, file=name, fault=fault):
                        reached, errors, _ = self.execute(model, 0x31000, 0xf8000, 0xf8000,
                                                          **{fault: name})
                        self.assertFalse(reached)
                        self.assertIn('Cannot read the Elite game files', errors[0])

    def test_relocation_does_not_hide_game_checksum_corruption(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.assertTrue(self.execute(model, 0x31000, 0xf8000, 0xf8000, corrupt=True)[0])


if __name__ == '__main__':
    unittest.main()
