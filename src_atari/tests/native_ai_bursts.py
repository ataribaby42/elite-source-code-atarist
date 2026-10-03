"""Execute burst timing, uninterrupted raster output, hit and audio routing."""
from native_missile_collision import make_suite as base_suite

def make_suite(root,s):
    prefix,_,tail,_=base_suite(root,s)
    out=[];names=[]
    call=lambda n:f' jsr ${s[n]:x}\n'
    def emit(t):out.append(t)
    def case(n):
        names.append(n);emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n clr.w qa_sounds\n clr.w qa_draws\n clr.w qa_lengths\n move.w #199,qa_roll\n')
    def eq(v,f,size='w'):emit(f' cmp.{size} #{v},{f}\n bne fail\n')
    def patch(n,label):
        a=s[n];emit(f' move.l ${a:x},qa_saved_{n}\n move.w ${a+4:x},qa_saved_{n}+4\n move.w #$4ef9,${a:x}\n move.l #{label},${a+2:x}\n')
    def restore(n):
        a=s[n];emit(f' move.l qa_saved_{n},${a:x}\n move.w qa_saved_{n}+4,${a+4:x}\n')
    def setup(power,npc=False,rear=False,length=18):
        emit(f' move.w #{power},qa_power\n move.w #{int(npc)},qa_npc\n move.w #{-1 if rear else 1},qa_side\n move.w #{length},qa_length\n bsr qa_setup\n')
    patch('random','qa_random');patch('ai_burst_length','qa_length_roll');patch('laser_impact_sound','qa_impact')
    for power,interval in ((9,6),(11,3)):
        for length in range(6,19):
            for npc in (False,True):
                case(f'{power}-point laser, {length} steps, {"NPC" if npc else "player"}: exact visual lifetime and {interval}-step damage interval')
                setup(power,npc,length=length)
                label=f'qa_frames_{len(names)}'
                emit(f' moveq #0,d6\n{label}:\n bsr qa_reset_stores\n'+call('ai_laser_tick')+call('ai_fire_laser'))
                # Original mood roll must not be repeated during a held burst.
                emit(' clr.w mood(a5)\n tst.w ai_laser(a5)\n beq fail\n moveq #0,d0\n move.w d6,d0\n')
                emit(f' divu.w #{interval},d0\n swap d0\n tst.w d0\n bne.s {label}_visual\n')
                eq(2,'ai_laser(a5)');emit(f' moveq #{24-power},d0\n bra.s {label}_check\n{label}_visual:\n')
                eq(1,'ai_laser(a5)');emit(f' moveq #24,d0\n{label}_check:\n')
                field='objects+obj_len*3+ai_front(a6)' if npc else 'front_shield(a6)'
                emit(f' cmp.w {field},d0\n bne fail\n addq.w #1,d6\n cmp.w #{length},d6\n blo {label}\n')
                eq(1,'qa_lengths');eq(0 if npc else (length+interval-1)//interval,'qa_sounds')
                eq(power,'ai_laser_loadout(a5)')
                emit(call('ai_laser_tick')+call('ai_fire_laser'));eq(0,'ai_laser(a5)');eq(0,'ai_laser_burst(a5)')
    for npc in (False,True):
        for power,interval in ((5,10),(9,6),(11,3)):
            case(f'Rear shield, {power}-point laser, {"NPC" if npc else "player"}: first hit and next legal tick')
            setup(power,npc,rear=True)
            emit(call('ai_laser_tick')+call('ai_fire_laser'))
            field='objects+obj_len*3+ai_aft(a6)' if npc else 'aft_shield(a6)'
            eq(24-power,field)
            emit(f' moveq #{interval-1},d6\nqa_rear_{len(names)}:\n bsr qa_reset_stores\n'+call('ai_laser_tick')+call('ai_fire_laser')+f' dbra d6,qa_rear_{len(names)}\n')
            eq(24-power,field);eq(0 if npc else 2,'qa_sounds')
    for npc in (False,True):
        case(f'Pulse against {"NPC" if npc else "player"}: only steps 0/10/20 fire; no burst-length roll')
        setup(5,npc)
        label=f'qa_pulse_{len(names)}'
        emit(f' moveq #0,d6\n{label}:\n bsr qa_reset_stores\n'+call('ai_laser_tick')+call('ai_fire_laser')+' moveq #0,d0\n move.w d6,d0\n divu.w #10,d0\n swap d0\n tst.w d0\n'+f' bne.s {label}_quiet\n')
        eq(2,'ai_laser(a5)');emit(f' bra.s {label}_next\n{label}_quiet:\n');eq(0,'ai_laser(a5)')
        field='objects+obj_len*3+ai_front(a6)' if npc else 'front_shield(a6)'
        eq(24,field)
        emit(f'{label}_next:\n addq.w #1,d6\n cmp.w #21,d6\n blo {label}\n')
        eq(0,'qa_lengths');eq(0,'ai_laser_burst(a5)');eq(0 if npc else 3,'qa_sounds')
    for power in (9,11):
        for kind in ('distance miss','aim-cone miss'):
            case(f'{power}-point laser: {kind} stays visible for 18 steps, with no damage or impact sound')
            setup(power)
            if kind=='distance miss':emit(' clr.w qa_roll\n')
            else:emit(' move.w #-15000,z_vector+k(a5)\n')
            label=f'qa_miss_{len(names)}'
            emit(f' moveq #17,d6\n{label}:\n'+call('ai_laser_tick')+call('ai_fire_laser'))
            eq(1,'ai_laser(a5)');eq(24,'front_shield(a6)')
            emit(f' dbra d6,{label}\n');eq(0,'qa_sounds');eq(1,'qa_lengths')
    guards=[('aim lost',' clr.w z_vector+k(a5)\n',False),('out of range',' move.l #12289,target_range(a6)\n',False),
            ('cloak',' move.w #1,cloaking_on(a6)\n',False),('controls locked',' move.w #1,controls_locked(a6)\n',False),
            ('peel-off',' move.w #log_peel_off,logic(a5)\n',False),('explosion',' move.w #log_exploding,logic(a5)\n',False),
            ('target gone',' move.l #no_target,target(a5)\n',True),('target removed',' bset #remove,objects+obj_len*3+flags(a6)\n',True),
            ('target exploding',' move.w #log_exploding,objects+obj_len*3+logic(a6)\n',True),('target switched',' clr.l target(a5)\n',True)]
    for name,change,npc in guards:
        case('Active burst stops immediately: '+name);setup(11,npc)
        emit(call('ai_laser_tick')+call('ai_fire_laser')+change+call('ai_laser_tick')+call('ai_fire_laser'))
        eq(0,'ai_laser(a5)');eq(0,'ai_laser_burst(a5)');eq(0,'ai_laser_target(a5)','l')
    case('Player cloak and control lock do not interrupt NPC-versus-NPC bursts')
    setup(9,True);emit(call('ai_laser_tick')+call('ai_fire_laser')+' move.w #1,cloaking_on(a6)\n move.w #1,controls_locked(a6)\n'+call('ai_laser_tick')+call('ai_fire_laser'));eq(1,'ai_laser(a5)');eq(17,'ai_laser_burst(a5)')
    case('Timers advance without any rendering; cooldown survives an interrupted burst')
    setup(5);emit(call('ai_laser_tick')+call('ai_fire_laser')+' move.w #log_cruise,logic(a5)\n moveq #9,d6\nqa_offscreen:\n'+call('ai_laser_tick')+' dbra d6,qa_offscreen\n');eq(0,'ai_laser_cooldown(a5)');eq(0,'ai_laser(a5)')
    for routine in ('create_object','alloc_object','remove_object','clear_objects'):
        case(routine+': stale burst, cooldown and target are reset')
        setup(9);emit(' move.w #12,ai_laser_burst(a5)\n move.w #5,ai_laser_cooldown(a5)\n move.l #$12345678,ai_laser_target(a5)\n move.l a5,a4\n')
        if routine=='alloc_object':
            emit(' lea objects(a6),a4\n move.w #12,ai_laser_burst(a4)\n move.w #5,ai_laser_cooldown(a4)\n move.l #$12345678,ai_laser_target(a4)\n clr.b flags(a4)\n')
        emit(call(routine));eq(0,'ai_laser_burst(a4)');eq(0,'ai_laser_cooldown(a4)');eq(0,'ai_laser_target(a4)','l')
    case('Copied wingman cannot inherit an active burst or cooldown')
    setup(11);emit(call('ai_laser_tick')+call('ai_fire_laser')+' lea objects+obj_len*5(a6),a4\n'+call('copy_object')+call('create_object'));eq(0,'ai_laser_burst(a4)');eq(0,'ai_laser_cooldown(a4)');eq(18,'ai_laser_burst(a5)')
    # Real raster output, including the visual-only frames between damage ticks.
    for power in (9,11):
        for length in (6,12,18):
            case(f'Visible {power}-point beam: real viewport pixels on every one of {length} frames, none afterward')
            setup(power,length=length);emit(call('prepare_cockpit')+call('front_view'))
            emit(' lea objects+obj_len*4(a6),a5\n')
            label=f'qa_raster_{len(names)}'
            emit(f' moveq #{length-1},d6\n{label}:\n'+call('ai_laser_tick')+call('ai_fire_laser')+' clr.w mood(a5)\n movem.l d6/a5,-(sp)\n bsr qa_raster\n tst.w d4\n beq fail\n movem.l (sp)+,d6/a5\n'+f' dbra d6,{label}\n'+call('ai_laser_tick')+call('ai_fire_laser')+' bsr qa_raster\n tst.w d4\n bne fail\n')
    restore('ai_burst_length')
    case('All 256 raw RNG bytes: 6..18 uniform mapping and retry for 247..255')
    emit(' moveq #0,d6\nqa_bytes:\n move.w d6,qa_roll\n clr.w qa_draws\n move.w #1,qa_retry\n'+call('ai_burst_length')+' moveq #6,d2\n cmp.w #247,d6\n bhs.s qa_rejected\n moveq #0,d2\n move.w d6,d2\n divu.w #13,d2\n swap d2\n addq.w #6,d2\n cmp.w #1,qa_draws\n bne fail\n bra.s qa_rng_check\nqa_rejected:\n cmp.w #2,qa_draws\n bne fail\nqa_rng_check:\n cmp.w d2,d0\n bne fail\n addq.w #1,d6\n cmp.w #256,d6\n blo qa_bytes\n clr.w qa_retry\n')
    restore('random');restore('laser_impact_sound')
    for index,seed in enumerate((0x13579b00,0xabcdef00,0x10203000)):
        case(f'Real game RNG {seed:08X}: 13000 durations, every length within expected sampling tolerance')
        emit(f' move.l #${seed:x},random_seed(a6)\n lea qa_histogram+{index*26},a3\n move.w #12999,d6\nqa_sample_{index}:\n'+call('ai_burst_length')+f' cmp.w #6,d0\n blo fail\n cmp.w #18,d0\n bhi fail\n subq.w #6,d0\n add.w d0,d0\n addq.w #1,(a3,d0.w)\n dbra d6,qa_sample_{index}\n moveq #12,d6\nqa_sample_check_{index}:\n move.w (a3)+,d0\n cmp.w #880,d0\n blo fail\n cmp.w #1120,d0\n bhi fail\n dbra d6,qa_sample_check_{index}\n')
    tail+='''
qa_setup:
 clr.w cloaking_on(a6)
 clr.w approach(a6)
 lea objects+obj_len*3(a6),a4
 move.b #1,flags(a4)
 move.w #cobra,type(a4)
'''+call('create_object')+''' move.w #log_cruise,logic(a4)
 move.w #unit,z_vector+k(a4)
 move.l #2000,zpos(a4)
 move.l #2000,this_zpos(a4)
 lea objects+obj_len*4(a6),a4
 move.b #1,flags(a4)
 move.w #cobra,type(a4)
'''+call('create_object')+''' move.l a4,a5
 move.w qa_power,ai_laser_loadout(a5)
 move.w #log_attack,logic(a5)
 move.w #255,mood(a5)
 move.w #unit,x_vector+i(a5)
 move.w #unit,y_vector+j(a5)
 move.w #-unit,z_vector+k(a5)
 move.l #3000,zpos(a5)
 move.l #3000,obj_range(a5)
 move.l #3000,this_zpos(a5)
 move.l #3000,target_range(a6)
 clr.l target(a5)
 tst.w qa_npc
 beq.s .side
 lea objects+obj_len*3(a6),a0
 move.l a0,target(a5)
 move.l #1000,target_range(a6)
.side:
 tst.w qa_side
 bpl.s .ready
 move.w #unit,z_vector+k(a5)
 move.l #-3000,zpos(a5)
 tst.w qa_npc
 beq.s .ready
 move.l #1000,zpos(a5)
.ready:
 clr.w qa_draws
 clr.w qa_lengths
 clr.w qa_sounds
 rts
qa_reset_stores:
 move.w #24,front_shield(a6)
 move.w #24,aft_shield(a6)
 move.w #96,energy(a6)
 move.w #24,objects+obj_len*3+ai_front(a6)
 move.w #24,objects+obj_len*3+ai_aft(a6)
 move.w #96,objects+obj_len*3+health(a6)
 move.w #-1,shields_fx(a6) ; every incoming hit must still request fresh audio
 rts
qa_random:
 addq.w #1,qa_draws
 move.w qa_roll,d0
 tst.w qa_retry
 beq.s .done
 cmp.w #1,qa_draws
 beq.s .done
 moveq #0,d0
.done:
 move.l #$deadbeef,d1
 rts
qa_length_roll:
 addq.w #1,qa_lengths
 move.w qa_length,d0
 rts
qa_impact:
 addq.w #1,qa_sounds
 rts
qa_saved_random: ds.b 6
qa_saved_ai_burst_length: ds.b 6
qa_saved_laser_impact_sound: ds.b 6
qa_histogram: ds.w 39
qa_length: dc.w 18
qa_lengths: dc.w 0
qa_sounds: dc.w 0
qa_roll: dc.w 199
qa_retry: dc.w 0
qa_draws: dc.w 0
qa_power: dc.w 9
qa_npc: dc.w 0
qa_side: dc.w 1
qa_raster:
'''+call('clear_image')+(call('wait_clear') if root.name=='src_amiga' else '')
    if root.name=='src_amiga':
        address='y_top*row_stride+x_left/8';stride='row_stride-x_size/8';step=2;planes=['0','plane1','plane2','plane3']
    else:
        address='y_top*160+x_left/2';stride='160-x_size/2';step=8;planes=['0','2','4','6']
    # Explicitly blank the private viewport; do not rely on asynchronous clears.
    for action in ('blank','scan'):
        if action=='scan':tail+=call('draw_ai_laser')+' moveq #0,d4\n'
        tail+=f' move.l scr_base(a6),a0\n lea {address}(a0),a0\n move.w #y_size-1,d7\n.{action}_row:\n move.w #x_size/16-1,d3\n.{action}_word:\n'
        for offset in planes:tail+=(f' clr.w {offset}(a0)\n' if action=='blank' else f' or.w {offset}(a0),d4\n')
        tail+=f' addq.l #{step},a0\n dbra d3,.{action}_word\n lea {stride}(a0),a0\n dbra d7,.{action}_row\n'
    tail+=' rts\n'
    return prefix,''.join(out),tail,names
