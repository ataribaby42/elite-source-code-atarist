"""Short PSG receipt tone, separate from identification, with bounded lifetime."""
def make_suite(root,s):
    prefix=' include "common.def"\n include "macros.m68"\n'
    source=(root/'asm/sounds.m68').read_text()
    start=source.index('\trsset 0',source.index('* Define sound effects record.'))
    prefix+=source[start:source.index('\tq_end_vars sounds',start)]+'\n'
    call=lambda n:f' jsr ${s[n]:x}\n'
    body='';names=[]
    def case(n):
        nonlocal body
        names.append(n);body+=f' move.w #{len(names)},qa_case\n'+call('quiet')+' bset #f_fx,user(a6)\n clr.w laser_audio_request(a6)\n'
    def arrival():return call('comm_arrival_sound')+' bsr qa_find\n cmp.w #1,d0\n bne fail\n'
    case('Identification keeps its original tone and a receipt uses a separate voice')
    body+=' moveq #sfx_locked,d0\n'+call('fx')+' bsr qa_find_id\n cmp.w #1,d0\n bne fail\n'+arrival()+' bsr qa_find_id\n cmp.w #1,d0\n bne fail\n'
    for ui in (0,1):
        case(('UI' if ui else '3D')+' receipt starts one short tone')
        body+=f' move.w #{1-ui},cockpit_on(a6)\n'+arrival()
    for frequency,ticks,label in ((2,5,'PAL'),(0,6,'NTSC')):
        case(label+' initializes exactly 100 ms of receipt audio')
        # Pause only the private emulator's audio IRQ entry while inspecting
        # the initial counter, then restore both code and video frequency.
        body+=f' move.w ${s["sound"]:x},qa_sound_opcode\n move.w #$4e75,${s["sound"]:x}\n move.b $ffff820a,qa_video\n move.b #{frequency},$ffff820a\n'
        body+=arrival()+f' cmp.w #{ticks},duration(a0)\n bne fail\n move.b qa_video,$ffff820a\n move.w qa_sound_opcode,${s["sound"]:x}\n'
    case('Twelve rapid receipts restart one voice without stacking')
    body+=arrival()+' move.w #11,qa_repeat\nqa_again:\n move.w #2,duration(a0)\n'+arrival()+' cmp.w #2,duration(a0)\n bls fail\n subq.w #1,qa_repeat\n bpl qa_again\n'
    case('Single fixed tone stops after five PAL or six NTSC services')
    body+=arrival()+' st hold_sound(a6)\n move.l a0,a5\n moveq #5,d6\n btst #1,$ffff820a\n bne.s qa_rate\n moveq #6,d6\nqa_rate:\n move.w d6,duration(a5)\n subq.w #2,d6\nqa_tick:\n'+call('comm_time')+' tst.w chn_active(a5)\n beq fail\n cmp.w #56,tone(a5)\n bne fail\n dbra d6,qa_tick\n'+call('comm_time')+' tst.w chn_active(a5)\n bne fail\n clr.w hold_sound(a6)\n'
    case('Identification during a receipt remains separate')
    body+=arrival()+' moveq #sfx_locked,d0\n'+call('fx')+' bsr qa_find\n cmp.w #1,d0\n bne fail\n bsr qa_find_id\n cmp.w #1,d0\n bne fail\n'
    case('Effects OFF suppresses receipt audio')
    body+=' bclr #f_fx,user(a6)\n'+call('comm_arrival_sound')+' bsr qa_find\n tst.w d0\n bne fail\n'
    case('Music retains priority')
    body+=' move.w #1,sound_type(a6)\n'+call('comm_arrival_sound')+' clr.w sound_type(a6)\n bsr qa_find\n tst.w d0\n bne fail\n'
    case('Held sound update rejects a receipt')
    body+=' st hold_sound(a6)\n'+call('comm_arrival_sound')+' clr.w hold_sound(a6)\n bsr qa_find\n tst.w d0\n bne fail\n'
    case('Quiet silences the receipt')
    body+=arrival()+call('quiet')+' bsr qa_find\n tst.w d0\n bne fail\n'+call('quiet')
    tail=f'''qa_case: dc.w 0
qa_repeat: dc.w 0
qa_sound_opcode: dc.w 0
qa_video: dc.w 0
qa_find:
 move.l #${s['comm_time']:x},d3
 moveq #56,d4
 moveq #11,d5
 bra.s qa_scan
qa_find_id:
 move.l #${s['mark_time']:x},d3
 moveq #50,d4
 moveq #12,d5
qa_scan:
 moveq #0,d0
 tst.w sound_type(a6)
 bpl.s .done
 lea chan_1(a6),a1
 moveq #2,d7
.loop:
 tst.w chn_active(a1)
 beq.s .next
 cmp.l service(a1),d3
 bne.s .next
 cmp.w tone(a1),d4
 bne fail
 cmp.w volume(a1),d5
 bne fail
 addq.w #1,d0
 move.l a1,a0
.next:
 lea fx_len(a1),a1
 dbra d7,.loop
.done:
 rts
'''
    return prefix,body,tail,names
