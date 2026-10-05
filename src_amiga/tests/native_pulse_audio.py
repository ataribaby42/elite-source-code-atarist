"""Check Pulse's real Paula DMA tail at hardware frame boundaries.

Run with cycle-exact emulation and sound_output=interrupts (or normal), so Paula
raises the block-complete interrupt even though the test emits no host audio.
"""


def make_suite(root, s):
    call = lambda name: f' jsr ${s[name]:x}\n'
    names = []
    body = [' move.l a6,-(sp)\n movea.l $4,a6\n jsr -120(a6)\n movea.l (sp)+,a6\n']

    def case(name):
        names.append(name)
        body.append(f' move.w #{len(names)},qa_case\n'+call('quiet')+
                    ' bset #f_fx,user(a6)\n clr.w condition(a6)\n'
                    ' clr.w torus_on(a6)\n clr.w docked(a6)\n'
                    ' clr.w game_over(a6)\n clr.w cockpit_on(a6)\n')

    # The first DMA interrupt is the block's startup request. Clear it only
    # after observing it; a later request means the 1,580-byte sample wrapped.
    for repeat in range(3):
        case(f'Pulse shot {repeat+1}: nine hardware frames, no repeated PCM attack, DMA muted on expiry')
        body.append(' bsr qa_frame\n move.w #$80,$dff09c\n moveq #sfx_laser,d0\n'+
                    call('fx')+call('sound')+
                    f' cmp.b #sfx_laser,${s["effect_ids"]:x}\n bne fail\n'
                    f' cmp.w #9,${s["effect_ticks"]:x}\n bne fail\n'
                    ' move.w $dff002,d0\n and.w #1,d0\n beq fail\n'
                    ' move.w #32,d7\n'
                    f'qa_dma_start_{repeat}:\n'
                    ' move.w $dff01e,d0\n and.w #$80,d0\n'
                    f' bne.s qa_dma_started_{repeat}\n'
                    ' bsr qa_line\n'
                    f' dbra d7,qa_dma_start_{repeat}\n bra fail\n'
                    f'qa_dma_started_{repeat}:\n move.w #$80,$dff09c\n'
                    ' move.w #8,qa_left\n'
                    f'qa_play_{repeat}:\n bsr qa_frame\n'
                    ' move.w $dff01e,d0\n and.w #$80,d0\n bne fail\n'+
                    call('sound')+
                    f' subq.w #1,qa_left\n bpl qa_play_{repeat}\n'
                    f' tst.w ${s["effect_ticks"]:x}\n bne fail\n'
                    f' tst.w ${s["effect_envelopes"]+8:x}\n bne fail\n'
                    ' move.w $dff002,d0\n and.w #1,d0\n bne fail\n'
                    # DMA-off may raise a final interrupt for the held data
                    # word. Only interrupts while DMA is running imply a wrap.
                    ' bsr qa_frame\n move.w $dff002,d0\n and.w #1,d0\n bne fail\n')

    case('Effects OFF does not start Pulse DMA')
    body.append(' bclr #f_fx,user(a6)\n moveq #sfx_laser,d0\n'+call('fx')+call('sound')+
                f' tst.w ${s["effect_ticks"]:x}\n bne fail\n'
                ' move.w $dff002,d0\n and.w #15,d0\n bne fail\n')
    body.append(call('quiet')+' move.l a6,-(sp)\n movea.l $4,a6\n jsr -126(a6)\n movea.l (sp)+,a6\n')
    tail = '''qa_case: dc.w 0
qa_left: dc.w 0
qa_line:
 move.b $dff006,d0
.wait:
 cmp.b $dff006,d0
 beq.s .wait
 rts
qa_frame:
 move.l $dff004,d0
 and.l #$1ff00,d0
 cmp.l #$2000,d0
 beq.s qa_frame
.wait:
 move.l $dff004,d0
 and.l #$1ff00,d0
 cmp.l #$2000,d0
 bne.s .wait
 rts
'''
    return ' include "common.def"\n include "macros.m68"\n', ''.join(body), tail, names
