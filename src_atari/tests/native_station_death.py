"""Real station impacts drain shields/energy, then run the full death animation."""
def make_suite(root, s):
    call=lambda n:f' jsr ${s[n]:x}\n'
    prefix=' include "common.def"\n include "macros.m68"\n'
    body=' clr.w csr_on(a6)\n clr.w display_clock(a6)\n'
    names=[]
    for case,view in enumerate((0,1),1):
        names.append(f'Moray station impacts and complete death animation from view {view}')
        body+=f' move.w #{case},qa_case\n move.w #3,player_ship(a6)\n'+call('ship_apply')
        body+=call('reset_system')+call('launch_system')+call('prepare_cockpit')+call('front_view' if view==0 else 'rear_view')
        body+=' move.w #20,speed(a6)\n clr.w game_over(a6)\n move.w #64,energy(a6)\n move.w #max_shield,front_shield(a6)\n clr.w cabin_temp(a6)\n move.w #48,altitude(a6)\n'
        body+=' bsr qa_guard_set\n'+call('swap_screen')+' bsr qa_guard_set\n'
        body+=f' move.w #100,d6\nqa_hits_{case}:\n move.w d6,-(sp)\n move.l #80,station_rec+xpos(a6)\n move.l #80,station_rec+ypos(a6)\n move.l #100,station_rec+zpos(a6)\n'
        body+=' move.w #1,qa_stage\n' +call('game_logic')+' bsr qa_guard_check\n move.w (sp)+,d6\n tst.w game_over(a6)\n'+f' bne.s qa_dead_{case}\n dbra d6,qa_hits_{case}\n bra fail\nqa_dead_{case}:\n'
        body+=' move.w #2,qa_stage\n cmp.w #no_energy,reason(a6)\n bne fail\n tst.w energy(a6)\n bne fail\n'
        body+=' move.w #3,qa_stage\n'+call('end_game')+' bsr qa_guard_check\n'+call('swap_screen')+' bsr qa_guard_check\n btst #in_use,objects+flags(a6)\n bne fail\n'
    return prefix,body,GUARDS+'qa_case: dc.w 0\nqa_stage: dc.w 0\n',names

GUARDS = """qa_guard_set:
 movem.l d0/d7/a0,-(sp)
 move.l scr_base(a6),a0
 move.w #y_size-1,d7
 lea y_top*160(a0),a0
qa_set_row:
 move.l #$55aa33cc,0(a0)
 move.l #$55aa33cc,4(a0)
 move.l #$55aa33cc,8(a0)
 move.l #$55aa33cc,12(a0)
 move.l #$55aa33cc,144(a0)
 move.l #$55aa33cc,148(a0)
 move.l #$55aa33cc,152(a0)
 move.l #$55aa33cc,156(a0)
 lea 160(a0),a0
 dbra d7,qa_set_row
 movem.l (sp)+,d0/d7/a0
 rts
qa_guard_check:
 movem.l d0/d7/a0,-(sp)
 move.l scr_base(a6),a0
 move.w #y_size-1,d7
 lea y_top*160(a0),a0
qa_check_row:
 cmp.l #$55aa33cc,0(a0)
 bne fail
 cmp.l #$55aa33cc,4(a0)
 bne fail
 cmp.l #$55aa33cc,8(a0)
 bne fail
 cmp.l #$55aa33cc,12(a0)
 bne fail
 cmp.l #$55aa33cc,144(a0)
 bne fail
 cmp.l #$55aa33cc,148(a0)
 bne fail
 cmp.l #$55aa33cc,152(a0)
 bne fail
 cmp.l #$55aa33cc,156(a0)
 bne fail
 lea 160(a0),a0
 dbra d7,qa_check_row
 movem.l (sp)+,d0/d7/a0
 rts
"""
