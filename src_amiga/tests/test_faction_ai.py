"""Faction AI targeting on MC68000/MC68020.

The real routines are assembled out of asm/ with vasm and executed under
Unicorn. World services the game would normally provide are stubbed.
Optional dependency: unicorn==2.1.4.
"""
from pathlib import Path
import re
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from test_raster import routine
from test_viewport import assemble, preamble

try:
    from unicorn import (Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE,
                         UC_PROT_READ, UC_PROT_EXEC)
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_A4, UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7,
        UC_M68K_REG_A0, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2,
        UC_M68K_REG_D7,
        UC_M68K_REG_PC,
        UC_M68K_REG_SR)
except ImportError:
    Uc = None

CODE, STOP, VARIABLES, STACK = 0x10000, 0x1000, 0x30000, 0x90000
CPUS = (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020) if Uc else ()

# Routines pulled out of the real sources. Later tasks extend these lists.
COMBAT = ['is_combat_ship', 'is_hostile', 'chebyshev_range', 'pick_target',
          'combat_state', 'retarget', 'damage_target', 'explode_object',
          'low_energy', 'hit_reaction', 'thargons', 'launch_missile',
          'target_lost', 'drop_missiles', 'check_missile', 'ecm',
          'ecm_check', 'create_thargoids', 'encounter_type',
          'encounter_skip', 'encounter_template', 'encounter_place',
          'encounter_offset', 'encounter_member', 'random_encounter',
          'create_pirates', 'launch_vipers', 'check_hit',
          'check_police']
LOGIC = ['target_coords', 'validate_target', 'target_range_calc',
         'ai_laser_aim', 'ai_laser_miss_threshold', 'do_attack',
         'peel_off_check', 'speed_control', 'do_locked']

CONSTANTS = [
    'objects', 'obj_len', 'max_objects', 'type', 'flags', 'in_use', 'remove',
    'angry', 'logic', 'log_attack', 'log_cruise', 'log_exploding',
    'ship_type', 'attack_type', 'act_attack', 'act_runaway', 'target',
    'no_target', 'xpos', 'ypos', 'zpos', 'obj_range', 'health', 'pre_attack',
    'on_course', 'this_obj', 'radar_range', 'first_combat', 'last_combat',
    'typ_trader', 'typ_pirate', 'typ_shuttle', 'typ_police', 'typ_alien',
    'viper', 'thargon', 'thargoid', 'cougar', 'constr', 'spacestn', 'cobra',
    'transporter', 'retarget_slot', 'npc_kill', 'target_range', 'krait',
    'python', 'log_peel_off', 'log_run_off', 'log_avoid', 'log_launch',
    'log_fly_planet', 'log_locked', 'log_timer', 'no_bounty', 'collided',
    'no_missiles', 'rating', 'peel_prob', 'velocity', 'vel_max', 'turn_rate',
    'mood', 'ai_laser', 'approach', 'radar_obj', 'cloaking_on',
    'controls_locked', 'fire_range', 'next_logic', 'npc_hit', 'act_nothing',
    'log_none', 'npc_launch_prob', 'missile_prob', 'mother', 'z_vector',
    'unit', 'log_ai_missile', 'log_missile', 'missile', 'npc_launch_prob',
    'missile_state', 'target_ptr', 'obj_rad', 'ecm_fitted', 'ecm_jammed',
    'sfx_alert', 'f_missiles', 'ecm_on', 'who_ecm', 'shields_fx',
    'exploded', 'loop_ctr', 'point', 'under_attack', 'obj_ctr',
    'tharg_max', 'role_pirate', 'role_trader', 'role_thargoid', 'role_viper',
    'role_bounty', 'spacing2', 'encounter_pirates', 'encounter_traders',
    'no_encounter_pirates', 'no_encounter_traders', 'gecko', 'moray', 'adder',
    'mamba', 'asp', 'sidewinder', 'anaconda', 'cobra_mk1', 'ferdelance',
    'boa', 'wolf', 'encounter_groups', 'splanet', 'govern',
    'encounter_lead', 'encounter_seat', 'rand_limit', 'rand_range',
    'mission', 'pirate_ctr', 'pirate_count', 'sfx_explosion',
    'npc_damage', 'launch_count', 'launch_rate', 'police_hunt',
    'hit_check', 'obj_hit', 'laser_power', 'police_record',
]

# Faction relation from the spec, section 4.2.
HOSTILITY = {
    'typ_trader':  {'typ_pirate', 'typ_alien'},
    'typ_pirate':  {'typ_trader', 'typ_shuttle', 'typ_police', 'typ_alien'},
    'typ_shuttle': {'typ_pirate', 'typ_alien'},
    'typ_police':  {'typ_pirate', 'typ_alien'},
    'typ_alien':   {'typ_trader', 'typ_pirate', 'typ_shuttle', 'typ_police'},
}


def ship_table():
    """Yield (name, type number, ship_type, attack_type) for each modelled object."""
    table = (ROOT / 'asm/objects.m68').read_text().split('include')[0]
    data = (ROOT / 'asm/objects.dat').read_text()
    for number, name in enumerate(re.findall(r'^\s*dc\.l\s+(\w+)\s*$', table, re.M)):
        record = re.search(r'^' + name + r':\s+dc\.l\s+\w+\s+dc\.l\s+\w+\s+'
                           r'dc\.l\s+\w+\s+dc\s+([^\n]+)', data, re.M)
        if record:
            values = [int(v) for v in record[1].split(',')]
            yield name, number, values[9], values[10]


