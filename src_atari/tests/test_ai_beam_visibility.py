"""Real culling, sorted draw queues and clipped AI beams on MC68000/020.

Large models/sky use deterministic fixtures. Small-ship dispatch, point/circle
drawing, projection, sorted queues and beam raster use the platform routines.
"""
from pathlib import Path
import math
import re
import struct
import unittest
from test_raster import BACKGROUND, GUARD, SCREEN, OTHER, paint, routine
from test_viewport import assemble, preamble, variable_block, circle_pixels
try:
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_PROT_READ, UC_PROT_EXEC
    from unicorn.m68k_const import *
except ImportError:
    Uc=None

ROOT=Path(__file__).resolve().parents[1]
CODE, VARIABLES, STACK, STOP, NODES, TRACE=0x10000,0x30000,0x90000,0x1000,0x70000,0x74000
VIEWS=('front','rear','left','right')

@unittest.skipIf(Uc is None,'AI beam visibility tests require unicorn==2.1.4')
class AIBeamVisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read=lambda name:(ROOT/'asm'/f'{name}.m68').read_text()
        vector,graphics,special=map(read,('vector','graphics','special'))
        groups=[(vector,('draw_object','queue_ai_laser','queue_draw_object','draw_all',
                         'draw_space','draw_space_layer','check_sights','visibility',
                         'perspective','transform','calc_yvector')+
                        tuple(f'{size}_swap_{view}' for view in VIEWS for size in ('w','l'))),
                (special,('draw_ai_laser','draw_point')),
                (graphics,('set_colour','c_line','line','horiz_line','vert_line','mask_plot','dot_to_addr',
                           'circle','circle_plotxy','circle_horiz'))]
        functions=[n for _,names in groups for n in names]
        constants='''objects obj_len obj_size type flags logic log_exploding cougar viper
            this_xpos this_ypos this_zpos xpos ypos zpos obj_range obj_rad hits_rad
            scr_radius centre_x centre_y gun_node no_nodes nodes x_vector z_vector
            ai_laser health rating random_seed cockpit_on visible invisible in_sights
            l_view_ptr w_view_ptr loop_ctr scr_base colour_ptr reverse_draw
            draw_list draw_len draw_size laser_only obj_ptr prev_ptr next_ptr
            next_record list_ptr laser_candidate vector_vars vector_vsize vector_used
            target no_target ship_type'''.split()
        asm=preamble()+'max_lines equ 10\nmax_vert equ 15\n'+vector[vector.index('\trsset 0'):vector.index('* ---- LOCAL MACROS ----')]
        asm+=variable_block(graphics,'graphics')
        for source,macro in ((vector,'cross'),(graphics,'outcodes')):
            asm+=re.search(r'^'+macro+r' macro.*?^\s*endm',source,re.M|re.S)[0]+'\n'
        asm+='\torg $10000\n\tdc.l '+','.join(functions+constants)+'\n'
        for source,names in groups:
            asm+='\n'.join(routine(source,n) for n in names)+'\n'
        asm+=graphics[graphics.index('\tq_global bit_masks'):graphics.index('clip_list:')]
        # Run the real small-ship branch; only the full model path is replaced.
        point_dispatch=routine(vector,'draw_it').split('q_vector_m68_33:',1)[0]
        point_dispatch=point_dispatch.split('q_subr draw_it',1)[1]
        asm+=f'''
draw_it:
 move.l {TRACE},a1
 move.l a5,(a1)+
 move.l a1,{TRACE}
{point_dispatch}
q_vector_m68_33:
 tst health(a5)
 beq .done
 moveq #2,d0
 jsr set_colour
 moveq #-10,d0
 moveq #55,d1
 moveq #10,d2
 moveq #55,d3
 jsr c_line
.done:
 move.l #$5a5a5a5a,a0
 move.l a0,a5
 rts
draw_sky:
dust_cloud:
fx:
check_missile:
disp_message:
registration_message:
amiga_poll:
draw_explosion:
 rts
random:
 moveq #0,d0
 rts
text1: dc.w 0
magnitude_table: dcb.w 512,0
mult_by_320: dc.w '''+','.join(str(y*320) for y in range(200))+'\n'
        cls.image,cls.s=assemble(asm,functions+constants)

    def boot(self,model,view='front',screen=SCREEN):
        self.cpu=Uc(UC_ARCH_M68K,UC_MODE_BIG_ENDIAN);self.cpu.ctl_set_cpu_model(model)
        self.cpu.mem_map(0,0x100000);self.cpu.mem_write(CODE,self.image)
        self.cpu.mem_protect(CODE,(len(self.image)+4095)&~4095,UC_PROT_READ|UC_PROT_EXEC)
        self.screen=screen;self.view=view;self.ship=VARIABLES+self.s['objects']
        self.var('cockpit_on',1);self.var('l_view_ptr',self.s['l_swap_'+view],4)
        self.var('w_view_ptr',self.s['w_swap_'+view],4);self.var('scr_base',screen,4)
        self.var('random_seed',0xabcdef01,4);self.put(TRACE,TRACE+4,4)
        self.cpu.mem_write(GUARD,BACKGROUND)
        self.guard_address=VARIABLES+self.s['draw_list']+self.s['draw_size']+4 # skip the live list_ptr field
        self.cpu.mem_write(self.guard_address,b'QUEUE-GUARD')
        self.assertLessEqual(self.s['vector_used'],self.s['vector_vsize']*2)

    def put(self,a,n,size=2):self.cpu.mem_write(a,(n&((1<<(size*8))-1)).to_bytes(size,'big'))
    def var(self,n,x,size=2):self.put(VARIABLES+self.s[n],x,size)
    def obj(self,n,x,size=2):self.put(self.ship+self.s[n],x,size)
    def read(self,n,obj=False,size=2):
        return int.from_bytes(self.cpu.mem_read((self.ship if obj else VARIABLES)+self.s[n],size),'big')
    def call(self,n,**regs):
        self.cpu.reg_write(UC_M68K_REG_SR,0x2700)
        self.cpu.reg_write(UC_M68K_REG_A6,VARIABLES);self.cpu.reg_write(UC_M68K_REG_A5,self.ship)
        self.cpu.reg_write(UC_M68K_REG_A7,STACK-4);self.put(STACK-4,STOP,4)
        for r,v in regs.items():self.cpu.reg_write(globals()['UC_M68K_REG_'+r.upper()],v&0xffffffff)
        self.cpu.emu_start(self.s[n],STOP,count=300000)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_PC),STOP,n)
        self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A7),STACK,n)

    def setup_ship(self,x=1000,y=0,z=3000,index=0):
        self.ship=VARIABLES+self.s['objects']+index*self.s['obj_len']
        xyz={'front':(x,y,z),'rear':(-x,y,-z),'left':(-z,y,x),'right':(z,y,-x)}[self.view]
        for n,v in zip(('xpos','ypos','zpos'),xyz):self.obj(n,v,4)
        self.obj('obj_range',round(math.sqrt(x*x+y*y+z*z)),4)
        self.obj('obj_rad',120);self.obj('type',self.s['viper'])
        self.obj('nodes',NODES,4);self.obj('x_vector',16384)
        self.put(self.ship+self.s['z_vector']+4,-16384)

    def queue(self,shot=True):
        self.call('draw_object') # before AI decides to fire
        self.obj('ai_laser',int(shot))
        self.call('queue_ai_laser') # after AI, before movement

    def entries(self):
        if not self.read('next_record',size=4):return []
        p=self.read('list_ptr',size=4);previous=0;out=[]
        while p:
            self.assertLess(len(out),30,'draw-list cycle/overflow')
            self.assertEqual(int.from_bytes(self.cpu.mem_read(p+self.s['prev_ptr'],4),'big'),previous)
            obj=int.from_bytes(self.cpu.mem_read(p+self.s['obj_ptr'],4),'big')
            flag=int.from_bytes(self.cpu.mem_read(p+self.s['laser_only'],2),'big')
            out.append((obj,flag));previous=p
            p=int.from_bytes(self.cpu.mem_read(p+self.s['next_ptr'],4),'big')
        self.assertEqual(self.cpu.mem_read(self.guard_address,11),b'QUEUE-GUARD')
        return out

    def buffer(self):return bytes(self.cpu.mem_read(GUARD,len(BACKGROUND)))
    def reset_buffer(self):self.cpu.mem_write(GUARD,BACKGROUND);self.put(TRACE,TRACE+4,4)
    def models_drawn(self):
        end=int.from_bytes(self.cpu.mem_read(TRACE,4),'big')
        return list(struct.unpack('>'+'I'*((end-TRACE-4)//4),self.cpu.mem_read(TRACE+4,end-TRACE-4)))

    def assert_viewport_only(self,data):
        # Mask out only the legal 256x112 flight rectangle. Everything else,
        # including cockpit, second screen and guard bytes, must be unchanged.
        clean=bytearray(data);reference=bytearray(BACKGROUND)
        points=((x,y) for y in range(8,120) for x in range(32,288))
        paint(clean,points,(0,0,0,0),self.screen)
        paint(reference,((x,y) for y in range(8,120) for x in range(32,288)),(0,0,0,0),self.screen)
        self.assertEqual(clean,reference)

    def test_offscreen_beams_reach_the_raster_in_all_views_and_both_buffers(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for view in VIEWS:
                for screen in (SCREEN,OTHER):
                    for x,y in ((0,0),(1000,0),(-1000,0),(0,600),(0,-600),(1000,600)):
                        self.boot(model,view,screen);self.setup_ship(x,y)
                        self.queue();offscreen=(x,y)!=(0,0)
                        self.assertEqual(self.entries(),[(self.ship,65535 if offscreen else 0)])
                        self.assertEqual(bool(self.read('visible')),not offscreen)
                        self.assertEqual(self.read('random_seed',size=4),0xabcdef01)
                        # Moving the world after queueing must not move this frame's beam.
                        self.obj('xpos',20000,4)
                        self.call('draw_space');actual=self.buffer()
                        self.assertNotEqual(actual,BACKGROUND)
                        self.assertEqual(self.models_drawn(),[] if offscreen else [self.ship])
                        self.assert_viewport_only(actual)
                        self.reset_buffer();self.call('draw_ai_laser')
                        self.assertEqual(actual,self.buffer(),'queue lost/changed the clipped beam')

    def test_point_sized_and_subpixel_emitters_show_beams_at_extended_range(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for view in VIEWS:
                for screen in (SCREEN,OTHER):
                    for radius in (1,40,56,80):
                        with self.subTest(cpu=model,view=view,screen=screen,radius=radius):
                            self.boot(model,view,screen)
                            self.setup_ship(x=0,z=12288)
                            self.obj('obj_rad',radius)
                            self.queue()
                            projected=radius*512//12288
                            self.assertEqual(self.read('scr_radius',True),projected)
                            self.assertLess(projected,4) # the real renderer uses a point below 4
                            self.assertEqual(self.entries(),[(self.ship,0 if projected else 65535)])
                            self.call('draw_space')
                            actual=self.buffer()
                            self.assertNotEqual(actual,BACKGROUND)
                            self.assertEqual(self.models_drawn(),[self.ship] if projected else [])
                            self.assert_viewport_only(actual)
                            # Compare the real point/circle against an independent
                            # pixel reference, then draw the beam over that body.
                            expected=bytearray(BACKGROUND)
                            if projected:
                                paint(expected,circle_pixels(0,0,projected-1,0),
                                      (65535,0,0,0),self.screen)
                                self.reset_buffer();self.call('draw_point',d0=self.s['viper'])
                                self.assertEqual(self.buffer(),expected)
                            self.reset_buffer();self.cpu.mem_write(GUARD,bytes(expected))
                            self.call('draw_ai_laser')
                            self.assertEqual(actual,self.buffer())

    def beam_from_offscreen(self,target,victim_drawn=True):
        """One offscreen emitter's beam, so the raster holds nothing else.

        The victim is on screen but contributes no pixels of its own: the
        harness's DRAW_IT draws nothing for a model with no health.
        """
        self.setup_ship(300,0,3000,index=1);victim=self.ship # inside the viewport
        self.obj('health',0)
        if victim_drawn:self.call('draw_object') # fills its THIS_* for this frame
        self.setup_ship(1000,600,3000,index=0) # off screen: a beam-only record
        self.obj('health',0)
        self.call('draw_object')
        self.put(self.ship+self.s['target'],{'player':0,'none':self.s['no_target'],
                                             'ship':victim}[target],4)
        self.obj('ai_laser',2)
        self.call('queue_ai_laser')
        # The emitter is queued for its beam alone; both ships have no health,
        # so the harness's DRAW_IT paints nothing and the beam is all there is.
        self.assertIn((self.ship,65535),self.entries())
        self.reset_buffer();self.call('draw_space')
        return self.buffer()

    def test_a_beam_at_a_ship_is_drawn_and_differs_from_one_at_the_player(self):
        """DRAW_AI_LASER has two arms. TARGET <= 0 sends the beam to the
        opposite screen edge, which is what every other test here exercises,
        because none of them sets TARGET and a fresh record reads zero -- the
        player. TARGET > 0 draws between the two ships instead, and that arm
        went unexercised until AI-versus-AI targeting made it the common one.
        """
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for view in VIEWS:
                self.boot(model,view)
                at_ship=self.beam_from_offscreen('ship')
                self.assertNotEqual(at_ship,BACKGROUND,'no ship-to-ship beam')
                self.assert_viewport_only(at_ship)

                self.boot(model,view)
                at_player=self.beam_from_offscreen('player')
                self.assertNotEqual(at_player,BACKGROUND)
                # NO_TARGET is -1, so it takes the player's arm as well.
                self.boot(model,view)
                self.assertEqual(self.beam_from_offscreen('none'),at_player)

                self.assertNotEqual(at_ship,at_player,
                                    'the two arms drew the same beam')

    def test_no_beam_at_a_ship_the_camera_cannot_see(self):
        """The arm needs the victim's view coordinates, and DRAW_OBJECT writes
        them only for an object in front of the camera. Without the guard the
        beam would be aimed at whatever last frame left behind."""
        for view in VIEWS:
            self.boot(UC_CPU_M68K_M68000,view)
            self.assertEqual(self.beam_from_offscreen('ship',victim_drawn=False),
                             BACKGROUND)

    def test_point_and_circle_occlusion_follows_depth_in_every_view_and_buffer(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for view in VIEWS:
                for screen in (SCREEN,OTHER):
                    for projected in (1,2,3):
                        for nearer in (False,True):
                            with self.subTest(cpu=model,view=view,screen=screen,
                                              radius=projected,nearer=nearer):
                                self.boot(model,view,screen)
                                self.setup_ship(x=0,z=12288)
                                self.obj('obj_rad',24*projected)
                                self.queue();emitter=self.ship
                                self.call('draw_space');beam=self.buffer();self.reset_buffer()
                                z=6144 if nearer else 18432
                                self.setup_ship(x=0,z=z,index=1)
                                self.obj('obj_rad',z*projected//512)
                                self.queue(shot=False);body=self.ship
                                self.assertEqual(self.read('scr_radius',True),projected)
                                self.call('draw_space');actual=self.buffer()
                                expected=bytearray(beam)
                                if nearer:
                                    paint(expected,circle_pixels(0,0,projected-1,0),
                                          (65535,0,0,0),self.screen)
                                    self.assertNotEqual(bytes(expected),beam,
                                                        'foreground body did not cover any beam pixels')
                                self.assertEqual(actual,expected)
                                order=[emitter,body] if nearer else [body,emitter]
                                self.assertEqual(self.entries(),[(obj,0) for obj in order])
                                self.assertEqual(self.models_drawn(),order)
                                self.assert_viewport_only(actual)

    def test_nonfiring_hidden_behind_and_nonflight_emitters_do_not_add_beams(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for view in VIEWS:
                for reason in ('no_shot','behind','hidden','no_cockpit'):
                    self.boot(model,view);self.setup_ship(z=-3000 if reason=='behind' else 3000)
                    for n,v in (('this_xpos',0),('this_ypos',0),('this_zpos',3000)):
                        self.obj(n,v,4) # stale coordinates must never resurrect a hidden beam
                    if reason=='hidden':self.obj('type',self.s['cougar']);self.var('loop_ctr',64,1)
                    if reason=='no_cockpit':self.var('cockpit_on',0)
                    self.queue(reason!='no_shot')
                    self.assertEqual(self.entries(),[])
                    self.call('draw_space');self.assertEqual(self.buffer(),BACKGROUND)
                    self.assertEqual(self.models_drawn(),[])
            self.boot(model);self.setup_ship();self.queue()
            self.call('draw_all');self.assertEqual(self.buffer(),BACKGROUND)
            self.assertEqual(self.models_drawn(),[],'hangar renderer drew a laser-only model')
            self.obj('logic',self.s['log_exploding']);self.call('draw_space')
            self.assertEqual(self.buffer(),BACKGROUND,'destroyed emitter kept its laser')

    def test_thirty_objects_keep_depth_order_capacity_and_no_duplicate_records(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for reverse in (0,1):
                self.boot(model);self.var('reverse_draw',reverse);objects=[]
                for i in range(30):
                    z=1200+(i*941)%4400
                    self.setup_ship(x=z//2 if i%2 else 0,z=z,index=i)
                    self.queue();objects.append((z,self.ship,65535 if i%2 else 0))
                    before=self.read('next_record',size=4);self.call('queue_ai_laser')
                    self.assertEqual(self.read('next_record',size=4),before)
                expected=[(obj,flag) for z,obj,flag in sorted(objects,reverse=not reverse)]
                self.assertEqual(self.entries(),expected)
                self.assertEqual(self.read('next_record',size=4),VARIABLES+self.s['draw_list']+30*self.s['draw_len'])
                self.call('draw_space');self.assert_viewport_only(self.buffer())
                self.assertEqual(self.models_drawn(),[obj for obj,flag in expected if not flag])

    def test_nearer_model_covers_offscreen_beam_and_farther_model_does_not(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for nearer in (False,True):
                self.boot(model);self.setup_ship(x=1100,y=330,z=3072);self.queue()
                emitter=self.ship;self.call('draw_ai_laser');beam=self.buffer();self.reset_buffer()
                self.setup_ship(x=0,z=1500 if nearer else 5000,index=1)
                self.obj('health',1);self.queue(shot=False);body=self.ship
                self.call('draw_space');actual=self.buffer()
                expected=bytearray(beam)
                if nearer:paint(expected,((x+160,8) for x in range(-10,11)),(0,65535,0,0),self.screen)
                self.assertEqual(actual,expected)
                self.assertEqual(self.models_drawn(),[body])
                self.assertEqual(self.entries(),[(emitter,65535),(body,0)] if nearer else [(body,0),(emitter,65535)])

    def test_late_queue_preserves_gameplay_registers_and_visibility(self):
        for model in (UC_CPU_M68K_M68000,UC_CPU_M68K_M68020):
            for shot in (False,True):
                self.boot(model);self.setup_ship();self.call('draw_object');self.obj('ai_laser',int(shot))
                saved={n:self.read(n) for n in ('visible','invisible','in_sights')}
                regs={**{f'd{i}':0xabcd1000+i for i in range(8)},**{f'a{i}':0x78000+i*32 for i in range(5)}}
                self.call('queue_ai_laser',**regs)
                for n,v in regs.items():self.assertEqual(self.cpu.reg_read(globals()['UC_M68K_REG_'+n.upper()]),v)
                self.assertEqual({n:self.read(n) for n in saved},saved)
                self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A5),self.ship)
                self.assertEqual(self.cpu.reg_read(UC_M68K_REG_A6),VARIABLES)
                self.assertEqual(self.read('random_seed',size=4),0xabcdef01)

if __name__=='__main__':unittest.main()
