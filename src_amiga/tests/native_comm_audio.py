"""Independent single Paula receipt beep, VBL retriggering and finite lifetime."""
def make_suite(root,s):
    prefix=' include "common.def"\n include "macros.m68"\n'
    call=lambda n:f' jsr ${s[n]:x}\n'
    body='';names=[]
    def case(n):
        nonlocal body
        names.append(n);body+=f' move.w #{len(names)},qa_case\n'+call('quiet')+' bset #f_fx,user(a6)\n clr.w laser_audio_request(a6)\n'
    def arrival():return call('comm_arrival_sound')+call('sound')+' bsr qa_find\n cmp.w #1,d0\n bne fail\n'
    case('Identification retains its original effect; receipt has an independent voice')
    body+=' moveq #sfx_locked,d0\n'+call('fx')+call('sound')+' bsr qa_find_id\n cmp.w #1,d0\n bne fail\n'+arrival()+' bsr qa_find_id\n cmp.w #1,d0\n bne fail\n'
    for ui in (0,1):
        case(('UI' if ui else '3D')+' receipt starts one short tone')
        body+=f' move.w #{1-ui},cockpit_on(a6)\n'+arrival()
    case('Twelve rapid receipts restart one voice without stacking')
    body+=arrival()+' move.w #11,qa_repeat\nqa_again:\n move.w #2,(a0)\n'+arrival()+' cmp.w #2,(a0)\n bls fail\n subq.w #1,qa_repeat\n bpl qa_again\n'
    case('Receipt has fixed pitch and a bounded PAL/NTSC stop time')
    body+=arrival()+f' move.l a0,d1\n sub.l #${s["effect_ticks"]:x},d1\n lsl.w #3,d1\n lea ${s["effect_envelopes"]:x},a1\n adda.w d1,a1\n cmp.w #404,(a1)\n bne fail\n tst.w 4(a1)\n bne fail\n tst.w 10(a1)\n bne fail\n'
    body+=' ifne display_ntsc\n cmp.w #8,(a0)\n else\n cmp.w #6,(a0)\n endc\n bhi fail\n move.w #9,qa_repeat\nqa_expire:\n'+call('sound')+' subq.w #1,qa_repeat\n bpl qa_expire\n bsr qa_find\n tst.w d0\n bne fail\n'
    case('Identification during a receipt remains a separate voice')
    body+=arrival()+' moveq #sfx_locked,d0\n'+call('fx')+call('sound')+' bsr qa_find\n cmp.w #1,d0\n bne fail\n bsr qa_find_id\n cmp.w #1,d0\n bne fail\n'
    case('Ordinary identification repeats keep duplicate suppression')
    body+=' moveq #sfx_locked,d0\n'+call('fx')+call('sound')+' bsr qa_find_id\n cmp.w #1,d0\n bne fail\n move.w #2,(a0)\n moveq #sfx_locked,d0\n'+call('fx')+call('sound')+' bsr qa_find_id\n cmp.w #1,d0\n bne fail\n cmp.w #2,(a0)\n bhi fail\n'
    case('Effects OFF suppresses receipt audio')
    body+=' bclr #f_fx,user(a6)\n'+call('comm_arrival_sound')+call('sound')+' bsr qa_find\n tst.w d0\n bne fail\n'
    case('Music retains priority')
    body+=f' move.w #1,${s["music_playing"]:x}\n'+call('comm_arrival_sound')+f' clr.w ${s["music_playing"]:x}\n'+call('sound')+' bsr qa_find\n tst.w d0\n bne fail\n'
    case('Audio reset rejects newly published receipts')
    body+=f' st ${s["audio_resetting"]:x}\n'+call('comm_arrival_sound')+f' clr.w ${s["audio_resetting"]:x}\n'+call('sound')+' bsr qa_find\n tst.w d0\n bne fail\n'
    case('Quiet removes the receipt and its pending request')
    body+=arrival()+call('comm_arrival_sound')+call('quiet')+call('sound')+' bsr qa_find\n tst.w d0\n bne fail\n'+call('quiet')
    tail=f'''qa_case: dc.w 0
qa_repeat: dc.w 0
qa_find:
 moveq #sfx_comm,d3
 bra.s qa_scan
qa_find_id:
 moveq #sfx_locked,d3
qa_scan:
 moveq #0,d0
 lea ${s['effect_ticks']:x},a1
 lea ${s['effect_ids']:x},a2
 moveq #3,d7
.loop:
 tst.w (a1)
 beq.s .next
 cmp.b (a2),d3
 bne.s .next
 addq.w #1,d0
 move.l a1,a0
.next:
 addq.l #2,a1
 addq.l #1,a2
 dbra d7,.loop
 rts
'''
    return prefix,body,tail,names
