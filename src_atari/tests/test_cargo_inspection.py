"""Run cargo inspection, real purchases and S-zone transitions on 68000/020.

Graphics, input, sound and scene animations are stubbed. Launch/reset and the
state-changing prefix of PREPARE_COCKPIT run from the actual game sources.
"""
from pathlib import Path
import random
import re
import struct
import unittest

from test_raster import routine
from test_viewport import assemble, preamble, variable_block

try:
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_PROT_READ, UC_PROT_EXEC, UC_HOOK_CODE
    from unicorn.m68k_const import *
except ImportError:
    Uc = None

ROOT = Path(__file__).resolve().parents[1]
CODE, VARIABLES, STACK, STOP = 0x10000, 0x30000, 0x90000, 0x1000
MODELS = (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020) if Uc else ()


@unittest.skipIf(Uc is None, 'cargo inspection tests require unicorn==2.1.4')
class CargoInspectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read = lambda name: (ROOT/'asm'/f'{name}.m68').read_text()
        cargo, main, init, cockpit, combat, data = map(read, ('cargo','main','init','cockpit','combat','data'))
        cls.market = [[int(x.strip()[1:],16) for x in row.split(',')]
                      for row in re.findall(r'^\s*dc (\$[^;\n]+);',data,re.M)[:18]]
        assert [r[4] for r in cls.market] == [0,0,0,4,0,0,4,0,0,0,2,0,0,0,0,0,0,0]
        names = '''check_cargo illegal radar_lock launch reset_system prepare_cockpit check_police d_buy d_sell
            hold products product_len units naughty price quantity cash this_cargo max_cargo cargo_items
            police_record checkpoint radar_obj f_schar planet_range station_destroyed spcstn_space spcstn_rearm
            splanet govern docked mission equip cargo_bay fuel_scoop var_size objects obj_size
            fixture_amount fixture_random fixture_vipers'''.split()
        asm = preamble() + variable_block(cargo,'cargo')
        asm += main[main.index('spcstn_space:'):main.index('\tq_module main')]
        asm += 'fixture_amount equ var_size\nfixture_random equ var_size+2\nfixture_vipers equ var_size+4\n'
        asm += '\torg $10000\n\tdc.l '+','.join(names)+'\nreturn: set *\n rts\n'
        for source, functions in ((cargo,('check_cargo','illegal','d_buy','find_buy','cargo_spare','get_unit','reduce_hold','d_sell','find_sell')),
                                  (main,('radar_lock','launch')), (init,('reset_system',)), (combat,('check_police',))):
            for name in functions:
                body = routine(source,name)
                if name == 'reduce_hold':
                    body = body.split('\tq_ret',1)[0]+'\tq_ret\n'
                asm += body+'\n'
        # The rest of PREPARE_COCKPIT draws graphics; all state changes above it
        # are retained so returning from a menu exercises the real compass reset.
        asm += routine(cockpit,'prepare_cockpit').split('\tjsr kill_sprites',1)[0]+'\trts\n'
        asm += re.search(r'^reset_table:\s*\n(?:\s*dc\.w[^\n]*\n)+',init,re.M).group(0)
        asm += '''
front_view:
 bra prepare_cockpit
input_number:
 move fixture_amount(a6),d1
 moveq #13,d0
 rts
rand:
 moveq #0,d0
 rts
random:
 move fixture_random(a6),d0
 rts
prepare_vipers:
 addq.w #1,fixture_vipers(a6)
 rts
'''
        stubs = '''cancel_jettison_confirm launch_sequence launch_system check_hack set_roll_angles set_climb_angles quiet
            draw_highlight no_select clear_input hide_cursor print_string print_number print_table print_char restore_cursor
            icon_coords error_box block print_buy_info prepare_text print_centre draw_cargo'''.split()
        asm += ':\n'.join(stubs)+':\n rts\n'
        asm += 'rip_off equ 19\nkey_left_x equ 48\nkey_right_x equ 208\nkey_top_y equ 60\n'
        asm += ':\n'.join(['text'+str(i) for i in range(4,9)]+['text13','text18','units_table'])+':\n dc.w 0\n'
        cls.image, cls.s = assemble(asm,names)

    def boot(self, model):
        self.cpu = Uc(UC_ARCH_M68K,UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(model)
        self.cpu.mem_map(0,0x100000)
        self.cpu.mem_write(CODE,self.image)
        self.cpu.mem_protect(CODE,(len(self.image)+4095)&~4095,UC_PROT_READ|UC_PROT_EXEC)
        self.cpu.reg_write(UC_M68K_REG_SR,0x2000)
        self.cpu.reg_write(UC_M68K_REG_A6,VARIABLES)
        for i,row in enumerate(self.market):
            self.product(i,'price',row[0]); self.product(i,'quantity',63)
            self.product(i,'units',(row[1]>>5)&3); self.product(i,'naughty',row[4])
        self.set('cash',100000000,4)
        self.police_checks = []
        self.cpu.hook_add(UC_HOOK_CODE,lambda *args:self.police_checks.append(self.get('police_record')),
                          begin=self.s['check_police'],end=self.s['check_police'])

    def set(self,name,value,size=2):
        self.cpu.mem_write(VARIABLES+self.s[name],(value&((1<<(8*size))-1)).to_bytes(size,'big'))
    def get(self,name,size=2):
        return int.from_bytes(self.cpu.mem_read(VARIABLES+self.s[name],size),'big')
    def cargo(self,item,mass):
        self.cpu.mem_write(VARIABLES+self.s['hold']+item*4,struct.pack('>I',mass))
    def product(self,item,field,value):
        self.cpu.mem_write(VARIABLES+self.s['products']+item*self.s['product_len']+self.s[field],struct.pack('>H',value))
    def government(self,value):
        self.cpu.mem_write(VARIABLES+self.s['splanet']+self.s['govern'],struct.pack('>H',value))
    def call(self,name,**regs):
        for r,value in regs.items():
            self.cpu.reg_write((UC_M68K_REG_D0 if r[0]=='d' else UC_M68K_REG_A0)+int(r[1]),value)
        self.cpu.reg_write(UC_M68K_REG_A7,STACK)
        self.cpu.mem_write(STACK,struct.pack('>I',STOP))
        self.cpu.emu_start(self.s[name],STOP,count=100000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC),STOP,name)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7),STACK+4,name)
    def step(self,offset):
        self.set('planet_range',self.s['spcstn_space']+offset,4)
        self.call('radar_lock')

    def test_each_commodity_all_governments_and_record_saturation(self):
        for model in MODELS:
            for government in range(8):
                for item in range(20):
                    factor = self.market[item][4] if item<18 else 0
                    for record,mass in ((0,0),(0,1000000),(47,1000000),(49,2000000),(250,35000000),(255,1000000)):
                        with self.subTest(cpu=model,government=government,item=item,record=record,mass=mass):
                            self.boot(model);self.government(government)
                            self.set('police_record',record);self.cargo(item,mass)
                            self.call('check_cargo')
                            self.assertEqual(self.get('police_record'),min(255,record+(mass//1000000)*factor))

    def test_mixed_hold_fractional_and_32_bit_boundaries(self):
        rng = random.Random(68000)
        masses = [0,1,999999,1000000,1999999,2000000,35000000,65535999,65536000,100000000,0x7fffffff,0xffffffff]
        masses += [rng.randrange(0x100000000) for _ in range(64)]
        for model in MODELS:
            self.boot(model)
            for mass in masses:
                self.cargo(3,mass);self.cargo(6,2500000);self.cargo(10,3999999)
                self.cargo(16,0xffffffff);self.cargo(17,0xffffffff)
                self.set('police_record',7)
                self.call('check_cargo')
                self.assertEqual(self.get('police_record'),min(255,7+4*(mass//1000000)+8+6))

    def test_scan_preserves_registers_objects_cargo_and_all_other_variables(self):
        for model in MODELS:
            self.boot(model);self.cargo(3,3000000);self.cargo(10,5000000)
            size=self.s['var_size']
            before=bytes(self.cpu.mem_read(VARIABLES,size))
            regs={f'{r}{n}':0x12340000+37*n for r,count in (('d',8),('a',6)) for n in range(count)}
            self.call('check_cargo',**regs)
            for r,value in regs.items():
                self.assertEqual(self.cpu.reg_read((UC_M68K_REG_D0 if r[0]=='d' else UC_M68K_REG_A0)+int(r[1])),value)
            after=bytearray(self.cpu.mem_read(VARIABLES,size));p=self.s['police_record']
            self.assertEqual(self.get('police_record'),22)
            after[p:p+2]=before[p:p+2]
            self.assertEqual(bytes(after),before)

    def test_entry_once_per_visit_and_police_sees_new_record(self):
        for model in MODELS:
            self.boot(model);self.government(7);self.cargo(10,5000000)
            self.step(1024);self.assertEqual(self.get('police_record'),0)
            self.step(-1);self.assertEqual(self.get('police_record'),10)
            self.assertEqual(self.police_checks,[10]);self.assertEqual(self.get('fixture_vipers'),1)
            for _ in range(180):self.step(-100)
            self.assertEqual(self.get('police_record'),10)
            for expected in (20,30,40):
                self.step(512);self.step(-1)
                self.assertEqual(self.get('police_record'),expected)
            self.assertEqual(self.police_checks,[10]) # original once-per-system response

    def test_hysteresis_ignores_brief_s_flicker_but_exact_outer_boundary_rearms(self):
        for model in MODELS:
            self.boot(model);self.cargo(10,1000000);self.step(-1)
            for offset in (0,1,100,511)*20:
                self.step(offset);self.assertEqual(self.get('radar_obj'),0)
                self.step(-1);self.assertEqual(self.get('radar_obj'),1)
                self.assertEqual(self.get('police_record'),2)
            self.step(512);self.assertEqual(self.get('checkpoint')&255,0)
            self.step(0);self.assertEqual(self.get('police_record'),2)
            self.step(-1);self.assertEqual(self.get('police_record'),4)

    def test_menus_launch_and_system_resets_do_not_create_false_entries(self):
        for model in MODELS:
            self.boot(model);self.cargo(3,1000000);self.step(-10)
            for _ in range(8):
                self.call('prepare_cockpit');self.assertEqual(self.get('radar_obj'),0)
                self.step(-10);self.assertEqual(self.get('police_record'),4)
            self.set('docked',65535);self.call('launch')
            self.assertEqual(self.get('checkpoint'),65535)
            for _ in range(60):self.step(-100)
            self.assertEqual(self.get('police_record'),4)
            self.step(512);self.step(-10);self.assertEqual(self.get('police_record'),8)
            self.assertEqual(self.police_checks,[4])
            self.call('reset_system') # shared by normal and galactic system changes
            self.step(512);self.step(-10);self.assertEqual(self.get('police_record'),12)
            self.assertEqual(self.police_checks,[4,12])

    def test_empty_hold_new_scooped_cargo_and_missing_station(self):
        for model in MODELS:
            self.boot(model);self.step(-1);self.assertEqual(self.get('police_record'),0)
            self.cargo(6,3000000) # cargo obtained while inside is inspected only next visit
            self.step(-1);self.assertEqual(self.get('police_record'),0)
            self.step(512);self.step(-1);self.assertEqual(self.get('police_record'),12)
            self.set('station_destroyed',65535)
            for _ in range(10):self.step(-100)
            self.assertEqual(self.get('police_record'),12)
            self.assertEqual(self.get('radar_obj'),0)
            self.assertEqual(self.get('checkpoint')&255,0)

    def test_purchase_penalties_and_unpenalized_sales_remain_unchanged(self):
        for model in MODELS:
            for government in range(8):
                for item,factor in ((3,4),(6,4),(10,2),(16,0),(17,0)):
                    self.boot(model);self.government(government)
                    self.set('docked',65535);self.set('this_cargo',item);self.set('fixture_amount',3)
                    self.call('d_buy')
                    self.assertEqual(self.get('police_record'),factor*3)
                    hold=VARIABLES+self.s['hold']+item*4
                    self.assertEqual(int.from_bytes(self.cpu.mem_read(hold,4),'big'),3000000)
                    self.set('max_cargo',1);self.set('this_cargo',0)
                    self.cpu.mem_write(VARIABLES+self.s['cargo_items'],bytes([item]))
                    self.call('d_sell',d0=0)
                    self.assertEqual(int.from_bytes(self.cpu.mem_read(hold,4),'big'),0)
                    self.assertEqual(self.get('police_record'),factor*3)


if __name__ == '__main__':
    unittest.main()
