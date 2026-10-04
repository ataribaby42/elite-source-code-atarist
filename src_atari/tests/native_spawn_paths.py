"""Exercise existing spawn paths in the linked game on a real emulated 68000."""
def make_suite(root, s):
    src=(root/'asm/combat.m68').read_text()
    prefix=' include "common.def"\n include "macros.m68"\n'+src[src.index('\tq_vars combat'):src.index('\tq_end_vars combat')]+'\n'
    flight=(root/'asm/flight.m68').read_text()
    prefix+=flight[flight.index('\tq_vars flight'):flight.index('\tq_end_vars flight')]+'\n'
    names=[]; parts=[]; extra=[]
    def emit(text): parts.append(text)
    def call(name): return f' jsr ${s[name]:x}\n'
    def case(name, reset=True):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n'+(' bsr qa_world\n' if reset else ''))
    def eq(value,field,size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')
    def zero(field,size='w'):
        emit(f' tst.{size} {field}\n bne fail\n')
    def check(count):
        emit(' bsr qa_check\n');eq(count,'qa_count')
    def patch(name,label):
        addr=s[name]
        return f' move.l ${addr:x},qa_saved_{name}\n move.w ${addr+4:x},qa_saved_{name}+4\n move.w #$4ef9,${addr:x}\n move.l #{label},${addr+2:x}\n'
    def restore(name):
        addr=s[name]
        return f' move.l qa_saved_{name},${addr:x}\n move.w qa_saved_{name}+4,${addr+4:x}\n'
    emit(patch('random','qa_random')+patch('rand','qa_rand')+patch('ai_laser_roll','qa_loadout_roll'))
    emit(patch('pirate_attack','qa_ambush')+patch('random_encounter','qa_encounter'))
    case('Ordinary wave routing: all 256 coin values in all eight governments')
    emit(''' moveq #0,d4
qa_gov:
 move.w d4,splanet+govern(a6)
 moveq #0,d5
qa_coin:
 move.w d5,qa_roll
 clr.w qa_rng_calls
 clr.w qa_route
 move.w #1,pirate_ctr(a6)
'''+call('create_pirates')+''' cmp.w #1,qa_rng_calls
 bne fail
 move.w d5,d0
 and.w #1,d0
 addq.w #1,d0
 cmp.w qa_route,d0
 bne fail
 move.w d4,d0
 addq.w #2,d0
 lsl.w #8,d0
 add.w d0,d0
 cmp.w pirate_ctr(a6),d0
 bne fail
 addq.w #1,d5
 cmp.w #256,d5
 blo qa_coin
 addq.w #1,d4
 cmp.w #8,d4
 blo qa_gov
''')
    for state in (0x15,0x21,0x41,0x52):
        case(f'Mission ${state:02X} always takes the original ambush route')
        emit(f' move.w #${state:x},mission(a6)\n moveq #0,d5\nqa_mission_{state}:\n move.w d5,qa_roll\n clr.w qa_rng_calls\n clr.w qa_route\n move.w #1,pirate_ctr(a6)\n'+call('create_pirates'))
        eq(1,'qa_route');zero('qa_rng_calls')
        emit(f' addq.w #1,d5\n cmp.w #256,d5\n blo qa_mission_{state}\n')
    for label,setup in [('Station space',' move.w #1,radar_obj(a6)\n'),('Two existing pirates',' move.w #2,pirate_count(a6)\n'),('Wave timer running',' move.w #2,pirate_ctr(a6)\n'),('Existing Constrictor',' move.w #$15,mission(a6)\n move.b #1,obj_ctr+constr(a6)\n')]:
        case(label+' blocks another ordinary wave')
        emit(' clr.w qa_rng_calls\n clr.w qa_route\n'+setup+call('create_pirates'));zero('qa_route')
    case('Constrictor bypasses ordinary wave gates')
    emit(' move.w #$15,mission(a6)\n move.w #1,radar_obj(a6)\n move.w #7,pirate_count(a6)\n move.w #500,pirate_ctr(a6)\n clr.w qa_rng_calls\n clr.w qa_route\n'+call('create_pirates'));eq(1,'qa_route')
    for route in ('spawn_pirate_wave','attack'):
        case(route+': exactly one 50% decision across all 256 coin values')
        emit(f' moveq #0,d5\nqa_route_{route}:\n move.w d5,qa_roll\n clr.w qa_route\n clr.w qa_rng_calls\n move.w #1,dust_type(a6)\n move.w #1,controls_locked(a6)\n move.w #17,old_speed(a6)\n'+call(route))
        eq(1,'qa_rng_calls')
        emit(' move.w d5,d0\n and.w #1,d0\n addq.w #1,d0\n cmp.w qa_route,d0\n bne fail\n')
        if route=='attack':
            eq(17,'speed(a6)');zero('controls_locked(a6)');zero('dust_type(a6)')
        emit(f' addq.w #1,d5\n cmp.w #256,d5\n blo qa_route_{route}\n')
        for state in (0x15,0x21,0x41,0x52):
            case(f'{route}: mission ${state:02X} never consumes a substitution roll')
            emit(f' move.w #${state:x},mission(a6)\n moveq #0,d5\nqa_route_{route}_{state}:\n move.w d5,qa_roll\n clr.w qa_route\n clr.w qa_rng_calls\n'+call(route))
            eq(1,'qa_route');zero('qa_rng_calls')
            emit(f' addq.w #1,d5\n cmp.w #256,d5\n blo qa_route_{route}_{state}\n')
    for gov in range(8):
        for roll in (254,255):
            case(f'Torus government {gov}, roll {roll}: event and one substitution decision')
            emit(f' move.w #{gov},splanet+govern(a6)\n move.w #{roll},qa_roll\n clr.w qa_route\n clr.w qa_rng_calls\n move.w #1,torus_on(a6)\n move.w #1,torus_ctr(a6)\n move.w #1,controls_locked(a6)\n move.w #2,dust_type(a6)\n move.w #17,old_speed(a6)\n'+call('torus_drive'))
            eq(1+(roll&1),'qa_route');eq(2,'qa_rng_calls');eq(17,'speed(a6)');zero('controls_locked(a6)');zero('dust_type(a6)');zero('torus_on(a6)');eq(1,'pirate_ctr(a6)')
    case('Torus with no original attack continues without a substitution roll')
    emit(' move.w #224,qa_roll\n clr.w qa_route\n clr.w qa_rng_calls\n clr.w force_stop(a6)\n move.w #1,torus_on(a6)\n move.w #1,torus_ctr(a6)\n'+call('torus_drive'))
    zero('qa_route');eq(1,'qa_rng_calls');eq(30,'torus_ctr(a6)')
    emit(' tst.w torus_on(a6)\n beq fail\n')
    for state in (0x15,0x21,0x41,0x52):
        case(f'Torus mission ${state:02X} preserves the original event roll and bypasses substitution')
        emit(f' move.w #${state:x},mission(a6)\n move.w #255,qa_roll\n clr.w qa_route\n clr.w qa_rng_calls\n move.w #1,torus_on(a6)\n move.w #1,torus_ctr(a6)\n'+call('torus_drive'))
        eq(1,'qa_route');eq(0 if state==0x21 else 1,'qa_rng_calls');zero('torus_on(a6)')
    emit(restore('pirate_attack')+restore('random_encounter'))

    for rating in (0,4,8):
        for high in (False,True):
            count=(rating+3)//2 if high else 1
            case(f'Original pirate ambush: rating {rating}, '+('maximum' if high else 'minimum')+' wingmen')
            emit(f' move.w #{rating},rating(a6)\n move.w #{65535 if high else 0},qa_fraction\n'+call('pirate_attack'))
            check(count);eq(count,'pirate_count(a6)');emit(' bsr qa_attacking\n')
    for state,ship,count in [(0x15,'constr',1),(0x21,'thargoid',5),(0x41,'cougar',3),(0x52,'thargoid',5)]:
        case(f'Mission ${state:02X} creates its original ships and player targets')
        emit(f' move.w #${state:x},mission(a6)\n move.w #8,rating(a6)\n move.w #$ffff,qa_fraction\n'+call('create_pirates'))
        check(count);eq(ship,'objects+obj_len*3+type(a6)');emit(' bsr qa_attacking\n')
        if ship=='cougar':
            eq('asp','objects+obj_len*4+type(a6)');eq('asp','objects+obj_len*5+type(a6)')
        if ship=='thargoid': eq(count,'obj_ctr+thargoid(a6)','b')
        if ship in ('cougar','constr'):
            emit(' lea objects+obj_len*3(a6),a5\n move.l #16000,obj_range(a5)\n move.l #no_target,target(a5)\n'+call('do_logic'))
            zero('target(a5)','l')
            emit(' cmp.w #log_cruise,logic(a5)\n beq fail\n')
    for state,ship,count in [(0x15,'constr',1),(0x21,'thargoid',5),(0x41,'cougar',3),(0x52,'thargoid',5)]:
        case(f'Mission ${state:02X} torus attack creates its original ships and player targets')
        emit(f' move.w #${state:x},mission(a6)\n move.w #8,rating(a6)\n move.w #$ffff,qa_fraction\n'+call('attack'))
        check(count);eq(ship,'objects+obj_len*3+type(a6)');emit(' bsr qa_attacking\n')
        if ship=='cougar':
            eq('asp','objects+obj_len*4+type(a6)');eq('asp','objects+obj_len*5+type(a6)')
        if ship=='thargoid': eq(count,'obj_ctr+thargoid(a6)','b')
        if ship in ('cougar','constr'):
            emit(' lea objects+obj_len*3(a6),a5\n move.l #16000,obj_range(a5)\n move.l #no_target,target(a5)\n'+call('do_logic'))
            zero('target(a5)','l')
            emit(' cmp.w #log_cruise,logic(a5)\n beq fail\n')
    case('Existing Cougar is not duplicated')
    emit(' move.w #$41,mission(a6)\n move.b #1,obj_ctr+cougar(a6)\n'+call('create_pirates'));check(0)
    case('Witch space spawns only Thargoids, respects cap and leaves other timers alone')
    emit(' move.w #1,witch_space(a6)\n move.w #3,tharg_max(a6)\n move.w #2,launch_count(a6)\n move.w #4,qa_iterations\nqa_witch:\n'+call('object_logic')+' subq.w #1,qa_iterations\n bne qa_witch\n')
    check(3);eq(3,'obj_ctr+thargoid(a6)','b');eq(2,'launch_count(a6)');eq(1,'pirate_ctr(a6)');eq(1,'trader_ctr(a6)');eq(1,'asteroid_ctr(a6)');emit(' bsr qa_attacking\n')

    for state,hunt in [(0,0),(0,1),(0x52,0)]:
        case(f'Station launch: mission ${state:02X}, police hunt {hunt}')
        emit(f' move.w #${state:x},mission(a6)\n move.w #{hunt},police_hunt(a6)\n move.w #2,launch_count(a6)\n move.w #1,launch_rate(a6)\n'+call('launch_vipers'))
        check(1);eq('thargoid' if state else 'viper','objects+obj_len*3+type(a6)');eq('log_police','objects+obj_len*3+logic(a6)');zero('objects+obj_len*3+velocity(a6)');eq(-1,'objects+obj_len*3+patrol_record(a6)');eq(1,'launch_count(a6)')
        eq(9,'objects+obj_len*3+ai_laser_loadout(a6)') # Pulse roll becomes Beam for police; alien replacement stays Beam
        emit(' btst #angry,objects+obj_len*3+flags(a6)\n'+(' beq fail\n' if hunt else ' bne fail\n'))
    for bit in (0,1):
        case(f'Station shuttle selection {bit} retains type, launch and normal acceleration')
        emit(f' move.w #1,radar_obj(a6)\n move.w #{bit},qa_roll\n'+call('launch_shuttle'))
        check(1);eq('shuttle+'+str(bit),'objects+obj_len*3+type(a6)');eq('log_fly_planet','objects+obj_len*3+logic(a6)')
    for label,setup in [('Mission 5',' move.w #$52,mission(a6)\n'),('Close station',' move.l #1000,station_range(a6)\n'),('Destroyed station',' move.w #1,station_destroyed(a6)\n'),('Existing shuttle',' move.b #1,obj_ctr+shuttle(a6)\n')]:
        case(label+' prevents another shuttle')
        emit(' move.w #1,radar_obj(a6)\n'+setup+call('launch_shuttle'));check(0)

    for station in (0,1):
        case(('Station' if station else 'Deep-space')+' traders: all five original models and no convoy speed')
        emit(' clr.w qa_model\nqa_traders_'+str(station)+':\n bsr qa_world\n')
        emit(f' move.w #{station},radar_obj(a6)\n move.w qa_model,d0\n lsl.w #8,d0\n lsl.w #6,d0\n cmp.w #4,qa_model\n blo qa_fraction_{station}\n move.w #$ffff,d0\nqa_fraction_{station}:\n move.w d0,qa_fraction\n'+call('create_trader'))
        check(1);eq(1,'trader_count(a6)')
        emit(' move.w qa_model,d0\n add.w #traders,d0\n cmp.w objects+obj_len*3+type(a6),d0\n bne fail\n')
        eq('log_launch' if station else 'log_cruise','objects+obj_len*3+logic(a6)')
        if station: zero('objects+obj_len*3+velocity(a6)')
        else: emit(' lea objects+obj_len*3(a6),a5\n move.w velocity(a5),d0\n cmp.w vel_max(a5),d0\n bne fail\n')
        emit(f' addq.w #1,qa_model\n cmp.w #5,qa_model\n blo qa_traders_{station}\n')
    case('Deep-space asteroid retains its own cruise speed and mining yield')
    emit(' clr.w qa_roll\n'+call('create_asteroid'));check(1);eq('asteroid','objects+obj_len*3+type(a6)');eq(1,'objects+obj_len*3+no_canisters(a6)')
    case('Station space suppresses asteroid spawning')
    emit(' move.w #1,radar_obj(a6)\n'+call('create_asteroid'));check(0)

    for target in ('player','ship'):
        case('AI missile against '+target+' preserves target, speed and ammunition')
        emit(' bsr qa_parent\n move.w #2,no_missiles(a5)\n clr.l target(a5)\n')
        if target=='ship':
            emit(' move.l a5,qa_parent_ptr\n lea objects+obj_len*5(a6),a4\n move.b #1,flags(a4)\n move.w #krait,type(a4)\n'+call('create_object')+' move.l #21000,zpos(a4)\n move.l a4,target(a5)\n')
        emit(call('launch_missile'));eq(1,'no_missiles(a5)');eq('missile','objects+obj_len*4+type(a6)');eq('log_missile' if target=='player' else 'log_ai_missile','objects+obj_len*4+logic(a6)')
        zero('objects+obj_len*4+convoy_speed(a6)');zero('objects+obj_len*4+cargo_mass(a6)','l')
        emit(' move.l target(a5),d0\n cmp.l objects+obj_len*4+target(a6),d0\n bne fail\n')
        emit(' lea objects+obj_len*4(a6),a5\n move.w vel_max(a5),d0\n cmp.w velocity(a5),d0\n bne fail\n')
    case('Player missile from a reused slot keeps its lock and decrements inventory')
    emit(' bsr qa_parent\n move.l a5,target_ptr(a6)\n move.w #2,missile_state(a6)\n move.w #3,equip+missiles(a6)\n'+call('fire_missile'))
    eq(2,'equip+missiles(a6)');zero('missile_state(a6)');eq('log_locked','objects+obj_len*4+logic(a6)');zero('objects+obj_len*4+convoy_speed(a6)')
    emit(' move.l target_ptr(a6),d0\n cmp.l objects+obj_len*4+target(a6),d0\n bne fail\n')
    for npc,count in ((0,7),(1,3)):
        case(f'Thargon release after {"AI" if npc else "player"} fire preserves mother slot and count')
        emit(' bsr qa_parent\n move.w #thargoid,type(a5)\n move.l a5,a4\n'+call('create_object')+f' move.w #7,convoy_speed(a5)\n move.w #3,this_obj(a6)\n move.w #{npc},npc_hit(a6)\n move.w #255,qa_roll\n'+call('thargons'))
        eq(count,'obj_ctr+thargon(a6)','b');zero('no_missiles(a5)')
        emit(f' lea objects+obj_len*4(a6),a0\n move.w #{count-1},d4\nqa_thargon_{npc}:\n cmp.w #3,mother(a0)\n bne fail\n tst.w convoy_speed(a0)\n bne fail\n cmp.w #log_run_off,logic(a0)\n bne fail\n lea obj_len(a0),a0\n dbra d4,qa_thargon_{npc}\n')
    case('Escape capsule from a convoy does not inherit its cruise setting')
    emit(' bsr qa_parent\n clr.w qa_roll\n'+call('launch_escape'))
    eq('log_abandoned','logic(a5)');eq('act_nothing','attack_type(a5)');zero('no_missiles(a5)');eq('worm','objects+obj_len*4+type(a6)');zero('objects+obj_len*4+convoy_speed(a6)');eq('log_cruise','objects+obj_len*4+logic(a6)')
    zero('objects+obj_len*4+ai_front(a6)');zero('objects+obj_len*4+ai_aft(a6)');zero('objects+obj_len*4+shield_flash(a6)');eq(96,'objects+obj_len*4+health(a6)')
    emit(call('do_logic'));zero('convoy_speed(a5)')
    case('Cargo released by a convoy retains independent 3..6 drift, quantity and payload')
    emit(' bsr qa_parent\n move.w #-1,cargo_type(a5)\n move.l a5,a4\n'+call('release_cargo'))
    eq('barrel','objects+obj_len*4+type(a6)');eq(-1,'objects+obj_len*4+cargo_type(a6)');zero('objects+obj_len*4+convoy_speed(a6)');zero('objects+obj_len*4+cargo_mass(a6)','l')
    emit(' lea objects+obj_len*4(a6),a5\n move.w velocity(a5),d4\n cmp.w #3,d4\n blo fail\n cmp.w #6,d4\n bhi fail\n move.l #1000,obj_range(a5)\n'+call('do_logic')+' cmp.w velocity(a5),d4\n bne fail\n')

    case('Full object pool safely rejects all principal spawners')
    emit(' bsr qa_fill\n')
    for routine,setup in [('pirate_attack',''),('create_trader',''),('create_asteroid',''),('create_thargoids',''),('launch_shuttle',' move.w #1,radar_obj(a6)\n'),('launch_vipers',' move.w #1,launch_count(a6)\n move.w #1,launch_rate(a6)\n')]:
        emit(setup+call(routine)+' bsr qa_full_unchanged\n')
    case('One available slot yields a partial ordinary pirate squadron')
    emit(' bsr qa_fill\n clr.b objects+obj_len*19+flags(a6)\n move.w #8,rating(a6)\n move.w #$ffff,qa_fraction\n'+call('pirate_attack'))
    eq(1,'pirate_count(a6)');zero('objects+obj_len*19+convoy_speed(a6)');eq('log_attack','objects+obj_len*19+logic(a6)');eq('$5678','objects+obj_len*20+velocity(a6)')

    emit(restore('random')+restore('rand')+restore('ai_laser_roll'))
    for state in (0,0x52):
        case(f'System after hyperspace, mission ${state:02X}: planet, station and sun records')
        emit(f' move.w #${state:x},mission(a6)\n'+call('create_system'))
        eq('planet','planet_rec+type(a6)');eq('dodec' if state else 'spacestn','station_rec+type(a6)');eq('sun','sun_rec+type(a6)');zero('planet_rec+convoy_speed(a6)');zero('station_rec+convoy_speed(a6)');zero('sun_rec+convoy_speed(a6)')
        emit(' tst.w planet_rec+obj_colour(a6)\n beq fail\n')
    case('Station departure creates normal system records at the enlarged stride')
    emit(call('launch_system'));eq('planet','planet_rec+type(a6)');eq('spacestn','station_rec+type(a6)');eq('sun','sun_rec+type(a6)')
    case('Removal frees the last slot and counters exactly once, then reuse clears convoy data')
    emit(' lea objects+obj_len*(max_objects-1)(a6),a4\n move.b #1,flags(a4)\n move.w #cobra,type(a4)\n'+call('create_object')+' move.w #7,convoy_speed(a4)\n bset #remove,flags(a4)\n'+call('remove_objects')+call('remove_objects'))
    zero('trader_count(a6)');zero('obj_ctr+cobra(a6)','b');zero('objects+obj_len*(max_objects-1)+flags(a6)','b')
    emit(' lea objects+obj_len*(max_objects-1)(a6),a4\n move.b #1,flags(a4)\n move.w #viper,type(a4)\n'+call('create_object'))
    zero('convoy_speed(a4)');eq(-1,'patrol_record(a4)');eq(1,'obj_ctr+viper(a6)','b')

    tail='''
qa_loadout_roll:
 moveq #0,d0
 rts
qa_random:
 addq.w #1,qa_rng_calls
 move.w qa_roll,d0
 move.w #$ff,d1
 rts
qa_rand:
 cmp.w #32768,d2
 bne qa_fraction_roll
 moveq #0,d0
 move.w qa_vector_seed,d0
 mulu #25173,d0
 add.w #13849,d0
 move.w d0,qa_vector_seed
 lsr.w #1,d0
 move.w #$ff,d1
 rts
qa_fraction_roll:
 moveq #0,d0
 move.w qa_fraction,d0
 mulu d2,d0
 swap d0
 move.w #$ff,d1
 rts
qa_ambush:
 move.w #1,qa_route
 rts
qa_encounter:
 move.w #2,qa_route
 rts
qa_world:
'''+call('clear_objects')+''' clr.w witch_space(a6)
 clr.w radar_obj(a6)
 clr.w mission(a6)
 clr.w police_hunt(a6)
 clr.w launch_count(a6)
 clr.w station_destroyed(a6)
 clr.w cloaking_on(a6)
 clr.w npc_hit(a6)
 clr.w visible(a6)
 move.w #1,pirate_ctr(a6)
 move.w #1,trader_ctr(a6)
 move.w #1,asteroid_ctr(a6)
 move.w #1,shuttle_ctr(a6)
 move.w #7,splanet+govern(a6)
 move.l #20000,station_range(a6)
 move.w #1,tharg_max(a6)
 move.l #$13579b00,random_seed(a6)
 lea planet_rec(a6),a4
 move.b #$87,flags(a4)
 move.w #planet,type(a4)
 lea sun_rec(a6),a4
 move.b #$87,flags(a4)
 move.w #sun,type(a4)
 lea station_rec(a6),a4
 move.b #1,flags(a4)
 move.w #spacestn,type(a4)
 move.w #unit,x_vector+i(a4)
 move.w #unit,y_vector+j(a4)
 move.w #unit,z_vector+k(a4)
 move.l #15000,zpos(a4)
'''+call('create_object')+''' lea objects+obj_len*3(a6),a0
 moveq #max_objects-4,d0
qa_taint:
 move.w #$1234,convoy_speed(a0)
 move.l #$123456,cargo_mass(a0)
 move.w #$2345,patrol_record(a0)
 lea obj_len(a0),a0
 dbra d0,qa_taint
 rts
qa_check:
 clr.w qa_count
 lea objects+obj_len*3(a6),a0
 moveq #max_objects-4,d3
qa_check_slot:
 btst #in_use,flags(a0)
 beq qa_check_next
 addq.w #1,qa_count
 tst.w convoy_speed(a0)
 bne fail
 tst.l cargo_mass(a0)
 bne fail
 cmp.w #-1,patrol_record(a0)
 bne fail
 tst.l nodes(a0)
 beq fail
 move.w energy_max(a0),d0
 tst.w ai_strength(a0)
 beq.s qa_expected_energy
 move.w #max_energy,d0
 cmp.w #max_shield,ai_front(a0)
 bne fail
 cmp.w #max_shield,ai_aft(a0)
 bne fail
 tst.w ai_energy_unit(a0)
 bne fail
qa_expected_energy:
 cmp.w health(a0),d0
 bne fail
 ; Header validation below uses the independent model data pointer.
 move.w type(a0),d0
 lsl.w #2,d0
'''+f' lea ${s["obj_data"]:x},a1\n'+''' move.l (a1,d0.w),a1
 move.l (a1),d0
 cmp.l nodes(a0),d0
 bne fail
 ; Shared player hull limits are covered independently by native_ai_systems.
 ; Objects without ship systems still use their exact model header speed.
 tst.w ai_strength(a0)
 bne.s qa_check_next
 move.w vel_max-nodes(a1),d0
 cmp.w vel_max(a0),d0
 bne fail
qa_check_next:
 lea obj_len(a0),a0
 dbra d3,qa_check_slot
 rts
qa_attacking:
 lea objects+obj_len*3(a6),a0
 moveq #max_objects-4,d3
qa_attack_slot:
 btst #in_use,flags(a0)
 beq qa_attack_next
 cmp.w #log_attack,logic(a0)
 bne fail
 tst.l target(a0)
 bne fail
 move.w vel_max(a0),d0
 cmp.w velocity(a0),d0
 bne fail
qa_attack_next:
 lea obj_len(a0),a0
 dbra d3,qa_attack_slot
 rts
qa_parent:
 lea objects+obj_len*3(a6),a4
 move.b #1,flags(a4)
 move.w #cobra,type(a4)
 move.w #log_cruise,logic(a4)
'''+call('create_object')+''' move.l a4,a5
 move.l #10000,zpos(a5)
 move.l #10000,obj_range(a5)
 move.w #unit,x_vector+i(a5)
 move.w #unit,y_vector+j(a5)
 move.w #unit,z_vector+k(a5)
 move.w #7,convoy_speed(a5)
 move.l #54321,cargo_mass(a5)
 rts
qa_fill:
 lea objects+obj_len*3(a6),a0
 moveq #max_objects-4,d0
qa_fill_slot:
 move.b #1,flags(a0)
 move.w #$5678,velocity(a0)
 lea obj_len(a0),a0
 dbra d0,qa_fill_slot
 rts
qa_full_unchanged:
 lea objects+obj_len*3(a6),a0
 moveq #max_objects-4,d0
qa_full_slot:
 cmp.w #$5678,velocity(a0)
 bne fail
 cmp.w #$1234,convoy_speed(a0)
 bne fail
 lea obj_len(a0),a0
 dbra d0,qa_full_slot
 rts
qa_case: dc.w 0
qa_fraction: dc.w $ffff
qa_roll: dc.w 255
qa_vector_seed: dc.w 12345
qa_rng_calls: dc.w 0
qa_route: dc.w 0
qa_count: dc.w 0
qa_model: dc.w 0
qa_iterations: dc.w 0
qa_parent_ptr: dc.l 0
qa_saved_ai_laser_roll: ds.b 6
qa_saved_random: ds.b 6
qa_saved_rand: ds.b 6
qa_saved_pirate_attack: ds.b 6
qa_saved_random_encounter: ds.b 6
'''
    return prefix,''.join(parts),tail,names
