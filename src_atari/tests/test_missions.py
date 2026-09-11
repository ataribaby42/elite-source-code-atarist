"""Exercise Mission 5 completion and unchanged combat behaviour on 68K.

Actual model sources, loader, allocation, explosions, damage, mission and
hyperdrive routines execute. Rendering/audio, missile travel, fragment
directions, cargo release and player shield damage are stubbed. This is not
a complete emulator playthrough. Optional dependency: unicorn==2.1.4.
"""
from pathlib import Path
import re
import struct
import unittest
from test_viewport import assemble, preamble

try:
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_PROT_READ, UC_PROT_EXEC
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_D0, UC_M68K_REG_A0, UC_M68K_REG_A4, UC_M68K_REG_A5,
        UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_PC, UC_M68K_REG_SR)
except ImportError:
    Uc = None

ROOT = Path(__file__).resolve().parents[1]
CODE, VARIABLES, ASSET, MISSILE, STACK, STOP = 0x10000, 0x30000, 0x50000, 0x80000, 0x90000, 0x1000

def compile_fixture(combat_source=None):
    src = {n: (ROOT / 'asm' / (n + '.m68')).read_text(encoding='utf-8')
           for n in ('missions', 'flight', 'orbit', 'main', 'init', 'combat', 'logic', 'maths', 'cockpit')}
    if combat_source is not None:
        src['combat'] = combat_source

    def routine(module, name):
        return re.search(r'^\s*q_subr ' + name + r'(?:,global)?\s*\n(.*?)'
                         r'(?=^\s*q_subr |\Z)', src[module], re.M | re.S)[0].split('; ---- LOCAL DATA ----', 1)[0]

    groups = {
        'missions': ['new_mission', 'dock_check', 'warning5', 'thanks5'],
        'flight': ['mission_check', 'start_hyperspace', 'collision', 'hit_station', 'beep'],
        'main': ['create_object', 'alloc_object', 'copy_object'],
        'init': ['relocate', 'reset_system'],
        'combat': ['check_hit', 'explode_object', 'add_kill', 'inc_record', 'launch_bomb'],
        'logic': ['do_locked'],
        'maths': ['random', 'rand'],
    }
    groups['combat'].append('laser_in_sights')
    names = [n for group in groups.values() for n in group]
    names += '''audit_scheduler audit_station laser_info mission next_mission jump_count mission_rate
    galaxy_no station_rec station_destroyed equip ecm_jammer health energy_max nodes type dodec
    spacestn obj_len flags logic log_exploding log_rotating this_zpos obj_range obj_hit hit_check
    in_sights laser_power obj_ctr viper target ecm_fitted ecm_jammed ecm_on random_seed
    exploded collided count_down last_screen req_planet current fuel missile_state
    energy_bomb witch_space objects max_objects missile thargoid thargon constr cougar cobra
    planet sun remove in_use kill_rating score rating police_record registration_id obj_size
    mother this_obj log_cruise attack_type act_nothing energy max_energy front_shield aft_shield
    typ_trader ship_type force exp_timer next_logic invincible no_bounty no_missiles
    trader_count pirate_count
    '''.split()
    assembly = preamble() + '\tinclude "bitlist.m68"\n'
    for module, start in [('combat', 'slow_charge:'), ('flight', 'torus_dur:'), ('logic', 'launch_dist:')]:
        assembly += src[module][src[module].index(start):src[module].index('\tq_module ' + module)]
    assembly += src['init'][src['init'].index('\trsset 0'):src['init'].index('* ---- LOCAL STORAGE ----')]
    assembly += 'max_mission equ 5\nobj_data equ $50000\n'
    assembly += '\torg $10000\n\tdc.l ' + ','.join(names) + '\n'
    for module, funcs in groups.items():
        assembly += '\n'.join(routine(module, n) for n in funcs)
    assembly += '\naudit_scheduler:\n' + src['flight'].split('q_flight_m68_99:\n', 1)[1].split('\tcmp #$14,mission(a6)', 1)[0] + '\trts\n'
    assembly += '\naudit_station:\n' + src['orbit'].split('q_orbit_m68_4:\n', 1)[1].split('; Create sun.', 1)[0] + '\trts\n'
    assembly += re.search(r'^laser_info:\s*\n(?:\s*dc [^\n]+\n)+', src['cockpit'], re.M)[0]
    assembly += '''
    get_dist:
        moveq #0,d2
        rts
    fuel_distance:
        moveq #1,d0
        rts
    '''
    stubs = '''mission_screen init_cursor status offer1 gone1 gone2 thanks1 thanks2 offer3 thanks3
    warning4 registration_assign start_peel_off target_lost release_cargo low_energy
    prepare_vipers disp_message random_direction fx auto_pilot speed_control
    check_inflight text_out salvage reduce_shields quiet set_roll_angles set_climb_angles'''.split()
    assembly += '\n'.join(n + ':\n\trts' for n in stubs)
    assembly += '\n' + '\n'.join(n + ':' for n in ('mission_table', 'text1', 'text2', 'text5', 'text13', 'text14', 'text20'))
    assembly += '\n\tdc.w 0\n'
    assembly += re.search(r'^rating_bands:.*?^no_colours:.*$', src['combat'], re.M | re.S)[0].split('; List of positions for pirates')[0]
    assembly += re.search(r'^reset_table:.*?(?=^\* Default game data)', src['init'], re.M | re.S)[0]
    code, s = assemble(assembly, names)
    assets, _ = assemble((ROOT / 'asm/objects.m68').read_text(encoding='utf-8'), [])
    return code, s, assets

