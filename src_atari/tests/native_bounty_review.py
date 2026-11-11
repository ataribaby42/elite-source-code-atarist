"""Review probes for departure transitions, provocation and pilot escape."""
from native_pirate_loot import make_suite as fixtures


def make_suite(root, s):
    prefix, _, tail, _ = fixtures(root, s)
    names, parts = [], []
    emit = parts.append
    call = lambda n: f' jsr ${s[n]:x}\n'

    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n'
             ' clr.w police_record(a6)\n clr.w police_hunt(a6)\n clr.w launch_count(a6)\n'
             ' clr.w game_over(a6)\n clr.w docked(a6)\n bclr #f_fx,user(a6)\n'
             ' move.l #1000,departure_clock(a6)\n')

    def obj(model='ferdelance', slot=3):
        emit(f' lea objects+{slot}*obj_len(a6),a4\n move.w #{model},d0\n'
             ' moveq #0,d4\n moveq #0,d5\n move.l #4000,d6\n bsr qa_create\n'
             ' move.l a4,a5\n move.l #4000,obj_range(a5)\n')

    def eq(n, field, size='w'):
        emit(f' cmp.{size} #{n},{field}\n bne fail\n')

    def laser():
        emit(' st in_sights(a6)\n clr.w obj_hit(a6)\n move.w #1,hit_check(a6)\n'
             ' move.w #1,laser_power(a6)\n clr.l this_xpos(a5)\n clr.l this_ypos(a5)\n'
             ' move.l #4000,this_zpos(a5)\n' + call('check_hit'))

    def escape():
        random = s['random']
        emit(f' move.l ${random:x},rv_random\n move.w ${random+4:x},rv_random+4\n'
             f' move.w #$4ef9,${random:x}\n move.l #rv_escape_once,${random+2:x}\n' + call('launch_escape'))

    # Execute the timing path with the real laser/missile threat and delayed
    # round-robin retargeting. The old test called RETARGET immediately after
    # the station turn, masking any intervening cruise that clears ANGRY.
    for threat in ('laser', 'missile'):
        for phase in range(30):
            case(f'{threat} during station turn survives retarget phase {phase}')
            obj()
            emit(' move.w #log_peel_off,logic(a5)\n move.w #log_departure_wait,next_logic(a5)\n'
                 ' move.w #2,peel_x_count(a5)\n move.w #20,peel_x(a5)\n clr.w peel_z_count(a5)\n')
            if threat == 'laser':
                laser()
            else:
                emit(' move.l a5,target_ptr(a6)\n move.w #2,missile_state(a6)\n'
                     ' move.w #2,equip+missiles(a6)\n' + call('fire_missile') +
                     ' lea objects+3*obj_len(a6),a5\n')
            eq('log_peel_off', 'logic(a5)')
            emit(f' move.w #3,this_obj(a6)\n move.w #{phase},retarget_slot(a6)\n'
                 f' move.w #35,rv_frames\nrv_phase_{threat}_{phase}:\n' + call('retarget') + call('do_logic') +
                 ' addq.w #1,retarget_slot(a6)\n cmp.w #max_objects,retarget_slot(a6)\n'
                 f' blo.s rv_slot_{threat}_{phase}\n clr.w retarget_slot(a6)\nrv_slot_{threat}_{phase}:\n'
                 f' subq.w #1,rv_frames\n bne rv_phase_{threat}_{phase}\n')
            emit(' btst #angry,flags(a5)\n beq fail\n')
            eq(0, 'target(a5)', 'l'); eq(0, 'departure_radius(a5)')

    case('An abandoned hunter cannot execute an armed jump after its pilot escaped')
    obj()
    emit(' move.w #log_peel_off,logic(a5)\n move.w #log_attack,next_logic(a5)\n'
         ' move.w #-1,departure_radius(a5)\n move.l #1000,departure_deadline(a5)\n')
    escape(); eq(1, 'obj_ctr+worm(a6)', 'b'); eq('log_abandoned', 'logic(a5)')
    emit(call('do_logic'))
    eq('log_abandoned', 'logic(a5)'); eq(0, 'departure_radius(a5)')

    for model in ('viper', 'thargoid', 'thargon'):
        case(model + ' retains its original inability to launch an escape capsule')
        obj(model); escape(); eq(0, 'obj_ctr+worm(a6)', 'b')
        eq('act_attack', 'attack_type(a5)'); eq('log_cruise', 'logic(a5)')

    for record in (39, 40, 50):
        case(f'Legal {record}: a neutral Viper keeps its own failed patrol decision next to a hunter')
        obj(); obj('viper', 4)
        emit(f' move.w #{record},police_record(a6)\n clr.w splanet+govern(a6)\n'
             ' move.w #-2,patrol_record(a5)\n move.l #$fc010000,random_seed(a6)\n'
             ' move.w #4,this_obj(a6)\n move.w #4,retarget_slot(a6)\n' + call('retarget'))
        eq('no_target', 'target(a5)', 'l'); eq('log_cruise', 'logic(a5)')
        emit(' btst #angry,flags(a5)\n bne fail\n lea objects+3*obj_len(a6),a5\n'
             ' move.w #3,this_obj(a6)\n move.w #3,retarget_slot(a6)\n' + call('retarget'))
        eq(0 if record >= 40 else 'no_target', 'target(a5)', 'l')

    case('A removed hunter slot can become a Viper without inheriting its role, count or jump')
    obj(); emit(' move.w #-1,departure_radius(a5)\n move.l #9000,departure_deadline(a5)\n'
                ' bset #remove,flags(a5)\n' + call('remove_objects'))
    eq(0, 'trader_count(a6)')
    emit(call('alloc_object') + ' bcc fail\n move.b #1,flags(a4)\n'
         ' move.w #viper,type(a4)\n move.w #log_cruise,logic(a4)\n' + call('create_object'))
    eq('typ_police', 'ship_type(a4)'); eq(0, 'trader_count(a6)'); eq(-1, 'patrol_record(a4)')
    eq(0, 'departure_radius(a4)'); eq(0, 'departure_deadline(a4)', 'l')

    # Keep both decisions deterministic while executing ordinary departure
    # selection. Outside the hunt, FDL still has the original 50/100 outcomes.
    rand = s['rand']
    case('No enemies: every original departure decision remains available to a neutral hunter')
    emit(f' move.l ${rand:x},rv_rand\n move.w ${rand+4:x},rv_rand+4\n'
         f' move.w #$4ef9,${rand:x}\n move.l #rv_departure_rand,${rand+2:x}\n'
         ' clr.w rv_roll\n clr.w rv_selected\nrv_departures:\n')
    obj(); emit(call('start_departure') + ' tst.w departure_radius(a5)\n beq.s rv_rejected\n'
                ' addq.w #1,rv_selected\nrv_rejected:\n addq.w #1,rv_roll\n'
                ' cmp.w #100,rv_roll\n bhs.s rv_decisions_done\n' + call('clear_objects') +
                ' bra rv_departures\nrv_decisions_done:\n')
    eq(50, 'rv_selected')
    emit(f' move.l rv_rand,${rand:x}\n move.w rv_rand+4,${rand+4:x}\n')
    random = s['random']
    tail += f'''\nrv_escape_once:
 move.l rv_random,${random:x}
 move.w rv_random+4,${random+4:x}
 moveq #0,d0
 rts
rv_departure_rand:
 moveq #0,d0
 cmp.w #100,d2
 bne.s .done
 move.w rv_roll,d0
.done:
 rts
rv_random: ds.b 6
rv_rand: ds.b 6
rv_roll: dc.w 0
rv_selected: dc.w 0
rv_frames: dc.w 0
'''
    return prefix, ''.join(parts), tail, names
