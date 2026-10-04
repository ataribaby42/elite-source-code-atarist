"""First flight frames after UI must be complete before they become visible."""


def make_suite(root, s):
    source = (root/'asm/planet.m68').read_text()
    prefix = ' include "common.def"\n include "macros.m68"\n'
    prefix += source[source.index('ps_features:'):source.index('    q_end_vars planet_surface')]+'\n'
    call = lambda name: ('' if name == 'wait_clear' and name not in s
                         else f' jsr ${s[name]:x}\n')
    body = ' bset #f_planets,user+1(a6)\n clr.w csr_on(a6)\n clr.w display_clock(a6)\n clr.w player_ship(a6)\n'
    body += call('ship_apply')+call('reset_system')+call('create_system')
    body += call('prepare_cockpit')+call('front_view')
    body += ' lea planet_rec(a6),a4\n move.w #8,obj_colour(a4)\n'+call('init_planet_surface')
    names = []
    views = ('front_view', 'rear_view', 'left_view', 'right_view')
    for page in ('local_chart', 'galactic_chart', 'status', 'inventory', 'data', 'options'):
        for view, routine in enumerate(views):
            for buffer in (1, 2):
                names.append(f'{page} to {routine}, buffer {buffer}: stable geography, hidden first frame, normal presentation')
                body += f' move.w #{len(names)},qa_case\n move.l screen{buffer}_ptr(a6),scr_base(a6)\n'
                body += call('clear_image')+call('swap_screen')+' bsr qa_save\n'
                body += call(page)+' bsr qa_compare\n'
                body += call(routine)+' bsr qa_compare\n'
                body += f' cmp.w #{view},view(a6)\n bne fail\n'
                body += ' bsr qa_front\n cmp.l scr_base(a6),d0\n beq fail\n move.l d0,qa_visible\n move.l scr_base(a6),qa_target\n move.l d0,a0\n bsr qa_hash\n movem.l d0-d1,qa_before_hash\n'
                body += call('clear_image')+call('wait_clear')
                body += ' lea planet_rec(a6),a5\n move.w #48*zoom_y,scr_radius(a5)\n clr.w centre_x(a5)\n clr.w centre_y(a5)\n clr.l this_xpos(a5)\n clr.l this_ypos(a5)\n move.l #100000,this_zpos(a5)\n move.w #planet,d0\n'
                body += call('draw_point')+call('draw_sight')
                body += ' bsr qa_front\n cmp.l qa_visible,d0\n bne fail\n move.l d0,a0\n bsr qa_hash\n cmp.l qa_before_hash,d0\n bne fail\n cmp.l qa_before_hash+4,d1\n bne fail\n'
                body += call('swap_screen')+' bsr qa_front\n cmp.l qa_target,d0\n bne fail\n cmp.l scr_base(a6),d0\n beq fail\n'
    for buffer in (1, 2):
        body += f' move.l screen{buffer}_ptr(a6),scr_base(a6)\n'+call('clear_image')+call('swap_screen')
        for routine in views:
            names.append(f'Existing 3D to {routine}, buffer {buffer}: keeps the hidden drawing target')
            body += f' move.w #{len(names)},qa_case\n move.l scr_base(a6),qa_target\n'
            body += call(routine)+' move.l scr_base(a6),d0\n cmp.l qa_target,d0\n bne fail\n bsr qa_front\n cmp.l scr_base(a6),d0\n beq fail\n'
    tail = '''qa_save:
 lea ps_map(a6),a0
 lea qa_saved(pc),a1
 move.w #ps_work_bytes/2-1,d7
qa_save_surface:
 move.w (a0)+,(a1)+
 dbra d7,qa_save_surface
 lea planet_rec(a6),a0
 move.w #obj_len/2-1,d7
qa_save_object:
 move.w (a0)+,(a1)+
 dbra d7,qa_save_object
 rts
qa_compare:
 lea ps_map(a6),a0
 lea qa_saved(pc),a1
 move.w #ps_work_bytes/2-1,d7
qa_compare_surface:
 move.w (a0)+,d0
 cmp.w (a1)+,d0
 bne fail
 dbra d7,qa_compare_surface
 lea planet_rec(a6),a0
 move.w #obj_len/2-1,d7
qa_compare_object:
 move.w (a0)+,d0
 cmp.w (a1)+,d0
 bne fail
 dbra d7,qa_compare_object
 rts
qa_hash:
 moveq #0,d0
 moveq #0,d1
 move.w #scr_bytes/4-1,d7
qa_hash_loop:
 move.l (a0)+,d2
 add.l d2,d0
 rol.l #1,d1
 eor.l d2,d1
 dbra d7,qa_hash_loop
 rts
qa_front:
'''
    # Read the actual presented buffer, independently of SCR_BASE.
    prefix += 'zoom_y: equ 1\nscr_bytes: equ 32000\n'
    tail += ' moveq #0,d0\n move.b $ffff8201,d0\n lsl.w #8,d0\n move.b $ffff8203,d0\n lsl.l #8,d0\n'
    tail += ' rts\nqa_case: dc.w 0\nqa_visible: dc.l 0\nqa_target: dc.l 0\nqa_before_hash: ds.l 2\nqa_saved: ds.b ps_work_bytes+obj_len\n even\n'
    return prefix, body, tail, names