class Machine:
    def __init__(self, model):
        self.cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(model)
        self.cpu.mem_map(0, 0x100000)
        self.cpu.mem_write(CODE, code)
        self.cpu.mem_protect(CODE, (len(code) + 4095) & ~4095, UC_PROT_READ | UC_PROT_EXEC)
        self.cpu.mem_write(ASSET, assets)
        self.station = VARIABLES + s['station_rec']
        self.call('relocate')

    def word(self, address, value=None):
        if value is None:
            return int.from_bytes(self.cpu.mem_read(address, 2), 'big')
        self.cpu.mem_write(address, struct.pack('>H', value & 65535))

    def long(self, address, value):
        self.cpu.mem_write(address, struct.pack('>I', value & 0xffffffff))

    def var(self, name, value=None):
        return self.word(VARIABLES + s[name], value)

    def obj(self, name, value=None):
        return self.word(self.station + s[name], value)

    def call(self, name, a5=None):
        self.cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        self.cpu.reg_write(UC_M68K_REG_A4, self.station)
        self.cpu.reg_write(UC_M68K_REG_A5, self.station if a5 is None else a5)
        self.cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.cpu.reg_write(UC_M68K_REG_A7, STACK - 4)
        self.long(STACK - 4, STOP)
        self.cpu.emu_start(s[name], STOP, count=100000)
        assert self.cpu.reg_read(UC_M68K_REG_PC) == STOP, name
        assert self.cpu.reg_read(UC_M68K_REG_A7) == STACK, name
        assert self.cpu.reg_read(UC_M68K_REG_A6) == VARIABLES, name

    def start(self):
        self.var('next_mission', 5)
        self.var('jump_count', 1)
        self.var('galaxy_no', 1)
        self.call('audit_scheduler')
        assert (self.var('mission'), self.var('next_mission'), self.var('jump_count')) == (0x50, 6, 64)
        self.call('dock_check')
        assert self.var('mission') == 0x51
        self.call('mission_check')
        assert self.var('mission') == 0x52
        self.call('audit_station')
        self.obj('flags', 0x100)
        for slot, kind in ((0, 'planet'), (2, 'sun')):
            self.word(VARIABLES+s['objects']+slot*s['obj_len'], 0x100)
            self.word(VARIABLES+s['objects']+slot*s['obj_len']+s['type'], s[kind])
        assert self.obj('type') == s['dodec']
        assert self.obj('health') == self.obj('energy_max') == 1024
        assert self.obj('ecm_fitted') == 65535
        self.var('hit_check', 1)
        self.var('in_sights', 1)
        self.long(self.station + s['this_zpos'], 3000)
        self.var('last_screen', 1)
        self.var('req_planet', 1)
        self.word(VARIABLES + s['equip'] + s['fuel'], 70)
        self.call('start_hyperspace')
        assert self.var('count_down') == 0, 'Mission 5 should block normal hyperdrive'

    def result(self):
        state = self.var('mission')
        destroyed = self.var('station_destroyed')
        exploding = self.obj('logic') == s['log_exploding']
        self.call('start_hyperspace')
        countdown = self.var('count_down')
        if state == 0x53:
            self.call('mission_check')
            assert self.var('mission') == 0x53
            self.call('audit_station')
            assert self.obj('type') == s['spacestn']
            self.call('reset_system')
            assert self.var('station_destroyed') == 0
            assert self.var('mission') == 0x53
        self.call('dock_check')
        return dict(mission_after_kill=f'{state:02X}', station_destroyed=destroyed,
                    exploding=exploding, hyperdrive_countdown=countdown,
                    mission_after_dock=f'{self.var("mission"):02X}',
                    ecm_jammer=self.word(VARIABLES + s['equip'] + s['ecm_jammer']))


