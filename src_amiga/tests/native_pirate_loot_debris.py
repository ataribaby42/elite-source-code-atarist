"""Native tests for scattered wreck cargo and player-caused destruction."""
from native_pirate_loot_theft import make_suite as helpers

def make_suite(root,s):
    prefix,_,tail,_=helpers(root,s)
    call=lambda n:f' jsr ${s[n]:x}\n'
    body=call('gen_prices');names=[]
    def emit(t):
        nonlocal body
        body+=t
    def case(n):
        names.append(n);emit(f' move.w #{len(names)},qa_case\n bsr qa_theft_world\n')
    def eq(v,f,size='w'):emit(f' cmp.{size} #{v},{f}\n bne fail\n')
    def victim(health=1):
        emit(f' lea objects+5*obj_len(a6),a4\n move.w #{health},health(a4)\n clr.w ai_front(a4)\n clr.w ai_aft(a4)\n clr.w ecm_fitted(a4)\n')
    def angry(slot):
        eq('log_attack',f'objects+{slot}*obj_len+logic(a6)')
        eq(0,f'objects+{slot}*obj_len+target(a6)','l')
        eq(0,f'objects+{slot}*obj_len+loot_mode(a6)')
        eq(0,f'objects+{slot}*obj_len+loot_target(a6)','l')
        eq(0,f'objects+{slot}*obj_len+pirate_truce(a6)')
        emit(f' btst #angry,objects+{slot}*obj_len+flags(a6)\n beq fail\n')
    def peaceful(slot):
        eq('loot_encounter',f'objects+{slot}*obj_len+loot_mode(a6)')
        eq('log_loot',f'objects+{slot}*obj_len+logic(a6)')
    def laser(power):
        emit(f' lea objects+5*obj_len(a6),a5\n clr.l this_xpos(a5)\n clr.l this_ypos(a5)\n move.l #4000,this_zpos(a5)\n st in_sights(a6)\n clr.w obj_hit(a6)\n move.w #1,hit_check(a6)\n move.w #{power},laser_power(a6)\n'+call('check_hit'))
    for weapon in ('laser','collision','player missile','NPC laser','NPC missile'):
        case(weapon+': real destruction path applies retaliation only to player-caused kills')
        victim()
        if weapon=='laser':laser(20)
        elif weapon=='collision':
            emit(' move.l a4,a5\n clr.l xpos(a5)\n move.l #20,ypos(a5)\n move.l #100,zpos(a5)\n clr.w computer_on(a6)\n clr.w controls_locked(a6)\n clr.w game_over(a6)\n move.w #255,energy(a6)\n move.w #255,front_shield(a6)\n move.w #255,aft_shield(a6)\n'+call('get_range')+call('collision'))
        elif weapon=='NPC laser':
            emit(' lea objects+9*obj_len(a6),a5\n move.l a4,target(a5)\n moveq #20,d0\n'+call('damage_target'))
        else:
            emit(' lea objects+10*obj_len(a6),a4\n move.w #missile,d0\n moveq #0,d4\n moveq #0,d5\n move.l #10990,d6\n bsr qa_create\n move.l a4,a5\n lea objects+5*obj_len(a6),a4\n move.l a4,target(a5)\n'+f' move.w #{"log_ai_missile" if weapon=="NPC missile" else "log_locked"},logic(a5)\n'+call('do_locked'))
        eq('log_exploding','objects+5*obj_len+logic(a6)')
        if weapon.startswith('NPC'):peaceful(3);peaceful(4)
        else:angry(3);angry(4)
        peaceful(7);eq(0,'npc_kill(a6)')
        eq(0,'hold+4(a6)','l')
        eq(0,'objects+5*obj_len+loot_owner(a6)','l')

    case('A nonlethal player laser hit does not report destruction')
    victim(100);laser(1);peaceful(3);peaceful(4)
    emit(' cmp.w #log_exploding,objects+5*obj_len+logic(a6)\n beq fail\n')

    case('A missed laser shot does not provoke cargo owners')
    victim();emit(' clr.w hit_check(a6)\n move.l a4,a5\n'+call('check_hit'));peaceful(3);peaceful(4)

    case('Destroying unrelated ordinary cargo does not provoke nearby scavengers')
    victim();emit(' clr.l loot_group(a4)\n');laser(20);peaceful(3);peaceful(4);peaceful(7)

    case('A destroyed member is ignored while a departing partner retaliates')
    emit(' lea objects+3*obj_len(a6),a4\n st npc_kill(a6)\n'+call('explode_object')+' clr.w npc_kill(a6)\n lea objects+4*obj_len(a6),a5\n'+call('loot_finish'))
    victim();laser(20)
    eq('log_exploding','objects+3*obj_len+logic(a6)');angry(4);peaceful(7)

    case('Repeated explosion notification cannot provoke a second time')
    victim();laser(20)
    for slot in (3,4):emit(f' move.w #loot_encounter,objects+{slot}*obj_len+loot_mode(a6)\n move.w #log_loot,objects+{slot}*obj_len+logic(a6)\n')
    emit(' lea objects+5*obj_len(a6),a4\n'+call('loot_destroyed'));peaceful(3);peaceful(4)

    case('After cargo destruction, a Viper still targets a pirate and the victim can retaliate')
    victim();laser(20)
    emit(' lea objects+9*obj_len(a6),a5\n move.w #9,this_obj(a6)\n move.w #9,retarget_slot(a6)\n'+call('retarget'))
    eq('log_attack','logic(a5)')
    emit(' move.l target(a5),a0\n cmpa.l #0,a0\n beq fail\n cmpa.l #no_target,a0\n beq fail\n cmp.w #typ_pirate,ship_type(a0)\n bne fail\n')

    case('128 real RNG groups: compact cargo, separated pirates, normalized independent headings and both speeds 1..2')
    emit(' clr.w qa_speed_mask\n clr.w qa_direction_mask\n move.w #128,qa_debris_groups\nqa_debris_loop:\n bsr qa_world\n'+call('spawn_loot_encounter')+' bsr qa_spawn_positions\n bsr qa_check_debris\n subq.w #1,qa_debris_groups\n bne qa_debris_loop\n')
    eq(3,'qa_speed_mask');eq(63,'qa_direction_mask')
    case('Actual cruise, spin and movement retain each container speed while following its own heading')
    emit(' bsr qa_world\n'+call('spawn_loot_encounter')+' lea objects+3*obj_len(a6),a5\n move.w velocity(a5),qa_original_speed\n move.l z_vector(a5),qa_original_direction\n move.w z_vector+4(a5),qa_original_direction+4\n movem.l xpos(a5),d4-d6\n movem.l d4-d6,qa_original_position\n move.w #16,qa_drift_steps\nqa_drift_loop:\n'+call('get_range')+call('do_logic')+call('orthogonal')+call('move')+' subq.w #1,qa_drift_steps\n bne qa_drift_loop\n move.w qa_original_speed,d0\n cmp.w velocity(a5),d0\n bne fail\n move.l xpos(a5),d0\n sub.l qa_original_position,d0\n move.l ypos(a5),d1\n sub.l qa_original_position+4,d1\n or.l d1,d0\n move.l zpos(a5),d1\n sub.l qa_original_position+8,d1\n or.l d1,d0\n beq fail\n')
    tail+='''qa_check_debris:
 lea objects+3*obj_len(a6),a5
 moveq #max_objects-4,d7
.member:
 btst #in_use,flags(a5)
 beq .next
 cmp.w #barrel,type(a5)
 bne .pirate
 lea objects+3*obj_len+xpos(a6),a0
 lea xpos(a5),a1
 moveq #2,d6
.coordinate:
 move.l (a1)+,d0
 sub.l (a0)+,d0
 bpl.s .abs
 neg.l d0
.abs:
 cmp.l #224,d0
 bhi fail
 dbra d6,.coordinate
 move.w velocity(a5),d0
 cmp.w #1,d0
 blo fail
 cmp.w #2,d0
 bhi fail
 cmp.w vel_max(a5),d0
 bne fail
 subq.w #1,d0
 move.w qa_speed_mask,d1
 bset d0,d1
 move.w d1,qa_speed_mask
 lea z_vector(a5),a0
 moveq #2,d6
 moveq #0,d3
 moveq #0,d2
.axis:
 move.w (a0)+,d0
 move.w d2,d1
 tst.w d0
 bpl.s .positive
 addq.w #1,d1
.positive:
 move.w qa_direction_mask,d4
 bset d1,d4
 move.w d4,qa_direction_mask
 muls.w d0,d0
 add.l d0,d3
 addq.w #2,d2
 dbra d6,.axis
 cmp.l #$0f000000,d3
 blo fail
 cmp.l #$11000000,d3
 bhi fail
 bra.s .next
.pirate:
 move.l xpos(a5),d0
 sub.l objects+3*obj_len+xpos(a6),d0
 bpl.s .pirate_abs
 neg.l d0
.pirate_abs:
 cmp.l #900,d0
 bne fail
 move.l ypos(a5),d0
 cmp.l objects+3*obj_len+ypos(a6),d0
 bne fail
 move.l zpos(a5),d0
 sub.l objects+3*obj_len+zpos(a6),d0
 cmp.l #1400,d0
 bne fail
.next:
 lea obj_len(a5),a5
 dbra d7,.member
 rts
qa_speed_mask: dc.w 0
qa_direction_mask: dc.w 0
qa_debris_groups: dc.w 0
qa_drift_steps: dc.w 0
qa_original_speed: dc.w 0
qa_original_direction: ds.b 6
qa_original_position: ds.l 3
'''
    return prefix,body,tail,names