@unittest.skipIf(Uc is None, 'optional faction AI tests require unicorn==2.1.4')
class FactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = {name: (ROOT / 'asm' / (name + '.m68')).read_text()
               for name in ('combat', 'logic')}
        names = COMBAT + LOGIC + list(cls.STUBBED)
        combat, logic = src['combat'], src['logic']
        assembly = preamble()
        assembly += combat[combat.index('slow_charge:'):combat.index('\tq_module combat')]
        assembly += logic[logic.index('fire_range:'):logic.index('\tq_module logic')]
        assembly += '\torg $10000\n\tdc.l ' + ','.join(names + CONSTANTS) + '\n'
        assembly += '\n'.join(routine(combat, name) for name in COMBAT)
        assembly += '\n'.join(routine(logic, name) for name in LOGIC)
        # EXPLODE_OBJECT indexes the real platlet colour table.
        assembly += '\n' + re.search(
            r'^platlet_colours:\s*\n(?:\s*dc [^\n]+\n)+\s*no_colours: equ [^\n]+',
            combat, re.M)[0] + '\n'
        # DO_ATTACK indexes the rating damage table in LOGIC's local data.
        assembly += '\n' + re.search(
            r'^damage:\s*\n\s*dc\.w [^\n]+', logic, re.M)[0] + '\n'
        # TARGET_LOST and LAUNCH_MISSILE print COMBAT's own strings.
        for name in ('text1', 'text7'):
            assembly += '\n' + re.search(
                r'^%s: dc\.b [^\n]+' % name, combat, re.M)[0]
        assembly += '\n\teven\n'
        assembly += cls.stubs()
        cls.code, cls.symbols = assemble(assembly, names + CONSTANTS)
        cls.symbols['no_target'] -= 1 << 32  # dc.l -1 reads back unsigned

    #: Distance GET_DIST reports, so the ship path can be checked without
    #: assembling the whole maths module.
    STUB_DISTANCE = 12345

    #: Subroutines the assembled code calls, stubbed so the tests can observe
    #: *whether* they ran rather than emulate the whole world.
    STUBBED = ('add_kill', 'inc_record', 'release_cargo',
               'alloc_object', 'copy_object', 'create_object',
               'random_direction', 'move_object', 'rand', 'random',
               'disp_message', 'fx', 'get_dist', 'launch_escape',
               'start_peel_off', 'start_run_off',
               'auto_pilot', 'reduce_shields', 'local_x_rotate',
               'local_z_rotate', 'unarm_missile', 'reduce_energy',
               'random_position', 'orbit', 'vector_pos', 'pirate_attack',
               'launch_ship', 'prepare_vipers', 'laser_in_sights')

    #: Assembled routines worth tracing as well as the stubs.
    WATCHED = STUBBED + ('thargons', 'launch_missile', 'target_lost')

    #: Scratch words outside CODE and VARIABLES that steer the two stubs the
    #: assembled routines actually take decisions on. A fresh Unicorn instance
    #: zeroes them, which is the behaviour every other test in this file wants.
    ALLOC_BUDGET, RANDOM_VALUE, ALLOC_POOL = 0x50000, 0x50002, 0x51000
    #: GET_DIST's answer. PREPARE seeds it with STUB_DISTANCE, so a test only
    #: plants a value when the distance itself is what it is exercising.
    DIST_VALUE = 0x50004
    #: RAND's 16-bit input, before it is scaled into the caller's range. Zero
    #: gives zero for every range, which is what every earlier test expects.
    RAND_VALUE = 0x50008

    @classmethod
    def stubs(cls):
        """World services this suite does not exercise."""
        # ALLOC_OBJECT hands out a record only while the test has granted a
        # budget. At the default zero it reports "no records left" (carry
        # clear), so EXPLODE_OBJECT takes its GIVE_UP path instead of building
        # platlets. RANDOM likewise returns whatever the test has planted.
        # The real routine returns only A4 and the carry flag, so the stub
        # preserves D0 as well: THARGONS counts its loop in it across the call.
        # It also leaves TARGET at NO_TARGET, as MAIN's does, because what a
        # freshly allocated record holds there decides who a new ship fights.
        text = ('\nalloc_object:\n'
                '\ttst.w $%x\n'
                '\tbeq.s .none\n'
                '\tmove.l d0,-(sp)\n'
                '\tsubq.w #1,$%x\n'
                '\tmove.w $%x,d0\n'
                '\tmulu #obj_len,d0\n'
                '\tlea $%x,a4\n'
                '\tadd.l d0,a4\n'
                '\tmove.l #no_target,target(a4)\n'
                '\tmove.l (sp)+,d0\n'
                '\tori #1,ccr\n'
                '\trts\n'
                '.none:\n'
                '\tandi #$fe,ccr\n'
                '\trts\n' % (cls.ALLOC_BUDGET, cls.ALLOC_BUDGET,
                             cls.ALLOC_BUDGET, cls.ALLOC_POOL))
        text += '\nget_dist:\n\tmove.l $%x,d2\n\trts\n' % cls.DIST_VALUE
        # ORBIT answers a fixed position behind the player, so
        # ENCOUNTER_PLACE's mirroring into the front hemisphere is exercised.
        text += ('\norbit:\n'
                 '\tmove.l #1234,xpos(a4)\n'
                 '\tmove.l #-5678,ypos(a4)\n'
                 '\tmove.l #-20000,zpos(a4)\n'
                 '\trts\n')
        text += ('\nrandom:\n\tmoveq #0,d0\n\tmove.w $%x,d0\n\trts\n'
                 % cls.RANDOM_VALUE)
        # RAND scales a 16-bit value into 0..D2-1 exactly as MATHS does, so a
        # test can ask for a chosen index instead of a chosen bit pattern.
        text += ('\nrand:\n'
                 '\tmoveq #0,d0\n'
                 '\tmove.w $%x,d0\n'
                 '\tmulu d2,d0\n'
                 '\tswap d0\n'
                 '\trts\n' % cls.RAND_VALUE)
        text += ('\nlaser_in_sights:\n'
                 '\tmoveq #1,d0\n'
                 '\trts\n')
        done = {'alloc_object', 'get_dist', 'random', 'rand', 'orbit',
                'laser_in_sights'}
        return text + ''.join('\n%s:\n\trts\n' % name for name in cls.STUBBED
                              if name not in done)

    def prepare(self, model=None):
        self.cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(model or CPUS[0])
        self.cpu.mem_map(0, 0x100000)
        self.cpu.mem_write(CODE, self.code)
        self.cpu.mem_protect(CODE, (len(self.code) + 4095) // 4096 * 4096,
                             UC_PROT_READ | UC_PROT_EXEC)
        self.cpu.mem_write(VARIABLES, bytes(0x8000))
        self.long(self.DIST_VALUE, self.STUB_DISTANCE)
        self.slot = lambda n: (VARIABLES + self.symbols['objects']
                               + n * self.symbols['obj_len'])
        self.ship, self.other = self.slot(0), self.slot(1)

    def word(self, address, value):
        self.cpu.mem_write(address, struct.pack('>H', value & 0xffff))

    def long(self, address, value):
        self.cpu.mem_write(address, struct.pack('>I', value & 0xffffffff))

    def var(self, name, value, size=2):
        (self.long if size == 4 else self.word)(VARIABLES + self.symbols[name], value)

    def field(self, slot, name, value, size=2):
        (self.long if size == 4 else self.word)(slot + self.symbols[name], value)

    def read(self, slot, name, size=2):
        value = int.from_bytes(self.cpu.mem_read(slot + self.symbols[name], size), 'big')
        return value - (1 << 8 * size) if value >> (8 * size - 1) else value

    def call(self, name, a4=None, d0=0, d1=0):
        self.cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        self.cpu.reg_write(UC_M68K_REG_D0, d0)
        self.cpu.reg_write(UC_M68K_REG_D1, d1)
        self.cpu.reg_write(UC_M68K_REG_A4, a4 if a4 is not None else self.other)
        self.cpu.reg_write(UC_M68K_REG_A5, self.ship)
        self.cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.cpu.reg_write(UC_M68K_REG_A7, STACK - 4)
        self.long(STACK - 4, STOP)
        self.cpu.emu_start(self.symbols[name], STOP, count=2000000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC), STOP, name)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7), STACK, name)
        return self.cpu.reg_read(UC_M68K_REG_D0) & 0xffff

    def call_with(self, name, a5, a4):
        """Like call, but with both object registers chosen by the caller."""
        self.cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        self.cpu.reg_write(UC_M68K_REG_A4, a4)
        self.cpu.reg_write(UC_M68K_REG_A5, a5)
        self.cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.cpu.reg_write(UC_M68K_REG_A7, STACK - 4)
        self.long(STACK - 4, STOP)
        self.cpu.emu_start(self.symbols[name], STOP, count=2000000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC), STOP, name)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7), STACK, name)
        return self.cpu.reg_read(UC_M68K_REG_D0)

    def place(self, slot, x, y, z):
        for axis, value in zip('xyz', (x, y, z)):
            self.field(slot, axis + 'pos', value, 4)

    def set_flags(self, slot, *bits):
        """FLAGS is a word, but BTST addresses its high byte."""
        value = 0
        for bit in bits:
            value |= 1 << self.symbols[bit]
        self.field(slot, 'flags', value << 8)

    def ship_at(self, slot, kind, x, y, z, ship_type='typ_pirate',
                attack='act_attack'):
        """Put a usable in-use ship of type `kind` into a slot."""
        self.set_flags(slot, 'in_use')
        self.field(slot, 'type', self.symbols[kind])
        self.field(slot, 'ship_type', self.symbols[ship_type])
        self.field(slot, 'attack_type', self.symbols[attack])
        self.field(slot, 'logic', self.symbols['log_cruise'])
        self.field(slot, 'target', self.symbols['no_target'], 4)
        self.place(slot, x, y, z)
        self.field(slot, 'obj_range', max(abs(x), abs(y), abs(z)), 4)

    PASSIVE = ('log_cruise', 'log_fly_planet')
    FIGHTING = ('log_attack', 'log_peel_off', 'log_run_off', 'log_avoid')
    LOCKED = ('log_launch', 'log_exploding', 'log_locked', 'log_timer')

    def scratch(self, address, value):
        """Plant a word the stubs read: ALLOC_BUDGET or RANDOM_VALUE."""
        self.cpu.mem_write(address, struct.pack('>H', value & 0xffff))

    def roll(self, index, count):
        """Plant the RAND input that yields `index` out of `count`."""
        self.scratch(self.RAND_VALUE, -(-index * 65536 // count) if index else 0)

    def watch_sounds(self):
        """Record the effect number each Q_SFX asks FX for."""
        self.sounds = []

        def trace(cpu, address, size, user):
            self.sounds.append(cpu.reg_read(UC_M68K_REG_D0) & 0xffff)
        self.cpu.hook_add(UC_HOOK_CODE, trace, begin=self.symbols['fx'],
                          end=self.symbols['fx'])

    def watch_stubs(self):
        self.entered = []
        for name in self.WATCHED:
            def trace(cpu, address, size, user, name=name):
                self.entered.append(name)
            self.cpu.hook_add(UC_HOOK_CODE, trace,
                              begin=self.symbols[name], end=self.symbols[name])

    def attacker(self, x, y, z):
        """An attacking ship able to turn, so PEEL_OFF_CHECK can divide."""
        self.ship_at(self.ship, 'krait', x, y, z)
        self.field(self.ship, 'logic', self.symbols['log_attack'])
        self.field(self.ship, 'turn_rate', 3)

    def steer(self):
        """The world coordinates DO_ATTACK hands to AUTO_PILOT for one frame."""
        course = []
        registers = (UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2)

        def trace(cpu, address, size, user):
            course.append(tuple(value - (1 << 32) if value >> 31 else value
                                for value in map(cpu.reg_read, registers)))
        self.cpu.hook_add(UC_HOOK_CODE, trace, begin=self.symbols['auto_pilot'],
                          end=self.symbols['auto_pilot'])
        self.call('do_attack')
        self.assertEqual(len(course), 1, 'AUTO_PILOT ran %d times' % len(course))
        return course[0]

    def aimed_shot(self, at_player, distance=4000):
        """A hunter lined up on its target and certain to take the shot.

        It sits square behind the world origin looking down +Z, so the player
        and a ship parked on the origin give it the same range and the same
        line of fire. AI_LASER is the answer: non-zero means it fired.
        """
        self.ship_at(self.ship, 'krait', 0, 0, -distance)
        self.ship_at(self.slot(1), 'cobra', 0, 0, 0, 'typ_trader')
        self.field(self.ship, 'logic', self.symbols['log_attack'])
        self.field(self.ship, 'turn_rate', 3)
        self.field(self.ship, 'mood', 200) ; # the firing roll always passes
        self.cpu.mem_write(self.ship + self.symbols['z_vector'],
                           struct.pack('>3h', 0, 0, self.symbols['unit']))
        self.field(self.ship, 'target', 0 if at_player else self.slot(1), 4)
        self.long(self.DIST_VALUE, distance)

    def test_a_hunter_lined_up_on_its_target_fires(self):
        """The fixture the two tests below measure against."""
        for at_player in (True, False):
            with self.subTest(at_player=at_player):
                self.prepare()
                self.aimed_shot(at_player)
                self.call('do_attack')
                self.assertNotEqual(self.read(self.ship, 'ai_laser'), 0)

    def test_the_fire_range_gate_measures_the_target_not_the_player(self):
        """AIMED_SHOT parks the hunter so that its distance to the player and
        to its target are deliberately the same, which is what makes it a fair
        comparison -- and leaves the gate's source untested. Here they differ:
        two ships fighting at the far edge of the scanner are thirty thousand
        units from the player and five hundred from each other. Reading
        OBJ_RANGE would silence every fight he is not standing next to."""
        self.prepare()
        self.ship_at(self.ship, 'krait', 0, 0, -30000, 'typ_pirate')
        self.ship_at(self.slot(1), 'cobra', 0, 0, -29500, 'typ_trader')
        self.field(self.ship, 'logic', self.symbols['log_attack'])
        self.field(self.ship, 'target', self.slot(1), 4)
        self.field(self.slot(1), 'health', 500)
        self.field(self.ship, 'turn_rate', 3)
        self.field(self.ship, 'mood', 200)      # the firing roll always passes
        self.cpu.mem_write(self.ship + self.symbols['z_vector'],
                           struct.pack('>3h', 0, 0, self.symbols['unit']))
        self.long(self.DIST_VALUE, 500)
        self.assertGreater(self.read(self.ship, 'obj_range', 4),
                           self.symbols['fire_range'])
        self.call('do_attack')
        self.assertNotEqual(self.read(self.ship, 'ai_laser'), 0,
                            'the hunter must fire at a target 500 units away')

    def test_the_players_cloak_and_locked_controls_only_cover_the_player(self):
        """Neither state hides one ship from another."""
        for name in ('cloaking_on', 'controls_locked'):
            for at_player, fires in ((True, False), (False, True)):
                with self.subTest(state=name, at_player=at_player):
                    self.prepare()
                    self.aimed_shot(at_player)
                    self.var(name, 1)
                    self.call('do_attack')
                    self.assertEqual(self.read(self.ship, 'ai_laser') != 0, fires)

    def test_a_hunter_flies_towards_its_ship_target(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.attacker(1000, -2000, 3000)
                self.ship_at(self.slot(1), 'cobra', 9000, 4000, -5000, 'typ_trader')
                self.field(self.ship, 'target', self.slot(1), 4)
                self.assertEqual(self.steer(), (9000, 4000, -5000))

    def test_a_hunter_fighting_the_player_still_flies_at_the_origin(self):
        self.prepare()
        self.attacker(1000, -2000, 3000)
        self.field(self.ship, 'target', 0, 4)
        self.assertEqual(self.steer(), (0, 0, 0))

    def test_a_ship_fighting_another_ship_launches_a_missile_at_it(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.watch_stubs()
                self.ship_at(self.ship, 'krait', 0, 0, 10000)
                self.ship_at(self.slot(1), 'cobra', 0, 0, 12000, 'typ_trader')
                self.field(self.ship, 'target', self.slot(1), 4)
                self.field(self.ship, 'no_missiles', 3)
                self.scratch(self.ALLOC_BUDGET, 1)
                self.call('low_energy')
                self.assertIn('launch_missile', self.entered)
                self.assertNotIn('thargons', self.entered)
                self.assertIn('launch_escape', self.entered)
                self.assertEqual(self.read(self.ship, 'no_missiles'), 2)
                missile = self.ALLOC_POOL
                self.assertEqual(self.read(missile, 'logic'),
                                 self.symbols['log_ai_missile'])
                self.assertEqual(self.read(missile, 'target', 4), self.slot(1))
                self.assertNotIn('disp_message', self.entered)

    def thargoid(self, npc_hit, roll=0, target=None):
        """A Thargoid with Thargons left and room in the object pool."""
        self.watch_stubs()
        self.ship_at(self.ship, 'thargoid', 0, 0, 10000, 'typ_alien')
        self.field(self.ship, 'no_missiles', 3)
        self.field(self.ship, 'target', self.slot(1) if target is None else target, 4)
        self.var('npc_hit', npc_hit)
        self.scratch(self.ALLOC_BUDGET, 8)
        self.scratch(self.RANDOM_VALUE, roll)

    def test_a_thargoid_releases_fewer_thargons_away_from_the_player(self):
        """A thargon is a ship, not a missile, so it still goes -- but an
        AI fight must not empty the thirty object slots in one release."""
        for npc_hit, roll, expected in ((0, 0, 4), (0, 255, 7),
                                        (1, 0, 2), (1, 255, 3)):
            with self.subTest(npc_hit=npc_hit, roll=roll):
                self.prepare()
                self.thargoid(npc_hit, roll)
                self.call('thargons')
                self.assertEqual(self.entered.count('create_object'), expected)
                self.assertEqual(self.read(self.ship, 'no_missiles'), 0)

    def test_a_thargoid_driven_off_by_another_ship_still_releases_thargons(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.ship_at(self.slot(1), 'krait', 0, 0, 12000)
                self.thargoid(npc_hit=1)
                self.call('low_energy')
                self.assertIn('thargons', self.entered)
                self.assertNotIn('launch_missile', self.entered)
                self.assertEqual(self.entered.count('create_object'), 2)

    def test_the_thargon_roll_away_from_the_player_ignores_his_rating(self):
        """The fixed odds of section 6.6, not RATING*4+MISSILE_PROB."""
        fixed = self.symbols['npc_launch_prob']
        for rating, roll, released in ((0, fixed - 1, True), (8, fixed, False)):
            with self.subTest(rating=rating, roll=roll):
                self.prepare()
                self.ship_at(self.slot(1), 'krait', 0, 0, 12000)
                self.thargoid(npc_hit=1, roll=roll)
                self.var('rating', rating)
                self.call('low_energy')
                self.assertEqual('thargons' in self.entered, released)

    def test_only_a_thargoid_releases_thargons(self):
        """Everything else that has something left lets go of a missile."""
        self.prepare()
        self.watch_stubs()
        self.ship_at(self.ship, 'krait', 0, 0, 10000)
        self.ship_at(self.slot(1), 'cobra', 0, 0, 12000, 'typ_trader')
        self.field(self.ship, 'target', self.slot(1), 4)
        self.field(self.ship, 'no_missiles', 3)
        self.scratch(self.ALLOC_BUDGET, 8)
        self.call('low_energy')
        self.assertNotIn('thargons', self.entered)
        self.assertIn('launch_missile', self.entered)

    def test_a_ship_with_nothing_left_launches_nothing(self):
        self.prepare()
        self.watch_stubs()
        self.ship_at(self.ship, 'krait', 0, 0, 10000)
        self.ship_at(self.slot(1), 'cobra', 0, 0, 12000, 'typ_trader')
        self.field(self.ship, 'target', self.slot(1), 4)
        self.field(self.ship, 'no_missiles', 0)
        self.scratch(self.ALLOC_BUDGET, 8)
        self.call('low_energy')
        self.assertNotIn('launch_missile', self.entered)
        self.assertNotIn('thargons', self.entered)

    def test_a_ship_fighting_the_player_still_launches_missiles(self):
        self.prepare()
        self.watch_stubs()
        self.ship_at(self.ship, 'krait', 0, 0, 2000)
        self.field(self.ship, 'target', 0, 4)
        self.field(self.ship, 'no_missiles', 3)
        self.call('low_energy')
        self.assertIn('launch_missile', self.entered)

    #: The 1988 break-off table, lifted from CHECK_HIT in
    #: src_orig/asm/combat.m68. HIT_REACTION is now the only copy of it and
    #: serves the player's fire and another ship's alike, so this pins it for
    #: both. None means the ship presses on without reacting.
    BREAK_OFF = (
        ('log_attack', 'act_attack', None),
        ('log_peel_off', 'act_attack', None),
        ('log_cruise', 'act_nothing', None),
        ('log_run_off', 'act_nothing', None),
        ('log_cruise', 'act_runaway', 'log_cruise'),
        ('log_run_off', 'act_runaway', 'log_cruise'),
        ('log_cruise', 'act_attack', 'log_attack'),
        ('log_avoid', 'act_attack', 'log_attack'),
        ('log_launch', 'act_attack', 'log_attack'),
        ('log_run_off', 'act_attack', 'log_avoid'),
    )

    def test_hit_reaction_matches_the_original_break_off(self):
        for state, attack, expected in self.BREAK_OFF:
            with self.subTest(logic=state, attack_type=attack):
                self.prepare()
                self.watch_stubs()
                self.ship_at(self.ship, 'cobra', 0, 0, 5000, 'typ_trader', attack)
                self.field(self.ship, 'logic', self.symbols[state])
                self.field(self.ship, 'health', 77)
                self.call('hit_reaction')
                if expected is None:
                    self.assertNotIn('start_peel_off', self.entered)
                    self.assertEqual(self.read(self.ship, 'next_logic'), 0)
                    self.assertEqual(self.read(self.ship, 'pre_attack'), 0)
                else:
                    self.assertIn('start_peel_off', self.entered)
                    self.assertEqual(self.read(self.ship, 'next_logic'),
                                     self.symbols[expected])
                    # Only a fresh attack run re-baselines the health it is
                    # measured against; the other two outcomes leave it alone.
                    self.assertEqual(self.read(self.ship, 'pre_attack'),
                                     77 if expected == 'log_attack' else 0)
                self.assertEqual(self.read(self.ship, 'logic'),
                                 self.symbols[state], 'LOGIC is START_PEEL_OFF\'s job')

    def hit(self, power, victim='cobra', ship_type='typ_trader',
            attack='act_attack', **fields):
        """Fire POWER at a ship in slot 1 and watch how it reacts."""
        self.watch_stubs()
        self.ship_at(self.ship, 'krait', 0, 0, 10000)
        self.ship_at(self.slot(1), victim, 0, 0, 12000, ship_type, attack)
        self.field(self.slot(1), 'health', 100)
        for name, value in fields.items():
            self.field(self.slot(1), name, value,
                       4 if name == 'target' else 2)
        self.field(self.ship, 'target', self.slot(1), 4)
        self.call('damage_target', d0=power)

    def test_a_ship_hit_by_another_ship_breaks_off(self):
        """The evasive turn the player's fire provokes, provoked by AI fire."""
        for state, expected in (('log_cruise', 'log_attack'),
                                ('log_run_off', 'log_avoid'),
                                ('log_attack', None),
                                ('log_peel_off', None)):
            with self.subTest(logic=state):
                self.prepare()
                self.hit(10, logic=self.symbols[state])
                if expected is None:
                    self.assertNotIn('start_peel_off', self.entered)
                else:
                    self.assertIn('start_peel_off', self.entered)
                    self.assertEqual(self.read(self.slot(1), 'next_logic'),
                                     self.symbols[expected])
                self.assertEqual(self.read(self.slot(1), 'health'), 90)
                self.assertEqual(self.read(self.ship, 'next_logic'), 0)

    def test_a_runaway_ship_hit_by_another_ship_flees(self):
        self.prepare()
        self.hit(10, victim='python', attack='act_runaway')
        self.assertIn('start_peel_off', self.entered)
        self.assertEqual(self.read(self.slot(1), 'next_logic'),
                         self.symbols['log_cruise'])

    def test_a_helpless_hull_hit_by_another_ship_does_not_react(self):
        self.prepare()
        self.hit(10, attack='act_nothing')
        self.assertNotIn('start_peel_off', self.entered)

    def test_a_badly_hurt_ship_runs_for_it(self):
        """Over half its energy gone in one attack run: the LOW_ENERGY path."""
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.hit(60, logic=self.symbols['log_attack'], pre_attack=100)
                self.assertIn('launch_escape', self.entered)
                self.assertIn('start_peel_off', self.entered)
                self.assertEqual(self.read(self.slot(1), 'next_logic'),
                                 self.symbols['log_run_off'])

    def test_a_lightly_hurt_ship_stays_on_its_run(self):
        self.prepare()
        self.hit(10, logic=self.symbols['log_attack'], pre_attack=100)
        self.assertNotIn('launch_escape', self.entered)
        self.assertNotIn('start_peel_off', self.entered)

    def test_no_missile_reaches_the_player_unless_he_provoked_it(self):
        """A ship fighting him, driven to low energy by a third ship, keeps its
        missile: the cockpit alert belongs to fights he is part of."""
        self.prepare()
        self.watch_stubs()
        self.ship_at(self.ship, 'krait', 0, 0, 10000)
        self.field(self.ship, 'target', 0, 4)
        self.field(self.ship, 'no_missiles', 3)
        self.scratch(self.ALLOC_BUDGET, 1)
        self.var('npc_hit', 1)
        self.call('low_energy')
        self.assertNotIn('create_object', self.entered)
        self.assertEqual(self.read(self.ship, 'no_missiles'), 3)

    def test_a_ship_without_a_target_launches_nothing_for_another_ship(self):
        """Driven low by another ship's fire with nobody of its own to shoot
        at, it keeps the missile. NO_TARGET is -1, so a bare "not the player"
        test would have sent LAUNCH_MISSILE looking for a record at
        $FFFFFFFF."""
        self.prepare()
        self.watch_stubs()
        self.ship_at(self.ship, 'krait', 0, 0, 10000)
        self.field(self.ship, 'target', self.symbols['no_target'], 4)
        self.field(self.ship, 'no_missiles', 3)
        self.scratch(self.ALLOC_BUDGET, 1)
        self.var('npc_hit', 1)
        self.call('low_energy')
        self.assertNotIn('launch_missile', self.entered)
        self.assertEqual(self.read(self.ship, 'no_missiles'), 3)

    def test_his_own_shot_still_brings_a_missile_from_a_ship_fighting_nobody(self):
        """RETARGET never gives the Python, the Shuttle or the Transporter a
        target, so TARGET stays at NO_TARGET for their whole lives, and any
        ship has it between fights. 1988 answered the player's fire with the
        ship's missile whatever it was doing at the time. Which fight the ship
        is in is TARGET's question; whose shot just landed is NPC_HIT's, and
        only the second one decides who the missile is for."""
        self.prepare()
        self.watch_stubs()
        self.ship_at(self.ship, 'python', 0, 0, 10000, 'typ_trader',
                     'act_runaway')
        self.field(self.ship, 'target', self.symbols['no_target'], 4)
        self.field(self.ship, 'no_missiles', 1)
        self.scratch(self.ALLOC_BUDGET, 1)
        self.call('low_energy')
        self.assertIn('launch_missile', self.entered)
        self.assertEqual(self.read(self.ship, 'no_missiles'), 0)
        # It flies at the player and announces itself, as his own attacker's
        # missile does, rather than becoming a silent LOG_AI_MISSILE.
        self.assertEqual(self.read(self.ALLOC_POOL, 'logic'),
                         self.symbols['log_missile'])
        self.assertIn('disp_message', self.entered)

    def missile_at(self, victim, logic='log_ai_missile', distance=10):
        """A missile in flight, close enough to detonate on its target."""
        self.ship_at(self.ship, 'missile', 0, 0, 0)
        self.field(self.ship, 'logic', self.symbols[logic])
        self.field(self.ship, 'target', victim, 4)
        self.field(victim, 'obj_rad', 50)
        self.long(self.DIST_VALUE, distance)

    def test_a_ships_missile_kills_without_crediting_the_player(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.watch_stubs()
                self.ship_at(self.slot(1), 'cobra', 0, 0, 0, 'typ_trader')
                self.missile_at(self.slot(1))
                self.call('do_locked')
                self.assertEqual(self.read(self.slot(1), 'logic'),
                                 self.symbols['log_exploding'])
                self.assertNotIn('add_kill', self.entered)
                self.assertNotIn('inc_record', self.entered)
                self.assertIn('release_cargo', self.entered)
                self.assertEqual(self.read(VARIABLES, 'npc_kill'), 0)

    def test_the_players_own_missile_still_credits_him(self):
        self.prepare()
        self.watch_stubs()
        self.ship_at(self.slot(1), 'cobra', 0, 0, 0, 'typ_trader')
        self.missile_at(self.slot(1), 'log_locked')
        self.call('do_locked')
        self.assertEqual(self.read(self.slot(1), 'logic'),
                         self.symbols['log_exploding'])
        self.assertIn('add_kill', self.entered)

    def test_a_missile_kill_does_not_report_the_missile_that_made_it(self):
        """DO_LOCKED calls TARGET_LOST on its own kill, and the missile doing
        the killing is still in the object list at that moment."""
        for logic in ('log_locked', 'log_ai_missile'):
            with self.subTest(logic=logic):
                self.prepare()
                self.watch_stubs()
                self.ship_at(self.slot(1), 'cobra', 0, 0, 0, 'typ_trader')
                self.missile_at(self.slot(1), logic)
                self.call('do_locked')
                self.assertEqual(self.read(self.slot(1), 'logic'),
                                 self.symbols['log_exploding'])
                self.assertNotIn('disp_message', self.entered)

    def test_a_second_missile_of_his_on_the_same_ship_is_reported(self):
        self.prepare()
        self.watch_stubs()
        self.ship_at(self.slot(1), 'cobra', 0, 0, 0, 'typ_trader')
        self.ship_at(self.slot(2), 'missile', 0, 0, 0)
        self.field(self.slot(2), 'logic', self.symbols['log_locked'])
        self.field(self.slot(2), 'target', self.slot(1), 4)
        self.missile_at(self.slot(1), 'log_locked')
        self.call('do_locked')
        removed = 1 << (8 + self.symbols['remove'])
        self.assertTrue(self.read(self.slot(2), 'flags') & removed)
        self.assertIn('disp_message', self.entered)

    def test_the_ecm_jammer_protects_his_missiles(self):
        """The reward for destroying the alien station. It stops the ship his
        missile is chasing from answering with ECM, and that answer is now a
        wave that really would destroy the missile."""
        for jammed, reaches_the_target in ((0, False), (1, True)):
            with self.subTest(jammer=jammed):
                self.prepare()
                self.watch_stubs()
                self.ship_at(self.slot(1), 'cobra', 0, 0, 0, 'typ_trader')
                self.field(self.slot(1), 'ecm_fitted', 1)
                self.missile_at(self.slot(1), 'log_locked')
                self.var('ecm_jammed', jammed)
                self.call('do_locked')
                self.assertEqual(self.read(self.slot(1), 'logic') ==
                                 self.symbols['log_exploding'], reaches_the_target)
                # Without it, the ship starts a wave of its own and says so.
                self.assertEqual(self.read(VARIABLES, 'who_ecm') != 0,
                                 not reaches_the_target)
                self.assertEqual('fx' in self.entered, True)

    def test_the_jammer_does_not_help_a_ship_that_carries_no_ecm(self):
        """It suppresses an answer; it does not invent one."""
        self.prepare()
        self.ship_at(self.slot(1), 'cobra', 0, 0, 0, 'typ_trader')
        self.field(self.slot(1), 'ecm_fitted', 0)
        self.missile_at(self.slot(1), 'log_locked')
        self.var('ecm_jammed', 0)
        self.call('do_locked')
        self.assertEqual(self.read(self.slot(1), 'logic'),
                         self.symbols['log_exploding'])
        self.assertEqual(self.read(VARIABLES, 'who_ecm'), 0)

    def test_the_jammer_suppresses_ecm_for_everyone(self):
        """It jams the use of ECM in the space around the player, not just the
        answer to his own missile: ENGAGE_ECM refuses him his own ECM while it
        is on, so a ship defending itself against another ship's missile is
        silenced by it too."""
        for logic in ('log_locked', 'log_ai_missile'):
            with self.subTest(logic=logic):
                self.prepare()
                self.ship_at(self.slot(1), 'cobra', 0, 0, 0, 'typ_trader')
                self.field(self.slot(1), 'ecm_fitted', 1)
                self.missile_at(self.slot(1), logic)
                self.var('ecm_jammed', 1)
                self.call('do_locked')
                self.assertEqual(self.read(self.slot(1), 'logic'),
                                 self.symbols['log_exploding'],
                                 'the jammer let a %s be answered' % logic)
                self.assertEqual(self.read(VARIABLES, 'who_ecm'), 0)

    def test_without_the_jammer_a_ship_answers_either_missile(self):
        for logic in ('log_locked', 'log_ai_missile'):
            with self.subTest(logic=logic):
                self.prepare()
                self.ship_at(self.slot(1), 'cobra', 0, 0, 0, 'typ_trader')
                self.field(self.slot(1), 'ecm_fitted', 1)
                self.missile_at(self.slot(1), logic)
                self.call('do_locked')
                self.assertNotEqual(self.read(self.slot(1), 'logic'),
                                    self.symbols['log_exploding'])
                self.assertNotEqual(self.read(VARIABLES, 'who_ecm'), 0)

    def test_target_lost_clears_every_missile_chasing_the_ship(self):
        """None may be left steering at a freed record, but only his is news."""
        for owners, reported in ((('log_ai_missile',), False),
                                 (('log_ai_missile', 'log_ai_missile'), False),
                                 (('log_ai_missile', 'log_locked'), True)):
            with self.subTest(owners=owners):
                self.prepare()
                self.watch_stubs()
                self.ship_at(self.slot(1), 'cobra', 0, 0, 0, 'typ_trader')
                for number, logic in enumerate(owners, start=2):
                    self.ship_at(self.slot(number), 'missile', 0, 0, 0)
                    self.field(self.slot(number), 'logic', self.symbols[logic])
                    self.field(self.slot(number), 'target', self.slot(1), 4)
                self.call_with('target_lost', self.ship, self.slot(1))
                removed = 1 << (8 + self.symbols['remove'])
                for number in range(2, 2 + len(owners)):
                    self.assertTrue(self.read(self.slot(number), 'flags') & removed,
                                    'slot %d left chasing a freed record' % number)
                self.assertEqual('disp_message' in self.entered, reported)

    def test_check_missile_answers_only_for_the_players_missiles(self):
        """Otherwise a ship's missile would block his own lock on that ship."""
        for logic, found in (('log_locked', True), ('log_ai_missile', False)):
            with self.subTest(logic=logic):
                self.prepare()
                self.ship_at(self.slot(1), 'cobra', 0, 0, 0, 'typ_trader')
                self.ship_at(self.slot(2), 'missile', 0, 0, 0)
                self.field(self.slot(2), 'logic', self.symbols[logic])
                self.field(self.slot(2), 'target', self.slot(1), 4)
                self.call_with('check_missile', self.ship, self.slot(1))
                counter = self.cpu.reg_read(UC_M68K_REG_D7) & 0xffff
                self.assertEqual(counter < 0x8000, found)

    def missile_launch(self, **globals_):
        self.watch_stubs()
        self.ship_at(self.ship, 'krait', 0, 0, 10000)
        self.ship_at(self.slot(1), 'cobra', 0, 0, 12000, 'typ_trader')
        self.field(self.ship, 'target', self.slot(1), 4)
        self.field(self.ship, 'no_missiles', 3)
        self.scratch(self.ALLOC_BUDGET, 1)
        for name, value in globals_.items():
            self.var(name, value)

    def test_the_range_guard_measures_the_ship_being_fired_at(self):
        """OBJ_RANGE is the distance from the player and says nothing here."""
        for distance, launched in ((1999, False), (2000, True)):
            with self.subTest(distance=distance):
                self.prepare()
                self.missile_launch()
                self.long(self.DIST_VALUE, distance)
                self.call('launch_missile')
                self.assertEqual('create_object' in self.entered, launched)
                self.assertEqual(self.read(self.ship, 'no_missiles'),
                                 2 if launched else 3)

    def test_the_players_cloak_does_not_cover_a_ship(self):
        self.prepare()
        self.missile_launch(cloaking_on=1)
        self.call('launch_missile')
        self.assertIn('create_object', self.entered)

    def in_flight(self, slot, logic):
        """A missile of someone's, somewhere in the world."""
        self.ship_at(slot, 'missile', 0, 0, 5000)
        self.field(slot, 'logic', self.symbols[logic])

    def test_an_ecm_wave_destroys_every_missile_in_flight(self):
        """ECM has never been selective, and a ship's missile is no exception."""
        for cpu in CPUS:
            for logic in ('log_locked', 'log_ai_missile', 'log_missile'):
                with self.subTest(cpu=cpu, logic=logic):
                    self.prepare(cpu)
                    self.in_flight(self.slot(1), logic)
                    self.var('ecm_on', 1)
                    self.call('ecm')
                    self.assertEqual(self.read(self.slot(1), 'logic'),
                                     self.symbols['log_exploding'])

    def test_nothing_is_destroyed_while_no_wave_is_running(self):
        self.prepare()
        self.in_flight(self.slot(1), 'log_locked')
        self.call('ecm')
        self.assertNotEqual(self.read(self.slot(1), 'logic'),
                            self.symbols['log_exploding'])

    def test_a_wave_leaves_ships_alone(self):
        self.prepare()
        self.ship_at(self.slot(1), 'cobra', 0, 0, 5000, 'typ_trader')
        self.var('ecm_on', 1)
        self.call('ecm')
        self.assertNotEqual(self.read(self.slot(1), 'logic'),
                            self.symbols['log_exploding'])

    def test_only_his_own_wave_costs_the_player_energy(self):
        for who, drains in ((0, True), (1, False)):
            with self.subTest(who_ecm=who):
                self.prepare()
                self.watch_stubs()
                self.in_flight(self.slot(1), 'log_missile')
                self.var('ecm_on', 1)
                self.var('who_ecm', who)
                self.call('ecm')
                self.assertEqual('reduce_energy' in self.entered, drains)

    def test_a_whole_fight_between_two_ships(self):
        """Cruise, target, aim, fire, damage, kill and drop cargo, driven
        through the real RETARGET and DO_ATTACK rather than a single routine.

        RANDOM answers 196 throughout: past MOOD so the shot is taken, past the
        distance miss threshold so it lands, and with its low two bits clear so
        the damage multiplier's rejection loop settles at once.
        """
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.watch_stubs()
                pirate, trader = self.ship, self.slot(1)
                # The player sits at the origin and is an ordinary candidate
                # for a pirate, so the trader has to be the closer one.
                self.ship_at(pirate, 'krait', 0, 0, -1000, 'typ_pirate')
                self.ship_at(trader, 'cobra', 0, 0, -1500, 'typ_trader')
                self.field(pirate, 'turn_rate', 3)
                self.field(pirate, 'mood', 255)
                self.field(trader, 'health', 5)
                self.field(trader, 'no_missiles', 0)
                self.cpu.mem_write(pirate + self.symbols['z_vector'],
                                   struct.pack('>3h', 0, 0, -self.symbols['unit']))
                self.long(self.DIST_VALUE, 500)  # it is 500 behind the trader
                self.scratch(self.RANDOM_VALUE, 196)

                # Cruising, with nobody picked out yet.
                self.assertEqual(self.read(pirate, 'target', 4),
                                 self.symbols['no_target'])

                # Its turn to re-target: the trader is the only candidate.
                self.call('retarget')
                self.assertEqual(self.read(pirate, 'target', 4), trader)
                self.assertEqual(self.read(pirate, 'logic'),
                                 self.symbols['log_attack'])
                self.assertEqual(self.read(pirate, 'pre_attack'),
                                 self.read(pirate, 'health'))

                # The trader answers on its own turn, and picks the pirate.
                self.var('this_obj', 1)
                self.var('retarget_slot', 1)
                self.call_with('retarget', trader, trader)
                self.assertEqual(self.read(trader, 'target', 4), pirate)
                self.assertEqual(self.read(trader, 'logic'),
                                 self.symbols['log_attack'])
                self.var('this_obj', 0)
                self.var('retarget_slot', 0)

                # Three attack frames bring the trader down.
                for frame in range(3):
                    self.assertNotEqual(self.read(trader, 'logic'),
                                        self.symbols['log_exploding'], frame)
                    self.call('do_attack')
                    self.assertEqual(self.read(pirate, 'ai_laser'), 2, frame)
                self.assertEqual(self.read(trader, 'logic'),
                                 self.symbols['log_exploding'])

                # None of it was the player's business.
                self.assertNotIn('add_kill', self.entered)
                self.assertNotIn('inc_record', self.entered)
                self.assertNotIn('reduce_shields', self.entered)
                self.assertNotIn('disp_message', self.entered)
                self.assertIn('release_cargo', self.entered)
                self.assertEqual(self.read(VARIABLES, 'npc_kill'), 0)
                self.assertEqual(self.read(pirate, 'flags')
                                 & (1 << (8 + self.symbols['angry'])), 0)
                # OBJ_RANGE still means "distance from the player", which RADAR,
                # COLLISION and DO_CRUISING all depend on.
                self.assertEqual(self.read(pirate, 'obj_range', 4), 1000)

    def test_peel_off_check_picks_its_input_from_the_target(self):
        """It leaves the peel distance in D0, which says which input it used:
        APPROACH, the closing speed towards the player, or the shooter's own
        VELOCITY. DO_POLICE, DO_LAUNCH and DO_FLY_PLANET reach it in states
        that never hold a faction target, so they must keep the first."""
        for target, expected in (('no_target', 3 * 600 // 3 + 1024),
                                 ('player', 3 * 600 // 3 + 1024),
                                 ('ship', 6 * 600 // 3 + 1024)):
            with self.subTest(target=target):
                self.prepare()
                self.ship_at(self.ship, 'viper', 0, 0, 5000, 'typ_police')
                self.ship_at(self.slot(1), 'krait', 0, 0, 5500)
                self.field(self.ship, 'target',
                           {'no_target': self.symbols['no_target'],
                            'player': 0, 'ship': self.slot(1)}[target], 4)
                self.field(self.ship, 'turn_rate', 3)
                self.field(self.ship, 'velocity', 6)
                self.var('approach', 3)
                self.assertEqual(self.call('peel_off_check'), expected)

    def test_a_mission_ship_keeps_attacking_the_player(self):
        """The Cougar and the Constrictor are outside the faction whitelist, so
        RETARGET never gives them a target and NO_TARGET is all they ever have.
        DO_ATTACK must read that as "the player", which is what LOG_ATTACK
        meant before faction targeting, and not send them cruising away."""
        for kind in ('constr', 'cougar'):
            with self.subTest(ship=kind):
                self.prepare()
                self.ship_at(self.ship, kind, 0, 0, 5000, 'typ_pirate')
                self.field(self.ship, 'logic', self.symbols['log_attack'])
                self.field(self.ship, 'target', self.symbols['no_target'], 4)
                self.field(self.ship, 'turn_rate', 3)
                self.call('retarget')
                self.assertEqual(self.read(self.ship, 'target', 4),
                                 self.symbols['no_target'], 'RETARGET must skip it')
                self.call('do_attack')
                self.assertEqual(self.read(self.ship, 'logic'),
                                 self.symbols['log_attack'],
                                 '%s broke off instead of attacking him' % kind)
                self.assertEqual(self.read(self.ship, 'target', 4), 0)

    def test_a_faction_ship_with_nothing_to_fight_still_disengages(self):
        """The fall back of section 5.1 has to survive that: a ship RETARGET
        does look after, and which has nothing left, flies off as before."""
        self.prepare()
        self.ship_at(self.ship, 'krait', 0, 0, 5000, 'typ_pirate')
        self.field(self.ship, 'logic', self.symbols['log_attack'])
        self.field(self.ship, 'target', self.symbols['no_target'], 4)
        self.field(self.ship, 'turn_rate', 3)
        self.call('do_attack')
        self.assertEqual(self.read(self.ship, 'logic'), self.symbols['log_cruise'])

    def test_a_mission_ship_is_never_dragged_into_the_faction_system(self):
        for kind in ('constr', 'cougar'):
            with self.subTest(ship=kind):
                self.prepare()
                self.ship_at(self.ship, kind, 0, 0, 5000, 'typ_pirate')
                self.ship_at(self.slot(1), 'cobra', 0, 0, 5200, 'typ_trader')
                self.field(self.ship, 'logic', self.symbols['log_attack'])
                self.field(self.ship, 'target', self.symbols['no_target'], 4)
                self.call('retarget')
                self.assertEqual(self.read(self.ship, 'target', 4),
                                 self.symbols['no_target'])
                # Nor is it a candidate for anybody else.
                self.call_with('is_combat_ship', self.slot(1), self.ship)
                self.assertEqual(self.cpu.reg_read(UC_M68K_REG_D0) & 0xffff, 0)

    def test_a_thargoid_in_witch_space_is_born_hunting_the_player(self):
        """CREATE_THARGOIDS means "attack the player" by LOG_ATTACK alone, so
        it has to say so in TARGET rather than leave ALLOC_OBJECT's NO_TARGET
        and spend a round of the re-target cursor cruising away."""
        self.prepare()
        self.var('tharg_max', 4)
        self.scratch(self.ALLOC_BUDGET, 1)
        self.call('create_thargoids')
        born = self.ALLOC_POOL
        self.assertEqual(self.read(born, 'type'), self.symbols['thargoid'])
        self.assertEqual(self.read(born, 'logic'), self.symbols['log_attack'])
        self.assertEqual(self.read(born, 'target', 4), 0)

    def test_a_role_rolls_only_from_its_own_table(self):
        """RANDOM_PIRATE's range holds the Thargoid, the Boa and the Wolf. The
        encounter's raiders are chosen deliberately and hold none of them."""
        tables = {
            'role_pirate': ('krait', 'gecko', 'moray', 'adder', 'mamba', 'asp',
                            'sidewinder'),
            'role_trader': ('cobra', 'python', 'anaconda', 'cobra_mk1'),
        }
        self.prepare()
        for role, ships in tables.items():
            with self.subTest(role=role):
                expected = {self.symbols[name] for name in ships}
                seen = set()
                for index in range(len(ships)):
                    self.roll(index, len(ships))
                    seen.add(self.call('encounter_type', d0=self.symbols[role]))
                self.assertEqual(seen, expected)
                for name in ('thargoid', 'boa', 'wolf', 'ferdelance', 'viper'):
                    self.assertNotIn(self.symbols[name], seen)

    def test_a_fixed_role_names_one_ship(self):
        self.prepare()
        for role, ship in (('role_thargoid', 'thargoid'),
                           ('role_viper', 'viper'),
                           ('role_bounty', 'ferdelance')):
            with self.subTest(role=role):
                for index in range(4):  # the roll must not reach these
                    self.roll(index, 4)
                    self.assertEqual(self.call('encounter_type',
                                               d0=self.symbols[role]),
                                     self.symbols[ship])

    #: Section 4.3 of the spec, as the assembler should encode it.
    TEMPLATES = (
        (1, 0, (('role_thargoid', 1), ('role_pirate', 2))),
        (1, 0, (('role_thargoid', 1), ('role_trader', 2))),
        (4, 0, (('role_pirate', 2), ('role_trader', 2))),
        (3, 2, (('role_pirate', 2), ('role_viper', 2))),
        (3, 1, (('role_pirate', 2), ('role_viper', 1))),
        (2, 0, (('role_pirate', 2), ('role_bounty', 1))),
        (2, 0, (('role_pirate', 2), ('role_bounty', 1), ('role_trader', 1))),
    )

    def government(self, value):
        self.word(VARIABLES + self.symbols['splanet'] + self.symbols['govern'],
                  value)

    def pairs_at(self, address):
        """Decode role/count pairs up to the terminating zero."""
        out = []
        while self.cpu.mem_read(address, 1)[0]:
            role, count = self.cpu.mem_read(address, 2)
            out.append((role, count))
            address += 2
        return out

    def expected_pairs(self, template):
        return [(self.symbols[role], count) for role, count in template[2]]

    def chosen_template(self):
        self.call('encounter_template')
        return self.pairs_at(self.cpu.reg_read(UC_M68K_REG_A0))

    def test_the_template_table_matches_the_spec(self):
        self.prepare()
        address = self.symbols['encounter_groups']
        for weight, govern, _ in self.TEMPLATES:
            self.assertEqual(self.cpu.mem_read(address, 2)[0], weight)
            self.assertEqual(self.cpu.mem_read(address, 2)[1], govern)
            address += 2
            while self.cpu.mem_read(address, 1)[0]:
                address += 2
            address += 1
        self.assertEqual(self.cpu.mem_read(address, 1)[0], 0, 'table must end')

    def test_a_template_is_never_chosen_against_its_government(self):
        """Two templates carry police and are gated; the rest always apply."""
        self.prepare()
        for govern in range(8):
            allowed = [entry for entry in self.TEMPLATES if entry[1] <= govern]
            total = sum(entry[0] for entry in allowed)
            seen = []
            for index in range(total):
                self.government(govern)
                self.roll(index, total)
                seen.append(self.chosen_template())
            with self.subTest(govern=govern):
                self.assertEqual(
                    seen, [self.expected_pairs(entry) for entry in allowed
                           for _ in range(entry[0])],
                    'government %d chose the wrong templates' % govern)

    def test_the_weights_hold(self):
        """Section 4.4: a Thargoid in an eighth of encounters, a fifth under
        anarchy where the police templates drop out."""
        self.prepare()
        for govern, share in ((0, 2 / 10), (1, 2 / 13), (7, 2 / 16)):
            allowed = [entry for entry in self.TEMPLATES if entry[1] <= govern]
            total = sum(entry[0] for entry in allowed)
            thargoids = 0
            for index in range(total):
                self.government(govern)
                self.roll(index, total)
                roles = [role for role, _ in self.chosen_template()]
                thargoids += self.symbols['role_thargoid'] in roles
            with self.subTest(govern=govern):
                self.assertAlmostEqual(thargoids / total, share, places=6)

    def member_budget(self):
        return int.from_bytes(self.cpu.mem_read(self.ALLOC_BUDGET, 2), 'big')

    def encounter(self, govern=7, template=0, budget=8):
        """Run RANDOM_ENCOUNTER with a chosen template and a stocked pool."""
        allowed = [entry for entry in self.TEMPLATES if entry[1] <= govern]
        total = sum(entry[0] for entry in allowed)
        index = sum(entry[0] for entry in allowed[:template])
        self.government(govern)
        self.roll(index, total)
        self.scratch(self.ALLOC_BUDGET, budget)
        self.call('random_encounter')
        placed = budget - self.member_budget()
        return [self.ALLOC_POOL + (budget - 1 - n) * self.symbols['obj_len']
                for n in range(placed)]

    def test_a_group_is_built_from_its_template(self):
        """RAND answers its lowest index, so every 1-2 role gives one ship."""
        self.prepare()
        self.watch_stubs()
        members = self.encounter(govern=7, template=2)  # pirates and traders
        self.assertEqual(len(members), 2)
        pirates = {self.symbols[name] for name in
                   ('krait', 'gecko', 'moray', 'adder', 'mamba', 'asp',
                    'sidewinder')}
        traders = {self.symbols[name] for name in
                   ('cobra', 'python', 'anaconda', 'cobra_mk1')}
        self.assertIn(self.read(members[0], 'type'), pirates)
        self.assertIn(self.read(members[1], 'type'), traders)

    def test_every_member_cruises_and_hunts_nobody_yet(self):
        self.prepare()
        for member in self.encounter(govern=7, template=6):
            self.assertEqual(self.read(member, 'logic'),
                             self.symbols['log_cruise'])
            self.assertEqual(self.read(member, 'target', 4),
                             self.symbols['no_target'])
            self.assertTrue(self.read(member, 'flags')
                            & (1 << (8 + self.symbols['in_use'])))

    def test_no_group_exceeds_four_members(self):
        for template in range(len(self.TEMPLATES)):
            with self.subTest(template=template):
                self.prepare()
                members = self.encounter(govern=7, template=template)
                self.assertLessEqual(len(members), 4)
                self.assertGreaterEqual(len(members), 2)

    def test_every_variable_role_can_bring_two(self):
        self.prepare()
        allowed = [entry for entry in self.TEMPLATES if entry[1] <= 7]
        total = sum(entry[0] for entry in allowed)
        self.government(7)
        self.roll(sum(entry[0] for entry in allowed[:2]), total)
        self.scratch(self.ALLOC_BUDGET, 8)
        self.scratch(self.RAND_VALUE, 0xffff)  # every 1-2 role gives its max
        self.call('random_encounter')
        self.assertEqual(8 - self.member_budget(), 4)

    def test_a_group_finishes_short_when_the_pool_runs_dry(self):
        self.prepare()
        members = self.encounter(govern=7, template=2, budget=1)
        self.assertEqual(len(members), 1)

    def test_the_group_is_placed_ahead_of_the_player(self):
        """ORBIT is stubbed to answer behind him; ENCOUNTER_PLACE must mirror
        it into the hemisphere he is facing, keeping the radius."""
        self.prepare()
        self.watch_stubs()
        members = self.encounter(govern=7, template=2)
        self.assertIn('orbit', self.entered)
        self.assertIn('vector_pos', self.entered)
        self.assertEqual(self.read(members[0], 'zpos', 4), 20000)

    def test_nothing_is_announced(self):
        self.prepare()
        self.watch_stubs()
        self.encounter(govern=7, template=2)
        self.assertNotIn('disp_message', self.entered)
        self.assertNotIn('fx', self.entered)

    def deep_space_wave(self, mission, coin):
        """Drive CREATE_PIRATES to the point where it would spawn a wave."""
        self.prepare()
        self.watch_stubs()
        self.var('mission', mission)
        self.var('radar_obj', 0)        # deep space
        self.var('pirate_count', 0)
        self.var('pirate_ctr', 1)       # the countdown expires on this call
        self.government(7)
        self.scratch(self.RANDOM_VALUE, coin)
        self.scratch(self.ALLOC_BUDGET, 8)
        self.call('create_pirates')

    def test_a_mission_wave_is_never_replaced(self):
        """$21 and $52 spawn Thargoids, $41 the Cougar, $15 the Constrictor.
        $15 cannot reach the substitution, and is tested anyway so the guard
        survives an edit to the Constrictor branch above it."""
        for mission in (0x15, 0x21, 0x41, 0x52):
            for coin in (0, 1):
                with self.subTest(mission=mission, coin=coin):
                    self.deep_space_wave(mission, coin)
                    self.assertIn('pirate_attack', self.entered)
                    self.assertNotIn('create_object', self.entered)

    def test_an_ordinary_wave_is_replaced_on_half_the_rolls(self):
        for coin, encounter in ((0, False), (1, True)):
            with self.subTest(coin=coin):
                self.deep_space_wave(0x00, coin)
                self.assertEqual('pirate_attack' not in self.entered, encounter)
                self.assertEqual('create_object' in self.entered, encounter)

    def test_no_encounter_outside_deep_space(self):
        self.prepare()
        self.watch_stubs()
        self.var('mission', 0)
        self.var('radar_obj', 1)  # inside station space
        self.var('pirate_count', 0)
        self.var('pirate_ctr', 1)
        self.scratch(self.RANDOM_VALUE, 1)
        self.scratch(self.ALLOC_BUDGET, 8)
        self.call('create_pirates')
        self.assertNotIn('pirate_attack', self.entered)
        self.assertNotIn('create_object', self.entered)

    def test_only_a_kill_the_player_made_is_heard(self):
        """EXPLODE_OBJECT is where every destruction ends, and NPC_KILL already
        says whether he had any part in it."""
        for npc, heard in ((0, True), (1, False)):
            with self.subTest(npc_kill=npc):
                self.prepare()
                self.watch_sounds()
                self.ship_at(self.slot(1), 'cobra', 0, 0, 0, 'typ_trader')
                self.var('npc_kill', npc)
                self.call_with('explode_object', self.ship, self.slot(1))
                self.assertEqual(self.read(self.slot(1), 'logic'),
                                 self.symbols['log_exploding'])
                self.assertEqual(self.symbols['sfx_explosion'] in self.sounds,
                                 heard)

    def test_a_ships_laser_kill_is_silent(self):
        self.prepare()
        self.watch_sounds()
        self.ship_at(self.ship, 'krait', 0, 0, 10000)
        self.ship_at(self.slot(1), 'cobra', 0, 0, 12000, 'typ_trader')
        self.field(self.ship, 'target', self.slot(1), 4)
        self.field(self.slot(1), 'health', 4)
        self.call('damage_target', d0=9)
        self.assertEqual(self.read(self.slot(1), 'logic'),
                         self.symbols['log_exploding'])
        self.assertNotIn(self.symbols['sfx_explosion'], self.sounds)

    def test_a_missile_kill_is_heard_only_when_the_missile_was_his(self):
        for logic, heard in (('log_locked', True), ('log_ai_missile', False)):
            with self.subTest(logic=logic):
                self.prepare()
                self.watch_sounds()
                self.ship_at(self.slot(1), 'cobra', 0, 0, 0, 'typ_trader')
                self.missile_at(self.slot(1), logic)
                self.call('do_locked')
                self.assertEqual(self.read(self.slot(1), 'logic'),
                                 self.symbols['log_exploding'])
                self.assertEqual(self.symbols['sfx_explosion'] in self.sounds,
                                 heard)

    def test_a_ships_laser_hits_for_two_to_twelve(self):
        """NPC_DAMAGE sets the base roll and the multiplier is 2..4, so a hit
        between two ships lands in 2..12. Both rolls are planted at their
        extremes without naming NPC_DAMAGE, so this pins the damage itself
        rather than restating the constant. RANDOM's low two bits choose the
        multiplier: 196 gives 2, 198 gives 4."""
        for base, coin, expected in ((0, 196, 2), (0xffff, 196, 6),
                                     (0, 198, 4), (0xffff, 198, 12)):
            with self.subTest(base=base, multiplier=coin):
                self.prepare()
                self.aimed_shot(at_player=False)
                self.field(self.slot(1), 'health', 100)
                self.scratch(self.RAND_VALUE, base) ; # planted at its extremes
                self.scratch(self.RANDOM_VALUE, coin)
                self.call('do_attack')
                self.assertEqual(100 - self.read(self.slot(1), 'health'),
                                 expected)

    def launch(self, mission=0):
        """Run LAUNCH_VIPERS to the point where it hands out one ship."""
        self.prepare()
        self.scratch(self.ALLOC_BUDGET, 1)
        self.var('launch_count', 1)
        self.var('launch_rate', 1)      # the countdown expires on this call
        self.var('police_hunt', 1)      # launched to arrest him
        self.var('mission', mission)
        self.call('launch_vipers')
        return self.ALLOC_POOL

    def test_a_launched_police_ship_leaves_the_dock_after_the_player(self):
        """PREPARE_VIPERS scales the wave by the player's combat rating, so a
        launch is always about him. He has to be marked on the ship itself:
        PICK_TARGET offers him only to a pirate, an alien or a ship already
        angry with him, and a policeman is none of those. Without the mark
        RETARGET finds a launched viper nothing to fight and, counting
        LOG_PEEL_OFF and LOG_RUN_OFF as fighting, sends it cruising out of
        scanner range instead."""
        for mission, kind in ((0x00, 'viper'), (0x52, 'thargoid')):
            with self.subTest(mission=mission):
                launched = self.launch(mission)
                self.assertEqual(self.read(launched, 'type'),
                                 self.symbols[kind])
                self.assertTrue(self.read(launched, 'flags')
                                & (1 << (8 + self.symbols['angry'])),
                                'launched ship is not marked as hunting him')

    def test_nothing_is_marked_when_no_viper_is_launched(self):
        """The mark belongs to the launch, not to the routine running."""
        self.prepare()
        self.scratch(self.ALLOC_BUDGET, 1)
        self.var('launch_count', 0)     # none waiting to launch
        self.var('launch_rate', 1)
        self.call('launch_vipers')
        self.assertEqual(self.read(self.ALLOC_POOL, 'flags'), 0)

    def test_only_a_policeman_sent_after_him_hunts_the_player(self):
        """The counterpart: a viper flying in a random encounter is busy with
        pirates and must leave him alone, which is what keeps the mark, rather
        than the SHIP_TYPE, as the thing PICK_TARGET reads."""
        for hunting in (False, True):
            with self.subTest(hunting=hunting):
                self.prepare()
                self.ship_at(self.ship, 'viper', 0, 0, 900, 'typ_police')
                self.field(self.ship, 'logic', self.symbols['log_run_off'])
                if hunting:
                    self.set_flags(self.ship, 'in_use', 'angry')
                self.call('retarget')
                if hunting:
                    self.assertEqual(self.read(self.ship, 'target', 4), 0)
                    self.assertEqual(self.read(self.ship, 'logic'),
                                     self.symbols['log_run_off'])
                else:
                    self.assertEqual(self.read(self.ship, 'target', 4),
                                     self.symbols['no_target'])
                    self.assertEqual(self.read(self.ship, 'logic'),
                                     self.symbols['log_cruise'])

    def test_a_viper_outside_the_station_launch_leaves_the_player_alone(self):
        """The counterpart of the launch mark, from the other side: a viper an
        encounter placed carries none, so the player is not a candidate for it
        at all and it hunts the pirate it came for even with him nearer."""
        self.prepare()
        # The player is 500 away from the viper, the pirate 3500 away.
        self.ship_at(self.ship, 'viper', 0, 0, 500, 'typ_police')
        self.ship_at(self.slot(1), 'krait', 0, 0, 4000)
        self.assertEqual(self.call('pick_target'), 1)
        self.assertEqual(self.read(self.ship, 'target', 4), self.slot(1))

    def test_a_launched_viper_still_prefers_a_nearer_pirate(self):
        """And the mark makes the player a candidate, not the only candidate.
        A launched viper stays an ordinary faction ship: of the player at
        10000 and a pirate at 2000 it takes the pirate."""
        self.prepare()
        self.ship_at(self.ship, 'viper', 0, 0, 10000, 'typ_police')
        self.set_flags(self.ship, 'in_use', 'angry')
        self.ship_at(self.slot(1), 'krait', 0, 0, 12000)
        self.assertEqual(self.call('pick_target'), 1)
        self.assertEqual(self.read(self.ship, 'target', 4), self.slot(1))

    def test_an_encounter_never_inherits_a_launch_mark(self):
        """ALLOC_OBJECT hands records back out, so a record a station launch
        marked can become an encounter's viper. Every creator writes FLAGS
        outright, which clears the mark; this pins that."""
        self.prepare()
        angry = 1 << (8 + self.symbols['angry'])
        for slot in range(8):
            self.field(self.ALLOC_POOL + slot * self.symbols['obj_len'],
                       'flags', angry)
        members = self.encounter(govern=7, template=3)  # pirates and vipers
        self.assertTrue(members)
        for member in members:
            self.assertFalse(self.read(member, 'flags') & angry,
                             'encounter ship inherited a launch mark')

    def global_word(self, name):
        return int.from_bytes(
            self.cpu.mem_read(VARIABLES + self.symbols[name], 2), 'big')

    def shoot(self, kind, ship_type, attack='act_attack'):
        """One accepted player shot landing inside station space."""
        self.prepare()
        self.watch_stubs()
        self.ship_at(self.ship, kind, 0, 0, 2000, ship_type, attack)
        self.field(self.ship, 'health', 500)   # survives the shot
        self.var('hit_check', 1)
        self.var('laser_power', 1)
        self.var('radar_obj', 1)               # inside station space
        self.call('check_hit')

    def test_an_alien_in_the_zone_scrambles_vipers_that_are_not_after_him(self):
        """1988 launches vipers whenever the player's shot lands on an alien
        inside station space: the station is scrambling against the alien, not
        arresting him. He may be perfectly clean, so the launch must not mark
        the ships for him or they turn on him once the aliens are dead."""
        self.shoot('thargoid', 'typ_alien')
        self.assertIn('prepare_vipers', self.entered)
        self.assertEqual(self.global_word('police_hunt'), 0)

    def test_shooting_the_station_or_its_own_launches_the_vipers_at_him(self):
        for kind, ship_type in (('spacestn', 'typ_trader'),
                                ('cobra', 'typ_trader'),
                                ('viper', 'typ_police')):
            with self.subTest(kind=kind):
                self.shoot(kind, ship_type)
                self.assertIn('prepare_vipers', self.entered)
                self.assertNotEqual(self.global_word('police_hunt'), 0)

    def test_his_police_record_launches_them_at_him_too(self):
        self.prepare()
        self.watch_stubs()
        self.var('police_record', 255)
        self.government(7)
        self.scratch(self.RANDOM_VALUE, 0)   # inside the probability
        self.call('check_police')
        self.assertIn('prepare_vipers', self.entered)
        self.assertNotEqual(self.global_word('police_hunt'), 0)

    def test_a_scrambled_viper_leaves_the_dock_unmarked(self):
        """The other half of the same rule, at the launch itself."""
        self.prepare()
        self.scratch(self.ALLOC_BUDGET, 1)
        self.var('launch_count', 1)
        self.var('launch_rate', 1)
        self.var('police_hunt', 0)           # scrambled against an alien
        self.call('launch_vipers')
        self.assertFalse(self.read(self.ALLOC_POOL, 'flags')
                         & (1 << (8 + self.symbols['angry'])),
                         'a scrambled viper must not hunt a clean player')

    def angry_bit(self, slot):
        return bool(self.read(slot, 'flags')
                    & (1 << (8 + self.symbols['angry'])))

    def test_his_own_shot_provokes_the_ship_it_lands_on(self):
        """ANGRY is what PICK_TARGET reads to decide whether the player is a
        candidate, and nothing used to set it except DO_ATTACK, which a ship
        only reaches once it already hunts him. A ship he shoots therefore
        never fought back: it broke off, found no target, and cruised away."""
        for kind, ship_type in (('cobra', 'typ_trader'), ('viper', 'typ_police')):
            with self.subTest(kind=kind):
                self.shoot(kind, ship_type)
                self.assertTrue(self.angry_bit(self.ship),
                                'his shot must provoke the ship')
                # And the provoked ship now takes him as a candidate.
                self.field(self.ship, 'target', self.symbols['no_target'], 4)
                self.call('pick_target')
                self.assertEqual(self.read(self.ship, 'target', 4), 0)

    def test_his_shot_does_not_provoke_what_cannot_fight_back(self):
        """The station, asteroids, canisters and the rest carry ACT_NOTHING.
        Marking them would light the cockpit attack indicator, which DO_LOGIC
        drives straight off ANGRY, every time he shoots a rock."""
        for kind, ship_type, attack in (('spacestn', 'typ_trader', 'act_nothing'),
                                        ('cobra', 'typ_trader', 'act_nothing'),
                                        ('python', 'typ_trader', 'act_runaway')):
            with self.subTest(kind=kind, attack=attack):
                self.shoot(kind, ship_type, attack)
                self.assertFalse(self.angry_bit(self.ship))

    def test_another_ships_shot_provokes_nobody(self):
        """ANGRY means the player provoked this ship, so an AI-versus-AI hit
        must leave it alone however hard it lands."""
        self.prepare()
        self.ship_at(self.ship, 'krait', 0, 0, 2000)
        self.ship_at(self.other, 'cobra', 0, 0, 3000, 'typ_trader')
        self.field(self.other, 'health', 500)
        self.field(self.ship, 'target', self.other, 4)
        self.call('damage_target', d0=5)
        self.assertFalse(self.angry_bit(self.other))
        self.assertFalse(self.angry_bit(self.ship))

    def test_a_provoked_ship_does_not_need_to_wait_for_retarget(self):
        """RETARGET reaches one slot every MAX_OBJECTS frames, but START_PEEL_OFF
        can be over in as few as 450/turn_rate -- eleven frames for a Thargoid,
        fourteen for a Krait. A ship the player shot therefore often arrives in
        DO_ATTACK before RETARGET has given it a target, and without this the
        IS_COMBAT_SHIP fallback would send it cruising, where DO_CRUISING clears
        ANGRY and the provocation is lost for good."""
        for angry, logic, target in ((True, 'log_attack', 0),
                                     (False, 'log_cruise', None)):
            with self.subTest(angry=angry):
                self.prepare()
                self.attacker(0, 0, 2000)
                self.field(self.ship, 'target', self.symbols['no_target'], 4)
                if angry:
                    self.set_flags(self.ship, 'in_use', 'angry')
                self.call('do_attack')
                self.assertEqual(self.read(self.ship, 'logic'),
                                 self.symbols[logic])
                self.assertEqual(self.read(self.ship, 'target', 4),
                                 self.symbols['no_target'] if target is None
                                 else target)

    def test_provoking_a_ship_does_not_pull_it_out_of_its_own_fight(self):
        """ANGRY makes the player a candidate, and DO_ATTACK's fallback names
        him outright when RETARGET has not got there yet. Neither may touch a
        ship that already holds a live target: it keeps the fight it is in,
        and PICK_TARGET decides between the two on distance like any other."""
        self.prepare()
        self.watch_stubs()
        pirate, trader = self.ship, self.slot(1)
        self.ship_at(pirate, 'krait', 0, 0, 9000, 'typ_pirate')
        self.ship_at(trader, 'cobra', 0, 0, 9500, 'typ_trader')
        self.field(pirate, 'logic', self.symbols['log_attack'])
        self.field(pirate, 'target', trader, 4)
        self.field(pirate, 'turn_rate', 3)
        self.set_flags(pirate, 'in_use', 'angry')
        self.long(self.DIST_VALUE, 500)

        # The fallback is never reached: VALIDATE_TARGET is happy.
        self.call('do_attack')
        self.assertEqual(self.read(pirate, 'target', 4), trader)
        self.assertEqual(self.read(pirate, 'logic'), self.symbols['log_attack'])

        # And its missile still belongs to that fight, not to the player.
        self.field(pirate, 'no_missiles', 2)
        self.long(self.DIST_VALUE, 5000)   # LAUNCH_MISSILE wants 2000 clear
        self.var('npc_hit', 1)
        self.scratch(self.ALLOC_BUDGET, 1)
        self.call('low_energy')
        self.assertEqual(self.read(self.ALLOC_POOL, 'logic'),
                         self.symbols['log_ai_missile'])
        self.assertEqual(self.read(self.ALLOC_POOL, 'target', 4), trader)
        self.assertNotIn('disp_message', self.entered)

    def test_damage_target_reduces_the_targets_health(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.watch_stubs()
                self.ship_at(self.ship, 'krait', 0, 0, 10000)
                self.ship_at(self.slot(1), 'cobra', 0, 0, 12000, 'typ_trader')
                self.field(self.ship, 'target', self.slot(1), 4)
                self.field(self.slot(1), 'health', 100)
                self.call('damage_target', d0=12)
                self.assertEqual(self.read(self.slot(1), 'health'), 88)
                self.assertNotIn('add_kill', self.entered)

    def test_a_lethal_hit_explodes_the_target_without_crediting_the_player(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.watch_stubs()
                self.ship_at(self.ship, 'krait', 0, 0, 10000)
                self.ship_at(self.slot(1), 'cobra', 0, 0, 12000, 'typ_trader')
                self.field(self.ship, 'target', self.slot(1), 4)
                self.field(self.slot(1), 'health', 4)
                self.call('damage_target', d0=9)
                self.assertEqual(self.read(self.slot(1), 'logic'),
                                 self.symbols['log_exploding'])
                self.assertNotIn('add_kill', self.entered)
                self.assertNotIn('inc_record', self.entered)
                self.assertIn('release_cargo', self.entered)
                self.assertIn('target_lost', self.entered)
                flags = self.read(self.slot(1), 'flags', 1)
                self.assertTrue(flags & 1 << self.symbols['no_bounty'])
                self.assertEqual(self.read(VARIABLES, 'npc_kill'), 0)

    def test_a_player_kill_still_credits_score_and_record(self):
        self.prepare()
        self.watch_stubs()
        self.ship_at(self.slot(1), 'cobra', 0, 0, 12000, 'typ_trader')
        self.var('npc_kill', 0)
        self.call_with('explode_object', self.ship, self.slot(1))
        self.assertIn('add_kill', self.entered)
        self.assertIn('inc_record', self.entered)
        flags = self.read(self.slot(1), 'flags', 1)
        self.assertFalse(flags & 1 << self.symbols['no_bounty'])

    def test_validate_target_accepts_the_player_and_live_ships(self):
        self.prepare()
        self.ship_at(self.ship, 'krait', 0, 0, 10000)
        self.ship_at(self.slot(1), 'cobra', 0, 0, 12000, 'typ_trader')
        self.field(self.ship, 'target', 0, 4)
        self.assertEqual(self.call('validate_target'), 1)
        self.field(self.ship, 'target', self.slot(1), 4)
        self.assertEqual(self.call('validate_target'), 1)

    def test_validate_target_drops_dead_and_missing_targets(self):
        cases = [('no target', lambda: self.field(
                     self.ship, 'target', self.symbols['no_target'], 4)),
                 ('freed record', lambda: self.set_flags(self.slot(1))),
                 ('being removed', lambda: self.set_flags(
                     self.slot(1), 'in_use', 'remove')),
                 ('exploding', lambda: self.field(
                     self.slot(1), 'logic', self.symbols['log_exploding']))]
        for label, break_it in cases:
            with self.subTest(reason=label):
                self.prepare()
                self.ship_at(self.ship, 'krait', 0, 0, 10000)
                self.ship_at(self.slot(1), 'cobra', 0, 0, 12000, 'typ_trader')
                self.field(self.ship, 'target', self.slot(1), 4)
                break_it()
                self.assertEqual(self.call('validate_target'), 0)
                self.assertEqual(self.read(self.ship, 'target', 4),
                                 self.symbols['no_target'])

    def test_target_range_uses_obj_range_for_the_player(self):
        self.prepare()
        self.ship_at(self.ship, 'krait', 0, 0, 4321)
        self.field(self.ship, 'target', 0, 4)
        self.call('target_range_calc')
        self.assertEqual(self.read(VARIABLES, 'target_range', 4), 4321)
        self.assertEqual(self.read(self.ship, 'obj_range', 4), 4321)

    def test_target_range_measures_the_gap_to_another_ship(self):
        self.prepare()
        self.ship_at(self.ship, 'krait', 0, 0, 4321)
        self.ship_at(self.slot(1), 'cobra', 0, 0, 9000, 'typ_trader')
        self.field(self.ship, 'target', self.slot(1), 4)
        self.call('target_range_calc')
        self.assertEqual(self.read(VARIABLES, 'target_range', 4), self.STUB_DISTANCE)
        self.assertEqual(self.read(self.ship, 'obj_range', 4), 4321)

    def test_combat_state_classifies_every_logic(self):
        for state, expected in ([(s, 1) for s in self.PASSIVE]
                                + [(s, 2) for s in self.FIGHTING]
                                + [(s, 0) for s in self.LOCKED]):
            with self.subTest(state=state):
                self.prepare()
                self.assertEqual(self.call('combat_state', d1=self.symbols[state]),
                                 expected)

    def test_a_cruising_ship_enters_combat(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.ship_at(self.ship, 'krait', 0, 0, 10000)
                self.field(self.ship, 'health', 90)
                self.field(self.ship, 'on_course', 7)
                self.ship_at(self.slot(1), 'cobra', 0, 0, 12000, 'typ_trader')
                self.call('retarget')
                self.assertEqual(self.read(self.ship, 'logic'), self.symbols['log_attack'])
                self.assertEqual(self.read(self.ship, 'target', 4), self.slot(1))
                self.assertEqual(self.read(self.ship, 'on_course'), 0)
                self.assertEqual(self.read(self.ship, 'pre_attack'), 90)

    def test_a_launching_or_docking_ship_is_never_interrupted(self):
        for state in self.LOCKED:
            with self.subTest(state=state):
                self.prepare()
                self.ship_at(self.ship, 'krait', 0, 0, 10000)
                self.field(self.ship, 'logic', self.symbols[state])
                self.ship_at(self.slot(1), 'cobra', 0, 0, 12000, 'typ_trader')
                self.call('retarget')
                self.assertEqual(self.read(self.ship, 'logic'), self.symbols[state])
                self.assertEqual(self.read(self.ship, 'target', 4),
                                 self.symbols['no_target'])

    def test_a_fighter_without_a_candidate_disengages(self):
        for state in self.FIGHTING:
            with self.subTest(state=state):
                self.prepare()
                self.ship_at(self.ship, 'krait', 0, 0, self.symbols['radar_range'] + 1)
                self.field(self.ship, 'logic', self.symbols[state])
                self.call('retarget')
                self.assertEqual(self.read(self.ship, 'logic'), self.symbols['log_cruise'])
                self.assertEqual(self.read(self.ship, 'on_course'), 1)

    def test_a_fighter_keeps_its_state_when_the_target_changes(self):
        self.prepare()
        self.ship_at(self.ship, 'krait', 0, 0, 10000)
        self.field(self.ship, 'logic', self.symbols['log_run_off'])
        self.ship_at(self.slot(1), 'cobra', 0, 0, 12000, 'typ_trader')
        self.call('retarget')
        self.assertEqual(self.read(self.ship, 'logic'), self.symbols['log_run_off'])
        self.assertEqual(self.read(self.ship, 'target', 4), self.slot(1))

    def test_only_this_frames_slot_re_targets(self):
        self.prepare()
        self.ship_at(self.ship, 'krait', 0, 0, 10000)
        self.ship_at(self.slot(1), 'cobra', 0, 0, 12000, 'typ_trader')
        self.var('this_obj', 0)
        self.var('retarget_slot', 1)
        self.call('retarget')
        self.assertEqual(self.read(self.ship, 'target', 4), self.symbols['no_target'])
        self.var('retarget_slot', 0)
        self.call('retarget')
        self.assertEqual(self.read(self.ship, 'target', 4), self.slot(1))

    def test_a_runaway_ship_never_hunts(self):
        self.prepare()
        self.ship_at(self.ship, 'python', 0, 0, 10000, 'typ_trader',
                     attack='act_runaway')
        self.ship_at(self.slot(1), 'krait', 0, 0, 12000)
        self.call('retarget')
        self.assertEqual(self.read(self.ship, 'target', 4), self.symbols['no_target'])
        self.assertEqual(self.read(self.ship, 'logic'), self.symbols['log_cruise'])

    def test_nearest_hostile_ship_wins(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                # The player is 10000 away; the nearest trader is 2000 away.
                self.ship_at(self.ship, 'krait', 0, 0, 10000)
                self.ship_at(self.slot(1), 'cobra', 0, 0, 16000, 'typ_trader')
                self.ship_at(self.slot(2), 'cobra', 0, 0, 12000, 'typ_trader')
                self.ship_at(self.slot(3), 'cobra', 0, 0, 19000, 'typ_trader')
                self.assertEqual(self.call('pick_target'), 1)
                self.assertEqual(self.read(self.ship, 'target', 4), self.slot(2))

    def test_player_competes_under_the_same_rule(self):
        for distance, expects_player in ((900, True), (3000, False)):
            with self.subTest(distance=distance):
                self.prepare()
                # The player is `distance` away, the trader always 2000 away.
                self.ship_at(self.ship, 'krait', 0, 0, distance)
                self.ship_at(self.slot(1), 'cobra', 0, 0, distance + 2000, 'typ_trader')
                self.call('pick_target')
                expected = 0 if expects_player else self.slot(1)
                self.assertEqual(self.read(self.ship, 'target', 4), expected)

    def test_trader_ignores_the_player_until_angry(self):
        self.prepare()
        # The player is 500 away, the pirate 3500 away.
        self.ship_at(self.ship, 'cobra', 0, 0, 500, 'typ_trader')
        self.ship_at(self.slot(1), 'krait', 0, 0, 4000)
        self.call('pick_target')
        self.assertEqual(self.read(self.ship, 'target', 4), self.slot(1))
        self.set_flags(self.ship, 'in_use', 'angry')
        self.call('pick_target')
        self.assertEqual(self.read(self.ship, 'target', 4), 0)

    def test_candidates_are_filtered(self):
        cases = [('not in use', lambda s: self.set_flags(s)),
                 ('flagged for removal', lambda s: self.set_flags(s, 'in_use', 'remove')),
                 ('exploding', lambda s: self.field(
                     s, 'logic', self.symbols['log_exploding'])),
                 ('not a combat ship', lambda s: self.field(
                     s, 'type', self.symbols['spacestn'])),
                 ('mission ship', lambda s: self.field(
                     s, 'type', self.symbols['cougar'])),
                 ('same faction', lambda s: self.field(
                     s, 'ship_type', self.symbols['typ_pirate'])),
                 ('beyond scanner range', lambda s: self.field(
                     s, 'obj_range', self.symbols['radar_range'] + 1, 4))]
        for label, break_it in cases:
            with self.subTest(reason=label):
                self.prepare()
                # Out of the player's scanner range, so he is not a candidate.
                self.ship_at(self.ship, 'krait', 0, 0, self.symbols['radar_range'] + 1)
                self.ship_at(self.slot(1), 'cobra', 0, 0, 2000, 'typ_trader')
                break_it(self.slot(1))
                self.assertEqual(self.call('pick_target'), 0)
                self.assertEqual(self.read(self.ship, 'target', 4),
                                 self.symbols['no_target'])

    def test_a_hunter_never_targets_itself(self):
        self.prepare()
        self.ship_at(self.ship, 'krait', 0, 0, self.symbols['radar_range'] + 1)
        self.assertEqual(self.call('pick_target'), 0)
        self.assertEqual(self.read(self.ship, 'target', 4), self.symbols['no_target'])

    def test_chebyshev_range_is_the_largest_axis_difference(self):
        cases = [((0, 0, 0), (300, 0, 0), 300),
                 ((0, 0, 0), (0, -400, 0), 400),
                 ((0, 0, 0), (100, 200, -700), 700),
                 ((1000, 2000, 3000), (1000, 2000, 3000), 0),
                 ((-5000, 0, 0), (5000, 0, 0), 10000),
                 ((6000, -6000, 100), (-6000, 6000, 100), 12000)]
        for cpu in CPUS:
            for hunter, candidate, expected in cases:
                with self.subTest(cpu=cpu, hunter=hunter, candidate=candidate):
                    self.prepare(cpu)
                    self.place(self.ship, *hunter)
                    self.place(self.other, *candidate)
                    self.call('chebyshev_range')
                    self.assertEqual(self.cpu.reg_read(UC_M68K_REG_D0), expected)

    def test_chebyshev_range_is_symmetric(self):
        self.prepare()
        self.place(self.ship, -120, 4000, 88)
        self.place(self.other, 900, -3000, 12)
        forward = self.call_with('chebyshev_range', self.ship, self.other)
        backward = self.call_with('chebyshev_range', self.other, self.ship)
        self.assertEqual(forward, backward)
        self.assertEqual(forward, 7000)

    def test_target_coords_returns_the_origin_for_the_player(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.place(self.ship, 700, -200, 1500)
                self.field(self.ship, 'target', 0, 4)
                self.call('target_coords')
                for register in (UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2):
                    self.assertEqual(self.cpu.reg_read(register), 0)

    def test_target_coords_returns_the_targets_position(self):
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.place(self.ship, 700, -200, 1500)
                self.place(self.other, -1234, 5678, 90)
                self.field(self.ship, 'target', self.other, 4)
                self.call('target_coords')
                values = [self.cpu.reg_read(r) for r in
                          (UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2)]
                values = [v - (1 << 32) if v >> 31 else v for v in values]
                self.assertEqual(values, [-1234, 5678, 90])

    def test_combat_whitelist_covers_exactly_the_fighting_ships(self):
        for cpu in CPUS:
            for name, number, _, _ in ship_table():
                with self.subTest(cpu=cpu, ship=name):
                    self.prepare(cpu)
                    expected = (number in (self.symbols['viper'], self.symbols['thargon'])
                                or self.symbols['first_combat'] <= number
                                <= self.symbols['last_combat'])
                    self.field(self.other, 'type', number)
                    self.assertEqual(bool(self.call('is_combat_ship')), expected)

    def test_mission_ships_and_scenery_are_never_combat_ships(self):
        self.prepare()
        for name in ('cougar', 'constr', 'spacestn'):
            with self.subTest(object=name):
                self.field(self.other, 'type', self.symbols[name])
                self.assertEqual(self.call('is_combat_ship'), 0)

    def test_faction_hostility_matrix(self):
        for cpu in CPUS:
            for hunter, hostile in HOSTILITY.items():
                for victim in HOSTILITY:
                    with self.subTest(cpu=cpu, hunter=hunter, victim=victim):
                        self.prepare(cpu)
                        self.field(self.ship, 'ship_type', self.symbols[hunter])
                        self.field(self.other, 'ship_type', self.symbols[victim])
                        self.assertEqual(bool(self.call('is_hostile')),
                                         victim in hostile)


    # ---- A Thargoid's brood, whoever killed her -------------------------

    def thargon_at(self, slot, mother_slot, z=1000):
        """A Thargon still in the fight, tied to the mother in MOTHER_SLOT."""
        self.ship_at(slot, 'thargon', 0, 0, z, 'typ_alien')
        self.field(slot, 'logic', self.symbols['log_attack'])
        self.field(slot, 'mother', mother_slot)

    def asleep(self, slot):
        """What EXPLODE_OBJECT leaves a Thargon whose mother has died: it
        cruises away and HIT_REACTION and LOW_ENERGY both pass over it."""
        return (self.read(slot, 'logic') == self.symbols['log_cruise']
                and self.read(slot, 'attack_type') == self.symbols['act_nothing'])

    def test_a_thargoid_the_player_shot_down_puts_her_brood_to_sleep(self):
        """CHECK_HIT explodes the very ship the main loop is servicing, so the
        cursor and the dying mother have always agreed on this path."""
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.ship_at(self.slot(2), 'thargoid', 0, 0, 1000, 'typ_alien')
                self.thargon_at(self.slot(3), 2)
                self.var('this_obj', 2)
                self.call_with('explode_object', self.slot(2), self.slot(2))
                self.assertTrue(self.asleep(self.slot(3)))

    def test_the_brood_that_sleeps_is_the_one_whose_mother_died(self):
        """A4 is the mother that died; THIS_OBJ is only the main loop's
        cursor, and the two part company as soon as something other than the
        dying ship is being serviced. Reading the cursor left her own brood
        hunting and put another mother's brood to sleep instead."""
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.ship_at(self.slot(1), 'thargoid', 0, 0, 1000, 'typ_alien')
                self.thargon_at(self.slot(2), 1)  # hers
                self.thargon_at(self.slot(3), 0)  # another mother's
                self.var('this_obj', 0)
                self.call_with('explode_object', self.ship, self.slot(1))
                self.assertTrue(self.asleep(self.slot(2)))
                self.assertFalse(self.asleep(self.slot(3)))

    def test_a_missile_kill_puts_the_thargoids_brood_to_sleep(self):
        """DO_LOCKED runs while the main loop services the missile, not the
        mother it detonates on."""
        for cpu in CPUS:
            for logic in ('log_locked', 'log_ai_missile'):
                with self.subTest(cpu=cpu, logic=logic):
                    self.prepare(cpu)
                    self.watch_stubs()
                    self.ship_at(self.slot(1), 'thargoid', 0, 0, 0, 'typ_alien')
                    self.thargon_at(self.slot(2), 1)
                    self.missile_at(self.slot(1), logic)
                    self.call('do_locked')
                    self.assertEqual(self.read(self.slot(1), 'logic'),
                                     self.symbols['log_exploding'])
                    self.assertTrue(self.asleep(self.slot(2)))

    def test_a_thargoid_another_ship_shot_down_puts_her_brood_to_sleep(self):
        """DAMAGE_TARGET runs while the main loop services the shooter."""
        for cpu in CPUS:
            with self.subTest(cpu=cpu):
                self.prepare(cpu)
                self.watch_stubs()
                self.ship_at(self.ship, 'cobra', 0, 0, 10000, 'typ_trader')
                self.ship_at(self.slot(1), 'thargoid', 0, 0, 12000, 'typ_alien')
                self.thargon_at(self.slot(2), 1)
                self.field(self.ship, 'target', self.slot(1), 4)
                self.field(self.slot(1), 'health', 4)
                self.call('damage_target', d0=9)
                self.assertEqual(self.read(self.slot(1), 'logic'),
                                 self.symbols['log_exploding'])
                self.assertTrue(self.asleep(self.slot(2)))


if __name__ == '__main__':
    unittest.main()
