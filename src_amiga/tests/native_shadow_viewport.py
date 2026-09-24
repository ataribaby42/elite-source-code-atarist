"""Compare every presented shadow frame with direct rendering of the same scene."""
import random


def make_suite(root,s):
    call=lambda name:f' jsr ${s[name]:x}\n'
    prefix=' include "common.def"\n include "macros.m68"\n'
    prefix+=f'qa_shadow_base: equ ${s["_shadow_base"]:x}\nqa_shadow_live: equ ${s["_shadow_live"]:x}\nqa_reference: equ ${s["_reference"]:x}\n'
    body=' clr.w csr_on(a6)\n clr.w display_clock(a6)\n clr.w player_ship(a6)\n'
    body+=call('ship_apply')+call('reset_system')+call('prepare_cockpit')+call('front_view')
    body+=' lea qa_cases(pc),a0\n move.l a0,qa_next\nqa_loop:\n move.l qa_next(pc),a3\n tst.w (a3)\n bmi qa_complete\n addq.w #1,qa_case\n bsr qa_setup\n'
    body+=' move.l scr_base(a6),qa_screen\n move.l qa_shadow_base,qa_saved_shadow\n clr.l qa_shadow_base\n clr.w qa_shadow_live\n move.l #qa_reference,scr_base(a6)\n move.l #qa_reference,a0\n move.w #scr_bytes/4-1,d7\n bsr qa_fill\n'
    body+=call('clear_image')+' bsr qa_draw\n'
    body+=' move.l qa_saved_shadow(pc),qa_shadow_base\n move.l qa_screen(pc),scr_base(a6)\n move.l qa_screen(pc),a0\n adda.l #view_bytes,a0\n move.w #(scr_bytes-view_bytes)/4-1,d7\n bsr qa_fill\n'
    body+=call('clear_image')+' bsr qa_draw\n'+call('swap_screen')
    body+=' move.l qa_screen(pc),a0\n move.l #qa_reference,a1\n move.w #scr_bytes/4-1,d7\nqa_compare:\n move.l (a0)+,d0\n cmp.l (a1)+,d0\n bne fail\n dbra d7,qa_compare\n add.l #24,qa_next\n bra qa_loop\nqa_complete:\n'
    tail='''qa_fill:
 move.l #$55aa33cc,(a0)+
 dbra d7,qa_fill
 rts
qa_setup:
 move.l qa_next(pc),a3
 cmp.w #2,(a3)
 bne.s qa_setup_done
'''+call('clear_objects')+call('alloc_object')+''' move.l qa_next(pc),a3
 move.b #1,flags(a4)
 move.w 2(a3),type(a4)
 move.w #unit,x_vector+i(a4)
 move.w #unit,y_vector+j(a4)
 move.w #unit,z_vector+k(a4)
'''+call('create_object')+''' move.l qa_next(pc),a3
 move.l 4(a3),objects+xpos(a6)
 move.l 8(a3),objects+ypos(a6)
 move.l 12(a3),objects+zpos(a6)
 lea objects(a6),a5
 move.w #71,d0
'''+call('local_z_rotate')+' move.w #37,d0\n'+call('local_x_rotate')+call('orthogonal')+'''qa_setup_done:
 rts
qa_draw:
 moveq #15,d0
'''+call('set_colour')+''' move.l qa_next(pc),a3
 move.w (a3),d0
 beq.s qa_line
 cmp.w #1,d0
 beq.s qa_text
 lea objects(a6),a5
 clr.w this_obj(a6)
'''+call('get_range')+call('draw_object')+call('draw_all')+''' rts
qa_line:
 movem.w 2(a3),d0-d3
'''+call('c_line')+''' rts
qa_text:
 move.w 2(a3),text_row(a6)
 move.l 4(a3),a0
'''+call('disp_message')+' moveq #15,d0\n'+call('text_blatt')+''' rts
qa_case: dc.w 0
qa_next: dc.l 0
qa_screen: dc.l 0
qa_saved_shadow: dc.l 0
qa_cases:
'''
    g=s['_geometry'];rng=random.Random(20260924)
    extremes=[-32768,-16000,g['x_min'],g['x_max'],g['y_min'],g['y_max'],-1,0,1,16000,32767]
    lines=[tuple(rng.choice(extremes) for _ in range(4)) for _ in range(192)]
    lines += [(-32768,y,32767,y) for y in (g['y_min'],g['y_min']+1,0,1,g['y_max']-1,g['y_max'])]
    # Repeated and then empty frames exercise unchanged, changed and cleared pieces.
    lines += [(0,0,15,1)]*6 + [(32767,32767,32767,32767)]*6
    names=[];strings=''
    for coords in lines:
        tail+=' dc.w 0,'+','.join(map(str,coords))+'\n ds.b 14\n'
        names.append('shadow line '+str(coords))
    for row in (0,g['no_rows']-1):
        for message in (b'',b'GAME OVER',b'X'*39,b'X'*40,b'X'*41,b'X'*127,b'X'*255,b'AB\rCD\nEF'):
            label='qa_text_'+str(len(names))
            tail+=f' dc.w 1,{row}\n dc.l {label}\n ds.b 16\n'
            strings+=label+': dc.b '+','.join(map(str,message+b'\0'))+'\n even\n'
            names.append(f'shadow text row {row}, length {len(message)}')
    for model in range(43):
        for x,y,z in ((0,-200,200),(0,0,800)):
            tail+=f' dc.w 2,{model}\n dc.l {x},{y},{z}\n ds.b 8\n'
            names.append(f'shadow model {model}, position {(x,y,z)}')
    tail+=' dc.w -1\n'+strings
    return prefix,body,tail,names
