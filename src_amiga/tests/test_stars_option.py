"""Exercise the real options menu, click dispatch and sky transitions on 68K.

UI drawing and OS calls are stubbed; sprite rasterisation has separate coverage.
"""
from pathlib import Path
import re
import struct
import unittest
from test_raster import routine
from test_viewport import assemble, preamble, variable_block
try:
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_PROT_READ, UC_PROT_EXEC
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_CPU_M68K_M68020,
        UC_M68K_REG_D0, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_PC, UC_M68K_REG_SR)
except ImportError:
    Uc = None
ROOT = Path(__file__).resolve().parents[1]
CODE, STOP, VARIABLES, STACK = 0x10000, 0x1000, 0x30000, 0x90000

@unittest.skipIf(Uc is None, 'optional options tests require unicorn==2.1.4')
class StarsOptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        options = (ROOT/'asm/options.m68').read_text()
        sky = (ROOT/'asm/sky.m68').read_text()
        bios = (ROOT/'asm/bios.m68').read_text()
        names = '''options change_stars change_flag change_cursor check_click init_sky
            set_sky_enabled options_table sky_enabled sky_basis sky_dirty sky_vars sky_used
            action_ptr action_table function button_pressed cursor_spr sp_xpos csr_on
            user game_state random_seed cursor_type xc1 yc1 xc2 yc2 icon_y i_stars
            i_damping i_effects i_quit i_reset'''.split()
        asm = preamble()+'\tinclude "bitlist.m68"\n'
        asm += options[options.index('icon_y:'):options.index('\tq_module options')]
        asm += sky[sky.index('sky_capacity:'):sky.index('    q_module sky')]
        asm += '\torg $10000\n\tdc.l '+','.join(names)+'\n'
        asm += options[options.index('\tq_subr options,global'):]
        asm += '\n\teven\n'+sky[sky.index('    q_subr init_sky'):]
        asm += '\n'+routine(bios,'check_click')
        asm += '\ninit_cursor:\n\tmove.l a0,action_table(a6)\n\tst csr_on(a6)\n\trts\n'
        externals = set(re.findall(r'^\s*xref (.*)', options, re.M)[0].split(','))
        for group in re.findall(r'^\s*xref (.*)', options, re.M):
            externals.update(group.strip().split(','))
        externals -= {'sky_enabled', 'set_sky_enabled', 'init_cursor'}
        externals.update(('c_plotxy','amiga_exit'))
        asm += '\n'+':\n'.join(sorted(externals))+':\n\trts\n'
        cls.code, cls.sym = assemble(asm,names)

    def put(self,name,value,size=2):
        self.cpu.mem_write(VARIABLES+self.sym[name],(value & ((1<<(size*8))-1)).to_bytes(size,'big'))

    def get(self,name,size=2):
        return int.from_bytes(self.cpu.mem_read(VARIABLES+self.sym[name],size),'big')

    def call(self,name,value=None):
        if value is not None:self.cpu.reg_write(UC_M68K_REG_D0,value & 0xffffffff)
        self.cpu.reg_write(UC_M68K_REG_SR,0x2700)
        self.cpu.reg_write(UC_M68K_REG_A6,VARIABLES)
        self.cpu.reg_write(UC_M68K_REG_A7,STACK-4)
        self.cpu.mem_write(STACK-4,struct.pack('>I',STOP))
        self.cpu.emu_start(self.sym[name],STOP,count=100000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC),STOP,name)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7),STACK,name)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A6),VARIABLES,name)

    def prepare(self,model):
        self.cpu=Uc(UC_ARCH_M68K,UC_MODE_BIG_ENDIAN)
        self.cpu.ctl_set_cpu_model(model)
        self.cpu.mem_map(0,0x100000)
        self.cpu.mem_write(CODE,self.code)
        self.cpu.mem_protect(CODE,(len(self.code)+4095)//4096*4096,UC_PROT_READ|UC_PROT_EXEC)
        self.put('user',0x3f00)
        self.put('cursor_type',2)
        self.put('random_seed',0x487ada32,4)
        self.call('init_sky')
        self.call('options')

    def click(self,x,y,double=False):
        self.put('button_pressed',0)
        self.cpu.mem_write(VARIABLES+self.sym['cursor_spr']+self.sym['sp_xpos'],struct.pack('>hh',x-10,y-8))
        self.cpu.reg_write(UC_M68K_REG_D0+2,14 if double else 10)
        self.call('check_click')
        self.assertTrue(self.get('button_pressed'))
        self.assertEqual(self.get('action_ptr',4),self.sym['change_stars'])
        value=self.get('function')
        self.put('button_pressed',0)
        self.call('change_stars',value)

    def box(self):
        return tuple(self.get(n) for n in ('xc1','yc1','xc2','yc2'))

    def test_menu_default_mouse_clicks_and_reopening_preserve_other_preferences(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            self.prepare(model)
            y=self.sym['icon_y'];on=(226,y-5,253,y+13);off=(259,y-5,294,y+13)
            self.assertEqual(self.box(),on)
            commander=bytes(self.cpu.mem_read(VARIABLES+self.sym['game_state'],256))
            for double in (False,True):
                # Actual hit testing, including every corner of both button borders.
                for enabled,box in ((0,off),(1,on)):
                    for x,yy in ((box[0],box[1]),(box[2],box[1]),(box[0],box[3]),(box[2],box[3])):
                        self.click(x,yy,double)
                        self.assertEqual(self.get('sky_enabled'),enabled)
                        self.assertEqual(self.get('user'),0x3f00 | (0x4000 if not enabled else 0))
                        self.assertEqual(self.box(),box)
                        self.call('options')
                        self.assertEqual(self.box(),box)
                        self.assertEqual(bytes(self.cpu.mem_read(VARIABLES+self.sym['game_state'],256)),commander)
                        self.assertEqual(self.get('random_seed',4),0x487ada32)
            self.assertEqual(self.get('cursor_type'),2)
            self.assertEqual(self.get('user'),0x3f00)

if __name__=='__main__':
    unittest.main()
