"""Native station departure, probability, timing and two-colour cloud checks."""
def make_suite(root, s):
    prefix=' include "common.def"\n include "macros.m68"\n'
    body=' st game_frozen(a6)\n clr.w csr_on(a6)\n clr.w display_clock(a6)\n clr.w speed(a6)\n clr.w retro_count(a6)\n'
    names=[];shots=0
    call=lambda name:f' jsr ${s[name]:x}\n'
    def emit(t):
        nonlocal body
        body+=t
    def case(name):
        names.append(name);emit(f' move.w #{len(names)},qa_case\n')
    def eq(value,field,size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')
    def new(model='cobra'):
        emit(call('clear_objects')+f' lea objects+3*obj_len(a6),a4\n move.w #{model},type(a4)\n move.b #1,flags(a4)\n move.l #no_target,target(a4)\n move.w #16384,x_vector(a4)\n move.w #16384,y_vector+2(a4)\n move.w #16384,z_vector+4(a4)\n'+call('create_object')+' move.l a4,a5\n move.l #20000,obj_range(a5)\n move.l #4000,zpos(a5)\n move.w #3,this_obj(a6)\n move.w #3,retarget_slot(a6)\n clr.w qa_rng_count\n move.l #1000,departure_clock(a6)\n')
    def snapshot(label):
        nonlocal shots
        shots+=1
        emit(' move.l scr_base(a6),qa_frame\n'+f'snap_{label}:\n nop\n')
        if root.name=='src_amiga':
            emit(f' move.w #{shots},qa_snapshot\nqa_shot_wait_{shots}:\n tst.w qa_snapshot\n bne.s qa_shot_wait_{shots}\n')
    def capture(label):
        emit(call('clear_image'))
        if 'wait_clear' in s:emit(call('wait_clear'))
        emit(call('draw_it'))
        snapshot(label)
    # The helper supplies deterministic choices without touching other RNGs.
    r=s['rand']
    emit(f' move.l ${r:x},qa_rand_saved\n move.w ${r+4:x},qa_rand_saved+4\n move.w #$4ef9,${r:x}\n move.l #qa_rand,${r+2:x}\n')
    case('Active departure probability is 50 percent; average installed trader radius is 82')
    emit(call('departure_chance'));eq(50,'d0')
    emit(call('departure_mean_radius'));eq(82,'d0')
    emit(call('departure_hz')+' move.w d0,qa_hz\n')
    case('Pause stops departure time while display interrupts continue')
    emit(' move.l departure_clock(a6),qa_clock\n move.w frame_count(a6),d6\n addq.w #4,d6\nqa_paused_vbl:\n cmp.w frame_count(a6),d6\n bne.s qa_paused_vbl\n move.l qa_clock,d0\n cmp.l departure_clock(a6),d0\n bne fail\n clr.w game_frozen(a6)\n move.w frame_count(a6),d6\n addq.w #4,d6\nqa_active_vbl:\n cmp.w frame_count(a6),d6\n bne.s qa_active_vbl\n st game_frozen(a6)\n move.l departure_clock(a6),d0\n sub.l qa_clock,d0\n cmp.l #4,d0\n blo fail\n')
    for model in ('cobra','python','ferdelance','anaconda','cobra_mk1'):
        case(model+': original station turn completes before the five-second wait')
        new(model)
        emit(' clr.w qa_roll\n clr.w qa_delay\n clr.w approach(a6)\n move.w #log_launch,logic(a5)\n'+call('do_launch'))
        eq('log_peel_off','logic(a5)');eq('log_departure_wait','next_logic(a5)')
        emit(call('retarget'));eq('log_peel_off','logic(a5)')
        emit(f' move.w #200,qa_limit\nqa_turn_{model}:\n'+call('do_logic')+f' cmp.w #log_peel_off,logic(a5)\n bne qa_turned_{model}\n subq.w #1,qa_limit\n bne qa_turn_{model}\n bra fail\nqa_turned_{model}:\n')
        eq('log_departure_wait','logic(a5)');eq(2,'qa_rng_count')
        emit(' moveq #5,d0\n mulu.w qa_hz,d0\n add.l #1000,d0\n cmp.l departure_deadline(a5),d0\n bne fail\n subq.l #1,d0\n move.l d0,departure_clock(a6)\n'+call('do_logic'))
        eq('log_departure_wait','logic(a5)')
        case(model+': jump stops the hull and clears targets without loot or counters changing')
        emit(' lea objects+4*obj_len(a6),a0\n move.l a5,target(a0)\n move.l a5,ai_laser_target(a0)\n move.w #1,ai_laser(a0)\n move.w #3,shield_flash(a5)\n move.w #2,missile_state(a6)\n move.l a5,target_ptr(a6)\n move.l departure_deadline(a5),departure_clock(a6)\n'+call('do_logic'))
        eq('log_departure_cloud','logic(a5)');eq(0,'velocity(a5)');eq(0,'shield_flash(a5)');eq(82,'obj_rad(a5)');eq(1,'trader_count(a6)');eq(model,'type(a5)');eq(0,'missile_state(a6)')
        eq('no_target','objects+4*obj_len+target(a6)','l');eq(0,'objects+4*obj_len+ai_laser_target(a6)','l')
        emit(' move.l a5,a4\n'+call('is_combat_ship'));eq(0,'d0')
        emit(' st in_sights(a6)\n move.w #1,hit_check(a6)\n'+call('check_hit'));eq('log_departure_cloud','logic(a5)')
        emit(' move.l xpos(a5),qa_position\n move.l ypos(a5),qa_position+4\n move.l zpos(a5),qa_position+8\n'+call('move'))
        for offset,axis in ((0,'xpos'),(4,'ypos'),(8,'zpos')):
            emit(f' move.l qa_position+{offset},d0\n cmp.l {axis}(a5),d0\n bne fail\n')
        emit(' move.w #7,speed(a6)\n'+call('move')+' clr.w speed(a6)\n move.l qa_position+8,d0\n subq.l #7,d0\n cmp.l zpos(a5),d0\n bne fail\n')
        case(model+': 1x, 1.5x, 2x, 1x and zero radius; normal removal balances counters')
        if model=='cobra':
            emit(call('prepare_cockpit')+call('front_view')+' st game_frozen(a6)\n clr.w csr_on(a6)\n lea objects+3*obj_len(a6),a5\n clr.l this_xpos(a5)\n clr.l this_ypos(a5)\n move.l #2048,this_zpos(a5)\n move.l #2048,obj_range(a5)\n')
        for phase,expected in ((0,82),(1,123),(2,164),(3,82),(4,0)):
            emit(f' moveq #{phase},d0\n mulu.w qa_hz,d0\n lsr.l #1,d0\n add.l departure_deadline(a5),d0\n move.l d0,departure_clock(a6)\n'+call('do_logic'))
            eq(expected,'obj_rad(a5)')
            if model=='cobra':capture('cloud_'+str(phase))
        emit(' btst #remove,flags(a5)\n beq fail\n'+call('remove_objects'))
        eq(0,'trader_count(a6)');eq(0,f'obj_ctr+{model}(a6)','b')
        emit(' btst #in_use,objects+3*obj_len+flags(a6)\n bne fail\n')
    case('A selected jump keeps its deadline through combat or evasion')
    new();emit(' clr.w qa_roll\n clr.w qa_delay\n'+call('start_departure')+' move.w #log_peel_off,logic(a5)\n move.w #log_attack,next_logic(a5)\n move.w #5,peel_x_count(a5)\n move.l departure_deadline(a5),departure_clock(a6)\n'+call('do_logic'))
    eq('log_departure_cloud','logic(a5)');eq(0,'velocity(a5)')
    case('A destroyed or removed trader cannot turn into a departure cloud')
    for removed in (False,True):
        new();emit(' clr.w qa_roll\n clr.w qa_delay\n'+call('start_departure'))
        emit(' bset #remove,flags(a5)\n' if removed else ' move.w #log_exploding,logic(a5)\n')
        emit(' move.l departure_deadline(a5),departure_clock(a6)\n'+call('departure_tick'))
        eq(0,'departure_radius(a5)')
        emit(' cmp.w #log_departure_cloud,logic(a5)\n beq fail\n')
    for model in ('shuttle','transporter','viper','krait'):
        case(model+': excluded from station trader jump selection')
        new(model);emit(call('start_departure'));eq('log_cruise','logic(a5)');eq(0,'qa_rng_count');eq(0,'departure_deadline(a5)','l')
    for delay in range(6):
        case(f'Random delay endpoint {delay+5} seconds, including deadline wrap')
        new();emit(f' clr.w qa_roll\n move.w #{delay},qa_delay\n move.l #$ffffff00,departure_clock(a6)\n'+call('start_departure'))
        emit(f' moveq #{delay+5},d0\n mulu.w qa_hz,d0\n sub.l #256,d0\n cmp.l departure_deadline(a5),d0\n bne fail\n subq.l #1,d0\n move.l d0,departure_clock(a6)\n'+call('do_logic'))
        eq('log_departure_wait','logic(a5)')
        emit(' addq.l #1,departure_clock(a6)\n'+call('do_logic'));eq('log_departure_cloud','logic(a5)')
    c=s['departure_chance']
    emit(f' move.w ${c:x},qa_chance_saved\n')
    for chance in (0,50,100):
        case(f'{chance} percent selects exactly {chance} of 100 rolls; skipped ships never reroll')
        new();emit(f' move.w #${0x7000+chance:x},${c:x}\n clr.w qa_roll\n clr.w qa_selected\nqa_roll_{chance}:\n clr.w qa_rng_count\n'+call('start_departure'))
        emit(f' cmp.w #log_departure_wait,logic(a5)\n bne qa_no_jump_{chance}\n addq.w #1,qa_selected\n bra qa_next_roll_{chance}\nqa_no_jump_{chance}:\n'+call('do_logic')+call('do_logic')+f' cmp.w #1,qa_rng_count\n bne fail\nqa_next_roll_{chance}:\n addq.w #1,qa_roll\n cmp.w #100,qa_roll\n blo qa_roll_{chance}\n')
        eq(chance,'qa_selected')
    emit(f' move.w qa_chance_saved,${c:x}\n move.l qa_rand_saved,${r:x}\n move.w qa_rand_saved+4,${r+4:x}\n')
    case('Newly created records cannot inherit a previous departure timer or cloud radius')
    new();emit(' move.l #-1,departure_deadline(a4)\n move.w #-1,departure_radius(a4)\n'+call('create_object'));eq(0,'departure_deadline(a4)','l');eq(0,'departure_radius(a4)')
    tail='''qa_rand:
 addq.w #1,qa_rng_count
 moveq #0,d0
 cmp.w #100,d2
 bne.s .delay
 move.w qa_roll,d0
 rts
.delay:
 cmp.w #6,d2
 bne.s .done
 move.w qa_delay,d0
.done:
 rts
qa_case: dc.w 0
qa_snapshot: dc.w 0
qa_frame: dc.l 0
qa_ticks_8: dc.w 0
qa_ticks_1: dc.w 0
qa_roll: dc.w 0
qa_delay: dc.w 0
qa_selected: dc.w 0
qa_limit: dc.w 0
qa_rng_count: dc.w 0
qa_hz: dc.w 0
qa_clock: dc.l 0
qa_position: ds.l 3
qa_rand_saved: ds.b 6
qa_chance_saved: dc.w 0
'''
    return prefix,body,tail,names
