"""Execute cargo transactions, real object allocation and scooping on 68000/020.

UI raster/OS and sound playback are stubbed. Inventory drawing still builds the
real icon map; mouse hit testing, confirmation dispatch and selling also run.
"""
from pathlib import Path
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


@unittest.skipIf(Uc is None, 'jettison CPU tests require unicorn==2.1.4')
class JettisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read=lambda n:(ROOT/'asm'/f'{n}.m68').read_text()
        cargo,bios,flight,main,data=map(read,('cargo','bios','flight','main','data'))
        cls.units=[(int(m,16)>>5)&3 for m in re.findall(r'^\s*dc \$[0-9a-f]+,\$([0-9a-f]+),.*;',data,re.M)[:18]]
        assert cls.units == [0]*12+[1,1,1,2,0,0]
        names='''jettison_cargo jettison_motion jettison_orientation random jettison_question jettison_penalty d_inventory poll_jettison s_inventory d_sell refresh_inventory
            check_click create_object copy_object remove_objects salvage move_object do_twisting
            objects obj_len obj_size max_objects flags in_use remove no_bounty type barrel
            cargo_type cargo_mass health velocity vel_max visible on_course log_twisting logic x_vector y_vector z_vector
            xpos ypos zpos obj_range obj_rad unit nodes obj_data_len no_canisters
            obj_ctr pirate_count trader_count registration_id max_obj_num
            docked game_over cockpit_on jettison_pending jettison_item hold equip fuel_scoop cargo_bay police_record radar_obj splanet govern
            products product_len units naughty quantity price cash cargo_items this_cargo max_cargo
            action_ptr action_table function button_pressed cursor_spr sp_xpos csr_on inventory_action_table
            selected highlight fixture_answer fixture_random fixture_fx fixture_prompts fixture_message
            fixture_calls fixture_real_random random_seed salvage_ok sfx_locked sfx_error sfx_cargo pad'''.split()
        asm=preamble()+'\tinclude "bitlist.m68"\n'
        asm+=re.search(r'^cross macro.*?^\s*endm',read('vector'),re.M|re.S).group(0)+'\n'
        asm+=cargo[cargo.index('cargo_x:'):cargo.index('\tq_module cargo')]
        asm+=variable_block(flight,'flight')+variable_block(bios,'bios')
        asm+='fixture_answer equ var_size\nfixture_random equ var_size+2\nfixture_fx equ var_size+4\n'
        asm+='fixture_real_random equ var_size+14\n'
        asm+='fixture_prompts equ var_size+6\nfixture_message equ var_size+8\nfixture_calls equ var_size+12\n'
        asm+='\torg $10000\n\tdc.l '+','.join(names)+'\n'
        asm+='return: set *\n rts\n'+cargo.split('\tq_module cargo',1)[1]
        asm+='\n\teven\n'
        for source,functions in ((main,('alloc_object','create_object','copy_object','remove_objects','remove_object','repair_drive')),
                                 (flight,('salvage','move_object')),
                                 (bios,('str_copy','str_cat','find_table','check_click','build_number')),
                                 (read('maths'),('divide_by_10','sqrt')),
                                 (read('vector'),('fix_unit','calc_yvector')),
                                 (read('logic'),('do_twisting','do_cruising','speed_control'))):
            for n in functions:asm+='\n'+routine(source,n)
        asm+='''
open_jettison_confirm:
 addq.w #1,fixture_prompts(a6)
 st jettison_pending(a6)
 rts
poll_jettison_confirm:
 move fixture_answer(a6),d0
 bmi .waiting
 clr jettison_pending(a6)
.waiting:
 rts
'''
        asm+='\nfx:\n move d0,fixture_fx(a6)\n rts\n'
        asm+='\nrandom:\n addq.w #1,fixture_calls(a6)\n tst fixture_real_random(a6)\n bne real_random\n move fixture_random(a6),d0\n rts\n'
        asm+=routine(read('maths'),'random').replace('q_subr random,global','q_subr real_random')
        asm+='\nrand:\n moveq #0,d0\n rts\n'
        asm+='\ninit_cursor:\n move.l a0,action_table(a6)\n st csr_on(a6)\n rts\n'
        asm+='\nprint_centre:\n move.l a0,fixture_message(a6)\n rts\n'
        externals=set()
        for group in re.findall(r'^\s*xref (.*)',cargo,re.M):externals.update(group.strip().split(','))
        actual={'alloc_object','create_object','open_jettison_confirm','poll_jettison_confirm','fx','init_cursor','str_copy','str_cat','find_table','print_centre','build_number','random','fix_unit','calc_yvector'}
        externals-=actual|{'product_list'}
        externals|={'registration_assign','target_lost','local_z_rotate'}
        asm+='\n'+':\n'.join(sorted(externals))+':\n rts\n'
        asm+='\nproduct_list:\n'+''.join(f" dc.b 'Commodity {n}',0\n" for n in range(20))+' even\n'
        header=re.search(r'^barrel:.*?^\s*dc ([^\n]+)',(ROOT/'asm/objects.dat').read_text(),re.M|re.S).group(1)
        asm+='obj_data:\n dcb.l max_obj_num,fixture_header\nfixture_header:\n dc.l 0,fixture_surfaces,product_list\n dc '+header+'\n'
        asm+='fixture_surfaces:\n dc.w 1\n dc.l 0\n'
        cls.image,cls.s=assemble(asm,names)

    def boot(self,model):
        self.cpu=Uc(UC_ARCH_M68K,UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(model);self.cpu.mem_map(0,0x100000)
        self.cpu.mem_write(CODE,self.image)
        self.cpu.mem_protect(CODE,(len(self.image)+4095)&~4095,UC_PROT_READ|UC_PROT_EXEC)
        self.cpu.reg_write(UC_M68K_REG_SR,0x2000);self.cpu.reg_write(UC_M68K_REG_A6,VARIABLES)
        for i,units in enumerate(self.units):
            self.word(self.at('products')+i*self.s['product_len']+self.s['units'],units)
        self.put('fixture_fx',0xffff);self.put('fixture_answer',1)
        self.word(self.at('equip')+self.s['fuel_scoop'],1)

    def at(self,n):return VARIABLES+self.s[n]
    def word(self,a,v=None):
        if v is not None:self.cpu.mem_write(a,struct.pack('>H',v&65535))
        return int.from_bytes(self.cpu.mem_read(a,2),'big')
    def long(self,a,v=None):
        if v is not None:self.cpu.mem_write(a,struct.pack('>I',v&0xffffffff))
        return int.from_bytes(self.cpu.mem_read(a,4),'big')
    def put(self,n,v):self.word(self.at(n),v)
    def get(self,n):return self.word(self.at(n))
    def cargo(self,i,v=None):return self.long(self.at('hold')+4*i,v)
    def obj(self,i=0):return self.at('objects')+i*self.s['obj_len']
    def call(self,n,**regs):
        for r,v in regs.items():self.cpu.reg_write((UC_M68K_REG_D0 if r[0]=='d' else UC_M68K_REG_A0)+int(r[1]),v&0xffffffff)
        self.cpu.reg_write(UC_M68K_REG_A7,STACK);self.long(STACK,STOP)
        self.cpu.emu_start(self.s[n],STOP,count=300000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC),STOP,n)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7),STACK+4,n)
        return self.cpu.reg_read(UC_M68K_REG_D0)&65535
    def objects(self):return bytes(self.cpu.mem_read(self.at('objects'),self.s['obj_size']))
    def scoop(self,obj=0):
        a=self.obj(obj);self.long(a+self.s['zpos'],100);self.long(a+self.s['ypos'],-40)
        self.call('salvage',a5=a)
    def click(self,index,double=True,answer=True):
        x,y=16+(index%6)*48+10,20+(index//6)*48+10
        self.word(self.at('cursor_spr')+self.s['sp_xpos'],x-10)
        self.word(self.at('cursor_spr')+self.s['sp_xpos']+2,y-8)
        self.put('button_pressed',0)
        self.call('check_click',d2=14 if double else 10)
        self.assertEqual(self.long(self.at('action_ptr')),self.s['d_inventory' if double else 's_inventory'])
        self.put('button_pressed',0)
        result=self.call('d_inventory' if double else 's_inventory',d0=self.get('function'))
        if answer and self.get('jettison_pending'):
            result=self.call('poll_jettison')
        return result

    def test_live_confirmation_rechecks_cargo_and_slots_only_on_yes(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for outcome in ('lost','reduced','full','cancel','success'):
                self.boot(model);self.cargo(10,2000000)
                self.call('refresh_inventory');self.click(0,answer=False)
                self.assertTrue(self.get('jettison_pending'))
                self.assertEqual(self.cargo(10),2000000)
                self.assertEqual(self.get('fixture_fx'),65535)
                self.put('fixture_answer',65535)
                for _ in range(60):self.call('poll_jettison')
                self.assertTrue(self.get('jettison_pending'))
                self.assertEqual(self.cargo(10),2000000)
                self.assertEqual(self.objects(),bytes(self.s['obj_size']))
                if outcome=='lost':self.cargo(10,0)
                if outcome=='reduced':self.cargo(10,157)
                if outcome=='full':
                    for slot in range(30):self.word(self.obj(slot)+self.s['flags'],0x100)
                # Another displayed item's index must never replace the saved commodity.
                self.cargo(0,1000000);self.put('this_cargo',0)
                self.put('fixture_answer',0 if outcome=='cancel' else 1)
                before=self.objects();legal=self.get('police_record')
                self.call('poll_jettison')
                self.assertFalse(self.get('jettison_pending'))
                self.assertEqual(self.cargo(0),1000000)
                if outcome in ('lost','full'):
                    self.assertEqual(self.get('fixture_fx'),self.s['sfx_error'])
                    self.assertEqual(self.objects(),before)
                    self.assertEqual(self.get('police_record'),legal)
                elif outcome=='cancel':
                    self.assertEqual(self.get('fixture_fx'),65535)
                    self.assertEqual(self.cargo(10),2000000)
                else:
                    self.assertEqual(self.get('fixture_fx'),self.s['sfx_locked'])
                    self.assertEqual(self.word(self.obj()+self.s['cargo_type']),10)
                    self.assertEqual(self.long(self.obj()+self.s['cargo_mass']),157 if outcome=='reduced' else 1000000)

    def test_all_commodities_units_and_exact_scoop(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for item in range(20):
                for amount in (0,1,157,999,1000,1500,999000,999999,1000000,1000001,2500157):
                    with self.subTest(model=model,item=item,amount=amount):
                        self.boot(model);self.cargo(item,amount)
                        before=self.objects()
                        ok=item<18 and amount>0
                        payload=min(amount,1000000)
                        result=self.call('jettison_cargo',d0=item)
                        self.assertEqual(result,int(ok))
                        self.assertEqual(self.cargo(item),amount-payload if ok else amount)
                        if not ok:self.assertEqual(self.objects(),before);continue
                        a=self.obj()
                        self.assertEqual(self.word(a+self.s['cargo_type']),item)
                        self.assertEqual(self.long(a+self.s['cargo_mass']),payload)
                        self.assertEqual(self.word(a+self.s['obj_rad']),50)
                        self.assertEqual(self.long(a+self.s['zpos']),(-400)&0xffffffff)
                        self.assertEqual(self.word(a+self.s['velocity']),3)
                        self.assertEqual(self.word(a+self.s['logic']),self.s['log_twisting'])
                        self.call('move_object',a4=a,d0=3)
                        self.assertEqual(self.long(a+self.s['zpos']),(-402)&0xffffffff)
                        self.put('fixture_random',3);self.scoop()
                        self.assertEqual(self.cargo(item),amount)
                        self.assertNotEqual(self.get('salvage_ok'),0)
                        self.assertEqual(self.get('fixture_calls'),5)
                        self.assertEqual(self.get('fixture_fx'),self.s['sfx_cargo'])

    def test_full_slots_and_deferred_removal_are_atomic(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            self.boot(model);self.cargo(17,35000000)
            for i in range(30):self.assertEqual(self.call('jettison_cargo',d0=17),1)
            self.put('radar_obj',1);self.word(self.at('splanet')+self.s['govern'],3)
            before=self.objects()
            self.assertEqual(self.call('jettison_cargo',d0=17),65535)
            self.assertEqual(self.cargo(17),5000000);self.assertEqual(self.objects(),before)
            self.assertEqual(self.get('police_record'),0)
            a=self.obj(7)
            self.word(a+self.s['flags'],self.word(a+self.s['flags'])|0x800)
            before=self.objects()
            self.assertEqual(self.call('jettison_cargo',d0=17),65535)
            self.assertEqual(self.objects(),before)
            self.call('remove_objects')
            self.assertEqual(self.call('jettison_cargo',d0=17),1)
            self.assertEqual(self.cargo(17),4000000);self.assertEqual(self.get('police_record'),15)
            self.assertEqual(self.cpu.mem_read(self.at('obj_ctr')+self.s['barrel'],1),b'\x1e')
            self.assertEqual(self.get('trader_count'),0);self.assertEqual(self.get('pirate_count'),0)

    def test_legal_scale_station_zone_anarchy_and_saturation(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            self.boot(model)
            for safe in (0,1):
                self.put('radar_obj',safe)
                for gov in range(8):
                    self.word(self.at('splanet')+self.s['govern'],gov)
                    for record in range(256):
                        self.put('police_record',record)
                        self.call('jettison_penalty')
                        self.assertEqual(self.get('police_record'),min(255,record+15) if safe and gov else record)

    def test_ui_single_double_cancel_last_tonne_and_full_feedback(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            self.boot(model);self.cargo(0,1000000);self.call('refresh_inventory')
            self.click(0,False);self.assertEqual(self.get('fixture_prompts'),0)
            self.put('fixture_answer',0);self.click(0)
            self.assertEqual(self.get('fixture_prompts'),1);self.assertEqual(self.cargo(0),1000000)
            self.assertEqual(self.objects(),bytes(self.s['obj_size']))
            self.put('fixture_answer',1);self.click(0)
            self.assertEqual(self.cargo(0),0);self.assertEqual(self.get('max_cargo'),0)
            self.assertEqual(self.get('fixture_fx'),self.s['sfx_locked'])
            self.assertEqual(self.long(self.at('action_table')),self.s['inventory_action_table'])
            self.cargo(16,1000000);self.call('refresh_inventory')
            for i in range(30):self.word(self.obj(i)+self.s['flags'],0x100)
            self.click(0)
            self.assertEqual(self.cargo(16),1000000);self.assertEqual(self.get('fixture_fx'),self.s['sfx_error'])

    def test_displayed_commodity_survives_live_cargo_changes(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            self.boot(model);self.cargo(0,1000000);self.cargo(16,2000000);self.cargo(17,3000000)
            self.call('refresh_inventory');self.cargo(0,0)
            self.click(1)
            self.assertEqual(self.cargo(16),1000000);self.assertEqual(self.cargo(17),3000000)
            self.assertEqual(self.word(self.obj()+self.s['cargo_type']),16)
            self.cargo(16,0);self.click(0)
            self.assertEqual(self.cargo(17),3000000)
            self.assertEqual(self.get('fixture_fx'),self.s['sfx_error'])
            self.click(0,False);self.assertEqual(self.get('max_cargo'),1)

    def test_single_click_erases_the_previous_selection(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            self.boot(model);self.cargo(0,1000000);self.cargo(17,1000000)
            highlights=[]
            hook=self.cpu.hook_add(UC_HOOK_CODE,lambda cpu,a,size,data:highlights.append(self.get('this_cargo')),
                                   begin=self.s['highlight'],end=self.s['highlight'])
            self.call('refresh_inventory');self.click(0,False);highlights.clear()
            self.click(1,False);self.cpu.hook_del(hook)
            self.assertEqual(highlights,[0,1])

    def test_docked_and_mission_cargo_never_prompt_or_spawn(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for item in (0,18,19):
                self.boot(model);self.cargo(item,1000000);self.call('refresh_inventory')
                self.put('docked',1 if item==0 else 0);self.click(0)
                self.assertEqual(self.get('fixture_prompts'),0)
                self.assertEqual(self.cargo(item),1000000)
                self.assertEqual(self.objects(),bytes(self.s['obj_size']))
            self.boot(model);self.put('docked',1);self.cargo(17,2000000)
            self.assertEqual(self.call('jettison_cargo',d0=17),0)
            for i in (20,255,65535):self.assertEqual(self.call('jettison_cargo',d0=i),0)

    def test_normal_salvage_capacity_and_reused_object_marker(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for item,unit in ((0,1000000),(12,1000),(15,1),(16,1000000),(17,1000000)):
                for random in range(4):
                    self.boot(model);self.cargo(0,1000000);self.call('jettison_cargo',d0=0)
                    self.call('create_object',a4=self.obj())
                    self.assertEqual(self.long(self.obj()+self.s['cargo_mass']),0)
                    self.assertEqual(self.word(self.obj()+self.s['velocity']),11)
                    self.assertEqual(self.word(self.obj()+self.s['vel_max']),11)
                    self.word(self.obj()+self.s['cargo_type'],item);self.put('fixture_random',random)
                    self.scoop();self.assertEqual(self.cargo(item),unit*(random+1))
                    self.assertEqual(self.get('fixture_calls'),6)
            self.boot(model);self.cargo(17,1000000);self.call('jettison_cargo',d0=17)
            self.cargo(0,19500000);self.scoop()
            self.assertEqual(self.cargo(17),0);self.assertEqual(self.get('salvage_ok'),0)
            self.cargo(0,19000000);self.scoop()
            self.assertEqual(self.cargo(17),1000000)
            self.word(self.at('equip')+self.s['fuel_scoop'],0)
            self.call('salvage',a5=self.obj());self.assertEqual(self.get('salvage_ok'),0)

    def test_repeated_full_bubble_scoop_remove_reuse(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            self.boot(model);self.word(self.at('equip')+self.s['cargo_bay'],1)
            for cycle in range(20):
                for item in range(12):self.cargo(item,2000000)
                self.cargo(16,3000000);self.cargo(17,3000000)
                for item in list(range(12))*2+[16]*3+[17]*3:
                    self.assertEqual(self.call('jettison_cargo',d0=item),1)
                for slot in range(30):self.scoop(slot)
                self.assertEqual(self.call('jettison_cargo',d0=17),65535)
                self.call('remove_objects')
                self.assertEqual(self.cpu.mem_read(self.at('obj_ctr')+self.s['barrel'],1),b'\0')
                for item in range(12):self.assertEqual(self.cargo(item),2000000)
                self.assertEqual(self.cargo(16),3000000);self.assertEqual(self.cargo(17),3000000)
            self.call('jettison_cargo',d0=17)
            self.call('copy_object',a5=self.obj(),a4=self.obj(1))
            self.assertEqual(self.long(self.obj(1)+self.s['cargo_mass']),1000000)
            self.call('create_object',a4=self.obj(1))
            self.assertEqual(self.long(self.obj(1)+self.s['cargo_mass']),0)

    def test_exact_prompt_kg_grams_and_tonne_cap(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for item in (0,12,13,14,15,16,17):
                for amount,label in ((1,'1g'),(157,'157g'),(999,'999g'),(1000,'1kg'),
                                     (1500,'1500g'),(999000,'999kg'),(999999,'999999g'),
                                     (1000000,'1t'),(1500000,'1t')):
                    with self.subTest(model=model,item=item,amount=amount):
                        self.boot(model);self.cargo(item,amount)
                        self.call('jettison_question',a4=self.at('hold')+item*4,d1=item)
                        prompt=bytes(self.cpu.mem_read(self.at('pad'),100)).split(b'\0')[0].decode()
                        self.assertEqual(prompt,f'Jettison {label} Commodity {item}')
                        self.call('refresh_inventory');self.click(0)
                        self.assertEqual(self.get('fixture_prompts'),1)
                        self.assertEqual(self.get('fixture_fx'),self.s['sfx_locked'])
                        self.assertEqual(self.cargo(item),max(0,amount-1000000))

    def test_exact_payload_capacity_boundaries_and_illegal_scoop(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for capacity in (20000000,35000000):
                for item in (0,12,13,14,15,16,17):
                    for mass in (1,157,999,1000,1500,999999,1000000):
                        for spare in (-1,0,mass-1,mass,mass+1):
                            with self.subTest(model=model,item=item,mass=mass,spare=spare):
                                self.boot(model);self.word(self.at('equip')+self.s['cargo_bay'],int(capacity==35000000))
                                self.cargo(item,mass);self.call('jettison_cargo',d0=item)
                                self.cargo(1,capacity-spare)
                                self.scoop()
                                ok=spare>=mass
                                self.assertEqual(self.cargo(item),mass if ok else 0)
                                self.assertEqual(bool(self.get('salvage_ok')),ok)
                                self.assertEqual(bool(self.word(self.obj()+self.s['flags'])&0x800),ok)
                                self.assertEqual(self.long(self.obj()+self.s['cargo_mass']),mass)
                                self.assertEqual(self.get('fixture_calls'),5)
            for item,factor in ((3,4),(6,4),(10,2),(13,0),(15,0)):
                self.boot(model);self.cargo(item,1000000)
                self.word(self.at('products')+item*self.s['product_len']+self.s['naughty'],factor)
                self.call('jettison_cargo',d0=item);self.scoop()
                self.assertEqual(self.get('police_record'),0)  # checked on station entry

    def test_multiple_canisters_keep_individual_masses(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            self.boot(model);self.cargo(13,2500157)
            for slot,mass in enumerate((1000000,1000000,500157)):
                self.assertEqual(self.call('jettison_cargo',d0=13),1)
                self.assertEqual(self.long(self.obj(slot)+self.s['cargo_mass']),mass)
            self.assertEqual(self.cargo(13),0)
            for slot in (2,0,1):self.scoop(slot)
            self.assertEqual(self.cargo(13),2500157)

    def test_random_rearward_drift_and_persistent_speed_limit(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            self.boot(model);self.put('fixture_real_random',1)
            self.long(self.at('random_seed'),0x347ac900)
            directions=set();steps=set();speeds=set()
            for sample in range(512):
                self.cargo(13,157);self.assertEqual(self.call('jettison_cargo',d0=13),1)
                a=self.obj();speed=self.word(a+self.s['velocity'])
                basis=[struct.unpack('>3h',self.cpu.mem_read(a+self.s[n+'_vector'],6)) for n in 'xyz']
                x,y,z=basis
                directions.add(z);speeds.add(speed)
                self.assertIn(speed,range(3,7));self.assertEqual(self.word(a+self.s['vel_max']),speed)
                self.assertLess(z[2],-13370)
                for vec in basis:self.assertLess(abs(sum(c*c for c in vec)-16384**2),100000)
                for first,second in ((x,y),(x,z),(y,z)):
                    self.assertLess(abs(sum(c*d for c,d in zip(first,second))),50000)
                self.call('do_twisting',a5=a)
                self.assertEqual(self.word(a+self.s['velocity']),speed)
                self.call('move_object',a4=a,d0=speed)
                position=struct.unpack('>3i',self.cpu.mem_read(a+self.s['xpos'],12))
                steps.add((position[0],position[1],position[2]+400))
                self.assertLess(position[2],-400)
                if sample<16:
                    for tick in range(120):
                        self.call('do_twisting',a5=a)
                        self.assertEqual(self.word(a+self.s['velocity']),speed)
                        self.call('move_object',a4=a,d0=speed)
                self.scoop();self.assertEqual(self.cargo(13),157)
                self.call('remove_objects')
            self.assertEqual(speeds,{3,4,5,6})
            self.assertGreater(len(directions),480)
            self.assertGreater(len(steps),30)
            self.assertTrue(any(x<0 for x,y,z in steps) and any(x>0 for x,y,z in steps))
            self.assertTrue(any(y<0 for x,y,z in steps) and any(y>0 for x,y,z in steps))
            self.cargo(13,157)
            for slot in range(30):self.word(self.obj(slot)+self.s['flags'],0x100)
            before=self.long(self.at('random_seed'))
            self.assertEqual(self.call('jettison_cargo',d0=13),65535)
            self.assertEqual(self.long(self.at('random_seed')),before)

    def test_initial_roll_preserves_drift_payload_and_registers(self):
        # Include zero/near-zero coefficients and every quadrant of the roll.
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            self.boot(model)
            pending=[]
            hook=self.cpu.hook_add(UC_HOOK_CODE,lambda cpu,a,size,data:self.put('fixture_random',pending.pop(0)),
                                   begin=self.s['random'],end=self.s['random'])
            phases=set()
            for first in (0,64,127,128,129,192,255):
                for second in (0,64,127,128,129,192,255):
                    a=self.obj()
                    for axis,values in zip('xyz',((-16384,0,0),(0,16384,0),(0,0,-16384))):
                        self.cpu.mem_write(a+self.s[axis+'_vector'],struct.pack('>3h',*values))
                    self.word(a+self.s['velocity'],4);self.word(a+self.s['vel_max'],4)
                    self.long(a+self.s['cargo_mass'],157);self.word(a+self.s['cargo_type'],15)
                    pending[:]=[first,second]
                    regs={**{f'd{i}':0xa5550123+i for i in range(8)},
                          **{f'a{i}':0x70000+i*0x100 for i in range(6)}}
                    regs['a4']=a
                    self.call('jettison_orientation',**regs)
                    self.assertFalse(pending)
                    for reg,value in regs.items():
                        self.assertEqual(self.cpu.reg_read((UC_M68K_REG_D0 if reg[0]=='d' else UC_M68K_REG_A0)+int(reg[1])),value)
                    x,y,z=[struct.unpack('>3h',self.cpu.mem_read(a+self.s[axis+'_vector'],6)) for axis in 'xyz']
                    phases.add(x)
                    self.assertEqual(z,(0,0,-16384))
                    for vec in (x,y):self.assertLess(abs(sum(c*c for c in vec)-16384**2),100000)
                    self.assertEqual(sum(c*d for c,d in zip(x,y)),0)
                    self.assertEqual(self.word(a+self.s['velocity']),4)
                    self.assertEqual(self.word(a+self.s['vel_max']),4)
                    self.assertEqual(self.long(a+self.s['cargo_mass']),157)
                    self.assertEqual(self.word(a+self.s['cargo_type']),15)
            self.cpu.hook_del(hook)
            self.assertGreater(len(phases),24)

    def test_transaction_preserves_registers_and_selling_still_sells_all(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for outcome in ('success','full','empty'):
                self.boot(model)
                if outcome!='empty':self.cargo(17,2000000)
                if outcome=='full':
                    for i in range(30):self.word(self.obj(i)+self.s['flags'],0x100)
                regs={**{f'd{i}':0xa5550123+i for i in range(1,8)},**{f'a{i}':0x70000+i*0x100 for i in range(6)}}
                self.call('jettison_cargo',d0=17,**regs)
                for reg,value in regs.items():
                    self.assertEqual(self.cpu.reg_read((UC_M68K_REG_D0 if reg[0]=='d' else UC_M68K_REG_A0)+int(reg[1])),value)
            self.boot(model);self.put('docked',1);self.cargo(17,3000000)
            self.word(self.at('products')+17*self.s['product_len']+self.s['price'],100)
            self.call('refresh_inventory');self.call('d_sell',d0=0)
            self.assertEqual(self.cargo(17),0);self.assertEqual(self.long(self.at('cash')),1140)
            self.assertEqual(self.objects(),bytes(self.s['obj_size']))


@unittest.skipIf(Uc is None, 'confirmation CPU tests require unicorn==2.1.4')
class ConfirmationTests(unittest.TestCase):
    at = JettisonTests.at
    word = JettisonTests.word
    long = JettisonTests.long
    put = JettisonTests.put
    get = JettisonTests.get
    call = JettisonTests.call
    @classmethod
    def setUpClass(cls):
        bios=(ROOT/'asm/bios.m68').read_text()
        action=(ROOT/'asm/action.m68').read_text()
        names='''confirm confirm_yn fixture_key fixture_mouse fixture_reads fixture_depth
            fixture_flush fixture_answer button_pressed function open_jettison_confirm poll_jettison_confirm
            cancel_jettison_confirm jettison_pending jettison_item docked game_over cockpit_on
            check_keys fixture_normal_actions action_ptr frame_count loop_ctr'''.split()
        asm=preamble()+'\tinclude "bitlist.m68"\nconfirm_x equ 105\nconfirm_y equ 83\n'
        for i,n in enumerate(names[2:8]):asm+=f'{n} equ var_size+{i*2}\n'
        asm+=action[action.index('threshold_x:'):action.index('\tq_module action')]
        asm+='fixture_normal_actions equ var_size+12\n'
        asm+='\torg $10000\n dc.l '+','.join(names)+'\nreturn: set *\n rts\n'
        asm+=routine(action,'check_keys')
        asm+='''
key_list:
 dc.w 'Y'
 dc.l fixture_normal_action
no_keys equ 1
fixture_normal_action:
 addq.w #1,fixture_normal_actions(a6)
 rts
poll_jettison:
 bra poll_jettison_confirm
increase_speed:
decrease_speed:
get_joystick:
roll_left:
roll_right:
climb:
dive:
fire:
check_mouse:
start_galactic:
disp_message:
text5:
fx:
 rts
'''
        asm+=routine(bios,'confirm_yn')+routine(bios,'confirm')
        for name in ('open_jettison_confirm','poll_jettison_confirm','cancel_jettison_confirm'):
            asm+=routine(bios,name)
        asm+='''
flush_keyboard:
 addq.w #1,fixture_flush(a6)
 rts
read_key:
 addq.w #1,fixture_reads(a6)
 move fixture_key(a6),d0
 rts
hide_cursor:
 addq.w #1,fixture_depth(a6)
 rts
restore_cursor:
 subq.w #1,fixture_depth(a6)
 rts
init_cursor:
 move fixture_mouse(a6),button_pressed(a6)
 move fixture_answer(a6),function(a6)
 rts
find_bitmap:
draw_sprite:
remove_sprite:
amiga_poll:
 rts
confirm_table:
 dc.w -1
 dc.l 0
'''
        cls.image,cls.s=assemble(asm,names)

    def boot(self,model):
        self.cpu=Uc(UC_ARCH_M68K,UC_MODE_BIG_ENDIAN);self.cpu.ctl_set_cpu_model(model)
        self.cpu.mem_map(0,0x100000);self.cpu.mem_write(CODE,self.image)
        self.cpu.mem_protect(CODE,(len(self.image)+4095)&~4095,UC_PROT_READ|UC_PROT_EXEC)
        self.cpu.reg_write(UC_M68K_REG_SR,0x2000);self.cpu.reg_write(UC_M68K_REG_A6,VARIABLES)

    def test_confirmation_keys_mouse_and_existing_callers(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for key,expected in ((ord('Y'),65535),(ord('N'),0),(27,0)):
                self.boot(model);self.put('fixture_key',key)
                self.assertEqual(self.call('confirm_yn'),expected)
                self.assertEqual(self.get('fixture_depth'),0);self.assertEqual(self.get('fixture_flush'),1)
            for routine_name in ('confirm','confirm_yn'):
                for answer in (0,65535):
                    self.boot(model);self.put('fixture_mouse',1);self.put('fixture_answer',answer)
                    self.put('fixture_key',ord('Y') if answer==0 else ord('N'))
                    self.assertEqual(self.call(routine_name),answer)
                    self.assertEqual(self.get('fixture_depth'),0);self.assertEqual(self.get('fixture_reads'),0)
                    self.assertEqual(self.get('button_pressed'),0)


    def test_live_panel_returns_while_waiting_and_balances_cursor_on_close(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for key,answer in ((ord('Y'),1),(ord('N'),0),(27,0)):
                self.boot(model)
                self.call('open_jettison_confirm')
                self.assertTrue(self.get('jettison_pending'))
                self.assertEqual(self.get('fixture_depth'),1)
                for ignored in (0,ord('X'),ord('H'),ord('G'),ord('A')):
                    self.put('fixture_key',ignored)
                    self.assertEqual(self.call('poll_jettison_confirm'),65535)
                    self.assertEqual(self.get('fixture_depth'),1)
                self.put('fixture_key',key)
                self.assertEqual(self.call('poll_jettison_confirm'),answer)
                self.assertFalse(self.get('jettison_pending'))
                self.assertEqual(self.get('fixture_depth'),0)
                self.call('cancel_jettison_confirm')
                self.assertEqual(self.get('fixture_depth'),0)
            for mouse in (0,65535):
                self.boot(model);self.call('open_jettison_confirm')
                self.put('button_pressed',1);self.put('function',mouse)
                self.put('fixture_key',ord('N') if mouse else ord('Y'))
                self.assertEqual(self.call('poll_jettison_confirm'),int(bool(mouse)))
                self.assertFalse(self.get('jettison_pending'))
                self.assertEqual(self.get('fixture_depth'),0)
            for transition in ('docked','game_over','cockpit_on'):
                self.boot(model);self.call('open_jettison_confirm')
                self.put('fixture_key',ord('Y'));self.put(transition,1)
                self.assertEqual(self.call('poll_jettison_confirm'),0)
                self.assertFalse(self.get('jettison_pending'))
                self.assertEqual(self.get('fixture_depth'),0)

    def test_input_router_captures_answers_and_returns_to_main_loop(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for key in (ord('Y'),ord('N'),27):
                self.boot(model)
                self.put('button_pressed',1)
                self.long(self.at('action_ptr'),self.s['open_jettison_confirm'])
                self.put('fixture_key',ord('Y'))
                self.call('check_keys')
                self.assertTrue(self.get('jettison_pending'))
                self.assertEqual(self.get('fixture_reads'),0) # no key dispatch after opening
                self.assertEqual(self.get('fixture_normal_actions'),0)
                self.put('fixture_key',ord('X'))
                self.put('frame_count',3);self.put('loop_ctr',7)
                for _ in range(60):self.call('check_keys')
                self.assertTrue(self.get('jettison_pending'))
                self.assertEqual(self.get('frame_count'),3)
                self.assertEqual(self.get('loop_ctr'),7)
                self.assertEqual(self.get('fixture_normal_actions'),0)
                self.put('fixture_key',key);self.call('check_keys')
                self.assertFalse(self.get('jettison_pending'))
                self.assertEqual(self.get('fixture_normal_actions'),0)
                self.assertEqual(self.get('fixture_depth'),0)
                # A new Y after closing resumes its ordinary binding.
                self.put('fixture_key',ord('Y'));self.call('check_keys')
                self.assertEqual(self.get('fixture_normal_actions'),1)

    def test_cancel_preserves_registers_and_is_inert_without_jettison(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for active in (False,True):
                self.boot(model)
                if active:self.call('open_jettison_confirm')
                regs={**{f'd{i}':0xab123000+i for i in range(8)},
                      **{f'a{i}':0x70000+i*0x100 for i in range(6)}}
                self.call('cancel_jettison_confirm',**regs)
                for reg,value in regs.items():
                    self.assertEqual(self.cpu.reg_read((UC_M68K_REG_D0 if reg[0]=='d' else UC_M68K_REG_A0)+int(reg[1])),value)
                self.assertEqual(self.get('fixture_depth'),0)
                self.assertFalse(self.get('jettison_pending'))

if __name__=='__main__':unittest.main()
