"""Exercise the actual PSG/Paula impact retrigger path, not a mocked sound call."""
def make_suite(root,s):
    prefix=' include "common.def"\n include "macros.m68"\n'
    amiga=root.name=='src_amiga'
    if not amiga:
        source=(root/'asm/sounds.m68').read_text()
        a=source.index('\trsset 0',source.index('* Define sound effects record.'))
        prefix+=source[a:source.index('\tq_end_vars sounds',a)]+'\n'
    out=[];names=[]
    call=lambda n:f' jsr ${s[n]:x}\n'
    def emit(t):out.append(t)
    def case(n):
        names.append(n);emit(f' move.w #{len(names)},qa_case\n'+call('quiet')+' bset #f_fx,user(a6)\n clr.w laser_audio_request(a6)\n')
    def eq(v,f,size='w'):emit(f' cmp.{size} #{v},{f}\n bne fail\n')
    def impact():emit(call('laser_impact_sound')+(call('sound') if amiga else '')+' bsr qa_find\n')
    case('First impact starts exactly one live shield voice')
    impact();eq(1,'d0')
    case('Twelve overlapping impacts restart the existing voice instead of suppressing or stacking them')
    impact();eq(1,'d0');emit(' move.l a0,qa_voice\n clr.w qa_count\nqa_repeat:\n')
    emit(' move.w #2,(a0)\n' if amiga else ' move.w #10,tone(a0)\n')
    impact();eq(1,'d0');emit(' cmpa.l qa_voice,a0\n bne fail\n')
    if amiga:emit(' cmp.w #2,(a0)\n bls fail\n')
    else:emit(' cmp.w #2,tone(a0)\n bhi fail\n')
    emit(' addq.w #1,qa_count\n cmp.w #12,qa_count\n blo qa_repeat\n')
    case('Effects OFF suppresses incoming impact audio')
    emit(' bclr #f_fx,user(a6)\n');impact();eq(0,'d0')
    case('Music suppresses incoming impact audio')
    music=f'${s["music_playing"]:x}' if amiga else 'sound_type(a6)'
    emit(f' move.w #1,{music}\n'+call('laser_impact_sound')+f' clr.w {music}\n'+(call('sound') if amiga else '')+' bsr qa_find\n');eq(0,'d0')
    case('Ordinary shield/ECM requests keep their previous duplicate suppression')
    impact();eq(1,'d0')
    if amiga:
        emit(' move.w #2,(a0)\n moveq #sfx_shields,d0\n'+call('fx')+call('sound')+' bsr qa_find\n cmp.w #1,d0\n bhi fail\n')
        # It may have expired in the real VBL, but cannot have been restarted.
        emit(f' lea ${s["effect_ticks"]:x},a0\n moveq #3,d7\nqa_old:\n cmp.w #2,(a0)+\n bhi fail\n dbra d7,qa_old\n')
    else:
        emit(' move.w #10,tone(a0)\n move.l a0,qa_voice\n lea objects(a6),a5\n clr.l zpos(a5)\n move.w #24,front_shield(a6)\n move.w #96,energy(a6)\n move.w #weapon_resistance_base,hull_missile_resistance(a6)\n moveq #1,d0\n'+call('reduce_missile_shields')+' move.l qa_voice,a0\n cmp.w #10,tone(a0)\n blo fail\n')
    case('Quiet clears active impacts and pending requests')
    impact();emit(call('laser_impact_sound')+call('quiet')+(call('sound') if amiga else '')+' bsr qa_find\n');eq(0,'d0')
    emit(call('quiet'))
    tail='qa_case: dc.w 0\nqa_count: dc.w 0\nqa_voice: dc.l 0\nqa_find:\n moveq #0,d0\n moveq #3,d7\n suba.l a0,a0\n'
    if amiga:
        tail+=f' lea ${s["effect_ticks"]:x},a1\n lea ${s["effect_ids"]:x},a2\n.loop:\n tst.w (a1)\n beq.s .next\n cmp.b #sfx_shields,(a2)\n bne.s .next\n addq.w #1,d0\n move.l a1,a0\n.next:\n addq.l #2,a1\n addq.l #1,a2\n dbra d7,.loop\n rts\n'
    else:
        tail+=' moveq #2,d7\n lea chan_1(a6),a1\n.loop:\n tst.w chn_active(a1)\n beq.s .next\n cmp.w #shields_fx,flag_ptr(a1)\n bne.s .next\n addq.w #1,d0\n move.l a1,a0\n.next:\n lea fx_len(a1),a1\n dbra d7,.loop\n rts\n'
    return prefix,''.join(out),tail,names
