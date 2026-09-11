"""Run instant-hit laser logic and the native raster on MC68000/MC68020.

The actual flight loop is used with unrelated world/UI services stubbed out.
Optional dependency: unicorn==2.1.4.
"""
from pathlib import Path
import math
import re
import struct
import unittest

from test_raster import BACKGROUND, GUARD, SCREEN, OTHER, paint, pixels, routine
from test_viewport import assemble, preamble, variable_block

try:
    from unicorn import (Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE,
                         UC_PROT_READ, UC_PROT_EXEC)
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_D0,
        UC_M68K_REG_D1, UC_M68K_REG_D2, UC_M68K_REG_D3, UC_M68K_REG_PC,
        UC_M68K_REG_SR)
except ImportError:
    Uc = None

ROOT = Path(__file__).resolve().parents[1]
CODE, STOP, VARIABLES, STACK = 0x10000, 0x1000, 0x30000, 0x90000
NODES, CLOCK = 0x71000, 0x466
LASER_COLOURS = (6, 4, 3, 15)  # pulse red, mining magenta, beam orange, military white
VIEWS = ('front', 'rear', 'left', 'right')


def player_colour(kind):
    return tuple(65535 if LASER_COLOURS[kind] & (1 << plane) else 0 for plane in range(4))


def ship_models():
    source = (ROOT / 'asm/objects.dat').read_text()
    table = (ROOT / 'asm/objects.m68').read_text().split('include')[0]
    exclude = {'spcstn', 'dodec', 'missile', 'barrel', 'astroid', 'platlet',
               'e', 'l', 'i', 't'}
    for name in re.findall(r'^\s*dc\.l\s+(\w+)\s*$', table, re.M):
        if name in exclude or name.startswith('panel'):
            continue
        record = re.search(r'^' + name + r':\s+dc\.l\s+(\w+)\s+'
                           r'dc\.l\s+\w+\s+dc\.l\s+\w+\s+dc\s+([^\n]+)',
                           source, re.M)
        values = [int(v) for v in record[2].split(',')]
        body = re.search(r'^' + record[1] + r':\s*((?:\s*dc\s+[^\n]+\s*)+)',
                         source, re.M)[1]
        words = [int(v) for v in re.findall(r'-?\d+', body)]
        yield name, values[5], values[1], words


