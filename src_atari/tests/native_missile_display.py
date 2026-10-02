"""Check missile HUD pixels, saturation and both display buffers on the real CPU."""


def make_suite(root, s):
    call = lambda name: f' jsr ${s[name]:x}\n'
    prefix = ' include "common.def"\n include "macros.m68"\n'
    prefix += 'QA_X equ 43\nQA_Y equ 186\nQA_STEP equ 12\nQA_LOGICAL_Y equ 185\nQA_OFFSET equ 184*160+16\nQA_ROWS equ 12\nQA_WORDS equ 20\nQA_STRIDE equ 160\n'
    names, out = [], []
    emit = out.append
    emit(' clr.w csr_on(a6)\n clr.w display_clock(a6)\n clr.w player_ship(a6)\n'+call('ship_apply')+call('prepare_cockpit'))
    for screen in (1, 2):
        emit(f' move.l screen{screen}_ptr(a6),scr_base(a6)\n'+call('update_inst'))
    capacities = [4, 1, 2, 2, 3, 3, 4, 6, 16, 1, 1, 0, 2]
    # Descending magazines include the >4 to 4 to 3 boundary and every empty slot.
    for ship, capacity in enumerate(capacities):
        for loaded in range(capacity, -1, -1):
            for state in ((0, 1, 2) if loaded else (0,)):
                names.append(f'Hull {ship}, capacity {capacity}, loaded {loaded}, state {state}: exact pixels in both buffers')
                emit(f' move.w #{len(names)},qa_case\n move.w #{ship},player_ship(a6)\n'+call('ship_apply'))
                emit(f' cmp.w #{capacity},hull_missiles(a6)\n bne fail\n move.w #{loaded},equip+missiles(a6)\n move.w #{state},missile_state(a6)\n')
                visible = min(loaded, 4)
                defs = ['empty' if i >= visible else ('installed' if i != visible-1 else ('installed', 'active', 'locked')[state]) for i in range(min(capacity, 4))]
                emit(' bsr qa_backdrop\n move.l screen1_ptr(a6),scr_base(a6)\n bsr qa_clear_reference\n')
                for slot, definition in enumerate(defs):
                    emit(f' lea qa_sprite,a4\n bset #dont_save,sp_flags(a4)\n move.w #QA_X+{slot}*QA_STEP,sp_xpos(a4)\n move.w #QA_Y,sp_ypos(a4)\n move.l #${s[definition+"_defn"]:x},data_ptr(a4)\n'+call('draw_sprite'))
                # Freeze all other instruments, invalidate only missiles.
                emit(' lea f_front(a6),a0\n moveq #13,d7\nqa_flags_'+str(len(names))+':\n move.w #$0300,(a0)+\n dbra d7,qa_flags_'+str(len(names))+'\n clr.w f_missiles(a6)\n move.l screen2_ptr(a6),scr_base(a6)\n'+call('update_inst')+' bsr qa_compare\n')
                # Dirty the first buffer again, then let its update bit refresh it.
                emit(' move.l screen1_ptr(a6),scr_base(a6)\n bsr qa_dirty\n'+call('update_inst')+' bsr qa_compare\n cmp.b #3,f_missiles(a6)\n bne fail\n')
                emit(f' cmp.w #{loaded},equip+missiles(a6)\n bne fail\n cmp.w #{state},missile_state(a6)\n bne fail\n cmp.w #{capacity},hull_missiles(a6)\n bne fail\n')
    tail = """qa_case: dc.w 0
qa_sprite: ds.b sprite_len
qa_backdrop:
 moveq #32,d0
 move.w #QA_LOGICAL_Y-1,d1
 moveq #1,d2
 moveq #80,d3
 moveq #12,d4
 moveq #white,d5
"""+call('block')+""" rts
qa_clear_reference:
 moveq #0,d5
 bra.s qa_field
qa_dirty:
 moveq #white,d5
qa_field:
 moveq #43,d0
 move.w #QA_LOGICAL_Y,d1
 moveq #0,d2
 moveq #48,d3
 moveq #8,d4
"""+call('block')+""" rts
qa_compare:

 move.l screen1_ptr(a6),a0
 move.l screen2_ptr(a6),a1
 lea QA_OFFSET(a0),a0
 lea QA_OFFSET(a1),a1
 move.w #QA_ROWS-1,d7
.row:
 move.w #QA_WORDS-1,d6
.word:
 move.w (a0)+,d0
 cmp.w (a1)+,d0
 bne fail
 dbra d6,.word
 lea QA_STRIDE-QA_WORDS*2(a0),a0
 lea QA_STRIDE-QA_WORDS*2(a1),a1
 dbra d7,.row
 rts
"""
    return prefix, ''.join(out), tail, names
