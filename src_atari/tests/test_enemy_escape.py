"""Run enemy escape and missile retaliation through the real 68K combat code.

Object allocation, copying, creation and model data are real. Random decisions
are controlled; unrelated rendering, audio, turning and identity services are
stubbed. Optional dependency: unicorn==2.1.4.
"""
from collections import deque
from pathlib import Path
import struct
import unittest

from test_raster import routine
from test_viewport import assemble, preamble

try:
    from unicorn import (Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE,
                         UC_PROT_READ, UC_PROT_EXEC)
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_A4, UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7,
        UC_M68K_REG_D0, UC_M68K_REG_PC, UC_M68K_REG_SR)
except ImportError:
    Uc = None

ROOT = Path(__file__).resolve().parents[1]
CODE, STOP, VARIABLES, ASSETS, STACK = 0x10000, 0x1000, 0x30000, 0x50000, 0x90000


@unittest.skipIf(Uc is None, 'enemy escape tests require unicorn==2.1.4')
class EnemyEscapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = {name: (ROOT/'asm'/f'{name}.m68').read_text()
               for name in ('combat', 'main', 'init')}
        groups = {
            'combat': ['laser_in_sights', 'check_hit', 'hit_reaction', 'low_energy',
                       'launch_escape', 'launch_missile', 'thargons'],
            'main': ['alloc_object', 'copy_object', 'create_object'],
            'init': ['relocate'],
        }
        stubs = ['random', 'random_direction', 'registration_assign', 'fx',
                 'disp_message', 'start_peel_off', 'start_run_off',
                 'explode_object', 'target_lost', 'release_cargo', 'prepare_vipers',
                 'get_dist']
        constants = '''objects obj_len max_objects flags in_use type ship_type
            cobra viper thargoid thargon worm missile typ_trader typ_pirate typ_shuttle
            typ_police typ_bounty typ_alien logic log_attack log_none log_cruise log_missile
            log_peel_off log_run_off next_logic act_runaway
            attack_type act_attack act_nothing no_missiles health pre_attack velocity vel_max
            this_xpos this_ypos this_zpos obj_range hits_rad hit_check in_sights
            obj_hit laser_power rating cloaking_on obj_ctr escape_prob missile_prob max_rating
            sfx_alert var_size
            xpos ypos zpos x_vector y_vector z_vector'''.split()
        names = [name for group in groups.values() for name in group] + stubs + constants
        assembly = preamble()
        assembly += src['combat'][src['combat'].index('slow_charge:'):
                                  src['combat'].index('\tq_module combat')]
        assembly += src['init'][src['init'].index('\trsset 0'):
                                src['init'].index('* ---- LOCAL STORAGE ----')]
        assembly += f'obj_data equ ${ASSETS:x}\n\torg ${CODE:x}\n'
        assembly += '\tdc.l '+','.join(names)+'\n'
        for module, funcs in groups.items():
            assembly += '\n'.join(routine(src[module], name) for name in funcs)
        assembly += '\n'.join(name+':\n\trts' for name in stubs)
        # Surface selection is unrelated to the combat probability under test.
        assembly += '\nrand:\n\tmoveq #0,d0\n\trts\ntext7:\n\tdc.w 0\n'
        cls.code, cls.s = assemble(assembly, names)
        # Compile the exact pre-fix routine in memory for behavioural comparison.
        # Neither the on-disk game source nor the distributed builds are changed.
        fix = '\tclr no_missiles(a5) ; abandoned hull cannot retaliate on this or later hits\n'
        if assembly.count(fix) != 1:
            raise AssertionError('Expected exactly one escape disarm instruction')
        cls.previous_code, cls.previous_symbols = assemble(assembly.replace(fix, ''), names)
        cls.assets, _ = assemble((ROOT/'asm/objects.m68').read_text(), [])

    def word(self, address, value=None):
        if value is None:
            return int.from_bytes(self.cpu.mem_read(address, 2), 'big')
        self.cpu.mem_write(address, struct.pack('>H', value & 65535))

    def long(self, address, value):
        self.cpu.mem_write(address, struct.pack('>I', value & 0xffffffff))

    def var(self, name, value=None):
        return self.word(VARIABLES+self.s[name], value)

    def obj(self, name, value=None, address=None):
        return self.word((self.ship if address is None else address)+self.s[name], value)

    def slot(self, index):
        return VARIABLES+self.s['objects']+index*self.s['obj_len']

    def call(self, name, a4=None):
        self.cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        self.cpu.reg_write(UC_M68K_REG_A4, self.ship if a4 is None else a4)
        self.cpu.reg_write(UC_M68K_REG_A5, self.ship)
        self.cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.cpu.reg_write(UC_M68K_REG_A7, STACK-4)
        self.long(STACK-4, STOP)
        self.cpu.emu_start(self.s[name], STOP, count=250000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC), STOP, name)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7), STACK, name)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A5), self.ship, name)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A6), VARIABLES, name)

    def prepare(self, model, role='typ_pirate', kind='cobra', previous=False):
        code = type(self).previous_code if previous else type(self).code
        self.s = type(self).previous_symbols if previous else type(self).s
        self.cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(model)
        self.cpu.mem_map(0, 0x100000)
        self.cpu.mem_write(CODE, code)
        self.cpu.mem_protect(CODE, (len(code)+4095) & ~4095,
                             UC_PROT_READ | UC_PROT_EXEC)
        self.cpu.mem_write(ASSETS, self.assets)
        self.ship = self.slot(0)
        self.random_values = deque()
        self.events = []
        def trace(cpu, address, size, user):
            if address == self.s['random']:
                cpu.reg_write(UC_M68K_REG_D0,
                              self.random_values.popleft() if self.random_values else 0)
            elif address == self.s['fx']:
                self.events.append(('sound', cpu.reg_read(UC_M68K_REG_D0) & 65535))
            elif address == self.s['disp_message']:
                self.events.append(('message',))
        for name in ('random', 'fx', 'disp_message'):
            self.cpu.hook_add(UC_HOOK_CODE, trace, begin=self.s[name], end=self.s[name])
        self.call('relocate')
        self.obj('flags', 1 << (8+self.s['in_use']))
        self.obj('type', self.s[kind])
        self.call('create_object')
        self.obj('ship_type', self.s[role])
        self.obj('logic', self.s['log_attack'])
        self.obj('attack_type', self.s['act_attack'])
        self.obj('no_missiles', 3)
        self.obj('health', 50)
        self.obj('pre_attack', 100)
        self.obj('velocity', 12)
        self.obj('hits_rad', 50)
        self.long(self.ship+self.s['this_zpos'], 3000)
        self.long(self.ship+self.s['obj_range'], 3000)
        for axis, value in zip('xyz', (100, -200, 3000)):
            self.long(self.ship+self.s[axis+'pos'], value)
        for axis, vector in zip('xyz', ((16384,0,0),(0,16384,0),(0,0,16384))):
            self.cpu.mem_write(self.ship+self.s[axis+'_vector'], struct.pack('>3h', *vector))
        self.var('hit_check', 1)
        self.var('in_sights', 1)
        self.var('laser_power', 10)
        self.cpu.mem_write(VARIABLES+self.s['obj_ctr']+self.s['viper'], b'\x02')

    def hit(self):
        self.var('obj_hit', 0)
        self.call('check_hit')

    def objects_of_type(self, kind):
        return [self.slot(i) for i in range(self.s['max_objects'])
                if self.obj('flags', address=self.slot(i)) & (1 << (8+self.s['in_use']))
                and self.obj('type', address=self.slot(i)) == self.s[kind]]

    def assert_no_missile_alert(self):
        self.assertNotIn(('sound', self.s['sfx_alert']), self.events)
        self.assertNotIn(('message',), self.events)

    def models(self):
        return (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020)

    def test_escape_prevents_missile_on_the_same_hit_for_all_eligible_roles(self):
        for model in self.models():
            for role in ('typ_trader', 'typ_pirate', 'typ_shuttle'):
                with self.subTest(cpu=model, role=role):
                    self.prepare(model, role)
                    movement = {name: bytes(self.cpu.mem_read(self.ship+self.s[name], size))
                                for name, size in [('velocity',2), ('xpos',4), ('ypos',4),
                                                   ('zpos',4), ('x_vector',6),
                                                   ('y_vector',6), ('z_vector',6)]}
                    self.hit()  # Random zero chooses both escape and missile, if allowed.
                    self.assertEqual(len(self.objects_of_type('worm')), 1)
                    self.assertEqual(self.objects_of_type('missile'), [])
                    self.assertEqual(self.obj('logic'), self.s['log_none'])
                    self.assertEqual(self.obj('attack_type'), self.s['act_nothing'])
                    self.assertEqual(self.obj('health'), 40)
                    for name, value in movement.items():
                        self.assertEqual(bytes(self.cpu.mem_read(self.ship+self.s[name], len(value))), value)
                    self.assert_no_missile_alert()

    def test_further_hits_on_abandoned_hull_keep_causing_damage_without_retaliation(self):
        for model in self.models():
            with self.subTest(cpu=model):
                self.prepare(model)
                self.call('launch_escape')
                for remaining_health in (40, 30, 20):
                    self.hit()
                    self.assertEqual(self.obj('health'), remaining_health)
                    self.assertEqual(self.objects_of_type('missile'), [])
                    self.assertEqual(len(self.objects_of_type('worm')), 1)
                    self.assertEqual(self.obj('logic'), self.s['log_none'])
                self.assert_no_missile_alert()

    def test_escape_does_not_remove_an_already_launched_missile(self):
        for model in self.models():
            with self.subTest(cpu=model):
                self.prepare(model)
                self.call('launch_missile')
                missile = self.objects_of_type('missile')[0]
                before = bytes(self.cpu.mem_read(missile, self.s['obj_len']))
                self.events.clear()
                self.hit()
                self.assertEqual(len(self.objects_of_type('worm')), 1)
                self.assertEqual(self.objects_of_type('missile'), [missile])
                self.assertEqual(bytes(self.cpu.mem_read(missile, self.s['obj_len'])), before)
                self.assert_no_missile_alert()

    def test_failed_escape_with_full_object_pool_preserves_armed_ship(self):
        for model in self.models():
            with self.subTest(cpu=model):
                self.prepare(model)
                for i in range(1, self.s['max_objects']):
                    self.obj('flags', 1 << (8+self.s['in_use']), address=self.slot(i))
                self.hit()
                self.assertEqual(self.objects_of_type('worm'), [])
                self.assertEqual(self.obj('no_missiles'), 3)
                self.assertEqual(self.obj('attack_type'), self.s['act_attack'])
                # A slot becomes free; a piloted ship can still retaliate.
                self.obj('flags', 0, address=self.slot(1))
                self.random_values.extend((self.s['escape_prob'], 0, 255))
                self.hit()
                self.assertEqual(len(self.objects_of_type('missile')), 1)
                self.assertEqual(self.obj('no_missiles'), 2)

    def test_failed_escape_roll_and_police_keep_normal_missile_retaliation(self):
        for model in self.models():
            for role, roll in (('typ_pirate', self.s['escape_prob']), ('typ_police', 0)):
                with self.subTest(cpu=model, role=role):
                    self.prepare(model, role)
                    self.random_values.extend((roll, 0, 255))
                    self.hit()
                    self.assertEqual(self.objects_of_type('worm'), [])
                    self.assertEqual(len(self.objects_of_type('missile')), 1)
                    self.assertEqual(self.obj('no_missiles'), 2)
                    self.assertEqual(self.obj('attack_type'), self.s['act_attack'])
                    self.assertIn(('sound', self.s['sfx_alert']), self.events)

    def test_thargoid_still_launches_thargons(self):
        for model in self.models():
            with self.subTest(cpu=model):
                self.prepare(model, 'typ_alien', 'thargoid')
                self.hit()
                self.assertEqual(len(self.objects_of_type('thargon')), 4)
                self.assertEqual(self.objects_of_type('worm'), [])
                self.assertEqual(self.objects_of_type('missile'), [])
                self.assertEqual(self.obj('no_missiles'), 0)

    def armed_hit(self, missile_roll=0):
        # Crew remains aboard; the last value suppresses the optional peel-off.
        self.random_values.clear()
        self.random_values.extend((255, missile_roll, 255) if self.obj('no_missiles')
                                  else (255, 255))
        self.hit()

    def assert_launch_result(self, expected, missiles_before=3):
        launched = self.objects_of_type('missile')
        self.assertEqual(len(launched), int(expected))
        self.assertEqual(self.obj('no_missiles'), missiles_before-int(expected))
        self.assertEqual(self.objects_of_type('worm'), [])
        self.assertGreater(self.obj('health'), 0)
        if not expected:
            self.assert_no_missile_alert()
            return
        self.assertEqual(self.events.count(('sound', self.s['sfx_alert'])), 1)
        self.assertEqual(self.events.count(('message',)), 1)
        missile = launched[0]
        self.assertEqual(self.obj('logic', address=missile), self.s['log_missile'])
        self.assertEqual(self.obj('flags', address=missile), 0x2100)
        self.assertEqual(self.obj('velocity', address=missile),
                         self.obj('vel_max', address=missile))
        self.assertGreater(self.obj('velocity', address=missile), 0)
        for name, size in [('xpos',4), ('ypos',4), ('zpos',4),
                           ('x_vector',6), ('y_vector',6), ('z_vector',6)]:
            self.assertEqual(bytes(self.cpu.mem_read(missile+self.s[name], size)),
                             bytes(self.cpu.mem_read(self.ship+self.s[name], size)))

    def test_damage_threshold_does_not_disarm_live_ship(self):
        for model in self.models():
            # pre_attack=100, damage=10: only health below 50 triggers defence.
            for health in (100, 61, 60, 59):
                with self.subTest(cpu=model, health_before=health):
                    self.prepare(model)
                    self.obj('health', health)
                    self.armed_hit()
                    self.assertEqual(self.obj('health'), health-10)
                    self.assert_launch_result(health-10 < 50)

    def test_probability_boundaries_at_every_player_rating_match_previous_code(self):
        for model in self.models():
            for rating in range(self.s['max_rating']+1):
                threshold = 15+4*rating
                for roll in (0, threshold-1, threshold, 255):
                    with self.subTest(cpu=model, rating=rating, roll=roll):
                        snapshots = []
                        for previous in (True, False):
                            self.prepare(model, previous=previous)
                            self.var('rating', rating)
                            self.armed_hit(roll)
                            self.assert_launch_result(roll < threshold)
                            snapshots.append((bytes(self.cpu.mem_read(VARIABLES, self.s['var_size'])),
                                              tuple(self.events), tuple(self.random_values)))
                        self.assertEqual(snapshots[0], snapshots[1])

    def test_launch_gates_preserve_ammunition_when_blocked(self):
        scenarios = [
            ('too_close', 1999, 0, 3, False, False),
            ('minimum_range', 2000, 0, 3, False, True),
            ('beyond_ai_laser_range', 14000, 0, 3, False, True),
            ('far_away', 30000, 0, 3, False, True),
            ('player_cloaked', 3000, 1, 3, False, False),
            ('no_ammunition', 3000, 0, 0, False, False),
            ('object_pool_full', 3000, 0, 3, True, False),
        ]
        for model in self.models():
            for name, distance, cloak, ammo, full, expected in scenarios:
                with self.subTest(cpu=model, scenario=name):
                    self.prepare(model)
                    self.long(self.ship+self.s['obj_range'], distance)
                    self.var('cloaking_on', cloak)
                    self.obj('no_missiles', ammo)
                    if full:
                        for i in range(1, self.s['max_objects']):
                            self.obj('flags', 0x0100, address=self.slot(i))
                    self.armed_hit()
                    self.assert_launch_result(expected, ammo)

    def test_live_roles_and_flight_states_match_previous_code(self):
        for model in self.models():
            for role in ('typ_trader', 'typ_pirate', 'typ_shuttle', 'typ_police', 'typ_bounty'):
                for state in ('log_attack', 'log_peel_off', 'log_run_off', 'log_cruise'):
                    with self.subTest(cpu=model, role=role, state=state):
                        snapshots = []
                        for previous in (True, False):
                            self.prepare(model, role, previous=previous)
                            self.obj('logic', self.s[state])
                            if role in ('typ_trader', 'typ_shuttle'):
                                self.obj('attack_type', self.s['act_runaway'])
                            # A new attack from cruising resets the health baseline;
                            # preserve this distinction from ships already fighting.
                            self.armed_hit()
                            expected = not (state == 'log_cruise' and
                                            role not in ('typ_trader', 'typ_shuttle'))
                            self.assert_launch_result(expected)
                            snapshots.append((bytes(self.cpu.mem_read(VARIABLES, self.s['var_size'])),
                                              tuple(self.events), tuple(self.random_values)))
                            self.assertEqual(self.objects_of_type('worm'), [])
                            self.assertEqual(self.obj('no_missiles'),
                                             3-len(self.objects_of_type('missile')))
                        self.assertEqual(snapshots[0], snapshots[1])

    def test_repeated_damage_fires_all_remaining_missiles_then_stops(self):
        for model in self.models():
            with self.subTest(cpu=model):
                self.prepare(model)
                self.obj('health', 64)
                self.obj('pre_attack', 128)
                self.var('laser_power', 1)
                # Reactions occur at health 63, 31, 15 and 7. The fourth has no ammo.
                for health_after in range(63, 6, -1):
                    self.armed_hit()
                    expected = sum(health_after <= threshold for threshold in (63,31,15))
                    self.assertEqual(self.obj('health'), health_after)
                    self.assertEqual(len(self.objects_of_type('missile')), expected)
                    self.assertEqual(self.obj('no_missiles'), 3-expected)
                    self.assertEqual(self.objects_of_type('worm'), [])
                self.assertEqual(self.events.count(('sound', self.s['sfx_alert'])), 3)
                self.assertEqual(self.events.count(('message',)), 3)


if __name__ == '__main__':
    unittest.main()
