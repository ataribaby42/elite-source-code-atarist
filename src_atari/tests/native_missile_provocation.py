"""Player missile launch threats, ECM and protected AI states on the real 68000."""
from native_missile_collision import make_suite as base_suite


def make_suite(root, s):
    prefix, _, tail, _ = base_suite(root, s)
    out, names = [], []
    emit = out.append
    call = lambda name: f' jsr ${s[name]:x}\n'

    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')

    def victim(reg='a4'):
        emit(f' lea objects+obj_len*3(a6),{reg}\n')

    def missile():
        emit(' lea objects+obj_len*4(a6),a5\n')

    def angry(expected=True):
        victim()
        emit(' btst #angry,flags(a4)\n'+(' beq' if expected else ' bne')+' fail\n')

    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n'+call('quiet')+
             ' bclr #f_fx,user(a6)\n bsr qa_world\n'+call('comm_reset')+
             ' move.b #1,objects+flags(a6)\n move.b #1,objects+obj_len+flags(a6)\n'
             ' move.b #1,objects+obj_len*2+flags(a6)\n clr.w scrambled_id(a6)\n'
             ' clr.w police_record(a6)\n clr.w police_hunt(a6)\n clr.w no_entry(a6)\n'
             ' clr.w station_destroyed(a6)\n move.w #3,equip+missiles(a6)\n'
             ' move.l #$4a532a00,player_registration(a6)\n')
        radio_roll(None)

    def radio_roll(index):
        outcome = 0 if index is None else 10+index
        seed = ((outcome-13849)*pow(25173, -1, 65536)) % 65536
        emit(f' move.w #{seed},ai_comm_seed(a6)\n')

    def spawn(model='cobra', logic='log_cruise'):
        victim()
        emit(f' move.b #1,flags(a4)\n move.w #{model},type(a4)\n'+call('create_object')+
             f' move.w #{logic},logic(a4)\n move.l #no_target,target(a4)\n'
             ' move.l #6000,zpos(a4)\n move.l #6000,obj_range(a4)\n'
             ' move.w #unit,x_vector+i(a4)\n move.w #unit,y_vector+j(a4)\n'
             ' move.w #-unit,z_vector+k(a4)\n move.l #$41420300,registration_id(a4)\n')

    def launch():
        victim()
        emit(' move.l a4,target_ptr(a6)\n move.w #2,missile_state(a6)\n'+call('fire_missile'))
        victim()
        eq(2, 'equip+missiles(a6)'); eq(0, 'missile_state(a6)')
        missile(); eq('log_locked', 'logic(a5)'); eq('missile', 'type(a5)')
        emit(' cmpa.l target(a5),a4\n bne fail\n')

    def unchanged():
        emit(' bsr qa_compare\n')

    def no_hit(mission='$41'):
        victim()
        eq(0, 'shield_flash(a4)')
        eq(0, 'comm_count(a6)'); eq(mission, 'mission(a6)')
        eq(0, 'no_entry(a6)'); eq(0, 'police_hunt(a6)'); eq(0, 'launch_count(a6)')
        eq(0, 'police_record(a6)'); eq(0, 'score(a6)', 'l'); eq(0, 'kill_count(a6)')
        eq(100000, 'cash(a6)', 'l'); eq(0, 'station_destroyed(a6)')

    for model in ('cobra', 'adder', 'gecko', 'moray', 'cobra_mk1', 'ferdelance',
                  'boa', 'anaconda', 'asp', 'sidewinder', 'krait', 'mamba',
                  'viper', 'wolf', 'thargoid', 'thargon'):
        case(f'{model}: successful launch provokes before impact, without a simulated hit')
        spawn(model); eq('act_attack', 'attack_type(a4)')
        emit(' move.w #61,health(a4)\n move.w #11,ai_front(a4)\n move.w #12,ai_aft(a4)\n')
        launch(); angry(); eq('log_attack', 'logic(a4)'); eq(0, 'target(a4)', 'l')
        eq(61, 'health(a4)'); eq(61, 'pre_attack(a4)'); eq(11, 'ai_front(a4)'); eq(12, 'ai_aft(a4)')
        no_hit()
        # Run the real AI twice while this slot is not due for faction retargeting.
        victim('a5'); emit(' move.w #3,this_obj(a6)\n move.w #7,retarget_slot(a6)\n'+
                           call('retarget')+call('do_logic')+call('retarget')+call('do_logic'))
        angry(); emit(' cmp.w #log_cruise,logic(a4)\n beq fail\n')

    for model in ('python', 'shuttle', 'transporter', 'worm'):
        case(f'{model}: launching at a fleeing or passive hull leaves its entire record unchanged')
        spawn(model); emit(' bsr qa_snapshot\n')
        if model == 'python': emit(' move.b #2,qa_record+radio_flags\n')
        launch(); unchanged(); angry(False); no_hit()

    for logic in ('log_launch', 'log_police', 'log_takeoff', 'log_takeoff+7',
                  'log_docking', 'log_docking+11', 'log_escape', 'log_abandoned'):
        case(f'{logic}: launch threat does not interrupt scripted movement')
        spawn(logic=logic); emit(' bsr qa_snapshot\n'); launch(); unchanged(); no_hit()

    for setup, label in [(' bset #invincible,flags(a4)\n', 'invincible hull'),
                         (' bset #remove,flags(a4)\n', 'pending removal'),
                         (' move.w #log_exploding,logic(a4)\n', 'exploding hull'),
                         (' move.w #act_nothing,attack_type(a4)\n', 'dormant Tharglet')]:
        case(label+': launch does not wake or overwrite the protected target')
        spawn('thargon' if label == 'dormant Tharglet' else 'cobra')
        emit(setup+' bsr qa_snapshot\n'); launch(); unchanged(); no_hit()

    for model, mission in [('constr', '$15'), ('constr', '$21'), ('cougar', '$41'),
                           ('spacestn', '$00'), ('dodec', '$52'), ('barrel', '$41'),
                           ('asteroid', '$41'), ('missile', '$41')]:
        case(f'{model}, mission {mission}: special target and mission state remain untouched at launch')
        spawn(model, 'log_attack' if model in ('constr', 'cougar') else 'log_cruise')
        emit(f' move.w #{mission},mission(a6)\n bsr qa_snapshot\n')
        launch(); unchanged(); no_hit(mission)

    for state in (0, 1):
        case(f'No lock (state {state}): failed launch cannot provoke or consume ammunition')
        spawn(); emit(f' move.w #{state},missile_state(a6)\n move.l a4,target_ptr(a6)\n bsr qa_snapshot\n'+call('fire_missile'))
        unchanged(); eq(3, 'equip+missiles(a6)'); eq(0, 'obj_ctr+missile(a6)', 'b'); no_hit()
    case('Full object bubble: failed allocation cannot provoke the target')
    spawn(); emit(' bsr qa_snapshot\n lea objects(a6),a0\n moveq #max_objects-1,d7\nqa_fill:\n'
                  ' bset #in_use,flags(a0)\n lea obj_len(a0),a0\n dbra d7,qa_fill\n')
    victim(); emit(' move.l a4,target_ptr(a6)\n move.w #2,missile_state(a6)\n'+call('fire_missile'))
    unchanged(); eq(3, 'equip+missiles(a6)'); eq(2, 'missile_state(a6)'); no_hit()

    case('Scrambled ID: only the targeted neutral pirate loses its truce, without legal penalties')
    spawn('sidewinder')
    emit(' move.w #$ff,scrambled_id(a6)\n move.w #9,pirate_truce(a4)\n'
         ' move.w #9,objects+obj_len*5+pirate_truce(a6)\n')
    launch(); angry(); eq(0, 'pirate_truce(a4)'); eq(9, 'objects+obj_len*5+pirate_truce(a6)'); no_hit()

    case('An existing AI fight and laser burst keep their target, manoeuvre and timers')
    spawn(logic='log_attack')
    emit(' lea objects+obj_len*5(a6),a0\n move.l a0,target(a4)\n move.l a0,ai_laser_target(a4)\n'
         ' move.w #5,ai_laser_burst(a4)\n move.w #7,on_course(a4)\n')
    launch(); angry(); eq('log_attack', 'logic(a4)'); eq(5, 'ai_laser_burst(a4)'); eq(7, 'on_course(a4)')
    emit(' lea objects+obj_len*5(a6),a0\n cmpa.l target(a4),a0\n bne fail\n'
         ' cmpa.l ai_laser_target(a4),a0\n bne fail\n'); no_hit()

    for next_logic in ('log_cruise', 'log_fly_planet', 'log_run_off', 'log_avoid'):
        case(f'Peel-off toward {next_logic}: preserve the turn, but never erase new hostility on cruise')
        spawn(logic='log_peel_off')
        emit(f' move.w #{next_logic},next_logic(a4)\n move.w #17,peel_x_count(a4)\n')
        launch(); angry(); eq('log_peel_off', 'logic(a4)'); eq(17, 'peel_x_count(a4)')
        eq('log_attack' if next_logic in ('log_cruise', 'log_fly_planet') else next_logic, 'next_logic(a4)')

    for model in ('cobra', 'python'):
        for fitted, jammed, roll, far, expected in [(1, 0, 0, False, True), (1, 0, 255, False, False),
                                                   (1, 1, 0, False, False), (0, 0, 0, False, False),
                                                   (1, 0, 0, True, False)]:
            case(f'{model}: ECM fitted={fitted}, jammed={jammed}, roll={roll}, far={far}')
            spawn(model); launch(); victim()
            emit(f' move.w #{fitted},ecm_fitted(a4)\n move.w #{jammed},ecm_jammed(a6)\n'
                 f' move.l #{30000 if far else 6000},zpos(a4)\n')
            missile(); emit(' clr.l xpos(a5)\n clr.l ypos(a5)\n move.l #5200,zpos(a5)\n'
                            ' move.l #5200,obj_range(a5)\n move.w #2,on_course(a5)\n'
                            f' move.w #{roll},qa_roll\n bsr qa_patch_random\n'+call('do_locked')+' bsr qa_restore_random\n')
            emit(' tst.w ecm_on(a6)\n'+(' beq' if expected else ' bne')+' fail\n')
            angry(model != 'python'); no_hit()
            if expected:
                emit(call('ecm')); missile(); eq('log_exploding', 'logic(a5)')
                angry(model != 'python')

    case('Python retains its low-energy defensive missile after being targeted')
    spawn('python'); launch(); angry(False)
    # LOW_ENERGY itself is unchanged: first roll declines escape, later rolls allow retaliation.
    victim('a5'); emit(' move.w #1,no_missiles(a5)\n move.w #20,health(a5)\n'
                      ' move.w #96,pre_attack(a5)\n clr.w qa_rng_step\n move.w #-1,qa_roll\n'
                      ' bsr qa_patch_random\n'+call('low_energy')+' bsr qa_restore_random\n')
    victim(); eq('act_runaway', 'attack_type(a4)'); eq(0, 'no_missiles(a4)'); angry(False)
    eq('log_missile', 'objects+obj_len*5+logic(a6)'); eq('no_target', 'objects+obj_len*5+target(a6)', 'l')

    for model in ('cobra', 'python'):
        for hidden in (False, True):
            for sent in (False, True):
                case(f'{model}: launch protest hidden={hidden}, sent={sent}; impact and repeated launch never repeat it')
                spawn(model)
                emit(f' move.w #{255 if hidden else 0},scrambled_id(a6)\n')
                radio_roll(3 if sent else None)
                launch(); angry(model != 'python')
                victim(); eq('$0200', 'radio_flags(a4)'); eq(96, 'health(a4)'); eq(24, 'ai_front(a4)')
                eq(int(sent), 'comm_count(a6)')
                if sent:
                    eq('comm_protest_text+3', 'comm_queue+comm_message(a6)')
                    eq('$41420300', 'comm_queue+comm_sender(a6)', 'l')
                    eq('comm_hidden' if hidden else '$4a532a00', 'comm_queue+comm_recipient(a6)', 'l')
                    eq(1, 'comm_queue+comm_to_player(a6)')
                # Force the next radio roll to succeed: neither event may use it.
                radio_roll(0); emit(' move.w ai_comm_seed(a6),qa_radio_seed\n')
                victim(); emit(' move.l a4,target_ptr(a6)\n move.w #2,missile_state(a6)\n'+call('fire_missile'))
                eq(1, 'equip+missiles(a6)'); eq(int(sent), 'comm_count(a6)')
                victim(); emit(' clr.w ecm_fitted(a4)\n')
                missile(); emit(' clr.l xpos(a5)\n clr.l ypos(a5)\n move.l #5900,zpos(a5)\n'
                                ' move.l #5900,obj_range(a5)\n move.w #2,on_course(a5)\n'+call('do_locked'))
                eq('log_exploding', 'logic(a5)'); eq(int(sent), 'comm_count(a6)')
                emit(' move.w ai_comm_seed(a6),d0\n cmp.w qa_radio_seed,d0\n bne fail\n')

    for model, base in [('sidewinder', 'comm_pirate_text'), ('viper', 'comm_police_text'),
                        ('thargoid', 'comm_alien_text')]:
        case(f'{model}: launch provocation reaches the existing attack radio event before impact')
        spawn(model)
        if model == 'sidewinder': emit(' move.w #$ff,scrambled_id(a6)\n move.w #9,pirate_truce(a4)\n')
        launch(); angry(); radio_roll(2); victim('a5'); emit(call('ai_comm_observe'))
        eq(1, 'comm_count(a6)'); eq(base+'+2', 'comm_queue+comm_message(a6)')
        eq(1, 'comm_queue+comm_to_player(a6)')
        victim(); eq(96, 'health(a4)'); eq(0, 'shield_flash(a4)')

    for passive in (True, False):
        case(f'Launch RNG parity: combat reaction enabled={not passive}')
        spawn()
        if passive: emit(' move.w #act_nothing,attack_type(a4)\n')
        emit(' move.l #$12345678,random_seed(a6)\n'); launch()
        if passive: emit(' move.l random_seed(a6),qa_seed\n')
        else: emit(' move.l random_seed(a6),d0\n cmp.l qa_seed,d0\n bne fail\n')

    tail += '''qa_snapshot:
 lea objects+obj_len*3(a6),a0
 lea qa_record,a1
 move.w #obj_len/2-1,d7
.copy:
 move.w (a0)+,(a1)+
 dbra d7,.copy
 rts
qa_compare:
 lea objects+obj_len*3(a6),a0
 lea qa_record,a1
 move.w #obj_len/2-1,d7
.word:
 cmpm.w (a0)+,(a1)+
 bne fail
 dbra d7,.word
 rts
'''
    a = s['random']
    tail += f'''qa_patch_random:
 move.l ${a:x},qa_random_saved
 move.w ${a+4:x},qa_random_saved+4
 move.w #$4ef9,${a:x}
 move.l #qa_random,${a+2:x}
 rts
qa_restore_random:
 move.l qa_random_saved,${a:x}
 move.w qa_random_saved+4,${a+4:x}
 rts
qa_random:
 moveq #0,d0
 move.w qa_roll,d0
 bpl.s .done
 moveq #0,d0
 tst.w qa_rng_step
 bne.s .next
 move.w #255,d0
.next:
 addq.w #1,qa_rng_step
.done:
 rts
qa_random_saved: ds.b 6
qa_roll: dc.w 0
qa_rng_step: dc.w 0
qa_seed: dc.l 0
qa_radio_seed: dc.w 0
qa_record: ds.b obj_len
'''
    return prefix, ''.join(out), tail, names
