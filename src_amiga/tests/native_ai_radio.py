"""AI radio exercised in the linked 68000 game; no Python gameplay simulation."""
import re


def make_suite(root, s):
    prefix=' include "common.def"\n include "macros.m68"\n'
    out, names, extra = [], [], []
    emit=out.append
    call=lambda n:f' jsr ${s[n]:x}\n'
    def eq(v,f,size='w'): emit(f' cmp.{size} #{v},{f}\n bne fail\n')
    def case(n):
        names.append(n);emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n')
    def spawn(model='cobra',role='typ_trader',slot=3):
        emit(f' lea objects+obj_len*{slot}(a6),a4\n move.b #1,flags(a4)\n move.w #{model},type(a4)\n'+call('create_object'))
        emit(f' move.w #{role},ship_type(a4)\n move.w #log_cruise,logic(a4)\n move.l #no_target,target(a4)\n move.l #1000,obj_range(a4)\n move.l #$41420300,registration_id(a4)\n')
    def sender():emit(' lea objects+obj_len*3(a6),a5\n')
    def roll(i=0):emit(f' move.w #{((10+i-13849)*pow(25173,-1,65536))%65536},ai_comm_seed(a6)\n')
    def observe():sender();emit(call('ai_comm_observe'))
    def count(n):eq(n,'comm_count(a6)');eq(n,'qa_beeps')
    def expire_cooldown():
        sender()
        emit(' move.w #ai_comm_cooldown_frames-1,d5\n')
        label=f'qa_cooldown_{len(names)}'
        emit(label+':\n'+call('ai_comm_tick')+f' dbra d5,{label}\n')
    def message(i,player=1,who='$41420300',recipient='$4a532a00'):
        count(1);eq(i,'comm_queue+comm_message(a6)')
        eq(player,'comm_queue+comm_to_player(a6)')
        eq(who,'comm_queue+comm_sender(a6)','l');eq(recipient,'comm_queue+comm_recipient(a6)','l')
    def attack():emit(' move.w #log_attack,logic(a4)\n clr.l target(a4)\n')
    hooks=[('comm_now','qa_now'),('comm_arrival_sound','qa_beep')]
    for n,label in hooks:
        a=s[n];emit(f' move.l ${a:x},qa_saved_{n}\n move.w ${a+4:x},qa_saved_{n}+4\n move.w #$4ef9,${a:x}\n move.l #{label},${a+2:x}\n')
    case('Full RNG cycle: exactly 50% silent, all ten variants equally likely')
    emit(' clr.w ai_comm_seed(a6)\n move.w #65519,d5\nqa_rng_loop:\n'+call('ai_comm_roll')+'''
 tst.w d0
 bmi.s qa_silent
 cmp.w #9,d0
 bhi fail
 add.w d0,d0
 lea qa_histogram,a0
 addq.w #1,(a0,d0.w)
 bra.s qa_rng_next
qa_silent:
 addq.w #1,qa_silent_count
qa_rng_next:
 dbra d5,qa_rng_loop
''')
    eq(32760,'qa_silent_count');eq(0,'ai_comm_seed(a6)')
    for i in range(10):eq(3276,f'qa_histogram+{2*i}')
    for status in (0,1,49,50,255):
        case(f'Trader greeting at legal record {status}; attempted only once')
        spawn();emit(f' move.w #{status},police_record(a6)\n');roll();observe()
        message(40 if status==0 else 50)
        roll(9);observe();count(1)
    case('Silent greeting consumes the event, including leaving/re-entering scanner range')
    spawn();emit(' clr.w ai_comm_seed(a6)\n');observe();count(0)
    emit(' move.l #100000,obj_range(a5)\n');observe();roll()
    emit(' move.l #1000,obj_range(a5)\n');observe();count(0)
    for label,setup in [('out of scanner',' move.l #radar_range+1,obj_range(a4)\n'),('launching',' move.w #log_launch,logic(a4)\n'),('docking',' move.w #log_docking,logic(a4)\n'),('fighting',' move.w #log_attack,logic(a4)\n'),('evading',' move.w #log_run_off,logic(a4)\n'),('angry',' bset #angry,flags(a4)\n'),('cloaked player',' move.w #1,cloaking_on(a6)\n'),('docked',' move.w #1,docked(a6)\n'),('dead player',' move.w #1,game_over(a6)\n'),('dead ship',' move.w #log_exploding,logic(a4)\n'),('removed',' bset #remove,flags(a4)\n')]:
        case('Trader remains silent when '+label);spawn();emit(setup);roll();observe();count(0)
    case('Greeting is allowed exactly at the scanner boundary, also on UI')
    spawn();emit(' move.l #radar_range,obj_range(a4)\n clr.w cockpit_on(a6)\n');roll();observe();message(40)
    for hidden in (0,255):
        case(f'Existing neutral pirate greets player, scrambled={hidden}')
        spawn(role='typ_pirate');emit(f' move.w #18,pirate_truce(a4)\n move.w #{hidden},scrambled_id(a6)\n')
        roll();observe();message(70,who='comm_hidden',recipient='comm_hidden' if hidden else '$4a532a00')
        eq(18,'pirate_truce(a5)');eq('no_target','target(a5)','l')
    case('Pirate truce permits a friendly player greeting even while fighting another AI')
    spawn(role='typ_pirate');attack();emit(' move.w #18,pirate_truce(a4)\n')
    spawn(slot=4);emit(' move.l a4,objects+obj_len*3+target(a6)\n');roll();observe()
    eq(70,'comm_queue+comm_message(a6)');eq(1,'comm_queue+comm_to_player(a6)')
    emit(' move.w qa_beeps,qa_beeps_before\n');roll();observe()
    emit(' move.w qa_beeps,d0\n cmp.w qa_beeps_before,d0\n bne fail\n')
    case('Scrambled ID alone never creates a truce or pirate greeting')
    spawn(role='typ_pirate');emit(' move.w #255,scrambled_id(a6)\n');roll();observe();count(0);eq(0,'pirate_truce(a5)')
    for model,role,base in [('cobra','typ_pirate',60),('thargoid','typ_alien',80),('viper','typ_police',90)]:
        for npc in (False,True):
            case(f'{model} new target ({"AI" if npc else "player"}), no repeat for same target')
            spawn(model,role);attack()
            if npc:
                spawn(slot=4);emit(' move.l a4,objects+obj_len*3+target(a6)\n move.l #$58590700,registration_id(a4)\n')
            roll();observe();message(base,int(not npc),'$41420300' if role=='typ_police' else 'comm_hidden','$58590700' if npc else '$4a532a00')
            roll(9);observe();count(1)
            emit(' move.w #log_peel_off,logic(a5)\n');observe();count(1)
            emit(' move.w #log_run_off,logic(a5)\n');observe();count(1)
    case('Failed threat is not retried until target really changes')
    spawn(role='typ_pirate');attack();emit(' clr.w ai_comm_seed(a6)\n');observe();count(0)
    roll();observe();count(0)
    spawn(slot=4);emit(' move.l a4,objects+obj_len*3+target(a6)\n');observe();message(60,0,'comm_hidden','$41420300')
    case('Recycled target slot with identical printable ID is a new target')
    spawn(role='typ_pirate');attack();spawn(slot=4)
    emit(' move.l a4,objects+obj_len*3+target(a6)\n');roll();observe();count(1)
    expire_cooldown();spawn(slot=4);roll();observe();count(2)
    case('Actual target loss followed by reacquisition creates one new event')
    spawn(role='typ_pirate');attack();roll();observe();count(1)
    emit(' move.l #no_target,target(a5)\n');observe();expire_cooldown();roll();emit(' clr.l target(a5)\n');observe();count(2)
    for state in ('unused','removed','exploding','out of scanner'):
        case('No threat to an AI target that is '+state)
        spawn(role='typ_pirate');attack();spawn(slot=4)
        emit(' move.l a4,objects+obj_len*3+target(a6)\n')
        emit({'unused':' clr.b flags(a4)\n','removed':' bset #remove,flags(a4)\n','exploding':' move.w #log_exploding,logic(a4)\n','out of scanner':' move.l #radar_range+1,obj_range(a4)\n'}[state])
        roll();observe();count(0)
    for model,role in [('cougar','typ_pirate'),('constr','typ_pirate'),('thargon','typ_alien'),('dodec','typ_police'),('missile','typ_pirate'),('worm','typ_trader'),('cobra','typ_bounty'),('viper','typ_bounty')]:
        case(f'No automatic combat messages from {model}/{role}')
        spawn(model,role);attack();roll();observe();count(0)
    for weapon in ('player laser','AI laser','player missile','AI missile'):
        case(weapon+': first survived hit answers the actual shooter once')
        spawn();spawn('adder','typ_pirate',4)
        emit(' move.l #$58590700,registration_id(a4)\n')
        if 'missile' in weapon:
            spawn('missile','typ_missile',5)
            if weapon=='player missile': emit(call('ai_comm_missile_player'))
            else:emit(' lea objects+obj_len*4(a6),a5\n'+call('ai_comm_missile_ai'))
            # A dead/recycled shooter cannot redirect the response.
            spawn('cobra','typ_trader',4)
            emit(' move.l #$42430100,registration_id(a4)\n lea objects+obj_len*5(a6),a5\n')
        else:
            emit(' suba.l a0,a0\n' if weapon=='player laser' else ' lea objects+obj_len*4(a6),a0\n')
        emit(' lea objects+obj_len*3(a6),a4\n');roll()
        damage='ship_missile_damage' if 'missile' in weapon else 'ship_ai_damage'
        emit(' moveq #5,d0\n'+call(damage));eq(0,'d0')
        message(100,int('player' in weapon),recipient='$4a532a00' if 'player' in weapon else 'comm_hidden')
        if 'missile' not in weapon:
            roll(8);emit(' moveq #5,d0\n'+call(damage));count(1)
    case('Failed protest is consumed across subsequent beam ticks and different attackers')
    spawn();emit(' suba.l a0,a0\n clr.w ai_comm_seed(a6)\n moveq #9,d0\n'+call('ship_ai_damage'));count(0)
    roll();emit(' moveq #9,d0\n'+call('ship_ai_damage'));count(0)
    spawn(slot=4);emit(' move.l a4,a0\n lea objects+obj_len*3(a6),a4\n moveq #9,d0\n'+call('ship_ai_damage'));count(0)
    for label,setup,power in [('invincible',' bset #invincible,flags(a4)\n',5),('zero damage','',0),('lethal hit',' clr.w ai_front(a4)\n clr.w ai_aft(a4)\n move.w #1,health(a4)\n',5)]:
        case('No protest after '+label);spawn();emit(setup);roll()
        emit(f' suba.l a0,a0\n moveq #{power},d0\n'+call('ship_ai_damage'));count(0)
    case('Fractional damage smaller than one energy point still triggers a protest')
    spawn();emit(' move.w #1122,ai_strength(a4)\n suba.l a0,a0\n');roll()
    emit(' moveq #5,d0\n'+call('ship_ai_damage'));message(100);eq(24,'ai_front(a4)')
    for logic in ('log_locked','log_ai_missile'):
        case(f'Actual missile impact ({logic}) answers owner and retains detonation')
        spawn();emit(' clr.w ecm_fitted(a4)\n move.l #100,zpos(a4)\n move.w #unit,z_vector+k(a4)\n')
        spawn('missile','typ_missile',4)
        emit(f' move.w #{logic},logic(a4)\n lea objects+obj_len*3(a6),a0\n move.l a0,target(a4)\n move.w #unit,z_vector+k(a4)\n')
        emit(call('ai_comm_missile_player') if logic=='log_locked' else ' move.l #$58590700,radio_owner(a4)\n')
        emit(' move.l a4,a5\n');roll();emit(call('do_locked'))
        message(100,int(logic=='log_locked'),recipient='$4a532a00' if logic=='log_locked' else '$58590700')
        eq('log_exploding','logic(a5)')
    for target in ('player','AI'):
        case(f'Actual AI missile launch at {target} stores its shooter snapshot')
        spawn('cobra','typ_pirate');emit(' move.w #2,no_missiles(a4)\n move.l #4000,obj_range(a4)\n move.l #-4000,zpos(a4)\n clr.l target(a4)\n')
        if target=='AI':spawn(slot=4);emit(' move.l a4,objects+obj_len*3+target(a6)\n')
        # Occupy 0..2 so ALLOC_OBJECT follows the normal flight pool layout.
        emit(' move.b #1,objects+flags(a6)\n move.b #1,objects+obj_len+flags(a6)\n move.b #1,objects+obj_len*2+flags(a6)\n')
        sender();emit(call('launch_missile'))
        eq('missile','type(a4)');eq('comm_hidden','radio_owner(a4)','l');eq(0,'radio_owner_player(a4)')
    case('Actual player missile launch stores hidden ID and explicit player flag')
    spawn();emit(' move.w #255,scrambled_id(a6)\n move.w #2,missile_state(a6)\n move.w #1,equip+missiles(a6)\n move.l a4,target_ptr(a6)\n'+call('fire_missile'))
    eq('comm_hidden','radio_owner(a4)','l');eq(1,'radio_owner_player(a4)')
    case('Creation discards copied radio state, while removal and allocation clear it')
    spawn();emit(' move.w #$ffff,radio_flags(a4)\n clr.l radio_target(a4)\n move.l #$1234,radio_owner(a4)\n move.w #1,radio_owner_player(a4)\n move.l radio_instance(a4),qa_serial\n'+call('create_object'))
    eq(0,'radio_flags(a4)');eq('no_target','radio_target(a4)','l');eq(0,'radio_owner(a4)','l');eq(0,'radio_owner_player(a4)')
    emit(' move.l radio_instance(a4),d0\n cmp.l qa_serial,d0\n beq fail\n bset #remove,flags(a4)\n'+call('remove_objects'))
    eq(0,'objects+obj_len*3+radio_instance(a6)','l')
    emit(' move.l #$1234,objects+radio_owner(a6)\n move.w #3,objects+radio_flags(a6)\n'+call('alloc_object'))
    eq(0,'radio_owner(a4)','l');eq(0,'radio_flags(a4)')
    case('Instance serial wrap skips both reserved target keys')
    emit(' move.l #$fffffffe,ai_comm_serial(a6)\n lea objects(a6),a4\n'+call('ai_comm_created'))
    eq(1,'radio_instance(a4)','l')
    case('Radio RNG leaves gameplay, registration and station RNG states untouched')
    spawn();emit(' move.l #$12345678,rseed1(a6)\n move.l #$87654321,random_seed(a6)\n move.w #73,comm_seed(a6)\n')
    roll();observe();message(40)
    eq('$12345678','rseed1(a6)','l');eq('$87654321','random_seed(a6)','l');eq(73,'comm_seed(a6)')
    for base,model,role,fighting in [(40,'cobra','typ_trader',False),(50,'cobra','typ_trader',False),(60,'cobra','typ_pirate',True),(70,'cobra','typ_pirate',False),(80,'thargoid','typ_alien',True),(90,'viper','typ_police',True),(100,'cobra','typ_trader',False)]:
        case(f'All ten variants of set {base} come through the real event and shared formatter')
        for i in range(10):
            emit(' bsr qa_world\n');spawn(model,role)
            if base==50:emit(' move.w #1,police_record(a6)\n')
            if base==70:emit(' move.w #20,pirate_truce(a4)\n')
            if fighting:attack()
            roll(i)
            if base==100:emit(' suba.l a0,a0\n moveq #5,d0\n'+call('ship_ai_damage'))
            else:observe()
            eq(base+i,'comm_queue+comm_message(a6)');count(1)
            text=re.search(rf'^comm_text{base+i}: dc.b "([^"]*)",0', (root/'asm/comm.m68').read_text(), re.M)[1]
            who='??-???' if base in (60,70,80) else 'AB-003'
            extra.append(f'qa_text_{base+i}: dc.b "{who}:JS-042, {text}",0\n even\n')
            emit(' lea comm_queue(a6),a5\n'+call('comm_format')+f' lea qa_text_{base+i},a0\n lea comm_buffer(a6),a1\n bsr qa_compare\n')
    case('Three AI receipts in UI retain the existing shared 7-second queue interval')
    for slot in range(3,6):
        spawn(slot=slot);roll();emit(' move.l a4,a5\n'+call('ai_comm_observe'))
    count(3);emit(' move.l #100000,qa_time\n'+call('comm_update'));count(3)
    emit(call('comm_lifetime')+' add.l d0,qa_time\n move.w #1,cockpit_on(a6)\n'+call('comm_update'));eq(2,'comm_count(a6)')
    emit(call('comm_update'));eq(2,'comm_count(a6)')
    for n,_ in hooks:
        a=s[n];emit(f' move.l qa_saved_{n},${a:x}\n move.w qa_saved_{n}+4,${a+4:x}\n')
    tail='''qa_world:
'''+call('clear_objects')+call('comm_reset')+'''
 clr.w docked(a6)
 clr.w game_over(a6)
 clr.w mission(a6)
 clr.w witch_space(a6)
 clr.w cloaking_on(a6)
 clr.w scrambled_id(a6)
 clr.w police_record(a6)
 clr.w cockpit_on(a6)
 clr.w ecm_on(a6)
 clr.w ecm_jammed(a6)
 clr.w qa_beeps
 clr.w radar_obj(a6)
 clr.l qa_time
 clr.l comm_last_tick(a6)
 move.l #$4a532a00,player_registration(a6)
 rts
qa_now:
 move.l qa_time,d0
 rts
qa_beep:
 addq.w #1,qa_beeps
 rts
qa_compare:
 move.b (a0)+,d0
 cmp.b (a1)+,d0
 bne fail
 tst.b d0
 bne.s qa_compare
 rts
qa_case: dc.w 0
qa_time: dc.l 0
qa_beeps: dc.w 0
qa_beeps_before: dc.w 0
qa_histogram: ds.w 10
qa_silent_count: dc.w 0
qa_serial: dc.l 0
qa_saved_comm_now: ds.b 6
qa_saved_comm_arrival_sound: ds.b 6
'''+''.join(extra)
    return prefix,''.join(out),tail,names
