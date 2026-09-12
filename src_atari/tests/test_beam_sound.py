"""Execute the real PSG driver: lasers, hangar launch, competing effects and shutdown."""
from pathlib import Path
import re
import struct
import unittest

from test_viewport import assemble
from test_raster import routine

try:
    from unicorn import (Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_PROT_READ,
                         UC_PROT_EXEC, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE)
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_A0, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_SR, UC_M68K_REG_PC, UC_M68K_REG_D0,
        UC_M68K_REG_D1, UC_M68K_REG_D2, UC_M68K_REG_D3, UC_M68K_REG_D4, UC_M68K_REG_D5,
        UC_M68K_REG_D6, UC_M68K_REG_D7, UC_M68K_REG_A1, UC_M68K_REG_A2,
        UC_M68K_REG_A3, UC_M68K_REG_A4, UC_M68K_REG_A5)
except ImportError:
    Uc = None

ROOT = Path(__file__).resolve().parents[1]
CODE, VARIABLES, STACK, STOP = 0x10000, 0x60000, 0xe0000, 0xf0000


class PSGTrace:
    def __init__(self, machine):
        self.registers = [0]*16
        self.selected = 0
        self.writes = []
        machine.hook_add(UC_HOOK_MEM_WRITE, self.write, begin=0xff8800, end=0xff8803)
        machine.hook_add(UC_HOOK_MEM_READ, self.read, begin=0xff8800, end=0xff8800)

    def write(self, machine, access, address, size, value, user):
        if address == 0xff8800:
            self.selected = value & 15
        elif address == 0xff8802:
            self.registers[self.selected] = value & 255
            self.writes.append((self.selected, value & 255))

    def read(self, machine, access, address, size, value, user):
        machine.mem_write(address, bytes([self.registers[self.selected]]))


