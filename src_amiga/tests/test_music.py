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
from tools.beam_audio import generate_beam_audio
from tools.rcs_audio import generate_rcs_audio
from tools.engine_audio import generate_engine_audio
from test_raster import routine
from test_viewport import variable_block

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
             'amiga_samples', 'effect_ticks', 'sfx_laser', 'sfx_doors', 'sfx_explosion', 'sfx_hit',
             'beam_samples', 'beam_kind', 'beam_volume', 'laser_audio_request', 'laser_type',
             'laser_temp', 'max_ltemp', 'game_frozen', 'game_over', 'docked', 'cockpit_on',
             'controls_locked', 'rcs_samples', 'rcs_voice', 'rcs_request', 'rcs_valid',
             'rcs_volume', 'prepare_rcs_frame', 'publish_rcs_sound', 'stop_rcs_sound',
             'roll_angle', 'climb_angle', 'damping', 'f_damping', 'sfx_error',
             'end_game', 'hyperspace_effect', 'docking_sequence',
             'engine_samples', 'engine_voice', 'speed', 'key_states']
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
    flight = (ROOT/'asm/flight.m68').read_text()
    text += [variable_block(flight, 'flight'), routine(flight, 'damping'),
             'set_roll_angles:\nset_climb_angles:\n rts\n']
    effects = (ROOT/'asm/effects.m68').read_text()
    for entry in ('end_game', 'hyperspace_effect', 'docking_sequence'):
        animation = routine(effects, entry)
        text.append(animation[:animation.index('\ttst view(a6)')]+'\trts\n')
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
        generate_beam_audio(directory)
        generate_rcs_audio(directory)
        generate_engine_audio(directory)
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
                lengths = struct.unpack_from('>19H', self.game, 0x60d0)
                for effect, sample in (('sfx_laser', 3), ('sfx_doors', 16)):
                    # Disabled effects must stay silent, including hangar launch.
                    machine.mem_write(VARIABLES+s['user'], b'\0\0')
                    machine.reg_write(UC_M68K_REG_D0, s[effect])
                    call(machine, s['fx'])
                    call(machine, s['sound'])
                    self.assertEqual(hardware.dma, 0)
                    machine.mem_write(VARIABLES+s['user'], b'\1\0')
                    machine.reg_write(UC_M68K_REG_D0, s[effect])
                    call(machine, s['fx'])
                    call(machine, s['sound'])
                    channels = [n for n in range(4) if hardware.dma & (1 << n)]
                    self.assertEqual(len(channels), 1)
                    channel = channels[0]
                    self.assertEqual(hardware.pointers[channel], s['amiga_samples']+sum(lengths[:sample]))
                    self.assertEqual(2*hardware.lengths[channel], lengths[sample])
                    # Include the longer launch envelope and its silent tail.
                    for _ in range(260):
                        call(machine, s['sound'])
                    self.assertEqual(hardware.dma, 0)
                    self.assertEqual(hardware.volumes, [0]*4)


    def configure_beam(self, machine, kind):
        for name, value in [('user', 0x100), ('cockpit_on', 1),
                            ('laser_type', kind), ('laser_audio_request', kind)]:
            machine.mem_write(VARIABLES+self.symbols[name], struct.pack('>H', value))

    def steer_rcs(self, machine, roll, pitch):
        s = self.symbols
        call(machine, s['prepare_rcs_frame'])
        for name, value in [('roll_angle', roll), ('climb_angle', pitch)]:
            machine.mem_write(VARIABLES+s[name], struct.pack('>H', value & 65535))
        call(machine, s['publish_rcs_sound'])

    def audio_word(self, machine, name):
        return int.from_bytes(machine.mem_read(self.symbols[name], 2), 'big')

    def test_throttle_keys_release_speed_limits_option_and_cinematics(self):
        s=self.symbols
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for key in (0x40,0x3a):
                m,h=self.output_machine(model);self.configure_beam(m,0)
                for speed in (0,11,22):
                    m.mem_write(VARIABLES+s['speed'],struct.pack('>H',speed))
                    self.steer_rcs(m,0,0);call(m,s['sound'])
                    self.assertEqual(self.audio_word(m,'engine_voice'),0)
                m.mem_write(VARIABLES+s['key_states']+key,b'\x01')
                periods=[]
                for speed in (1,11,21):
                    m.mem_write(VARIABLES+s['speed'],struct.pack('>H',speed))
                    self.steer_rcs(m,0,0)
                    for _ in range(7): call(m,s['sound'])
                    self.assertEqual(self.audio_word(m,'engine_voice'),1)
                    periods.append(h.periods[0])
                self.assertEqual(periods,[419,321,224])
                self.assertEqual(h.attacks,1)
                m.mem_write(VARIABLES+s['key_states']+key,b'\0');call(m,s['sound'])
                self.assertEqual(h.dma,0)
                for mode in ('disabled','end_game','hyperspace_effect','docking_sequence'):
                    m.mem_write(VARIABLES+s['user'],b'\x01\0')
                    m.mem_write(VARIABLES+s['key_states']+key,b'\x01')
                    self.steer_rcs(m,0,0);call(m,s['sound'])
                    self.assertEqual(self.audio_word(m,'engine_voice'),1)
                    if mode=='disabled':
                        m.mem_write(VARIABLES+s['user'],b'\x81\0');call(m,s['sound'])
                    else: call(m,s[mode])
                    self.assertEqual(h.dma,0)
                    for _ in range(6): call(m,s['sound'])
                    self.assertEqual(self.audio_word(m,'engine_voice'),0)

    def test_throttle_is_silent_at_blocked_limits_but_allows_opposite_direction(self):
        s=self.symbols
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for key,limit,opposite in ((0x40,22,0x3a),(0x3a,0,0x40)):
                m,h=self.output_machine(model);self.configure_beam(m,0)
                m.mem_write(VARIABLES+s['speed'],struct.pack('>H',limit))
                m.mem_write(VARIABLES+s['key_states']+key,b'\x01')
                self.steer_rcs(m,0,0);call(m,s['sound'])
                self.assertEqual(self.audio_word(m,'engine_voice'),0)
                self.assertEqual(h.dma,0)
                m.mem_write(VARIABLES+s['speed'],struct.pack('>H',11))
                self.steer_rcs(m,0,0);call(m,s['sound'])
                self.assertNotEqual(self.audio_word(m,'engine_voice'),0)
                m.mem_write(VARIABLES+s['speed'],struct.pack('>H',limit))
                call(m,s['sound'])
                self.assertEqual(self.audio_word(m,'engine_voice'),0)
                self.assertEqual(h.volumes,[0]*4)
                self.assertEqual(h.dma,0)
                for _ in range(5): call(m,s['sound'])
                self.assertEqual(h.dma,0)
                m.mem_write(VARIABLES+s['key_states']+key,b'\0')
                m.mem_write(VARIABLES+s['key_states']+opposite,b'\x01')
                self.steer_rcs(m,0,0);call(m,s['sound'])
                self.assertNotEqual(self.audio_word(m,'engine_voice'),0)

    def test_throttle_yields_to_rcs_and_ordinary_effects(self):
        s=self.symbols
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            m,h=self.output_machine(model);self.configure_beam(m,2)
            m.mem_write(VARIABLES+s['key_states']+0x40,b'\x01')
            self.steer_rcs(m,0,0);call(m,s['sound'])
            self.assertEqual(self.audio_word(m,'engine_voice'),1)
            for effect in ('sfx_error','sfx_doors'):
                m.reg_write(UC_M68K_REG_D0,s[effect]);call(m,s['fx']);call(m,s['sound'])
            self.steer_rcs(m,2,0);call(m,s['sound'])
            self.assertEqual(self.audio_word(m,'engine_voice'),0)
            self.assertEqual(self.audio_word(m,'rcs_voice'),1)
            m,h=self.output_machine(model);self.configure_beam(m,2)
            m.mem_write(VARIABLES+s['key_states']+0x40,b'\x01')
            self.steer_rcs(m,2,0);call(m,s['sound'])
            for effect in ('sfx_error','sfx_doors'):
                m.reg_write(UC_M68K_REG_D0,s[effect]);call(m,s['fx']);call(m,s['sound'])
            self.assertEqual(self.audio_word(m,'engine_voice'),0)
            self.assertEqual(self.audio_word(m,'rcs_voice'),1)

    def test_rcs_real_damping_steady_rotation_and_no_loop_restarts(self):
        s = self.symbols
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            m, h = self.output_machine(model)
            self.configure_beam(m, 0)
            m.mem_write(VARIABLES+s['user'], struct.pack('>H', 0x100 | (1 << (8+s['f_damping']))))
            self.steer_rcs(m, 6, -4)
            for _ in range(8):
                call(m, s['sound'])
            self.assertEqual(h.volumes, [8, 0, 0, 0])
            self.assertEqual(h.pointers[0], s['rcs_samples'])
            starts = h.attacks
            for roll, pitch in ((4, -2), (2, 0), (0, 0)):
                call(m, s['damping'])
                call(m, s['publish_rcs_sound'])
                self.assertEqual(int.from_bytes(m.mem_read(VARIABLES+s['roll_angle'],2),'big'),roll)
                self.assertEqual(int.from_bytes(m.mem_read(VARIABLES+s['climb_angle'],2),'big'),pitch & 65535)
                self.assertEqual(self.audio_word(m,'rcs_request'),1)
                for _ in range(3):
                    call(m,s['sound'])
                self.assertEqual(h.attacks,starts)
            self.steer_rcs(m, 40, 0)
            self.steer_rcs(m, 40, 0)
            for _ in range(4):
                call(m,s['sound'])
            self.assertEqual(h.volumes,[0]*4)
            self.assertEqual(h.dma,0)

    def test_rcs_lowest_priority_resumes_and_yields_beam_channel(self):
        s = self.symbols
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            m,h = self.output_machine(model)
            self.configure_beam(m,2)
            self.steer_rcs(m,2,0)
            call(m,s['sound'])
            self.assertEqual(self.audio_word(m,'rcs_voice'),1)
            for n,effect in enumerate(('sfx_laser','sfx_error','sfx_doors')):
                m.reg_write(UC_M68K_REG_D0,s[effect])
                call(m,s['fx'])
                call(m,s['sound'])
                self.assertEqual(self.audio_word(m,'rcs_voice'),1 if n < 2 else 0)
                self.assertEqual(h.pointers[3],s['beam_samples'])
            for _ in range(200):
                call(m,s['sound'])
            self.assertNotEqual(self.audio_word(m,'rcs_voice'),0)
            m,h = self.output_machine(model)
            self.configure_beam(m,0)
            self.steer_rcs(m,2,0)
            for effect in ('sfx_error','sfx_doors','sfx_explosion'):
                m.reg_write(UC_M68K_REG_D0,s[effect])
                call(m,s['fx'])
            call(m,s['sound'])
            self.assertEqual(self.audio_word(m,'rcs_voice'),4)
            self.configure_beam(m,2)
            call(m,s['sound'])
            self.assertEqual(self.audio_word(m,'rcs_voice'),0)
            self.assertEqual(h.pointers[3],s['beam_samples'])

    def test_rcs_cinematic_entries_and_option_shutdown(self):
        s = self.symbols
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for entry in ('end_game','hyperspace_effect','docking_sequence','quiet','start_tune'):
                m,h = self.output_machine(model)
                self.configure_beam(m,0)
                self.steer_rcs(m,2,0)
                call(m,s['sound'])
                self.assertEqual(self.audio_word(m,'rcs_voice'),1)
                call(m,s[entry])
                self.assertEqual(h.volumes,[0]*4)
                self.assertEqual(self.audio_word(m,'rcs_voice'),0)
                self.assertEqual(self.audio_word(m,'rcs_request'),0)
                for _ in range(10):
                    call(m,s['sound'])
                    self.assertEqual(self.audio_word(m,'rcs_voice'),0)
            for flag,value in [('user',0x8100),('user',0),('docked',1),
                               ('game_frozen',1),('game_over',1),('controls_locked',1),('cockpit_on',0)]:
                m,h = self.output_machine(model)
                self.configure_beam(m,2)
                self.steer_rcs(m,2,0)
                call(m,s['sound'])
                m.mem_write(VARIABLES+s[flag],struct.pack('>H',value))
                call(m,s['sound'])
                self.assertEqual(self.audio_word(m,'rcs_voice'),0)
                self.assertEqual(h.volumes[0],0)
                if value == 0x8100:
                    self.assertTrue(h.dma & 8)
                    m.mem_write(VARIABLES+s['user'],b'\x01\x00')
                    self.steer_rcs(m,4,0)
                    call(m,s['sound'])
                    self.assertEqual(self.audio_word(m,'rcs_voice'),1)

    def test_continuous_beams_loop_without_retrigger_and_keep_other_effect_channels(self):
        s = self.symbols
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for kind in (2, 3):
                machine, hardware = self.output_machine(model)
                self.configure_beam(machine, kind)
                pointer = s['beam_samples']+(kind-2)*4096
                starts = []
                for frame in range(600):
                    if frame in (20, 50, 80, 110, 140, 170, 200):
                        machine.reg_write(UC_M68K_REG_D0, s['sfx_explosion'])
                        call(machine, s['fx'])
                    call(machine, s['sound'])
                    self.assertTrue(hardware.dma & 8)
                    self.assertEqual(hardware.pointers[3], pointer)
                    self.assertEqual(hardware.lengths[3], 2048)
                    self.assertEqual(hardware.periods[3], 214)
                    self.assertEqual(hardware.volumes[3], min((frame+1)*16, 48))
                    starts.append(hardware.enabled[3])
                self.assertEqual(len(set(starts)), 1, 'held sound restarted')
                self.assertGreater(hardware.attacks, 1, 'other effects did not play')
                machine.mem_write(VARIABLES+s['laser_audio_request'], b'\0\0')
                volumes = []
                for _ in range(4):
                    call(machine, s['sound'])
                    volumes.append(hardware.volumes[3])
                self.assertEqual(volumes, [32, 16, 0, 0])
                self.assertEqual(hardware.dma, 0)
                self.assertEqual(hardware.volumes, [0]*4)

    def test_target_hits_are_audible_alongside_both_continuous_lasers(self):
        s = self.symbols
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for kind in (2, 3):
                machine, hardware = self.output_machine(model)
                self.configure_beam(machine, kind)
                for _ in range(10):
                    call(machine, s['sound'])
                beam_started = hardware.enabled[3]
                for _ in range(8):
                    machine.reg_write(UC_M68K_REG_D0, s['sfx_hit'])
                    call(machine, s['fx'])
                    call(machine, s['sound'])
                    # Native sfx_hit maps to original ADF sample 12 (zero-based).
                    audible_hits = [n for n in range(3)
                                    if hardware.dma & (1 << n)
                                    and hardware.pointers[n] == s['amiga_samples']+24728
                                    and hardware.lengths[n] == 2752//2
                                    and hardware.volumes[n] == 64]
                    self.assertTrue(audible_hits, 'target impact was not audible')
                    self.assertTrue(hardware.dma & 8)
                    self.assertEqual(hardware.volumes[3], 48)
                    self.assertEqual(hardware.enabled[3], beam_started)
                    for _ in range(10):
                        call(machine, s['sound'])
                call(machine, s['quiet'])
                self.assertEqual(hardware.dma, 0)
                self.assertEqual(hardware.volumes, [0]*4)

    def test_beam_shutdown_guards_type_switch_and_music_takeover(self):
        s = self.symbols
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for name, value in [('user', 0), ('cockpit_on', 0), ('docked', 1),
                                ('game_frozen', 1), ('game_over', 1),
                                ('controls_locked', 1), ('laser_temp', s['max_ltemp']),
                                ('laser_type', 0)]:
                machine, hardware = self.output_machine(model)
                self.configure_beam(machine, 2)
                for _ in range(8):
                    call(machine, s['sound'])
                machine.mem_write(VARIABLES+s[name], struct.pack('>H', value))
                for _ in range(5):
                    call(machine, s['sound'])
                self.assertEqual(hardware.dma, 0, name)
                self.assertEqual(hardware.volumes, [0]*4, name)
                self.assertEqual(machine.mem_read(VARIABLES+s['laser_audio_request'], 2), b'\0\0')
            machine, hardware = self.output_machine(model)
            self.configure_beam(machine, 2)
            for _ in range(8):
                call(machine, s['sound'])
            self.configure_beam(machine, 3)
            for _ in range(8):
                call(machine, s['sound'])
            self.assertEqual(hardware.attacks, 2)
            self.assertEqual(hardware.pointers[3], s['beam_samples']+4096)
            call(machine, s['start_tune'])
            self.assertEqual(machine.mem_read(s['beam_kind'], 2), b'\0\0')
            self.assertEqual(machine.mem_read(VARIABLES+s['laser_audio_request'], 2), b'\0\0')
            for _ in range(50):
                call(machine, s['sound'])
            call(machine, s['quiet'])
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
                 (s['amiga_samples'], 53908), (s['beam_samples'], 8192),
                 (s['rcs_samples'], 4096), (s['engine_samples'], 1024)]
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
