"""Execute registration, creation, sights and commander serialization on 68K.

Optional CPU dependency: unicorn==2.1.4. OS I/O and UI drawing are stubbed;
the actual save/restore, message copying, model-header copy and targeting run.
"""
from pathlib import Path
import struct
import unittest

from test_raster import routine
from test_viewport import assemble, preamble, variable_block

try:
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_PROT_READ, UC_PROT_EXEC, UC_HOOK_CODE
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_A0, UC_M68K_REG_A4, UC_M68K_REG_A5, UC_M68K_REG_A6,
        UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_PC, UC_M68K_REG_SR)
except ImportError:
    Uc = None

ROOT = Path(__file__).resolve().parents[1]
CODE, STOP, VARIABLES, STACK, NAME = 0x10000, 0x1000, 0x30000, 0x90000, 0x80000


@unittest.skipIf(Uc is None, 'registration CPU tests require unicorn==2.1.4')
class RegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read = lambda name: (ROOT / 'asm' / (name + '.m68')).read_text(encoding='utf-8')
        src = {n: read(n) for n in ('registration', 'main', 'vector', 'disk', 'init',
                                  'bios', 'graphics', 'combat', 'data')}
        constants = '''registration_tag player_registration registration_state registration_buffer
            registration_id objects obj_len obj_data_len nodes surfaces text type flags in_use
            ship_type typ_trader typ_pirate typ_police typ_alien thargoid thargon viper dodec constr spacestn
            missile barrel asteroid worm platlet planet sun photon hyp_circle cobra cougar
            angry invincible game_state io_buffer cash score rating equip escape_capsule
            police_record hold current galaxy_no gal_seed fluctuation random_seed player_name
            obj_range this_xpos this_ypos centre_x centre_y obj_rad hits_rad in_sights laser_type
            id_trigger missile_state target_ptr target text_buffer text_offset text_frames
            max_objects max_obj_num req_planet player_record witch_space mission count_down
            jump_trigger speed no_cols text_top'''.split()
        names = ['registration_assign', 'registration_next', 'registration_generate',
                 'registration_new_player', 'registration_validate', 'registration_message',
                 'registration_status', 'create_object', 'copy_object', 'clear_objects',
                 'alloc_object', 'escape', 'check_sights', 'save_state', 'restore_state',
                 'default_game', 'scramble', 'new_game', 'var_list', 'fixture_header',
                 'locate', 'print_string']
        assembly = preamble() + 'max_vert equ 15\n' + variable_block(src['graphics'], 'graphics')
        assembly += '\torg $10000\n\tdc.l ' + ','.join(names + constants) + '\n'
        assembly += 'return: set *\n\trts\npersistance equ 30\n'
        assembly += src['registration'].split('    q_module registration', 1)[1]
        for module, functions in {
            'main': ('create_object', 'copy_object', 'clear_objects', 'alloc_object'),
            'vector': ('perspective', 'check_sights'),
            'combat': ('check_missile',),
            'disk': ('save_state', 'restore_state', 'default_game', 'scramble'),
            'bios': ('str_copy',), 'graphics': ('disp_message',),
        }.items():
            for name in functions:
                part = routine(src[module], name)
                # SCRAMBLE is the last routine and is followed by all disk tables.
                if name == 'scramble':
                    part = part.split('; ---- LOCAL DATA ----', 1)[0]
                assembly += '\n' + part
        assembly += routine(src['main'], 'escape').split('* ---- LOCAL DATA ----', 1)[0]
        assembly += '\nescape_data:' + src['main'].split('escape_data:', 1)[1].split('* Various text messages.', 1)[0] + '\n'
        assembly += src['disk'][src['disk'].index('var_list:'):].split('; Disk icon draw data table.', 1)[0]
        default = src['init'][src['init'].index('\tq_global new_game'):]
        assembly += default.split('* Table of local variable data.', 1)[0]
        assembly += src['data'][src['data'].index('\tq_global magnitude_table'):].split('* Table of cosines', 1)[0]
        assembly += '''
gen_prices:
    rts
home_cursor:
    rts
build_name:
    rts
text_colour:
    rts
locate:
    rts
print_string:
    rts
fx:
    rts
check_inflight:
    rts
beep:
    rts
lock_controls:
    rts
front_view:
    rts
rand:
    moveq #0,d0
    rts
text1: dc.b 'Target locked',0
text6: dc.b 'Capsule released',0
text29: dc.b 'Capsule Not Installed',0
text30: dc.b 'Capsule Malfunction!',0
jameson: dc.b 'Jameson',0
    even
obj_data:
    dcb.l max_obj_num,fixture_header
fixture_header:
    dc.l 0,fixture_surfaces,fixture_name
    dc.w 0,0,20,100,20,0,0,100,0,typ_trader,0,0,0,0,0,0,0,0
fixture_surfaces:
    dc.w 1
    dc.l 0,0
fixture_name: dc.b 'Cobra MkIII',0
    even
'''
        cls.images = {}
        for maximum in (0, 1):
            cls.images[maximum] = assemble(f'commander_max equ {maximum}\n' + assembly,
                                           names + constants)

    def setUp(self):
        self.boot()

    def boot(self, model=None, maximum=0):
        self.cpu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(UC_CPU_M68K_M68000 if model is None else model)
        self.cpu.mem_map(0, 0x100000)
        image, self.s = self.images[maximum]
        self.cpu.mem_write(CODE, image)
        self.cpu.mem_protect(CODE, (len(image) + 4095) & ~4095, UC_PROT_READ | UC_PROT_EXEC)
        self.cpu.reg_write(UC_M68K_REG_SR, 0x2000)
        self.cpu.reg_write(UC_M68K_REG_A6, VARIABLES)
        self.call('default_game')
        self.call('restore_state')

    def at(self, name):
        return VARIABLES + self.s[name]

    def word(self, address, value=None):
        if value is not None:
            self.cpu.mem_write(address, struct.pack('>H', value & 65535))
        return int.from_bytes(self.cpu.mem_read(address, 2), 'big')

    def long(self, address, value=None):
        if value is not None:
            self.cpu.mem_write(address, struct.pack('>I', value & 0xffffffff))
        return int.from_bytes(self.cpu.mem_read(address, 4), 'big')

    def call(self, name, **registers):
        for reg, value in registers.items():
            index = (UC_M68K_REG_D0 if reg[0] == 'd' else UC_M68K_REG_A0) + int(reg[1:])
            self.cpu.reg_write(index, value)
        self.cpu.reg_write(UC_M68K_REG_A7, STACK)
        self.long(STACK, STOP)
        self.cpu.emu_start(self.s[name], STOP, count=100000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC), STOP, name + ' did not return')
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7), STACK + 4)

    def obj(self, slot=0, kind='viper', role='typ_police', create=True):
        address = self.at('objects') + slot * self.s['obj_len']
        self.cpu.mem_write(address, bytes(self.s['obj_len']))
        self.cpu.mem_write(address + self.s['flags'], bytes([1 << self.s['in_use']]))
        self.word(address + self.s['type'], self.s[kind] if isinstance(kind, str) else kind)
        if create:
            self.call('create_object', a4=address)
        self.word(address + self.s['ship_type'], self.s[role])
        self.long(address + self.s['text'], NAME)
        self.cpu.mem_write(NAME, b'Viper\0')
        return address

    def rid(self, obj):
        return bytes(self.cpu.mem_read(obj + self.s['registration_id'], 4))

    def message(self, obj, name='Viper'):
        self.cpu.mem_write(NAME, name.encode('ascii') + b'\0')
        self.call('registration_message', a5=obj)
        return self.text()

    def text(self):
        return bytes(self.cpu.mem_read(self.at('text_buffer'), 128)).split(b'\0', 1)[0].decode('ascii')

    def test_new_commander_and_max_have_default_registration(self):
        for maximum in (0, 1):
            with self.subTest(maximum=maximum):
                self.boot(maximum=maximum)
                self.assertEqual(self.long(self.at('player_registration')), 0x4a532a00)
                self.assertEqual(self.long(self.at('cash')), 10000000 if maximum else 1000)
                self.assertEqual(self.word(self.at('rating')), 7 if maximum else 0)
                self.assertEqual(self.long(self.at('score')), 0xa0000 if maximum else 0)

    def test_private_generator_has_full_period_and_never_changes_game_rng(self):
        self.long(self.at('random_seed'), 0x12345678)
        self.word(self.at('registration_state'), 0xa5)
        seen = set()
        for _ in range(255):
            self.call('registration_next')
            seen.add(self.cpu.reg_read(UC_M68K_REG_D0))
        self.assertEqual(seen, set(range(1, 256)))
        self.assertEqual(self.word(self.at('registration_state')), 0xa5)
        self.assertEqual(self.long(self.at('random_seed')), 0x12345678)

    def test_full_scene_and_reused_slots_have_distinct_stable_ids(self):
        objects = [self.obj(i) for i in range(self.s['max_objects'])]
        for wave in range(10):
            ids = [self.rid(obj) for obj in objects]
            self.assertEqual(len(set(ids)), len(ids))
            self.assertEqual(len({rid[2] for rid in ids}), len(ids))
            for rid in ids:
                self.assertTrue(65 <= rid[0] <= 90 and 65 <= rid[1] <= 90)
                self.assertTrue(1 <= rid[2] <= 255)
                self.assertEqual(rid[3], 0)
            obj = objects[wave % len(objects)]
            before = self.rid(obj)
            message = self.message(obj)
            self.word(self.at('current'), 255)
            self.word(self.at('galaxy_no'), wave & 7)
            self.word(self.at('fluctuation'), wave)
            self.assertEqual(self.message(obj), message)
            self.obj(wave % len(objects))
            self.assertNotEqual(self.rid(obj), before)

    def test_copy_then_create_replaces_parent_identity_and_keeps_header(self):
        parent = self.obj(0, 'cobra', 'typ_trader')
        self.long(parent + self.s['text'], self.long(self.s['fixture_header'] + 8))
        child = self.obj(1, create=False)
        self.call('copy_object', a4=child, a5=parent)
        self.assertEqual(self.rid(child), self.rid(parent))
        self.call('create_object', a4=child)
        self.assertNotEqual(self.rid(child), self.rid(parent))
        self.assertEqual(bytes(self.cpu.mem_read(parent + self.s['nodes'], self.s['obj_data_len'])),
                         bytes(self.cpu.mem_read(child + self.s['nodes'], self.s['obj_data_len'])))

    def test_ship_types_and_unregistered_objects(self):
        eligible = {self.s['thargon']} | (set(range(self.s['viper'], self.s['constr'] + 1)) - {self.s['dodec']})
        for kind in list(range(self.s['max_obj_num'])) + [self.s[n] for n in ('planet', 'sun', 'photon', 'hyp_circle')]:
            with self.subTest(kind=kind):
                obj = self.obj(kind=kind)
                self.assertEqual(any(self.rid(obj)), kind in eligible)
                if kind not in eligible and kind not in (self.s['spacestn'], self.s['dodec']):
                    self.assertEqual(self.message(obj, 'Debris'), 'Debris')

    def test_pirates_hide_id_but_hostile_police_keep_it(self):
        obj = self.obj(role='typ_pirate')
        self.assertEqual(self.message(obj, 'Krait'), 'Krait ??-???')
        self.word(obj + self.s['ship_type'], self.s['typ_police'])
        self.cpu.mem_write(obj + self.s['flags'], bytes([(1 << self.s['in_use']) | (1 << self.s['angry'])]))
        self.assertRegex(self.message(obj), r'^Viper [A-Z]{2}-\d{3}$')

    def test_coriolis_identity_and_hidden_alien_station_in_all_galaxies(self):
        for kind, prefix in (('spacestn', 'C'), ('dodec', None)):
            obj = self.obj(kind=kind)
            for galaxy in range(8):
                for system in (0, 7, 255):
                    self.word(self.at('galaxy_no'), galaxy)
                    self.word(self.at('current'), system)
                    name = 'Space Station' if prefix else 'Alien Space Station'
                    suffix = f'C{galaxy+1}-{system:03}' if prefix else '??-???'
                    self.assertEqual(self.message(obj, name), f'{name} {suffix}')
                    self.call('registration_new_player')
                    self.assertEqual(self.message(obj, name), f'{name} {suffix}')

    def test_alien_station_mask_preserves_object_rng_and_registers_on_both_cpus(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.boot(model)
            obj = self.obj(kind='dodec')
            for identity in (0, 0x415a7f00):
                self.long(obj + self.s['registration_id'], identity)
                before = bytes(self.cpu.mem_read(obj, self.s['obj_len']))
                seed = self.long(self.at('random_seed'))
                registration_seed = self.word(self.at('registration_state'))
                self.assertEqual(self.message(obj, 'Alien Space Station'), 'Alien Space Station ??-???')
                registers = {f'd{i}': 0x12345600+i for i in range(8)}
                registers.update({f'a{i}': 0x80000+i*16 for i in range(6)})
                registers.update(a5=obj)
                self.call('registration_message', **registers)
                for reg, value in registers.items():
                    index = (UC_M68K_REG_D0 if reg[0] == 'd' else UC_M68K_REG_A0) + int(reg[1:])
                    self.assertEqual(self.cpu.reg_read(index), value)
                self.assertEqual(bytes(self.cpu.mem_read(obj, self.s['obj_len'])), before)
                self.assertEqual(self.long(self.at('random_seed')), seed)
                self.assertEqual(self.word(self.at('registration_state')), registration_seed)

    def test_hidden_aliens_and_visible_constrictor_keep_their_combat_role(self):
        for kind, name, hidden in (('thargoid', 'Thargoid', True),
                                   ('thargon', 'Thargon', True),
                                   ('constr', 'Constrictor', False)):
            obj = self.obj(kind=kind, role='typ_alien')
            before = bytes(self.cpu.mem_read(obj, self.s['obj_len']))
            if hidden:
                self.assertEqual(self.message(obj, name), name + ' ??-???')
            else:
                self.assertRegex(self.message(obj, name), '^' + name + r' [A-Z]{2}-\d{3}$')
            self.assertEqual(bytes(self.cpu.mem_read(obj, self.s['obj_len'])), before)

    def test_format_bounds_and_read_only_code_on_68000_and_68020(self):
        for model in (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020):
            self.boot(model)
            obj = self.obj()
            for number in (1, 9, 10, 42, 99, 100, 255):
                self.cpu.mem_write(obj + self.s['registration_id'], b'AZ' + bytes([number, 0]))
                self.assertEqual(self.message(obj), f'Viper AZ-{number:03}')
            guard = self.at('registration_buffer') + self.s['no_cols'] + 2
            self.cpu.mem_write(guard, b'GUARD')
            self.assertEqual(len(self.message(obj, 'X' * 80)), 32)
            self.assertEqual(bytes(self.cpu.mem_read(guard, 5)), b'GUARD')
            registers = {f'd{i}': 0x12345600+i for i in range(8)}
            registers.update({f'a{i}': 0x80000+i*16 for i in range(6)})
            registers.update(a4=obj, a5=obj)
            for routine_name in ('registration_assign', 'registration_message', 'registration_new_player',
                                 'registration_validate', 'registration_status', 'create_object'):
                self.call(routine_name, **registers)
                for reg, value in registers.items():
                    index = (UC_M68K_REG_D0 if reg[0] == 'd' else UC_M68K_REG_A0) + int(reg[1:])
                    self.assertEqual(self.cpu.reg_read(index), value, (routine_name, reg))
                self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A6), VARIABLES)

    def test_sights_identification_without_laser_and_missile_message_priority(self):
        obj = self.obj()
        self.long(obj + self.s['obj_range'], 1000)
        self.word(obj + self.s['obj_rad'], 100)
        self.word(obj + self.s['hits_rad'], 20)
        for laser, missile, identify in ((-1, 1, 1), (0, 0, 1), (0, 1, 1), (0, 1, 0)):
            with self.subTest(laser=laser, missile=missile, identify=identify):
                self.word(self.at('laser_type'), laser)
                self.word(self.at('missile_state'), missile)
                self.word(self.at('id_trigger'), identify)
                self.word(self.at('in_sights'), 0)
                self.call('check_sights', a5=obj)
                self.assertEqual(self.word(self.at('in_sights')), 0 if laser < 0 else 0xff00)
                self.assertEqual(self.word(self.at('id_trigger')), 0)
                self.assertEqual(self.word(self.at('missile_state')), 2 if laser >= 0 and missile else missile)
                if identify:
                    self.assertRegex(self.text(), r'^Viper [A-Z]{2}-\d{3}$')
                else:
                    self.assertEqual(self.text(), 'Target locked')
        # A target outside the original hit radius must neither be identified nor locked.
        self.long(obj + self.s['this_xpos'], 100)
        self.word(self.at('id_trigger'), 1)
        self.word(self.at('missile_state'), 1)
        self.word(self.at('in_sights'), 0)
        self.call('check_sights', a5=obj)
        self.assertEqual(self.word(self.at('id_trigger')), 1)
        self.assertEqual(self.word(self.at('missile_state')), 1)
        self.assertEqual(self.word(self.at('in_sights')), 0)

    def test_save_round_trip_preserves_old_prefix_and_stays_256_bytes(self):
        self.call('registration_new_player')
        identity = self.long(self.at('player_registration'))
        self.long(self.at('cash'), 7654321)
        self.long(self.at('score'), 123456)
        self.word(self.at('mission'), 0x52)
        self.call('save_state')
        saved = bytes(self.cpu.mem_read(self.at('game_state'), 256))
        self.assertEqual(saved[178:182], b'RID1')
        self.assertEqual(int.from_bytes(saved[182:186], 'big'), identity)
        self.assertEqual(saved[186:], bytes(70))
        self.cpu.mem_write(self.at('io_buffer'), saved)
        self.call('scramble')
        encoded = bytes(self.cpu.mem_read(self.at('io_buffer'), 256))
        self.assertEqual(encoded, bytes(b ^ (255-i) for i, b in enumerate(saved)))
        self.call('scramble')
        self.assertEqual(bytes(self.cpu.mem_read(self.at('io_buffer'), 256)), saved)
        self.call('registration_new_player')
        self.call('restore_state')
        self.assertEqual(self.long(self.at('player_registration')), identity)
        self.assertEqual(self.long(self.at('cash')), 7654321)
        self.assertEqual(self.long(self.at('score')), 123456)
        self.assertEqual(self.word(self.at('mission')), 0x52)
        self.call('save_state')
        self.assertEqual(bytes(self.cpu.mem_read(self.at('game_state'), 256)), saved)
        # Historical saves did not populate bytes 178 onward.
        for extension in (bytes(78), b'\xff'*78, b'RID1aZ\x01\0'+bytes(70), b'RID1AZ\0\0'+bytes(70)):
            self.cpu.mem_write(self.at('game_state'), saved[:178] + extension)
            self.call('restore_state')
            self.assertEqual(self.long(self.at('player_registration')), 0x4a532a00)
            self.call('save_state')
            migrated = bytes(self.cpu.mem_read(self.at('game_state'), 256))
            self.assertEqual(migrated[:178], saved[:178])

    def test_successful_escape_changes_hull_id_failed_escape_does_not(self):
        old = self.long(self.at('player_registration'))
        for reason in ('no_capsule', 'witch_space', 'mission', 'full'):
            self.call('clear_objects')
            self.word(self.at('equip') + self.s['escape_capsule'], reason != 'no_capsule')
            self.word(self.at('witch_space'), reason == 'witch_space')
            self.word(self.at('mission'), 0x52 if reason == 'mission' else 0)
            if reason == 'full':
                for i in range(self.s['max_objects']):
                    self.obj(i)
            self.call('escape')
            self.assertEqual(self.long(self.at('player_registration')), old)
        self.call('clear_objects')
        self.word(self.at('equip') + self.s['escape_capsule'], 1)
        self.word(self.at('witch_space'), 0)
        self.word(self.at('mission'), 0)
        self.call('escape')
        self.assertNotEqual(self.long(self.at('player_registration')), old)
        self.assertEqual(int.from_bytes(self.rid(self.at('objects')), 'big'), old)
        self.assertEqual(self.word(self.at('equip') + self.s['escape_capsule']), 0)

    def test_status_uses_free_row_and_keeps_player_id(self):
        positions, strings = [], []
        def observe(cpu, address, size, data):
            if address == self.s['locate']:
                positions.append((cpu.reg_read(UC_M68K_REG_D0) & 65535,
                                  cpu.reg_read(UC_M68K_REG_D0+1) & 65535))
            if address == self.s['print_string']:
                ptr = cpu.reg_read(UC_M68K_REG_A0)
                strings.append(bytes(cpu.mem_read(ptr, 64)).split(b'\0', 1)[0])
        self.cpu.hook_add(UC_HOOK_CODE, observe)
        self.call('registration_status')
        self.assertEqual(positions, [(0, 74), (14, 74)])
        self.assertEqual(strings, [b'Registration:', b'JS-042'])
        self.assertLessEqual((14+6)*8, 210)
        self.assertLess(74+8, 86)


if __name__ == '__main__':
    unittest.main()
