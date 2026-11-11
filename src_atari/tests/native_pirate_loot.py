"""Native 68000 salvage behaviour, pursuit, reservation and faction regressions."""
def make_suite(root,s):
    prefix=' include "common.def"\n include "macros.m68"\n'
    src=(root/'asm/combat.m68').read_text()
    prefix+=src[src.index('\tq_vars combat'):src.index('\tq_end_vars combat')]+'\n'
    names=[];parts=[]
    call=lambda name:f' jsr ${s[name]:x}\n'
    def emit(t):parts.append(t)
    def case(n):
        names.append(n);emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n')
    def eq(v,f,size='w'):emit(f' cmp.{size} #{v},{f}\n bne fail\n')
    def obj(slot,model='krait',x=0,y=0,z=10000):
        emit(f' lea objects+{slot}*obj_len(a6),a4\n move.w #{model},d0\n move.l #{x},d4\n move.l #{y},d5\n move.l #{z},d6\n bsr qa_create\n')
    def pirate(slot=3,mode='loot_encounter'):
        emit(f' lea objects+{slot}*obj_len(a6),a5\n move.w #{mode},loot_mode(a5)\n move.w #log_loot,logic(a5)\n')
    def retarget(slot=3):
        emit(f' lea objects+{slot}*obj_len(a6),a5\n move.w #{slot},this_obj(a6)\n move.w #{slot},retarget_slot(a6)\n'+call('retarget'))
    def select():
        obj(3);obj(5,'barrel',z=11000);pirate();retarget()
        emit(' lea objects+5*obj_len(a6),a0\n cmpa.l loot_target(a5),a0\n bne fail\n')
    r=s['rand']
    emit(f' move.l ${r:x},qa_saved_rand\n move.w ${r+4:x},qa_saved_rand+4\n move.w #$4ef9,${r:x}\n move.l #qa_rand,${r+2:x}\n')
    case('Real destruction tags dropped cargo and arms only pirates targeting the victim')
    obj(3);obj(4,'cobra',z=11000);obj(7,'viper');obj(8)
    emit(' lea objects+4*obj_len(a6),a4\n move.l a4,objects+3*obj_len+target(a6)\n move.l a4,objects+7*obj_len+target(a6)\n move.l #no_target,objects+8*obj_len+target(a6)\n move.w #1,no_canisters(a4)\n move.w #1,cargo_type(a4)\n st npc_kill(a6)\n'+call('explode_object'))
    eq('loot_pending','objects+3*obj_len+loot_mode(a6)');eq(0,'objects+7*obj_len+loot_mode(a6)');eq(0,'objects+8*obj_len+loot_mode(a6)')
    emit(' move.w #2,qa_small_left\n move.w #1,qa_small_first\n'+call('release_cargo')+' clr.w qa_small_left\n clr.w npc_kill(a6)\n')
    eq(1,'obj_ctr+barrel(a6)','b')
    emit(' lea objects(a6),a0\n moveq #max_objects-1,d1\nqa_find_drop:\n cmp.w #barrel,type(a0)\n beq.s qa_drop_found\n lea obj_len(a0),a0\n dbra d1,qa_find_drop\n bra fail\nqa_drop_found:\n move.l objects+4*obj_len+radio_instance(a6),d0\n cmp.l loot_origin(a0),d0\n bne fail\n')
    case('All 100 probability outcomes select exactly 50 times, with no frame rerolls')
    emit(' clr.w qa_roll\n clr.w qa_selected\nqa_probability:\n bsr qa_wreck\n st qa_force100\n clr.w qa_roll_calls\n'+call('retarget')+' clr.w qa_force100\n cmp.w #1,qa_roll_calls\n bne fail\n cmp.w #50,qa_roll\n bhs.s qa_declined\n addq.w #1,qa_selected\n cmp.w #loot_wreck,loot_mode(a5)\n bne fail\n bra.s qa_probability_next\nqa_declined:\n tst.w loot_mode(a5)\n bne fail\n'+call('retarget')+call('retarget')+' cmp.w #1,qa_roll_calls\n bne fail\nqa_probability_next:\n addq.w #1,qa_roll\n cmp.w #100,qa_roll\n blo qa_probability\n')
    eq(50,'qa_selected')
    case('Without another hostile target, salvage is certain and consumes no 50 percent roll')
    emit(' bsr qa_wreck\n move.w #16,pirate_truce(a5)\n st qa_force100\n clr.w qa_roll_calls\n'+call('retarget')+' clr.w qa_force100\n')
    eq('loot_wreck','loot_mode(a5)');eq(0,'qa_roll_calls');eq('no_target','target(a5)','l')
    case('No cargo from this wreck: no random draw and the next enemy is attacked')
    emit(' bsr qa_wreck\n clr.l objects+5*obj_len+loot_origin(a6)\n st qa_force100\n clr.w qa_roll_calls\n'+call('retarget')+' clr.w qa_force100\n')
    eq(0,'loot_mode(a5)');eq(0,'qa_roll_calls');eq('log_attack','logic(a5)')
    case('Only the victim cargo is selected even when unrelated loot is closer')
    emit(' bsr qa_wreck\n move.w #16,pirate_truce(a5)\n')
    obj(6,'barrel',z=10200);retarget()
    emit(' lea objects+5*obj_len(a6),a0\n cmpa.l loot_target(a5),a0\n bne fail\n')
    case('Freshly dropped cargo is selectable before its first main-loop range update')
    emit(' bsr qa_wreck\n move.w #16,pirate_truce(a5)\n move.l #$ff000000,objects+5*obj_len+obj_range(a6)\n move.w #123,approach(a6)\n'+call('retarget'))
    eq('loot_wreck','loot_mode(a5)');eq(123,'approach(a6)')
    case('A diagonal cargo candidate remains reachable rather than repeatedly losing its reservation')
    obj(3);obj(5,'barrel',x=3500,y=3500,z=13500);pirate();retarget()
    emit(call('do_logic'));emit(' tst.l loot_target(a5)\n beq fail\n')
    case('Two pirates and one barrel: one owner, one quiet unarmed waiter')
    select();obj(4);pirate(4);retarget(4)
    eq(0,'loot_target(a5)','l');eq('loot_encounter','loot_mode(a5)');eq('no_target','target(a5)','l')
    emit(' lea objects+3*obj_len(a6),a0\n cmpa.l objects+5*obj_len+loot_owner(a6),a0\n bne fail\n')
    case('Two pirates reserve different barrels and never switch to the player while collecting')
    select();obj(6,'barrel',x=500,z=11000);obj(4);pirate(4);retarget(4)
    emit(' lea objects+6*obj_len(a6),a0\n cmpa.l loot_target(a5),a0\n bne fail\n')
    for slot in (3,4):
        retarget(slot);eq('log_loot','logic(a5)');eq('no_target','target(a5)','l')
    for event in ('hit','destroyed','removed','recycled'):
        case('Reservation transfers after owner is '+event)
        select();obj(4);pirate(4)
        emit(' lea objects+3*obj_len(a6),a4\n')
        if event=='hit':emit(' suba.l a0,a0\n'+call('loot_hit'))
        elif event=='destroyed':emit(' st npc_kill(a6)\n'+call('explode_object')+' clr.w npc_kill(a6)\n')
        elif event=='removed':emit(' bset #remove,flags(a4)\n'+call('remove_objects'))
        else:emit(call('create_object'))
        retarget(4)
        emit(' lea objects+5*obj_len(a6),a0\n cmpa.l loot_target(a5),a0\n bne fail\n')
    for event in ('removed','destroyed','recycled_barrel','recycled_ship','special'):
        case('Collector rejects cargo that was '+event)
        select();emit(' lea objects+5*obj_len(a6),a4\n')
        if event=='removed':emit(' bset #remove,flags(a4)\n')
        elif event=='destroyed':emit(' st npc_kill(a6)\n'+call('explode_object')+' clr.w npc_kill(a6)\n')
        elif event=='special':emit(' move.w #-1,cargo_type(a4)\n')
        else:
            if event=='recycled_ship':emit(' move.w #viper,type(a4)\n')
            emit(call('create_object'))
        emit(' lea objects+3*obj_len(a6),a5\n'+call('do_logic'))
        eq(0,'loot_target(a5)','l');eq(0,'loot_count(a5)')
    for mode in ('loot_pending','loot_wreck','loot_encounter','loot_departing'):
        case('Police Viper still targets a pirate in state '+mode)
        obj(3);pirate(3,mode);obj(4,'viper',z=10500)
        retarget(4)
        eq('log_attack','logic(a5)')
        emit(' lea objects+3*obj_len(a6),a0\n cmpa.l target(a5),a0\n bne fail\n')
    case('Actual Viper laser damage ends collection and selects the attacking Viper')
    select();obj(4,'viper',z=10500)
    emit(' lea objects+4*obj_len(a6),a5\n lea objects+3*obj_len(a6),a0\n move.l a0,target(a5)\n moveq #1,d0\n'+call('damage_target'))
    eq(0,'objects+3*obj_len+loot_mode(a6)');eq(0,'objects+5*obj_len+loot_owner(a6)','l')
    emit(' cmpa.l objects+3*obj_len+target(a6),a5\n bne fail\n')
    case('Actual player laser hit cancels collection and revokes Scramble ID neutrality')
    select();emit(' move.w #17,pirate_truce(a5)\n st in_sights(a6)\n clr.w obj_hit(a6)\n move.w #1,hit_check(a6)\n move.w #1,laser_power(a6)\n clr.l this_xpos(a5)\n clr.l this_ypos(a5)\n move.l #4000,this_zpos(a5)\n'+call('check_hit'))
    eq(0,'loot_mode(a5)');eq(0,'pirate_truce(a5)');eq(0,'target(a5)','l');eq(0,'objects+5*obj_len+loot_owner(a6)','l')
    emit(' btst #angry,flags(a5)\n beq fail\n')
    for ai in (False,True):
        case(('AI' if ai else 'Player')+' actual missile launch interrupts collection before impact')
        select()
        if ai:
            obj(4,'viper',z=14000);emit(' lea objects+4*obj_len(a6),a5\n lea objects+3*obj_len(a6),a0\n move.l a0,target(a5)\n move.w #2,no_missiles(a5)\n'+call('launch_missile'))
        else:emit(' move.l a5,target_ptr(a6)\n move.w #2,missile_state(a6)\n move.w #2,equip+missiles(a6)\n'+call('fire_missile'))
        eq(0,'objects+3*obj_len+loot_mode(a6)');eq(0,'objects+5*obj_len+loot_owner(a6)','l');eq(1,'obj_ctr+missile(a6)','b')
    case('Only the attacked member abandons the salvage encounter')
    select();obj(4);pirate(4);retarget(4)
    emit(' lea objects+3*obj_len(a6),a4\n suba.l a0,a0\n'+call('loot_hit'))
    eq(0,'objects+3*obj_len+loot_mode(a6)');eq('loot_encounter','objects+4*obj_len+loot_mode(a6)')
    retarget(4);emit(' tst.l loot_target(a5)\n beq fail\n')
    case('A peacefully departing scavenger still retaliates when attacked')
    obj(3);pirate(3,'loot_departing');emit(' move.w #log_cruise,logic(a5)\n move.l a5,a4\n suba.l a0,a0\n'+call('loot_hit'))
    eq('log_attack','logic(a5)');eq(0,'loot_mode(a5)');eq(0,'target(a5)','l')
    case('Player scoops a reserved barrel using unchanged exact-payload accounting')
    select();emit(' lea objects+5*obj_len(a6),a5\n move.l #100,zpos(a5)\n move.l #-20,ypos(a5)\n move.w #1,equip+fuel_scoop(a6)\n move.w #1,cargo_type(a5)\n move.l #123456,cargo_mass(a5)\n clr.l hold+4(a6)\n'+call('salvage'))
    eq(123456,'hold+4(a6)','l');emit(' btst #remove,flags(a5)\n beq fail\n lea objects+3*obj_len(a6),a5\n'+call('do_logic'))
    eq(0,'loot_target(a5)','l');eq(0,'loot_count(a5)')
    case('NPC pickup is exactly once and changes no player hold, cash, score or mission')
    select();emit(' move.l #10080,objects+5*obj_len+zpos(a6)\n move.l #654321,hold+4(a6)\n move.l #43210,cash(a6)\n move.w #123,score(a6)\n move.w #$15,mission(a6)\n'+call('do_logic')+call('do_logic'))
    eq(1,'loot_count(a5)');eq(654321,'hold+4(a6)','l');eq(43210,'cash(a6)','l');eq(123,'score(a6)');eq('$15','mission(a6)')
    emit(call('remove_objects'));eq(0,'obj_ctr+barrel(a6)','b');eq(1,'pirate_count(a6)')
    case('NPC pickup prevents player collision from collecting the same container later in that frame')
    select();emit(' move.l #10080,objects+5*obj_len+zpos(a6)\n'+call('do_logic')+' lea objects+5*obj_len(a6),a5\n move.l #100,zpos(a5)\n move.l #-20,ypos(a5)\n move.w #1,equip+fuel_scoop(a6)\n move.l #1000000,cargo_mass(a5)\n clr.l hold+4(a6)\n clr.w computer_on(a6)\n clr.w controls_locked(a6)\n'+call('get_range')+call('collision'))
    eq(0,'hold+4(a6)','l');eq(1,'objects+3*obj_len+loot_count(a6)')
    case('Four-barrel lifetime capacity ends the special encounter peacefully')
    select();emit(' move.w #3,loot_count(a5)\n move.l #10080,objects+5*obj_len+zpos(a6)\n'+call('do_logic'))
    eq(4,'loot_count(a5)');eq('loot_departing','loot_mode(a5)');eq('log_cruise','logic(a5)')
    retarget();eq('log_cruise','logic(a5)');eq('no_target','target(a5)','l')
    case('Approach timeout releases the barrel and leaves peacefully')
    select();emit(' move.w #loot_approach_steps-1,loot_steps(a5)\n'+call('do_logic'))
    eq('loot_departing','loot_mode(a5)');eq(0,'objects+5*obj_len+loot_owner(a6)','l')
    case('Leaving scanner range releases reservation and removes the collector normally')
    select();emit(' move.l #radar_range+1,obj_range(a5)\n'+call('do_logic'))
    emit(' btst #remove,flags(a5)\n beq fail\n');eq(0,'objects+5*obj_len+loot_owner(a6)','l')
    emit(call('remove_objects'));eq(0,'pirate_count(a6)')
    for model in ('viper','shuttle','transporter','cobra','python','constr','cougar','thargoid'):
        case(model+' does not acquire pirate salvage behaviour after its target dies')
        obj(3,model);obj(4,'cobra');emit(' lea objects+4*obj_len(a6),a4\n move.l a4,objects+3*obj_len+target(a6)\n st npc_kill(a6)\n'+call('explode_object')+' clr.w npc_kill(a6)\n')
        eq(0,'objects+3*obj_len+loot_mode(a6)')
    for model in ('barrel','platlet','worm'):
        case('Special equipment and non-container objects are excluded: '+model)
        obj(3);obj(5,model,z=11000)
        if model=='barrel':emit(' move.w #-1,cargo_type(a4)\n')
        pirate();retarget();eq(0,'loot_target(a5)','l');eq('loot_departing','loot_mode(a5)')
    case('Create clears every salvage field after a copied or reused object record')
    obj(3);emit(' lea loot_origin(a4),a0\n moveq #(loot_end-loot_origin)/2-1,d0\nqa_poison:\n move.w #-1,(a0)+\n dbra d0,qa_poison\n'+call('create_object')+' lea loot_origin(a4),a0\n moveq #(loot_end-loot_origin)/2-1,d0\nqa_clean:\n tst.w (a0)+\n bne fail\n dbra d0,qa_clean\n')
    for cargo in range(4,9):
        for pirates in (1,2):
            case(f'New encounter creates {cargo} barrels and {pirates} pirates at distinct scanner-visible positions')
            emit(f' st qa_force_cargo\n move.w #{cargo-4},qa_cargo_roll\n move.w #1,qa_small_left\n move.w #{pirates-1},qa_small_second\n'+call('spawn_loot_encounter'))
            eq(cargo,'obj_ctr+barrel(a6)','b');eq(pirates,'pirate_count(a6)')
            emit(' bsr qa_spawn_positions\n')
    for free in range(11):
        case(f'New encounter with {free} free slots preserves four barrels and one pirate or creates nothing')
        emit(' lea objects+3*obj_len(a6),a0\n moveq #max_objects-4,d0\nqa_full_'+str(free)+':\n bset #in_use,flags(a0)\n lea obj_len(a0),a0\n dbra d0,qa_full_'+str(free)+'\n')
        for slot in range(3,3+free):emit(f' clr.b objects+{slot}*obj_len+flags(a6)\n')
        emit(' st qa_force_cargo\n move.w #4,qa_cargo_roll\n move.w #1,qa_small_left\n move.w #1,qa_small_second\n'+call('spawn_loot_encounter'))
        eq(0 if free<5 else max(4,free-2),'obj_ctr+barrel(a6)','b')
        eq(0 if free<5 else (1 if free==5 else 2),'pirate_count(a6)')
    case('128 real-RNG salvage encounters stay inside scanner range and use distinct positions')
    emit(' move.w #128,qa_groups\nqa_group_loop:\n bsr qa_world\n'+call('spawn_loot_encounter')+' bsr qa_spawn_positions\n subq.w #1,qa_groups\n bne qa_group_loop\n')
    # Use real steering, world movement and orthogonalization, including cargo drift.
    for model in ('krait','gecko','moray','adder','mamba','asp','sidewinder','boa','wolf'):
        for direction,(x,y,z) in enumerate(((0,0,2000),(1700,900,0),(-1400,-600,-1800),(0,0,-100))):
            case(f'{model}: actual pursuit and pickup from direction {direction}, cargo drifting at 1..2')
            obj(3,model);obj(5,'barrel',x=x,y=y,z=10000+z)
            emit(f' move.w #{1+direction%2},velocity(a4)\n move.w #{1+direction%2},vel_max(a4)\n')
            pirate();retarget()
            emit(' clr.w qa_frames\n bsr qa_pursue\n')
            eq(1,'objects+3*obj_len+loot_count(a6)')
    emit(f' move.l qa_saved_rand,${r:x}\n move.w qa_saved_rand+4,${r+4:x}\n')
    tail='''qa_world:
'''+call('clear_objects')+''' st game_frozen(a6)
 clr.w csr_on(a6)
 clr.w display_clock(a6)
 clr.w speed(a6)
 clr.w roll_angle(a6)
 clr.w climb_angle(a6)
 clr.w retro_count(a6)
 clr.w mission(a6)
 clr.w radar_obj(a6)
 clr.w npc_hit(a6)
 clr.w npc_kill(a6)
 clr.w collided(a6)
 clr.w missile_state(a6)
 clr.w cloaking_on(a6)
 clr.w qa_force100
 clr.w qa_small_left
 clr.w qa_force_cargo
 clr.w scrambled_id(a6)
 move.b #1,objects+flags(a6)
 move.b #1,objects+obj_len+flags(a6)
 move.b #1,objects+2*obj_len+flags(a6)
 rts
qa_create:
 move.w d0,type(a4)
 move.b #1,flags(a4)
 move.w #log_cruise,logic(a4)
 move.l #no_target,target(a4)
 move.w #unit,x_vector(a4)
 move.w #unit,y_vector+2(a4)
 move.w #unit,z_vector+4(a4)
'''+call('create_object')+''' move.l d4,xpos(a4)
 move.l d5,ypos(a4)
 move.l d6,zpos(a4)
 move.l #10000,obj_range(a4)
 move.w #1,cargo_type(a4)
 clr.w velocity(a4)
 rts
qa_wreck:
 bsr qa_world
 lea objects+3*obj_len(a6),a4
 move.w #krait,d0
 moveq #0,d4
 moveq #0,d5
 move.l #10000,d6
 bsr qa_create
 lea objects+4*obj_len(a6),a4
 move.w #cobra,d0
 move.l #12000,d6
 bsr qa_create
 move.l a4,objects+3*obj_len+target(a6)
 move.w #log_attack,objects+3*obj_len+logic(a6)
 st npc_kill(a6)
'''+call('loot_destroyed')+''' move.w #log_exploding,logic(a4)
 clr.w npc_kill(a6)
 lea objects+5*obj_len(a6),a4
 move.w #barrel,d0
 move.l #11000,d6
 bsr qa_create
 move.l objects+4*obj_len+radio_instance(a6),loot_origin(a4)
 lea objects+3*obj_len(a6),a5
 move.w #3,this_obj(a6)
 move.w #3,retarget_slot(a6)
 rts
qa_rand:
 cmp.w #5,d2
 bne.s .probability
 tst.w qa_force_cargo
 beq.s .real
 clr.w qa_force_cargo
 moveq #0,d0
 move.w qa_cargo_roll,d0
 rts
.probability:
 cmp.w #100,d2
 bne.s .small
 tst.w qa_force100
 beq.s .real
 addq.w #1,qa_roll_calls
 moveq #0,d0
 move.w qa_roll,d0
 rts
.small:
 cmp.w #2,d2
 bne.s .real
 tst.w qa_small_left
 beq.s .real
 moveq #0,d0
 move.w qa_small_second,d0
 subq.w #1,qa_small_left
 beq.s .chosen
 move.w qa_small_first,d0
.chosen:
 rts
.real:
'''+call('random')+''' move.w d0,-(sp)
'''+call('random')+''' lsl.w #8,d0
 or.w (sp)+,d0
 mulu.w d2,d0
 swap d0
 rts
qa_spawn_positions:
 lea objects+3*obj_len(a6),a5
 move.w #3,this_obj(a6)
.outer:
 btst #in_use,flags(a5)
 beq.s .next
 move.l objects+3*obj_len+radio_instance(a6),d0
 cmp.l loot_group(a5),d0
 bne fail
'''+call('get_range')+''' cmp.l #radar_range,obj_range(a5)
 bhi fail
 lea obj_len(a5),a0
 move.w this_obj(a6),d3
 addq.w #1,d3
.inner:
 cmp.w #max_objects,d3
 bhs.s .next
 btst #in_use,flags(a0)
 beq.s .inner_next
 move.l xpos(a0),d0
 cmp.l xpos(a5),d0
 bne.s .inner_next
 move.l ypos(a0),d0
 cmp.l ypos(a5),d0
 bne.s .inner_next
 move.l zpos(a0),d0
 cmp.l zpos(a5),d0
 beq fail
.inner_next:
 lea obj_len(a0),a0
 addq.w #1,d3
 bra.s .inner
.next:
 lea obj_len(a5),a5
 addq.w #1,this_obj(a6)
 cmp.w #max_objects,this_obj(a6)
 blo .outer
 rts
qa_pursue:
 lea objects+3*obj_len(a6),a5
'''+call('get_range')+call('do_logic')+call('orthogonal')+call('move')+''' btst #remove,objects+5*obj_len+flags(a6)
 bne.s .done
 lea objects+5*obj_len(a6),a5
'''+call('get_range')+call('do_logic')+call('orthogonal')+call('move')+''' addq.w #1,qa_frames
 cmp.w #loot_approach_steps,qa_frames
 bhs fail
 bra qa_pursue
.done:
 rts
qa_case: dc.w 0
qa_frames: dc.w 0
qa_groups: dc.w 0
qa_roll: dc.w 0
qa_roll_calls: dc.w 0
qa_force100: dc.w 0
qa_selected: dc.w 0
qa_force_cargo: dc.w 0
qa_cargo_roll: dc.w 0
qa_small_left: dc.w 0
qa_small_first: dc.w 0
qa_small_second: dc.w 0
qa_saved_rand: ds.b 6
'''
    return prefix,''.join(parts),tail,names
