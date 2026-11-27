"""Exhaustive energy boundaries and sustained live firing/recharge regressions."""
from native_ai_bursts import make_suite as burst_suite


def make_suite(root, s):
    prefix, _, tail, _ = burst_suite(root, s)
    out, names = [], []
    call = lambda name: f' jsr ${s[name]:x}\n'
    def emit(text): out.append(text)
    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n'
             ' clr.w game_frozen(a6)\n clr.w firing(a6)\n clr.w laser_pending(a6)\n'
             ' clr.w laser_temp(a6)\n clr.w laser_beam(a6)\n clr.w laser_flash(a6)\n'
             ' clr.w qe_shots\n move.w #199,qa_roll\n')
    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')
    def check_store(actual, field, debt):
        whole = (actual+65535)//65536
        eq(whole, field); eq(whole*65536-actual, debt)
    def patch(name, target):
        addr=s[name]
        emit(f' move.l ${addr:x},qa_saved_{name}\n move.w ${addr+4:x},qa_saved_{name}+4\n'
             f' move.w #$4ef9,${addr:x}\n move.l #{target},${addr+2:x}\n')
    def restore(name):
        addr=s[name]
        emit(f' move.l qa_saved_{name},${addr:x}\n move.w qa_saved_{name}+4,${addr+4:x}\n')
    def setup(power, model='cobra'):
        emit(f' move.w #{power},qa_power\n clr.w qa_npc\n move.w #1,qa_side\n'
             ' move.w #18,qa_length\n bsr qa_setup\n move.l a5,a4\n')
        emit(f' move.w #{model},type(a4)\n'+call('ship_ai_init'))
        emit(f' move.w #{power},ai_laser_loadout(a5)\n'
             ' move.w #-15000,z_vector+k(a5)\n')  # A visible miss avoids harming a victim.
    patch('random','qa_random')
    patch('ai_burst_length','qa_length_roll')
    patch('laser_impact_sound','qa_impact')

    case('Every 16-bit fraction below one point: exact drain, reserve and no healing')
    emit(' moveq #0,d6\nqe_fraction_loop:\n'
         ' move.w #1,qe_store\n move.w d6,qe_debt\n'
         ' lea qe_store,a0\n lea qe_debt,a1\n'+call('ship_laser_energy')+
         ' move.l #65536,d4\n sub.l d6,d4\n'
         ' cmp.w #16384,d6\n bhi.s qe_fraction_floor\n'
         ' sub.l #24576,d4\n bra.s qe_fraction_check\n'
         'qe_fraction_floor:\n cmp.w #40960,d6\n bhi.s qe_fraction_check\n'
         ' move.l #24576,d4\nqe_fraction_check:\n'
         ' moveq #0,d0\n move.w qe_store,d0\n swap d0\n'
         ' moveq #0,d1\n move.w qe_debt,d1\n sub.l d1,d0\n'
         ' cmp.l d4,d0\n bne fail\n addq.l #1,d6\n'
         ' cmp.l #65536,d6\n blo qe_fraction_loop\n')
    for field in ('qe_guard1','qe_guard2','qe_guard3'):
        eq('$5aa5',field)

    case('Every 16-bit fraction at five displayed points: exact AI 5% threshold')
    setup(9)
    emit(' moveq #0,d6\nqe_threshold_loop:\n'
         ' move.w #5,health(a5)\n move.w d6,ai_energy_fraction(a5)\n'
         ' clr.w ai_laser_cooldown(a5)\n clr.w ai_laser_burst(a5)\n'
         ' clr.l ai_laser_target(a5)\n'+call('ai_laser_tick')+call('ai_fire_laser')+
         ' move.w d6,d4\n cmp.w #13107,d6\n bhi.s qe_threshold_blocked\n'
         ' add.w #24576,d4\n cmp.w #1,ai_laser(a5)\n bne fail\n'
         ' bra.s qe_threshold_check\nqe_threshold_blocked:\n'
         ' tst.w ai_laser(a5)\n bne fail\n tst.w ai_laser_cooldown(a5)\n bne fail\n'
         'qe_threshold_check:\n cmp.w #5,health(a5)\n bne fail\n'
         ' cmp.w ai_energy_fraction(a5),d4\n bne fail\n'
         ' addq.l #1,d6\n cmp.l #65536,d6\n blo qe_threshold_loop\n')

    # Independent energy-budget model: exact remaining charge, never rounded bars.
    unit=65536; full=96*unit; shot_cost=3*unit//8; cutoff=(full+19)//20
    for ai in (False,True):
        weapons=((5,10),(9,6),(11,3)) if ai else tuple(enumerate((10,8,6,3)))
        for model,base_grade in (('cobra',1),('ferdelance',2)):
            for upgrade in (0,1,2):
                for weapon,interval in weapons:
                    frames=3600 if ai else 1200
                    case(f'{"AI" if ai else "Player"} {model}, laser {weapon}, unit {upgrade}: '
                         f'{frames} frames with wounded shields and ongoing recharge')
                    if ai:
                        setup(weapon,model)
                        emit(f' move.w #{upgrade},ai_energy_unit(a5)\n'
                             ' move.w #22,ai_front(a5)\n move.w #21,ai_aft(a5)\n'
                             f' move.w #{interval},qe_interval\n')
                    else:
                        emit(f' move.w #{weapon},laser_type(a6)\n move.w #{interval},laser_rate(a6)\n'
                             f' move.w #{base_grade},hull_recharge(a6)\n'
                             f' move.w #{upgrade},equip+energy_unit(a6)\n'
                             ' move.w #1,recharge_count(a6)\n move.w #22,front_shield(a6)\n'
                             ' move.w #21,aft_shield(a6)\n')
                    energy=full;front=22*unit;aft=21*unit;heat=0;cooldown=0;charge=1;shots=0
                    period={1:24,2:15,3:9,4:7}[base_grade+upgrade]
                    for frame in range(1,frames+1):
                        if ai:cooldown=max(0,cooldown-1)
                        if cooldown==0 and (energy>=cutoff if ai else heat<48):
                            energy=max(shot_cost,energy-shot_cost)
                            cooldown=interval;shots+=1
                            if not ai:heat+=1
                        charge-=1
                        if charge==0:
                            charge=period
                            energy=min(full,energy+unit)
                            if base_grade+upgrade>1 or energy==full:
                                front=min(24*unit,front+unit);aft=min(24*unit,aft+unit)
                            if not ai:heat=max(0,heat-1)
                        if not ai:cooldown=max(0,cooldown-1)
                        if frame%600:continue
                        label=f'qe_run_{len(names)}_{frame}'
                        emit(f' move.w #599,d6\n{label}:\n bsr qe_{"ai" if ai else "player"}_frame\n'
                             f' dbra d6,{label}\n')
                        if ai:
                            check_store(energy,'health(a5)','ai_energy_fraction(a5)')
                            eq(front//unit,'ai_front(a5)');eq(aft//unit,'ai_aft(a5)')
                            eq(cooldown,'ai_laser_cooldown(a5)');eq(charge,'ai_charge_count(a5)')
                        else:
                            check_store(energy,'energy(a6)','energy_fraction(a6)')
                            eq(front//unit,'front_shield(a6)');eq(aft//unit,'aft_shield(a6)')
                            eq(heat,'laser_temp(a6)');eq(cooldown,'firing(a6)');eq(charge,'recharge_count(a6)')
                        eq(shots,'qe_shots');eq(0,'game_over(a6)')

    for initial, fraction in ((95,1),(96,24576),(96,0)):
        for grade in (1,2,3,4):
            case(f'Player/AI recharge at {initial} minus {fraction}/65536, grade {grade}')
            setup(9)
            emit(f' move.w #{initial},health(a5)\n move.w #{initial},energy(a6)\n'
                 f' move.w #{fraction},ai_energy_fraction(a5)\n move.w #{fraction},energy_fraction(a6)\n'
                 ' move.w #20,ai_front(a5)\n move.w #20,front_shield(a6)\n'
                 f' move.w #{grade},ai_recharge(a5)\n move.w #{grade},hull_recharge(a6)\n'
                 ' clr.w equip+energy_unit(a6)\n move.w #1,recharge_count(a6)\n'+call('recharge'))
            after=min(full,initial*unit-fraction+unit)
            allowed=grade>1 or after==full
            for field,debt in (('health(a5)','ai_energy_fraction(a5)'),('energy(a6)','energy_fraction(a6)')):
                check_store(after,field,debt)
            eq(21 if allowed else 20,'front_shield(a6)');eq(21 if allowed else 20,'ai_front(a5)')

    case('Fractional laser energy then ECM/cloak drain remains lethal, without revival')
    emit(' move.w #1,energy(a6)\n move.w #40960,energy_fraction(a6)\n'
         ' moveq #1,d0\n'+call('reduce_energy')+call('recharge'))
    eq(0,'energy(a6)');eq(0,'energy_fraction(a6)')

    case('Player shot invalidates both cockpit buffers and each redraw consumes its own flag')
    emit(call('prepare_cockpit')+call('front_view')+
         ' move.w #2,laser_type(a6)\n move.w #6,laser_rate(a6)\n'
         ' move.w #$0300,f_energy(a6)\n'+call('fire'))
    eq(0,'f_energy(a6)')
    for screen,flags in ((1,1),(2,3)):
        emit(f' move.l screen{screen}_ptr(a6),scr_base(a6)\n'+call('update_inst'))
        eq(flags,'f_energy(a6)','b')

    restore('random');restore('ai_burst_length');restore('laser_impact_sound')
    tail+='''
qe_player_frame:
 movem.l d0-d7/a0-a5,-(sp)
 clr.w laser_pending(a6)
'''+call('fire')+''' tst.w laser_pending(a6)
 beq.s .charge
 addq.w #1,qe_shots
.charge:
 move.w laser_pending(a6),hit_check(a6)
'''+call('recharge')+call('draw_lasers')+''' movem.l (sp)+,d0-d7/a0-a5
 rts
qe_ai_frame:
 movem.l d0-d7/a0-a5,-(sp)
'''+call('ai_laser_tick')+call('ai_fire_laser')+''' tst.w ai_laser(a5)
 beq.s .charge
 move.w qe_interval,d0
 cmp.w ai_laser_cooldown(a5),d0
 bne.s .charge
 addq.w #1,qe_shots
.charge:
'''+call('ship_ai_recharge')+''' movem.l (sp)+,d0-d7/a0-a5
 rts
qe_guard1: dc.w $5aa5
qe_store: dc.w 0
qe_guard2: dc.w $5aa5
qe_debt: dc.w 0
qe_guard3: dc.w $5aa5
qe_shots: dc.w 0
qe_interval: dc.w 0
'''
    return prefix, ''.join(out), tail, names