@unittest.skipIf(Uc is None, 'mission CPU tests require unicorn==2.1.4')
class MissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global code, s, assets
        code, s, assets = compile_fixture()

    def machines(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            yield Machine(model)

    def complete(self, m):
        self.assertEqual(m.result(), dict(mission_after_kill='53', station_destroyed=65280,
            exploding=True, hyperdrive_countdown=10, mission_after_dock='00', ecm_jammer=1))
        self.assertEqual(m.var('next_mission'), 6)
        # No repeated reward: remove it and revisit the dock check.
        m.word(VARIABLES + s['equip'] + s['ecm_jammer'], 0)
        m.call('dock_check')
        self.assertEqual(m.word(VARIABLES + s['equip'] + s['ecm_jammer']), 0)
        m.call('new_mission')
        self.assertEqual((m.var('mission'), m.var('next_mission')), (0, 6))

    def test_scheduler_and_all_four_lasers_complete_once_with_original_damage(self):
        for m in self.machines():
            for kind, power, hits in ((0, 5, 205), (1, 7, 147), (2, 9, 114), (3, 11, 94)):
                with self.subTest(cpu=m.cpu.ctl_get_cpu_model(), kind=kind):
                    m.__init__(m.cpu.ctl_get_cpu_model())
                    m.start()
                    self.assertEqual(int.from_bytes(m.cpu.mem_read(s['laser_info'] + kind*6 + 2, 2), 'big'), power)
                    m.var('laser_power', power)
                    for shot in range(hits):
                        m.var('obj_hit', 0)
                        m.call('check_hit')
                        self.assertEqual(m.var('mission'), 0x53 if shot == hits-1 else 0x52)
                        self.assertEqual(m.obj('health'), (1024-(shot+1)*power) & 65535)
                    self.complete(m)

    def test_missile_arrival_completes_with_sparse_partial_and_full_object_pool(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for occupied in (4, 26, 30):
                with self.subTest(cpu=model, occupied=occupied):
                    m = Machine(model)
                    m.start()
                    # Reserved world slots and the missile are occupied in flight.
                    for slot in range(occupied):
                        m.word(VARIABLES + s['objects'] + slot*s['obj_len'], 0x100)
                    missile = VARIABLES + s['objects'] + (occupied-1)*s['obj_len']
                    m.word(missile + s['type'], s['missile'])
                    m.long(missile + s['target'], m.station)
                    m.long(VARIABLES + s['random_seed'], 0x12345678)
                    before = bytes(m.cpu.mem_read(VARIABLES + s['objects'], s['obj_size']))
                    m.call('do_locked', a5=missile)
                    self.assertTrue(m.cpu.mem_read(missile, 1)[0] & (1 << s['remove']))
                    # Existing unrelated slots must be byte-for-byte intact.
                    for slot in range(occupied):
                        if slot not in (1, occupied-1):
                            start = slot*s['obj_len']
                            self.assertEqual(bytes(m.cpu.mem_read(VARIABLES+s['objects']+start, s['obj_len'])),
                                             before[start:start+s['obj_len']])
                    self.complete(m)

    def test_collision_finisher_completes_without_changing_damage(self):
        for m in self.machines():
            m.start()
            m.var('laser_power', 5)
            for _ in range(204):
                m.var('obj_hit', 0)
                m.call('check_hit')
            self.assertEqual(m.obj('health'), 4)
            self.assertEqual(m.var('mission'), 0x52)
            m.long(m.station + s['obj_range'], 0)
            m.call('collision')
            self.assertEqual(m.obj('health'), (4-25) & 65535)
            self.complete(m)

    def test_bomb_preserves_station_and_mission_but_destroys_nearby_ship(self):
        for m in self.machines():
            m.start()
            # The three reserved records are skipped independently of their model.
            for slot in (0, 2):
                m.word(VARIABLES + s['objects'] + slot*s['obj_len'], 0x100)
            victim = VARIABLES + s['objects'] + 3*s['obj_len']
            m.word(victim + s['flags'], 0x100)
            m.word(victim + s['type'], s['viper'])
            m.word(VARIABLES + s['equip'] + s['energy_bomb'], 1)
            protected = bytes(m.cpu.mem_read(VARIABLES + s['objects'], 3*s['obj_len']))
            m.call('launch_bomb')
            self.assertEqual(bytes(m.cpu.mem_read(VARIABLES+s['objects'], 3*s['obj_len'])), protected)
            self.assertEqual(m.word(victim+s['logic']), s['log_exploding'])
            self.assertEqual((m.var('mission'), m.var('station_destroyed')), (0x52, 0))
            self.assertEqual(m.word(VARIABLES+s['equip']+s['energy_bomb']), 0)
            m.call('start_hyperspace')
            self.assertEqual(m.var('count_down'), 0)

    def test_only_active_mission5_and_first_station_explosion_can_advance(self):
        for m in self.machines():
            for state in (0, 0x10, 0x15, 0x16, 0x21, 0x33, 0x41, 0x50, 0x51, 0x53, 0x54):
                m.var('mission', state)
                m.var('station_destroyed', 0)
                m.obj('type', s['dodec'])
                m.obj('logic', s['log_rotating'])
                m.var('collided', 1)  # suppress debris; mission guard is independent
                m.call('explode_object')
                self.assertEqual((m.var('mission'), m.var('station_destroyed')), (state, 0))
            m.var('mission', 0x52)
            m.obj('logic', s['log_rotating'])
            m.call('explode_object')
            self.assertEqual((m.var('mission'), m.var('station_destroyed')), (0x53, 0xff00))
            m.call('explode_object')
            self.assertEqual(m.var('mission'), 0x53)
            # Even if an active state is reloaded, a previously exploding object is no new kill.
            m.var('mission', 0x52)
            m.var('station_destroyed', 0)
            m.call('explode_object')
            self.assertEqual((m.var('mission'), m.var('station_destroyed')), (0x52, 0))

    def test_other_types_do_not_complete_mission5_and_explosion_preserves_registers(self):
        for m in self.machines():
            for kind in ('spacestn', 'viper', 'thargoid', 'thargon', 'constr', 'cougar', 'cobra'):
                m.var('mission', 0x52)
                m.obj('type', s[kind])
                m.obj('logic', s['log_rotating'])
                m.var('collided', 1)
                m.call('explode_object')
                self.assertEqual((m.var('mission'), m.var('station_destroyed')), (0x52, 0))
            for kind in ('dodec', 'viper'):
                m.obj('type', s[kind])
                m.obj('logic', s['log_rotating'])
                m.var('mission', 0x52)
                m.var('collided', 1)
                registers = {UC_M68K_REG_D0+i: 0x12345600+i for i in range(8)}
                registers.update({UC_M68K_REG_A0+i: 0x80000+i*16 for i in range(4)})
                registers.update({UC_M68K_REG_A4: m.station, UC_M68K_REG_A5: m.station,
                                  UC_M68K_REG_A6: VARIABLES})
                for reg, value in registers.items():
                    m.cpu.reg_write(reg, value)
                m.call('explode_object')
                self.assertEqual({reg: m.cpu.reg_read(reg) for reg in registers}, registers)

    def test_constrictor_laser_completion_score_and_normal_station_immunity(self):
        for m in self.machines():
            m.var('mission', 0x15)
            m.obj('type', s['constr'])
            m.obj('health', 10)
            m.obj('kill_rating', 5000)
            m.var('hit_check', 1)
            m.var('in_sights', 1)
            m.var('laser_power', 11)
            m.long(m.station+s['this_zpos'], 3000)
            m.call('check_hit')
            self.assertEqual((m.var('mission'), m.var('station_destroyed')), (0x16, 0))
            self.assertEqual(int.from_bytes(m.cpu.mem_read(VARIABLES+s['score'], 4), 'big'), 5000)
            m.var('mission', 0x52)
            m.var('obj_hit', 0)
            m.obj('type', s['spacestn'])
            m.obj('logic', s['log_rotating'])
            m.obj('health', 1024)
            m.call('check_hit')
            self.assertEqual(m.obj('health'), 1024)
            self.assertEqual(m.obj('logic'), s['log_rotating'])
            self.assertEqual((m.var('mission'), m.var('station_destroyed')), (0x52, 0))

    def test_scheduler_does_not_interrupt_other_missions_or_start_in_galaxy1(self):
        for m in self.machines():
            for galaxy, active in [(0, 0), (1, 0x15), (1, 0x21), (1, 0x33), (1, 0x41), (1, 0x52)]:
                m.var('galaxy_no', galaxy)
                m.var('mission', active)
                m.var('next_mission', 5)
                m.var('jump_count', 1)
                m.call('audit_scheduler')
                self.assertEqual((m.var('mission'), m.var('next_mission'), m.var('jump_count')), (active, 5, 1))

if __name__ == '__main__':
    unittest.main()