@unittest.skipIf(Uc is None, 'optional sound tests require unicorn==2.1.4')
class BeamSoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        names = ['sound', 'quiet', 'fx', 'start_tune', 'beam_channel', 'beam_kind',
                 'laser_audio_request', 'laser_type', 'laser_temp', 'max_ltemp',
                 'cockpit_on', 'docked', 'game_frozen', 'game_over', 'controls_locked',
                 'user', 'volume', 'reg_volume', 'reg_tone', 'hold_chan',
                 'sfx_explosion', 'sfx_ecm', 'sfx_laser', 'sfx_hit', 'sound_type', 'random_seed', 'blue_danube',
                 'sfx_launch', 'chan_1', 'chan_2', 'chan_3', 'chn_active', 'service', 'do_launch',
                 'launch_ticks', 'launch_sequence', 'f_sequence']
        source = (ROOT/'asm/sounds.m68').read_text()
        source = re.sub(r'^\s*xref random\s*$', '', source, flags=re.M)
        source = source.replace('\tq_module sounds',
            '\torg $10000\n\tdc.l '+','.join(names)+'\nreturn: set *\n\trts')
        source += routine((ROOT/'asm/maths.m68').read_text(), 'random')
        music = (ROOT/'asm/music.m68').read_text()
        source += music[music.index('\tq_global blue_danube'):]
        # Execute the actual launch entry through its sound request, stopping
        # before 3D object creation. The two earlier display calls are stubbed.
        launch = routine((ROOT/'asm/effects.m68').read_text(), 'launch_sequence')
        source += '\teven\n' + launch[:launch.index('\tjsr alloc_object')]
        source += ('\trts\nq_effects_m68_7:\n\trts\n'
                   'front_view:\nclear_objects:\n\trts\n')
        cls.code, cls.symbols = assemble(source, names)

    def prepare(self, model, kind=2):
        self.machine = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.machine.ctl_set_cpu_model(model)
        self.machine.mem_map(0, 0x100000)
        self.machine.mem_map(0xff8000, 0x1000)
        self.machine.mem_write(CODE, self.code)
        self.machine.mem_protect(CODE, (len(self.code)+4095)//4096*4096,
                                 UC_PROT_READ | UC_PROT_EXEC)
        self.machine.reg_write(UC_M68K_REG_SR, 0x2700)
        self.machine.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.hardware = PSGTrace(self.machine)
        self.var('user', 0x100)
        self.var('cockpit_on', 1)
        self.var('laser_type', kind)
        self.var('laser_audio_request', kind)

    def var(self, name, value):
        self.machine.mem_write(VARIABLES+self.symbols[name], struct.pack('>H', value))

    def read(self, name, size=2):
        return int.from_bytes(self.machine.mem_read(VARIABLES+self.symbols[name], size), 'big')

    def call(self, name):
        self.machine.reg_write(UC_M68K_REG_A7, STACK-4)
        self.machine.mem_write(STACK-4, struct.pack('>I', STOP))
        self.machine.emu_start(self.symbols[name], STOP, count=200000)
        self.assertEqual(self.machine.reg_read(UC_M68K_REG_PC), STOP, name)
        self.assertEqual(self.machine.reg_read(UC_M68K_REG_A7), STACK)

    def channel(self):
        address = self.read('beam_channel', 4)
        register = int.from_bytes(self.machine.mem_read(address+self.symbols['reg_volume'], 2), 'big')
        return register-8

    def effect(self, name):
        self.machine.reg_write(UC_M68K_REG_D0, self.symbols[name])
        self.call('fx')

    def test_launch_trigger_obeys_effects_and_animation_settings(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for effects in (False, True):
                for sequence in (False, True):
                    self.prepare(model, 0)
                    self.var('user', ((int(effects) << 0 | int(sequence) << self.symbols['f_sequence']) << 8))
                    self.call('launch_sequence')
                    self.assertEqual(bool(self.read('chan_1')), effects and sequence)
                    for _ in range(30):
                        self.call('sound')
                    self.assertEqual(bool(self.hardware.registers[8]), effects and sequence)
                    self.call('quiet')

    def test_launch_pitch_envelope_registers_rng_and_final_silence(self):
        registers = [UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2, UC_M68K_REG_D3,
                     UC_M68K_REG_D4, UC_M68K_REG_D5, UC_M68K_REG_D6, UC_M68K_REG_D7,
                     UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A2, UC_M68K_REG_A3,
                     UC_M68K_REG_A4, UC_M68K_REG_A5, UC_M68K_REG_A6]
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.prepare(model, 0)
            for n, register in enumerate(registers[:-1]):
                self.machine.reg_write(register, 0xabc000+n*0x101)
            self.machine.reg_write(UC_M68K_REG_D0, self.symbols['sfx_launch'])
            before = [self.machine.reg_read(r) for r in registers]
            self.call('fx')
            self.assertEqual([self.machine.reg_read(r) for r in registers], before)
            seed = bytes(self.machine.mem_read(VARIABLES+self.symbols['random_seed'], 4))
            periods, levels = [], []
            for _ in range(self.symbols['launch_ticks']):
                self.call('sound')
                r = self.hardware.registers
                periods.append(r[0] | r[1] << 8)
                levels.append(r[8])
                self.assertEqual(r[9:11], [0, 0])
                self.assertTrue(0 <= r[6] <= 31)
                self.assertTrue(0 <= r[8] <= 14)
            self.assertGreater(periods[0], periods[-2]*1.9)
            self.assertEqual(levels[:28], sorted(levels[:28]))
            self.assertEqual(levels[27:170], [14]*143)
            self.assertEqual(levels[170:], sorted(levels[170:], reverse=True))
            self.assertEqual(levels[-1], 0)
            self.assertEqual(self.read('chan_1'), 0)
            self.assertEqual(bytes(self.machine.mem_read(VARIABLES+self.symbols['random_seed'], 4)), seed)
            self.assertFalse(any(reg >= 11 for reg, value in self.hardware.writes))
            for _ in range(300):
                self.call('sound')
                self.assertEqual(self.hardware.registers[8:11], [0, 0, 0])

    def test_launch_shutdown_preemption_and_channel_reuse(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for shutdown in ('quiet', 'disabled', 'preempt', 'music'):
                self.prepare(model, 0)
                self.effect('sfx_launch')
                for _ in range(40):
                    self.call('sound')
                if shutdown == 'quiet':
                    self.call('quiet')
                elif shutdown == 'disabled':
                    self.var('user', 0)
                    self.call('sound')
                elif shutdown == 'preempt':
                    for _ in range(3):
                        self.effect('sfx_hit')
                    for _ in range(10):
                        self.call('sound')
                    # Original impact effects finish by disabling their mixer
                    # and tone; their volume register alone need not be zero.
                    self.assertEqual([self.read(n) for n in ('chan_1', 'chan_2', 'chan_3')], [0, 0, 0])
                    self.assertEqual(self.hardware.registers[:6], [0]*6)
                    self.assertEqual(self.hardware.registers[7] & 0x38, 0x38)
                    self.call('quiet')
                else:
                    self.machine.reg_write(UC_M68K_REG_A0, self.symbols['blue_danube'])
                    self.call('start_tune')
                    for _ in range(20):
                        self.call('sound')
                    self.assertEqual(self.read('sound_type'), 1)
                    self.call('quiet')
                self.assertEqual(self.hardware.registers[8:11], [0, 0, 0], shutdown)
                self.var('user', 0x100)
                self.effect('sfx_launch')
                for _ in range(self.symbols['launch_ticks']+2):
                    self.call('sound')
                self.assertEqual(self.hardware.registers[8:11], [0, 0, 0])

    def test_held_beam_survives_effect_allocation_and_releases_to_silence(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for kind in (2, 3):
                self.prepare(model, kind)
                self.call('sound')
                channel = self.channel()
                address = self.read('beam_channel', 4)
                for frame in range(600):
                    if frame % 30 == 10:
                        self.effect('sfx_explosion')
                    if frame == 60:
                        self.effect('sfx_ecm')
                    self.call('sound')
                    self.assertEqual(self.read('beam_channel', 4), address)
                    self.assertEqual(self.read('beam_kind'), kind)
                    self.assertEqual(self.hardware.registers[8+channel], min((frame+2)*2, 12))
                    period = (self.hardware.registers[channel*2] |
                              (self.hardware.registers[channel*2+1] & 15) << 8)
                    low, high = (310, 322) if kind == 2 else (173, 179)
                    self.assertTrue(low <= period <= high, period)
                self.var('laser_audio_request', 0)
                volumes = []
                for _ in range(4):
                    self.call('sound')
                    volumes.append(self.hardware.registers[8+channel])
                self.assertEqual(volumes, [9, 6, 3, 0])
                self.assertEqual(self.read('beam_kind'), 0)
                self.assertEqual(self.read('beam_channel', 4), 0)
                self.effect('sfx_laser')
                self.call('sound')
                self.call('quiet')
                self.assertEqual(self.hardware.registers[8:11], [0]*3)

    def test_target_hits_are_audible_alongside_both_continuous_lasers(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for kind in (2, 3):
                self.prepare(model, kind)
                for _ in range(10):
                    self.call('sound')
                beam_channel = self.channel()
                for _ in range(8):
                    self.effect('sfx_hit')
                    self.call('sound')
                    registers = self.hardware.registers
                    audible_hits = [n for n in range(3) if n != beam_channel
                                    and registers[8+n] == 14
                                    and not registers[7] & (8 << n)]
                    self.assertTrue(audible_hits, 'target impact was not audible')
                    self.assertEqual(registers[8+beam_channel], 12)
                    self.assertFalse(registers[7] & (1 << beam_channel))
                    self.assertTrue(registers[7] & (8 << beam_channel))
                    for _ in range(10):
                        self.call('sound')
                self.call('quiet')
                self.assertEqual(self.hardware.registers[8:11], [0]*3)

    def test_shutdown_guards_and_weapon_switch(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for name, value in [('user', 0), ('cockpit_on', 0), ('docked', 1),
                                ('game_frozen', 1), ('game_over', 1), ('controls_locked', 1),
                                ('laser_temp', self.symbols['max_ltemp']), ('laser_type', 0)]:
                self.prepare(model)
                for _ in range(10):
                    self.call('sound')
                self.var(name, value)
                for _ in range(6):
                    self.call('sound')
                self.assertEqual(self.hardware.registers[8:11], [0]*3, name)
                self.assertEqual(self.read('laser_audio_request'), 0)
                self.assertEqual(self.read('beam_kind'), 0)
            self.prepare(model)
            for _ in range(10):
                self.call('sound')
            self.var('laser_type', 3)
            self.var('laser_audio_request', 3)
            for _ in range(10):
                self.call('sound')
            self.assertEqual(self.read('beam_kind'), 3)
            self.machine.reg_write(UC_M68K_REG_A0, self.symbols['blue_danube'])
            self.call('start_tune')
            self.assertEqual(self.read('beam_kind'), 0)
            self.assertEqual(self.read('laser_audio_request'), 0)
            for _ in range(50):
                self.call('sound')
            self.assertEqual(self.read('sound_type'), 1)
            self.call('quiet')
            self.assertEqual(self.read('laser_audio_request'), 0)
            self.assertEqual(self.hardware.registers[8:11], [0]*3)


if __name__ == '__main__':
    unittest.main()
