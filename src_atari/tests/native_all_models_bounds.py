"""Guarded rendering of every game mesh at near-camera and off-screen poses."""
from native_viewport_bounds import GUARDS


def make_suite(root, s):
    call = lambda name: f' jsr ${s[name]:x}\n'
    prefix = ' include "common.def"\n include "macros.m68"\n'
    body = ' clr.w csr_on(a6)\n clr.w display_clock(a6)\n clr.w player_ship(a6)\n'
    body += call('ship_apply')+call('reset_system')+call('prepare_cockpit')+call('front_view')
    body += ' clr.w qa_model\nqa_model_loop:\n'+call('clear_objects')+call('alloc_object')
    body += ' move.b #1,flags(a4)\n move.w qa_model(pc),type(a4)\n move.w #unit,x_vector+i(a4)\n move.w #unit,y_vector+j(a4)\n move.w #unit,z_vector+k(a4)\n'
    body += call('create_object')+' clr.w qa_rotation\nqa_rot_loop:\n move.w qa_rotation(pc),d0\n beq.s qa_render\n cmp.w #1,d0\n beq.s qa_render\n cmp.w #7,d0\n beq.s qa_render\n cmp.w #14,d0\n bne qa_rotate\nqa_render:\n lea qa_positions(pc),a0\n move.l a0,qa_next\nqa_position:\n move.l qa_next(pc),a0\n move.l (a0)+,d0\n cmp.l #$7fffffff,d0\n beq qa_rotate\n move.l d0,objects+xpos(a6)\n move.l (a0)+,objects+ypos(a6)\n move.l (a0)+,objects+zpos(a6)\n move.l a0,qa_next\n addq.w #1,qa_case\n bsr qa_fill\n'
    body += call('clear_image')+' lea objects(a6),a5\n clr.w this_obj(a6)\n'
    body += call('get_range')+call('draw_object')+call('draw_all')+' bsr qa_guard_check\n'+call('swap_screen')+' bra qa_position\nqa_rotate:\n lea objects(a6),a5\n move.w #71,d0\n'
    body += call('local_z_rotate')+' move.w #37,d0\n'+call('local_x_rotate')+call('orthogonal')
    body += ' addq.w #1,qa_rotation\n cmp.w #15,qa_rotation\n blo qa_rot_loop\n addq.w #1,qa_model\n cmp.w #max_obj_num,qa_model\n blo qa_model_loop\n'
    guards = GUARDS
    
    tail = guards+'qa_case: dc.w 0\nqa_model: dc.w 0\nqa_rotation: dc.w 0\nqa_next: dc.l 0\nqa_positions:\n'
    poses = [(x,y,z) for z in (1,200,800) for x,y in ((0,0),(0,-200),(-600,-50),(600,50),(0,600),(0,-600))]
    for pose in poses:
        tail += ' dc.l '+','.join(map(str,pose))+'\n'
    tail += ' dc.l $7fffffff\n'
    names = [f'model {model}, rotation {rot}, position {pose}' for model in range(43) for rot in (0,1,7,14) for pose in poses]
    return prefix,body,tail,names
