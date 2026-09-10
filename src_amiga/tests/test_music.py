"""Execute the native replay against the original ADF player on 68000/68020.

Optional dependency: unicorn==2.1.4. No emulator or disassembler is needed
by the normal build. Original instructions are used only as a test oracle.
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
from tools.amiga_assets import extract_assets, ofs_file

try:
    from unicorn import (Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_PROT_READ,
                         UC_PROT_EXEC, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ)
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_SR, UC_M68K_REG_A7, UC_M68K_REG_A6, UC_M68K_REG_D0,
        UC_M68K_REG_PC)
except ImportError:
    Uc = None

CODE, STOP, STACK, VARIABLES = 0x10000, 0xf0000, 0xe0000, 0xc0000


def assemble(directory):
    names = ['amiga_music_init', 'amiga_music_tick', 'wb_state', 'wb_score',
             'wb_samples', 'wb_silence', 'amiga_music_retrigger',
             'amiga_music_attack', 'amiga_music_loops', 'music_code_end',
             'start_tune', 'start_fade', 'sound', 'quiet', 'fx', 'music_dma',
             'music_playing', 'fade_ticks', 'user', 'f_fx', 'end_hyperspace',
             'amiga_samples', 'effect_ticks']
    music = (ROOT/'asm/music.m68').read_text()
    sounds = (ROOT/'asm/sounds.m68').read_text()
    # Keep executable pages separate so writes to instructions fail even when
    # Unicorn's CPU model does not model a physical instruction cache.
    code = ('amiga_implementation equ 1\namiga_workspace_implementation equ 1\n'
            'fileio_implementation equ 1\n include "common.def"\n'
            ' include "macros.m68"\n org $10000\n dc.l '+','.join(names)+'\n')
    sounds = re.sub(r'^\s*include "(?:common.def|macros.m68)"\s*$', '', sounds, flags=re.M)
    # Order the sections explicitly in the flat test image.
    text, data, variables, chip = [], [], [], []
    for source in (sounds, music):
        dest = text
        for line in source.splitlines():
            if re.match(r'\s*x(?:def|ref)\b', line):
                continue
            match = re.match(r'\s*section (\w+),(\w+)', line)
            if match:
                dest = {'text': text, 'music_data': data, 'audio_vars': variables,
                        'amiga_audio': chip}[match[1]]
            else:
                dest.append(line)
    code += '\n'.join(text)+'\n cnop 0,4096\nmusic_code_end:\n'
    code += '\n'.join(data)+'\n cnop 0,4096\n'
    code += '\n'.join(variables)+'\n cnop 0,4096\n'
    code += '\n'.join(chip)+'\n'
    source, binary = directory/'music.s', directory/'music.bin'
    source.write_text(code)
    result = subprocess.run([str(ROOT.parent/'tools/vasmm68k_mot.exe'),
        '-m68000', '-Fbin', '-no-opt', '-align', '-allmp', '-spaces', '-nocase',
        '-I'+str(directory), '-I'+str(ROOT/'asm'), '-o', str(binary), str(source)],
        cwd=directory, text=True, capture_output=True)
    if result.returncode:
        raise AssertionError(result.stdout+result.stderr)
    data = binary.read_bytes()
    return data, dict(zip(names, struct.unpack_from('>'+len(names)*'I', data)))


def cpu(model):
    result = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
    result.ctl_set_cpu_model(model)
    result.mem_map(0, 0x100000)
    result.mem_map(0xdff000, 0x1000)
    result.reg_write(UC_M68K_REG_SR, 0x2700)
    result.reg_write(UC_M68K_REG_A6, VARIABLES)
    return result


def call(machine, address):
    machine.reg_write(UC_M68K_REG_A7, STACK-4)
    machine.mem_write(STACK-4, struct.pack('>I', STOP))
    machine.emu_start(address, STOP, count=200000)
    if machine.reg_read(UC_M68K_REG_PC) != STOP:
        raise AssertionError('Replay did not return')


@unittest.skipIf(Uc is None, 'optional music tests require unicorn==2.1.4')
class MusicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT/'build').mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix='test-music-', dir=ROOT/'build')
        cls.addClassCleanup(cls.temp.cleanup)
        directory = Path(cls.temp.name)
        adf = ROOT.parent/'resources/amiga/Elite 2.0.adf'
        cls.game = ofs_file(adf.read_bytes(), 887)
        extract_assets(adf, directory)
        cls.code, cls.symbols = assemble(directory)

    def native(self, model):
        machine = cpu(model)
        machine.mem_write(CODE, self.code)
        machine.mem_protect(CODE, self.symbols['music_code_end']-CODE,
                            UC_PROT_READ | UC_PROT_EXEC)
        return machine

    def test_complete_arrangement_matches_original(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            with self.subTest(cpu=model):
                original, native = cpu(model), self.native(model)
                original.mem_write(0x400, self.game[0x5cc:0x17bc8])
                original.mem_write(0x5a066, self.game[0x68dcc:0x68dcc+60350]+b'\0\0')
                original.mem_write(0x7e36c, b'\1')
                call(original, 0x5f32)
                call(native, self.symbols['amiga_music_init'])
                patterns, wraps, previous = set(), [0]*4, [2]*4
                for frame in range(18000):
                    call(original, 0x5f32)
                    call(native, self.symbols['amiga_music_tick'])
                    expected = bytearray(original.mem_read(0x69b6, 0x12a))
                    actual = bytearray(native.mem_read(self.symbols['wb_state'], 0x12a))
                    # Relocate pointers back to the original address space.
                    for address in range(0x6a60, 0x6a70, 4):
                        offset = address-0x69b6
                        value = struct.unpack_from('>I', actual, offset)[0]
                        if value:
                            value = (0x68c24 if value == self.symbols['wb_silence'] else
                                     value-self.symbols['wb_samples']+0x5a066)
                        struct.pack_into('>I', actual, offset, value)
                    for address in range(0x6a80, 0x6aa8, 4):
                        offset = address-0x69b6
                        value = struct.unpack_from('>I', actual, offset)[0]
                        if value:
                            value += 0x6c84-self.symbols['wb_score']
                        struct.pack_into('>I', actual, offset, value)
                    if actual != expected:
                        differences = [(hex(0x69b6+i), x, y) for i, (x, y)
                                       in enumerate(zip(expected, actual)) if x != y]
                        self.fail(f'frame {frame}: {differences[:16]}')
                    for channel in range(4):
                        order = expected[8+12+channel]
                        patterns.add((channel, order))
                        wraps[channel] += order < previous[channel]
                        previous[channel] = order
                # Every channel crosses its 17-byte order list and restarts.
                self.assertTrue(all((channel, 16) in patterns for channel in range(4)))
                self.assertTrue(all(wraps))

    def output_machine(self, model):
        machine = self.native(model)
        hardware = PaulaTrace(machine, self.symbols)
        return machine, hardware

    def test_paula_attacks_loops_and_fade(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            with self.subTest(cpu=model):
                machine, hardware = self.output_machine(model)
                s = self.symbols
                call(machine, s['start_tune'])
                for frame in range(9600):  # full 189.6-second arrangement and restart
                    call(machine, s['sound'])
                    state = machine.mem_read(s['wb_state'], 0x12a)
                    active = ~state[0x97] & 15
                    self.assertEqual(hardware.dma, active)
                    self.assertEqual(hardware.volumes,
                        [state[0x68+n] if active & (1 << n) else 0 for n in range(4)])
                    self.assertEqual(hardware.periods, list(struct.unpack('>4H', state[:8])))
                self.assertGreater(hardware.attacks, 1000)
                call(machine, s['start_fade'])
                for tick in range(31, 0, -1):
                    call(machine, s['sound'])
                    state = machine.mem_read(s['wb_state'], 0x12a)
                    self.assertEqual(hardware.volumes,
                        [(state[0x68+n]*tick//32) if hardware.dma & (1 << n) else 0
                         for n in range(4)])
                call(machine, s['sound'])
                self.assertEqual(hardware.dma, 0)
                self.assertEqual(hardware.volumes, [0]*4)
                writes = hardware.writes
                for _ in range(100):
                    call(machine, s['sound'])
                self.assertEqual(hardware.writes, writes)

    def test_restart_quiet_and_effects_after_music(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            with self.subTest(cpu=model):
                machine, hardware = self.output_machine(model)
                s = self.symbols
                snapshots = []
                for _ in range(3):
                    call(machine, s['start_tune'])
                    for frame in range(40):
                        call(machine, s['sound'])
                    snapshots.append(bytes(machine.mem_read(s['wb_state'], 0x12a)))
                self.assertEqual(snapshots[0], snapshots[1])
                self.assertEqual(snapshots[0], snapshots[2])
                call(machine, s['quiet'])
                self.assertEqual(hardware.dma, 0)
                self.assertEqual(hardware.volumes, [0]*4)
                machine.mem_write(VARIABLES+s['user'], b'\1\0')
                machine.reg_write(UC_M68K_REG_D0, 3)  # laser
                call(machine, s['fx'])
                call(machine, s['sound'])
                self.assertNotEqual(hardware.dma, 0)
                for _ in range(180):
                    call(machine, s['sound'])
                self.assertEqual(hardware.dma, 0)
                self.assertEqual(hardware.volumes, [0]*4)


class PaulaTrace:
    """Register-level DMA model; this checks ordering, not analogue audio quality."""
    def __init__(self, machine, symbols):
        self.machine, self.symbols = machine, symbols
        self.line = self.dma = self.attacks = self.writes = 0
        self.volumes, self.periods = [0]*4, [0]*4
        self.pointers, self.lengths = [0]*4, [0]*4
        self.muted, self.enabled = [-1000]*4, [-1000]*4
        machine.hook_add(UC_HOOK_MEM_READ, self.read, begin=0xdff006, end=0xdff006)
        machine.hook_add(UC_HOOK_MEM_WRITE, self.write, begin=0xdff000, end=0xdfffff)

    def read(self, machine, access, address, size, value, user):
        self.line += 1
        machine.mem_write(address, bytes([self.line & 255]))

    def valid_span(self, channel):
        p, length = self.pointers[channel], 2*self.lengths[channel]
        s = self.symbols
        banks = [(s['wb_samples'], 60350), (s['wb_silence'], 2),
                 (s['amiga_samples'], 53908)]
        assert length and any(start <= p and p+length <= start+size
                              for start, size in banks), (channel, hex(p), length)

    def write(self, machine, access, address, size, value, user):
        self.writes += 1
        if address == 0xdff096:
            bits = value & 15
            if value & 0x8000:
                for n in range(4):
                    if bits & (1 << n) and not self.dma & (1 << n):
                        self.valid_span(n)
                        self.enabled[n] = self.line
                        self.attacks += 1
                self.dma |= bits
            else:
                for n in range(4):
                    if bits & self.dma & (1 << n):
                        assert self.volumes[n] == 0, 'DMA stopped before muting'
                        # At least one complete old sample period must elapse.
                        assert (self.line-self.muted[n]-1)*227 >= self.periods[n]
                self.dma &= ~bits
            return
        if not 0xdff0a0 <= address < 0xdff0e0:
            raise AssertionError('Unexpected custom register write '+hex(address))
        n, register = divmod(address-0xdff0a0, 16)
        if register == 0:
            if self.dma & (1 << n):
                assert self.line-self.enabled[n] >= 2, 'Attack replaced before DMA fetch'
            self.pointers[n] = value
        elif register == 4:
            self.lengths[n] = value
        elif register == 6:
            self.periods[n] = value
        elif register == 8:
            assert 0 <= value <= 64
            self.volumes[n] = value
            if value == 0:
                self.muted[n] = self.line
        elif register != 10:
            raise AssertionError('Unexpected audio register '+hex(address))
        if self.dma & (1 << n) and register == 0:
            self.valid_span(n)


if __name__ == '__main__':
    unittest.main()