@unittest.skipIf(Uc is None, 'optional laser tests require unicorn==2.1.4')
class LaserTests(unittest.TestCase):
    ai_fire_sound = False
    beam_style = 'dualbeam'
    bases = ((-92, -80), (80, 92))

    @classmethod
    def setUpClass(cls):
        src = {name: (ROOT / 'asm' / (name + '.m68')).read_text()
               for name in ('combat', 'special', 'logic', 'main', 'vector',
                            'graphics', 'maths', 'cockpit')}
        groups = {
            'combat': ['fire', 'laser_in_sights', 'check_hit', 'reduce_shields', 'reduce_energy'],
            'special': ['draw_lasers', 'draw_laser_wedge', 'draw_ai_laser'],
            'logic': ['ai_laser_aim', 'do_attack'],
            'main': ['game_logic'],
            'vector': ['transform', 'calc_yvector'] +
                      [f'{size}_swap_{view}' for view in VIEWS for size in ('w', 'l')],
            'maths': ['random', 'rand'],
            'graphics': ['c_line', 'line', 'horiz_line', 'vert_line', 'mask_plot',
                         'dot_to_addr', 'solid_polygon', 'set_colour'],
        }
        names = [name for group in groups.values() for name in group] + ['fx']
        constants = ['laser_pending', 'hit_check', 'firing', 'laser_beam',
                     'laser_flash', 'laser_flash_end', 'laser_tip_x', 'laser_tip_y', 'laser_audio_request',
                     'laser_temp', 'laser_type', 'laser_rate', 'laser_power',
                     'max_ltemp', 'game_frozen', 'docked', 'cockpit_on',
                     'scr_base', 'colour_ptr', 'random_seed', 'obj_hit',
                     'objects', 'obj_len', 'max_objects', 'type', 'flags', 'in_use',
                     'invincible', 'yvector_ok', 'ai_laser', 'logic', 'log_attack',
                     'log_cruise', 'log_exploding', 'health', 'pre_attack',
                     'attack_type', 'act_nothing', 'obj_ctr', 'viper', 'constr', 'thargoid', 'thargon',
                     'mood', 'rating', 'obj_range', 'xpos', 'ypos', 'zpos',
                     'this_xpos', 'this_ypos', 'this_zpos', 'in_sights', 'hits_rad',
                     'gun_node', 'no_nodes', 'nodes', 'x_vector', 'y_vector',
                     'z_vector', 'w_view_ptr', 'l_view_ptr', 'unit', 'view',
                     'cloaking_on', 'controls_locked', 'radar_obj', 'on_course',
                     'front_shield', 'aft_shield', 'max_shield', 'shields_fx', 'energy', 'max_energy',
                     'frame_count', 'reduce_ctr', 'laser_info', 'white', 'sfx_laser', 'sfx_shields', 'sfx_hit']
        assembly = ('laser_singlebeam equ 1\n' if cls.beam_style == 'singlebeam' else '')
        assembly += 'aifiresound equ 1\n' if cls.ai_fire_sound else ''
        assembly += preamble() + '\tinclude "bitlist.m68"\n'
        assembly += 'max_vert equ 15\n'
        assembly += variable_block(src['graphics'], 'graphics').replace('judder:', 'graphics_judder:')
        assembly += 'left_arm equ $74000\nright_arm equ $75000\n'
        if ROOT.name == 'src_amiga':
            assembly += f'frclock equ {CLOCK}\n'
        combat = src['combat']
        assembly += combat[combat.index('slow_charge:'):combat.index('\tq_module combat')]
        logic = src['logic']
        assembly += logic[logic.index('fire_range:'):logic.index('\tq_module logic')]
        for file, macro in [('graphics', 'outcodes'), ('vector', 'cross')]:
            assembly += re.search(r'^' + macro + r' macro.*?^\s*endm',
                                  src[file], re.M | re.S)[0] + '\n'
        assembly += '\torg $10000\n\tdc.l ' + ','.join(names + constants) + '\n'
        for file, group in groups.items():
            assembly += '\n'.join(routine(src[file], name) for name in group)
        assembly += re.search(r'^damage:\s*\n\s*dc.w[^\n]+', logic, re.M)[0] + '\n'
        assembly += re.search(r'^laser_info:\s*\n(?:\s*dc [^\n]+\n)+',
                              src['cockpit'], re.M)[0] + '\n'
        assembly += src['graphics'][src['graphics'].index('\tq_global bit_masks'):
                                    src['graphics'].index('clip_list:')]
        assembly += '\nmult_by_320:\n\tdc.w ' + ','.join(str(y * 320) for y in range(200)) + '\n'
        assembly += f'''
draw_object:
    movem.l xpos(a5),d0-d2
    move.l l_view_ptr(a6),a0
    jsr (a0)
    movem.l d0-d2,this_xpos(a5)
    st in_sights(a6)
    btst #invincible,flags(a5)
    beq .done
    clr in_sights(a6)
.done:
    rts
peel_off_check:
    ori #1,ccr
    rts
'''
        stubs = ['auto_pilot', 'short_equip', 'fx', 'start_peel_off', 'explode_object', 'target_lost',
                 'release_cargo', 'low_energy', 'prepare_vipers',
                 'disp_message', 'find_table', 'str_copy', 'str_cat', 'speed_control',
                 'clear_image', 'remove_radar', 'update_inst', 'do_countdown',
                 'damping', 'flash_message', 'torus_drive', 'get_range', 'collision',
                 'radar', 'mini_radar', 'do_logic', 'world_z_rotate', 'world_x_rotate',
                 'orthogonal', 'move', 'radar_lock', 'calc_altitude', 'warnings',
                 'ecm', 'docking', 'recharge', 'draw_space', 'draw_sight', 'text_blatt',
                 'swap_screen', 'remove_objects', 'object_logic', 'run_docking',
                 'hyperspace', 'is_game_over']
        assembly += '\n' + '\n'.join(name + ':\n\trts' for name in stubs) + '\n'
        assembly += 'text12:\ntext13:\ntext18:\ntext19:\n\tdc.w 0\n'
        (ROOT / 'build/laser-qa').mkdir(parents=True, exist_ok=True)
        (ROOT / ('build/laser-qa/test-lasers-' + cls.beam_style + ('-audible' if cls.ai_fire_sound else '-silent') + '.s')).write_text(assembly)
        cls.code, cls.symbols = assemble(assembly, names + constants)

    def word(self, address, value):
        self.cpu.mem_write(address, struct.pack('>H', value & 65535))

    def long(self, address, value):
        self.cpu.mem_write(address, struct.pack('>I', value & 0xffffffff))

    def var(self, name, value, size=2):
        (self.long if size == 4 else self.word)(VARIABLES + self.symbols[name], value)

    def obj(self, name, value, size=2):
        (self.long if size == 4 else self.word)(self.ship + self.symbols[name], value)

    def read(self, name, obj=False, size=2):
        return int.from_bytes(self.cpu.mem_read((self.ship if obj else VARIABLES) +
                                                self.symbols[name], size), 'big')

    def call(self, name):
        self.cpu.reg_write(UC_M68K_REG_SR, 0x2700)
        self.cpu.reg_write(UC_M68K_REG_A5, self.ship)
        self.cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.cpu.reg_write(UC_M68K_REG_A7, STACK - 4)
        self.long(STACK - 4, STOP)
        self.cpu.emu_start(self.symbols[name], STOP, count=250000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC), STOP, name)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7), STACK, name)
        return self.cpu.reg_read(UC_M68K_REG_D0) & 65535

    def prepare(self, model=UC_CPU_M68K_M68000 if Uc else None, view=0, screen=SCREEN):
        self.cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(model)
        self.cpu.mem_map(0, 0x100000)
        self.cpu.mem_write(CODE, self.code)
        self.cpu.mem_protect(CODE, (len(self.code) + 4095) // 4096 * 4096,
                             UC_PROT_READ | UC_PROT_EXEC)
        self.cpu.mem_write(GUARD, BACKGROUND)
        self.ship = VARIABLES + self.symbols['objects']
        self.var('scr_base', screen, 4)
        self.var('random_seed', 0x347ac9, 4)
        self.var('cockpit_on', 1)
        self.var('in_sights', 1)
        self.var('frame_count', 3)
        self.var('reduce_ctr', 100)
        self.var('view', view)
        for size in ('w', 'l'):
            self.var(size + '_view_ptr', self.symbols[f'{size}_swap_{VIEWS[view]}'], 4)
        self.cpu.mem_write(VARIABLES + self.symbols['obj_ctr'] + self.symbols['viper'], b'\x02')
        self.obj('flags', (1 << self.symbols['in_use']) << 8)
        self.obj('logic', self.symbols['log_attack'])
        self.obj('type', self.symbols['viper'])
        self.obj('health', 1000)
        self.obj('pre_attack', 1000)
        self.obj('hits_rad', 50)
        self.obj('mood', 255)
        self.obj('nodes', NODES, 4)
        self.obj('no_nodes', 0)
        self.cpu.mem_write(NODES, struct.pack('>4h', 0, 0, 60, 0))
        for axis, vector in zip('xyz', ((16384, 0, 0), (0, 16384, 0), (0, 0, 16384))):
            self.cpu.mem_write(self.ship + self.symbols[axis + '_vector'], struct.pack('>3h', *vector))
        for axis, value in zip('xyz', ((0, 0, 3000), (0, 0, -3000),
                                       (-3000, 0, 0), (3000, 0, 0))[view]):
            self.obj(axis + 'pos', value, 4)
        self.obj('this_zpos', 3000, 4)
        self.obj('obj_range', 3000, 4)
        self.var('front_shield', self.symbols['max_shield'])
        self.var('aft_shield', self.symbols['max_shield'])
        self.var('energy', self.symbols['max_energy'])
        self.damage_calls = []
        def damage_trace(cpu, address, size, user):
            self.damage_calls.append(cpu.reg_read(UC_M68K_REG_D0) & 65535)
        self.cpu.hook_add(UC_HOOK_CODE, damage_trace,
                          begin=self.symbols['reduce_shields'], end=self.symbols['reduce_shields'])
        self.sound_calls = []
        def sound_trace(cpu, address, size, user):
            self.sound_calls.append(cpu.reg_read(UC_M68K_REG_D0) & 65535)
        self.cpu.hook_add(UC_HOOK_CODE, sound_trace,
                          begin=self.symbols['fx'], end=self.symbols['fx'])
        self.lines = []
        def trace(cpu, address, size, user):
            if address == self.symbols['c_line']:
                values = [cpu.reg_read(r) & 65535 for r in
                          (UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2, UC_M68K_REG_D3)]
                self.lines.append(tuple(v - 65536 if v & 32768 else v for v in values))
        self.cpu.hook_add(UC_HOOK_CODE, trace, begin=self.symbols['c_line'], end=self.symbols['c_line'])
        self.wedges = []
        def wedge_trace(cpu, address, size, user):
            left, right = (cpu.reg_read(r) & 65535 for r in (UC_M68K_REG_D0, UC_M68K_REG_D2))
            tip = (self.read('laser_tip_x'), self.read('laser_tip_y'))
            self.wedges.append(tuple(v - 65536 if v & 32768 else v for v in (left, right, *tip)))
        self.cpu.hook_add(UC_HOOK_CODE, wedge_trace,
                          begin=self.symbols['draw_laser_wedge'], end=self.symbols['draw_laser_wedge'])
        self.weapon(0)

    def weapon(self, kind):
        rate, power, _ = struct.unpack('>3H', self.cpu.mem_read(self.symbols['laser_info'] + kind * 6, 6))
        self.var('laser_type', kind)
        self.var('laser_rate', rate)
        self.var('laser_power', power)
        return power

    def frame(self, fire=True, tick=0):
        self.long(CLOCK, tick)
        if fire:
            self.call('fire')
        self.var('frame_count', 3)
        self.call('game_logic')

    def test_first_shot_hits_in_same_frame_in_every_view_and_keeps_all_powers(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for view in range(4):
                for kind, power in enumerate((5, 7, 9, 11)):
                    with self.subTest(model=model, view=view, weapon=kind):
                        self.prepare(model, view)
                        self.assertEqual(self.weapon(kind), power)
                        self.frame()
                        self.assertEqual(self.read('health', True), 1000 - power)
                        self.assertEqual(self.read('laser_pending'), 0)
                        self.assertIn(self.symbols['sfx_hit'], self.sound_calls)
                        self.assertEqual(self.symbols['sfx_laser'] in self.sound_calls, kind < 2)
                        self.assertEqual(self.read('laser_audio_request'), kind if kind >= 2 else 0)
                        self.assertEqual(len(self.wedges), len(self.bases))
                        self.assertEqual(self.cpu.mem_read(self.read('colour_ptr', size=4), 16),
                                         struct.pack('>8H', *(player_colour(kind) * 2)))

    def test_original_damage_and_heat_intervals_ignore_wall_clock_speed(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for kind, interval in enumerate((10, 8, 6, 3)):
                for tick_step in (0, 3, 100000003):
                    self.prepare(model)
                    power = self.weapon(kind)
                    self.assertEqual(self.read('laser_rate'), interval)
                    for frame in range(interval * 3 + 1):
                        self.wedges.clear()
                        self.frame(tick=(0xfffffffc + frame * tick_step) & 0xffffffff)
                        shots = frame // interval + 1
                        self.assertEqual(self.read('health', True), 1000 - shots * power)
                        self.assertEqual(self.read('laser_temp'), shots)
                        self.assertEqual(self.read('laser_beam'), 0)
                        if kind >= 2:
                            self.assertEqual(len(self.wedges), len(self.bases))

    def test_continuous_visual_stops_on_release_and_resume_does_not_bypass_cooldown(self):
        for kind, interval in ((2, 6), (3, 3)):
            self.prepare()
            power = self.weapon(kind)
            self.frame()
            self.wedges.clear()
            self.frame(fire=False)
            self.assertEqual(self.read('laser_audio_request'), 0)
            self.assertEqual(self.wedges, [])
            self.assertEqual(self.read('health', True), 1000 - power)
            for frame in range(2, interval):
                self.wedges.clear()
                self.frame()
                self.assertEqual(len(self.wedges), len(self.bases))
                self.assertEqual(self.read('health', True), 1000 - power)
                self.assertEqual(self.read('laser_temp'), 1)
            self.frame()
            self.assertEqual(self.read('health', True), 1000 - 2 * power)
            self.assertEqual(self.read('laser_temp'), 2)

    def test_pulse_flashes_only_at_original_shot_intervals(self):
        self.prepare()
        for frame in range(31):
            self.wedges.clear()
            self.frame(tick=frame * 3)
            self.assertEqual(len(self.wedges), len(self.bases) if frame % 10 == 0 else 0)
            self.assertEqual(self.read('health', True), 1000 - (frame // 10 + 1) * 5)

    def test_cosmetic_jitter_never_moves_the_hit_axis_and_corners_are_not_hits(self):
        self.prepare()
        self.var('laser_tip_x', -32000)
        self.var('laser_tip_y', 32000)
        for x, y, expected in ((0, 0, 1), (30, 40, 1), (40, 40, 0),
                               (50, 0, 1), (51, 0, 0), (-50, 0, 1), (65536, 0, 0)):
            self.obj('this_xpos', x, 4)
            self.obj('this_ypos', y, 4)
            self.assertEqual(self.call('laser_in_sights'), expected, (x, y))
        self.obj('this_xpos', 0, 4)
        self.obj('this_ypos', 0, 4)
        self.obj('logic', self.symbols['log_exploding'])
        self.assertEqual(self.call('laser_in_sights'), 0)
        self.obj('logic', self.symbols['log_attack'])
        self.obj('this_zpos', -10, 4)
        self.assertEqual(self.call('laser_in_sights'), 0)

    def test_weapon_coloured_beams_stay_inside_both_buffers_and_have_one_shared_tip(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for screen in (SCREEN, OTHER):
                for kind in range(4):
                    self.prepare(model, screen=screen)
                    self.weapon(kind)
                    tips = set()
                    for _ in range(12):
                        self.cpu.mem_write(GUARD, BACKGROUND)
                        self.wedges.clear()
                        # Both styles must consume the same two cosmetic RNG calls.
                        seed = self.read('random_seed', size=4)
                        self.call('random')
                        self.call('random')
                        next_seed = self.read('random_seed', size=4)
                        self.var('random_seed', seed, 4)
                        self.frame()
                        self.assertEqual(self.read('random_seed', size=4), next_seed)
                        self.assertEqual(self.lines, [])
                        self.assertEqual(len(self.wedges), len(self.bases))
                        tip = self.wedges[0][2:]
                        tips.add(tip)
                        self.assertTrue(-4 <= tip[0] <= 3 and -2 <= tip[1] <= 1)
                        self.assertTrue(all(wedge[2:] == tip for wedge in self.wedges))
                        self.assertEqual(tuple(wedge[:2] for wedge in self.wedges), self.bases)
                        expected = bytearray(BACKGROUND)
                        for left, right, x, y in self.wedges:
                            # Fill between the independently rasterized edges, including
                            # every bottom-row pixel. There must be no outline-only gaps.
                            rows = {}
                            for base in (left, right):
                                for px, py in pixels(x + 160, 63 - y, base + 160, 119):
                                    rows.setdefault(py, []).append(px)
                            points = ((px, py) for py, xs in rows.items()
                                      for px in range(min(xs), max(xs) + 1))
                            paint(expected, points, player_colour(kind), screen)
                        self.assertEqual(self.cpu.mem_read(GUARD, len(BACKGROUND)), expected)
                    self.assertGreater(len(tips), 3)

    def test_pulse_flash_does_not_repeat_damage_and_flyback_wrap_is_safe(self):
        self.prepare()
        self.frame(tick=0xfffffffc)
        self.wedges.clear()
        self.frame(fire=False, tick=0xfffffffd)
        self.assertEqual(len(self.wedges), len(self.bases))
        self.assertEqual(self.read('health', True), 995)
        self.wedges.clear()
        self.frame(tick=2)
        self.assertEqual(self.wedges, [])
        self.assertEqual(self.read('health', True), 995)
        for frame in range(3, 10):
            self.frame(tick=frame * 1000)
            self.assertEqual(self.read('health', True), 995)
        self.frame(tick=10000)
        self.assertEqual(self.read('health', True), 990)

    def test_heat_limit_and_disabled_or_paused_fire_do_not_queue_a_shot(self):
        for variable, value in [('laser_temp', 48), ('laser_temp', 49),
                                ('laser_type', -1), ('game_frozen', 1), ('docked', 1)]:
            self.prepare()
            self.var(variable, value)
            self.call('fire')
            self.assertEqual(self.read('laser_pending'), 0, variable)
            self.assertEqual(self.read('laser_beam'), 0, variable)
        self.prepare()
        self.weapon(2)
        for _ in range(49 * 6):
            self.frame()
        self.assertEqual(self.read('health', True), 1000 - 48 * 9)
        self.assertEqual(self.read('laser_temp'), 48)
        self.wedges.clear()
        self.frame()
        self.assertEqual(self.wedges, [])

    def aim(self, angle, behind=False):
        sign = 1 if behind else -1
        self.obj('zpos', -3000 if behind else 3000, 4)
        vector = (round(16384 * math.sin(math.radians(angle))), 0,
                  sign * round(16384 * math.cos(math.radians(angle))))
        self.cpu.mem_write(self.ship + self.symbols['z_vector'], struct.pack('>3h', *vector))

    def test_ai_uses_fresh_aim_and_can_fire_without_hitting(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for angle, result in ((0, 2), (10, 2), (20, 1), (40, 0), (180, 0)):
                self.prepare(model)
                self.aim(angle)
                self.var('shields_fx', 1)
                self.obj('on_course', 0)
                self.assertEqual(self.call('ai_laser_aim'), result)
                shield = self.read('front_shield')
                self.call('do_attack')
                self.assertEqual(bool(self.read('ai_laser', True)), result != 0)
                damage = shield - self.read('front_shield')
                self.assertIn(damage, {0, 2, 3, 4, 6, 8, 9, 12} if result == 2 else {0})
                self.assertEqual(len(self.damage_calls), 1 if damage else 0)
                self.assertEqual(self.sound_calls, [self.symbols['sfx_laser']] if result and self.ai_fire_sound else [])

    def test_ai_scaled_damage_ranges_constrictor_power_and_shield_side(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for behind in (False, True):
                for rating, maximum in enumerate((3, 3, 3, 5, 5, 5, 7, 7, 7, 6)):
                    self.prepare(model)
                    self.aim(0, behind)
                    self.var('rating', min(rating, 8))
                    if rating == 9:
                        self.obj('type', self.symbols['constr'])
                    side = 'aft_shield' if behind else 'front_shield'
                    other = 'front_shield' if behind else 'aft_shield'
                    observed = set()
                    misses = 0
                    for _ in range(256):
                        self.var(side, self.symbols['max_shield'])
                        self.var('energy', self.symbols['max_energy'])
                        self.damage_calls.clear()
                        self.call('do_attack')
                        self.assertLessEqual(len(self.damage_calls), 1)
                        damage = self.damage_calls[0] if self.damage_calls else 0
                        if damage:
                            observed.add(damage)
                        else:
                            misses += 1
                        self.assertEqual(self.read(side), max(0, self.symbols['max_shield'] - damage))
                        self.assertEqual(self.read('energy'), self.symbols['max_energy'] -
                                         max(0, damage - self.symbols['max_shield']))
                    self.assertTrue(0 < misses < 256)
                    bases = (6,) if rating == 9 else range(1, maximum + 1)
                    self.assertEqual(observed, {base * multiplier for base in bases for multiplier in (2, 3, 4)})
                    self.assertEqual(self.read(other), self.symbols['max_shield'])

    def test_ai_multiplier_uses_separate_roll_and_rejects_fourth_choice(self):
        # Keep actual attack, multiplier and shield/energy routines; control only
        # the random service outputs to exercise every byte and the retry path.
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.prepare(model)
            self.aim(0)
            self.var('rating', 8)
            random_values, ranges = [], []
            base = 1
            def return_value(cpu, value):
                sp = cpu.reg_read(UC_M68K_REG_A7)
                destination = int.from_bytes(cpu.mem_read(sp, 4), 'big')
                cpu.reg_write(UC_M68K_REG_D0, value)
                cpu.reg_write(UC_M68K_REG_A7, sp + 4)
                cpu.reg_write(UC_M68K_REG_PC, destination)
            def random_value(cpu, address, size, user):
                self.assertTrue(random_values, 'unexpected extra random draw')
                return_value(cpu, random_values.pop(0))
            def base_value(cpu, address, size, user):
                ranges.append(cpu.reg_read(UC_M68K_REG_D2) & 65535)
                return_value(cpu, base - 1)
            self.cpu.hook_add(UC_HOOK_CODE, random_value,
                              begin=self.symbols['random'], end=self.symbols['random'])
            self.cpu.hook_add(UC_HOOK_CODE, base_value,
                              begin=self.symbols['rand'], end=self.symbols['rand'])
            counts = {2: 0, 3: 0, 4: 0}
            for raw in range(256):
                base = raw % 7 + 1
                retry = raw % 4 == 3
                multiplier = 2 if retry else raw % 4 + 2
                random_values[:] = [0, 25, raw] + ([255, 3, 0] if retry else [])
                self.var('front_shield', 24)
                self.var('energy', 96)
                self.damage_calls.clear()
                ranges.clear()
                self.call('do_attack')
                self.assertEqual(random_values, [])
                self.assertEqual(ranges, [7])
                self.assertEqual(self.damage_calls, [base * multiplier])
                if not retry:
                    counts[multiplier] += 1
            self.assertEqual(counts, {2: 64, 3: 64, 4: 64})
            self.aim(20) # A visible miss consumes only the firing-opportunity roll.
            random_values[:] = [0]
            self.damage_calls.clear()
            ranges.clear()
            self.call('do_attack')
            self.assertEqual(random_values, [])
            self.assertEqual(ranges, [])
            self.assertEqual(self.damage_calls, [])
            self.assertTrue(self.read('ai_laser', True))

    def test_ai_accuracy_is_90_10_and_respects_firing_sound_option(self):
        # Exercise every possible accuracy byte in the actual attack routine.
        # Keep the real bounded-damage roll and multiplier; replace only random
        # bytes, checking the exact draw count, visible line and requested sounds.
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for behind in (False, True):
                for kind in ('viper', 'constr'):
                    self.prepare(model, view=1 if behind else 0)
                    self.aim(0, behind)
                    self.obj('type', self.symbols[kind])
                    side = 'aft_shield' if behind else 'front_shield'
                    other = 'front_shield' if behind else 'aft_shield'
                    random_values = []
                    def random_value(cpu, address, size, user):
                        self.assertTrue(random_values, 'unexpected extra random draw')
                        sp = cpu.reg_read(UC_M68K_REG_A7)
                        destination = int.from_bytes(cpu.mem_read(sp, 4), 'big')
                        cpu.reg_write(UC_M68K_REG_D0, random_values.pop(0))
                        cpu.reg_write(UC_M68K_REG_A7, sp + 4)
                        cpu.reg_write(UC_M68K_REG_PC, destination)
                    self.cpu.hook_add(UC_HOOK_CODE, random_value,
                                      begin=self.symbols['random'], end=self.symbols['random'])
                    accepted_hits, accepted_misses = 0, 0
                    for raw in range(256):
                        hit = raw >= 25
                        random_values[:] = [0, raw]
                        if raw >= 250:
                            random_values.extend([255, 25]) # retry twice, then hit
                        if hit:
                            random_values.extend([0] if kind == 'constr' else [0, 0, 0])
                        self.var(side, 24)
                        self.var('energy', 96)
                        self.var('shields_fx', 0)
                        self.obj('ai_laser', 0)
                        self.damage_calls.clear()
                        self.sound_calls.clear()
                        self.call('do_attack')
                        self.assertEqual(random_values, [])
                        damage = (12 if kind == 'constr' else 2) if hit else 0
                        self.assertEqual(self.damage_calls, [damage] if hit else [])
                        self.assertEqual(self.read(side), 24 - damage)
                        self.assertEqual(self.read(other), 24)
                        self.assertEqual(self.read('energy'), 96)
                        self.assertTrue(self.read('ai_laser', True))
                        sounds = ([self.symbols['sfx_shields']] if hit else [])
                        if self.ai_fire_sound:
                            sounds.append(self.symbols['sfx_laser'])
                        self.assertEqual(self.sound_calls, sounds)
                        if raw < 250:
                            accepted_hits += hit
                            accepted_misses += not hit
                        if raw in (0, 24, 25, 249, 250, 255):
                            self.lines.clear()
                            self.call('draw_ai_laser')
                            self.assertEqual(len(self.lines), 1)
                    self.assertEqual((accepted_hits, accepted_misses), (225, 25))

    def test_ai_respects_range_cloaking_and_control_locks(self):
        for variable, value, obj in [('obj_range', 7001, True),
                                      ('obj_range', 0, True),
                                      ('cloaking_on', 1, False),
                                      ('controls_locked', 1, False)]:
            self.prepare()
            self.aim(0)
            (self.obj if obj else self.var)(variable, value, 4 if obj else 2)
            self.call('do_attack')
            self.assertEqual(self.read('ai_laser', True), 0)
            self.assertEqual(self.read('front_shield'), self.symbols['max_shield'])

    def test_all_22_models_draw_from_their_gun_node_with_rating_colours_in_all_views(self):
        models = list(ship_models())
        self.assertEqual(len(models), 22)
        def swap(v, view):
            x, y, z = v
            return ((x, y, z), (-x, y, -z), (z, y, -x), (-z, y, x))[view]
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for view in range(4):
                for name, gun, last, words in models:
                    for rating in range(9):
                        with self.subTest(model=model, view=view, ship=name, rating=rating):
                            self.prepare(model, view)
                            self.var('rating', rating)
                            kind = {'constri': 'constr', 'tharg': 'thargoid', 'thargon': 'thargon'}.get(name, 'viper')
                            self.obj('type', self.symbols[kind])
                            self.assertTrue(0 <= gun <= last)
                            self.cpu.mem_write(NODES, struct.pack('>' + 'h' * len(words), *words))
                            self.obj('gun_node', gun)
                            self.obj('no_nodes', last)
                            self.obj('ai_laser', 1)
                            self.call('draw_ai_laser')
                            self.assertEqual(len(self.lines), 1)
                            x, y, z = swap(words[gun * 4:gun * 4 + 3], view)
                            expected = (int(x * 512 / (3000 + z)), int(y * 512 / (3000 + z)))
                            self.assertEqual(self.lines[0][:2], expected)
                            ink = 15 if name == 'constri' else (6, 6, 6, 3, 3, 3, 15, 15, 15)[rating]
                            if kind in ('thargoid', 'thargon'):
                                ink = 10
                            masks = struct.pack('>4H', *(65535 if ink & (1 << p) else 0 for p in range(4)))
                            self.assertEqual(self.cpu.mem_read(self.read('colour_ptr', size=4), 8), masks)

    def test_near_plane_enemy_beams_do_not_overflow_the_line_clipper(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            for x, y, z in ((63, 0, 1), (-63, 0, 1), (0, 63, 1),
                            (0, -63, 1), (100, 0, 1), (0, 100, 1),
                            (0, 0, 32768), (0, 0, -1)):
                self.prepare(model)
                self.cpu.mem_write(NODES, bytes(8))
                for field, value in zip(('this_xpos', 'this_ypos', 'this_zpos'), (x, y, z)):
                    self.obj(field, value, 4)
                self.obj('ai_laser', 1)
                self.call('draw_ai_laser')
                self.assertEqual(self.lines, [], (x, y, z))
                self.assertEqual(self.cpu.mem_read(GUARD, len(BACKGROUND)), BACKGROUND)

    def test_enemy_beams_expire_and_invalid_or_exploding_emitters_do_not_draw(self):
        for field, value in [('gun_node', -1), ('gun_node', 1),
                             ('logic', None), ('this_zpos', -1)]:
            self.prepare()
            self.obj('ai_laser', 1)
            self.obj(field, self.symbols['log_exploding'] if value is None else value,
                     4 if field == 'this_zpos' else 2)
            self.call('draw_ai_laser')
            self.assertEqual(self.lines, [])
        self.prepare()
        self.obj('ai_laser', 1)
        self.frame(fire=False)
        self.assertEqual(self.read('ai_laser', True), 0)


class SingleBeamLaserTests(LaserTests):
    beam_style = 'singlebeam'
    bases = ((-3, 3),)


class AudibleAILaserTests(LaserTests):
    ai_fire_sound = True


class AudibleAISingleBeamLaserTests(SingleBeamLaserTests):
    ai_fire_sound = True


if __name__ == '__main__':
    unittest.main()
