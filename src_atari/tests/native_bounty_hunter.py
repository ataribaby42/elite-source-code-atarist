"""Fer-de-Lance hunting, civilian accounting and police/salvage integration.

Run against the linked game, including installed object headers. The fixtures
reuse the local salvage suite's ordinary object creation helpers.
"""
from native_pirate_loot import make_suite as salvage_suite


def make_suite(root, s):
    prefix, _, tail, _ = salvage_suite(root, s)
    flight = (root / 'asm/flight.m68').read_text()
    prefix += flight[flight.index('\tq_vars flight'):flight.index('\tq_end_vars flight')] + '\n'
    parts, names = [], []
    emit = parts.append
    call = lambda name: f' jsr ${s[name]:x}\n'

    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n'
             ' clr.w police_record(a6)\n clr.w police_hunt(a6)\n clr.w launch_count(a6)\n'
             ' clr.w station_destroyed(a6)\n clr.w no_entry(a6)\n'
             ' clr.w docked(a6)\n clr.w game_over(a6)\n clr.w witch_space(a6)\n'
             ' clr.w torus_on(a6)\n clr.w torus_ctr(a6)\n'
             ' move.l #1000,departure_clock(a6)\n bclr #f_fx,user(a6)\n')

    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')

    def obj(slot=3, model='ferdelance', z=10000):
        emit(f' lea objects+{slot}*obj_len(a6),a4\n move.w #{model},d0\n'
             f' moveq #0,d4\n moveq #0,d5\n move.l #{z},d6\n bsr qa_create\n'
             f' move.l #{abs(z)},obj_range(a4)\n move.l a4,a5\n')

    def select(slot=3):
        emit(f' lea objects+{slot}*obj_len(a6),a5\n move.w #{slot},this_obj(a6)\n'
             f' move.w #{slot},retarget_slot(a6)\n' + call('retarget'))

    def target(slot):
        emit(f' lea objects+{slot}*obj_len(a6),a0\n cmpa.l target(a5),a0\n bne fail\n')

    def arm():
        emit(' move.w #-1,departure_radius(a5)\n move.l #1000,departure_deadline(a5)\n'
             ' move.w #log_departure_wait,logic(a5)\n')

    def laser():
        emit(' st in_sights(a6)\n clr.w obj_hit(a6)\n move.w #1,hit_check(a6)\n'
             ' move.w #1,laser_power(a6)\n clr.l this_xpos(a5)\n clr.l this_ypos(a5)\n'
             ' move.l #4000,this_zpos(a5)\n' + call('check_hit'))

    case('Installed Fer-de-Lance is an armed hunter; civilian traffic still gates spawns and torus')
    obj()
    eq('typ_bounty', 'ship_type(a5)'); eq('act_attack', 'attack_type(a5)')
    eq(1, 'trader_count(a6)'); eq(0, 'pirate_count(a6)'); eq(-1, 'patrol_record(a5)')
    emit(' move.w #1,trader_ctr(a6)\n' + call('create_trader'))
    eq(1, 'obj_ctr+ferdelance(a6)', 'b'); eq(1, 'trader_count(a6)')
    emit(' move.w hull_speed(a6),speed(a6)\n move.l #$1000000,planet_range(a6)\n'
         ' move.l #$2000000,sun_range(a6)\n' + call('torus'))
    eq(0, 'torus_on(a6)')
    emit(' lea objects+3*obj_len(a6),a5\n bset #remove,flags(a5)\n' + call('remove_objects'))
    eq(0, 'trader_count(a6)'); eq(0, 'obj_ctr+ferdelance(a6)', 'b')
    emit(call('torus')); emit(' tst.w torus_on(a6)\n beq fail\n')

    case('Copying and removing hunter instances balances counters without changing roles')
    obj(); emit(' lea objects+4*obj_len(a6),a4\n' + call('copy_object') + call('create_object'))
    eq('typ_bounty', 'ship_type(a4)'); eq(2, 'trader_count(a6)')
    emit(' bset #remove,flags(a4)\n bset #remove,objects+3*obj_len+flags(a6)\n' + call('remove_objects'))
    eq(0, 'trader_count(a6)'); eq(0, 'pirate_count(a6)')

    for station in (0, 1):
        case(('Station' if station else 'Solo deep-space') + ' spawn installs the actual hunter role')
        emit(f' move.w #{station},radar_obj(a6)\n move.w #1,trader_ctr(a6)\n'
             ' move.l #20000,station_range(a6)\n lea station_rec(a6),a4\n'
             ' move.w #unit,x_vector(a4)\n move.w #unit,y_vector+2(a4)\n'
             ' move.w #unit,z_vector+4(a4)\n')
        rand = s['rand']
        emit(f' move.l ${rand:x},bh_rand\n move.w ${rand+4:x},bh_rand+4\n'
             f' move.w #$4ef9,${rand:x}\n move.l #bh_fdl_once,${rand+2:x}\n' + call('create_trader'))
        eq('ferdelance', 'objects+3*obj_len+type(a6)')
        eq('typ_bounty', 'objects+3*obj_len+ship_type(a6)')
        eq('log_launch' if station else 'log_cruise', 'objects+3*obj_len+logic(a6)')
        eq(1, 'trader_count(a6)'); eq(0, 'pirate_count(a6)')

    case('Encounter member creation installs hunter role and leaves police patrol state disabled')
    emit(' clr.l encounter_lead(a6)\n clr.w encounter_seat(a6)\n'
         ' move.w #5,encounter_role(a6)\n' + call('encounter_member'))
    eq('ferdelance', 'objects+3*obj_len+type(a6)')
    eq('typ_bounty', 'objects+3*obj_len+ship_type(a6)'); eq(-1, 'objects+3*obj_len+patrol_record(a6)')
    eq(1, 'trader_count(a6)')

    # Full relation matrix, including the unchanged police row/column.
    case('All 64 faction relations: hunter/pirate/alien reciprocity; police and civilians neutral')
    masks = [0x82, 0xB5, 0x82, 0, 0x82, 0x82, 0, 0x37]
    for hunter, mask in enumerate(masks):
        for victim in range(8):
            emit(f' lea objects+3*obj_len(a6),a5\n lea objects+4*obj_len(a6),a4\n'
                 f' move.w #{hunter},ship_type(a5)\n move.w #{victim},ship_type(a4)\n' + call('is_hostile'))
            eq((mask >> victim) & 1, 'd0')

    for record in (0, 1, 39, 40, 49, 50, 127, 255):
        for scrambled in (0, 255):
            case(f'Legal record {record}, Scrambled ID {scrambled}: deterministic hunter decision')
            obj(); emit(f' move.w #{record},police_record(a6)\n move.w #{scrambled},scrambled_id(a6)\n'
                        ' move.l random_seed(a6),bh_seed\n')
            select(); select()
            eq(0 if record >= 40 else 'no_target', 'target(a5)', 'l')
            eq('log_attack' if record >= 40 else 'log_cruise', 'logic(a5)')
            eq(0, 'pirate_truce(a5)'); eq(0, 'launch_count(a6)')
            emit(' move.l random_seed(a6),d0\n cmp.l bh_seed,d0\n bne fail\n')

    case('A neutral existing hunter notices the legal record rising from 39 to 40')
    obj(); emit(' move.w #39,police_record(a6)\n'); select(); eq('no_target', 'target(a5)', 'l')
    emit(' move.w #40,police_record(a6)\n'); select(); eq(0, 'target(a5)', 'l'); eq('log_attack', 'logic(a5)')

    for label, record, pirate_z, chosen in [('clean player', 0, 10500, 4),
                                           ('wanted player farther', 40, 10500, 4),
                                           ('wanted player nearer', 40, -10000, None)]:
        case('Nearest eligible target: ' + label)
        obj(); obj(4, 'krait', pirate_z); emit(f' move.w #{record},police_record(a6)\n')
        select(); eq('log_attack', 'logic(a5)')
        if chosen is None: eq(0, 'target(a5)', 'l')
        else: target(chosen)

    for model in ('cobra', 'python', 'shuttle', 'transporter', 'viper', 'ferdelance', 'constr', 'cougar', 'barrel'):
        case('Hunter leaves protected/non-hostile object alone: ' + model)
        obj(); obj(4, model, 10500); select(); eq('no_target', 'target(a5)', 'l')

    for state in ('pending removal', 'exploding', 'hyperspace cloud', 'outside scanner'):
        case('Hunter rejects pirate candidate ' + state)
        obj(); obj(4, 'krait', 10500)
        emit({'pending removal': ' bset #remove,flags(a4)\n',
              'exploding': ' move.w #log_exploding,logic(a4)\n',
              'hyperspace cloud': ' move.w #log_departure_cloud,logic(a4)\n',
              'outside scanner': ' move.l #radar_range+1,obj_range(a4)\n'}[state])
        select(); eq('no_target', 'target(a5)', 'l')

    case('Out-of-range hunter does not acquire even a Fugitive player')
    obj(); emit(' move.w #255,police_record(a6)\n move.l #radar_range+1,obj_range(a5)\n')
    select(); eq('no_target', 'target(a5)', 'l')

    case('After its last enemy disappears, hunter cruises without taking salvage')
    obj(); obj(4, 'krait', 10500); obj(5, 'barrel', 10600); select(); target(4)
    emit(' bset #remove,objects+4*obj_len+flags(a6)\n'); select()
    eq('no_target', 'target(a5)', 'l'); eq('log_cruise', 'logic(a5)'); eq(0, 'loot_mode(a5)')
    eq(0, 'loot_target(a5)', 'l')

    for logic in ('log_launch', 'log_police', 'log_docking', 'log_abandoned', 'log_departure_cloud'):
        case('A warrant does not interrupt protected movement: ' + logic)
        obj(); emit(f' move.w #{logic},logic(a5)\n move.w #255,police_record(a6)\n')
        select(); eq(logic, 'logic(a5)'); eq('no_target', 'target(a5)', 'l')

    case('Station departure turn completes before the hunter starts its pursuit')
    obj(); emit(' move.w #40,police_record(a6)\n move.w #log_peel_off,logic(a5)\n'
                ' move.w #log_departure_wait,next_logic(a5)\n')
    select(); eq('log_peel_off', 'logic(a5)'); eq('no_target', 'target(a5)', 'l')
    emit(' move.w #log_departure_wait,logic(a5)\n'); select(); eq('log_attack', 'logic(a5)')

    for record in (0, 39, 40, 50):
        case(f'S zone actual launch and turn at record {record}: hunter threshold, no early pursuit')
        obj(z=4000)
        emit(f' move.w #{record},police_record(a6)\n st radar_obj(a6)\n clr.w approach(a6)\n'
             ' move.w #log_launch,logic(a5)\n' + call('do_launch'))
        eq('log_peel_off', 'logic(a5)'); select(); eq('log_peel_off', 'logic(a5)')
        emit(f' move.w #200,bh_steps\nbh_turn_{record}:\n' + call('do_logic') +
             f' cmp.w #log_peel_off,logic(a5)\n bne bh_clear_{record}\n'
             f' subq.w #1,bh_steps\n bne bh_turn_{record}\n bra fail\nbh_clear_{record}:\n')
        select()
        eq(0 if record >= 40 else 'no_target', 'target(a5)', 'l')
        if record >= 40:
            eq('log_attack', 'logic(a5)'); eq(0, 'departure_radius(a5)')
            emit(' move.w #100,ai_laser_cooldown(a5)\n' + call('do_logic'))
            emit(' cmp.w #log_cruise,logic(a5)\n beq fail\n')
        else:
            emit(' cmp.w #log_attack,logic(a5)\n beq fail\n')

    for opponent in ('player warrant', 'pirate'):
        case('Acquiring ' + opponent + ' cancels an armed station jump at its deadline')
        obj(); arm()
        if opponent == 'player warrant': emit(' move.w #40,police_record(a6)\n')
        else: obj(4, 'krait', 10500)
        select(); eq(0, 'departure_radius(a5)')
        emit(call('do_logic')); emit(' cmp.w #log_departure_cloud,logic(a5)\n beq fail\n')

    case('Clean player laser provocation cancels the jump before scheduled retargeting')
    obj(); arm(); laser(); emit(call('do_logic'))
    eq(0, 'departure_radius(a5)'); emit(' btst #angry,flags(a5)\n beq fail\n')
    select(); eq(0, 'target(a5)', 'l')

    case('Clean player missile launch cancels the jump before impact')
    obj(); arm(); emit(' move.l a5,target_ptr(a6)\n move.w #2,missile_state(a6)\n'
                      ' move.w #2,equip+missiles(a6)\n' + call('fire_missile') +
                      ' lea objects+3*obj_len(a6),a5\n' + call('departure_tick'))
    eq(0, 'departure_radius(a5)'); eq(0, 'target(a5)', 'l')

    case('Pirate laser provocation also cancels the jump before the next retarget slot')
    obj(); arm(); obj(4, 'krait', 10500)
    emit(' lea objects+3*obj_len(a6),a0\n move.l a0,target(a5)\n moveq #1,d0\n' + call('damage_target') +
         ' lea objects+3*obj_len(a6),a5\n' + call('departure_tick'))
    eq(0, 'departure_radius(a5)'); select(); target(4)

    for hunter in ('ferdelance', 'viper'):
        for mode in ('loot_pending', 'loot_wreck', 'loot_encounter', 'loot_departing'):
            case(hunter + ' still acquires a pirate in ' + mode)
            obj(3, 'krait'); emit(f' move.w #{mode},loot_mode(a5)\n move.w #log_loot,logic(a5)\n')
            obj(4, hunter, 10500); select(4); target(3); eq('log_attack', 'logic(a5)')
        case(hunter + ' actual damage releases reserved cargo and restores pirate combat acceleration')
        obj(3, 'krait'); emit(' move.w #loot_encounter,loot_mode(a5)\n move.w #log_loot,logic(a5)\n')
        obj(5, 'barrel', 11000); select(3)
        emit(' tst.l loot_target(a5)\n beq fail\n moveq #8,d0\n' + call('loot_speed'))
        obj(4, hunter, 10500); select(4); target(3)
        emit(' moveq #1,d0\n' + call('damage_target'))
        eq(0, 'objects+3*obj_len+loot_mode(a6)'); eq(0, 'objects+5*obj_len+loot_owner(a6)', 'l')
        emit(' cmpa.l objects+3*obj_len+target(a6),a5\n bne fail\n'
             ' lea objects+3*obj_len(a6),a5\n move.w #4,velocity(a5)\n'
             ' move.w #1,on_course(a5)\n move.w #1000,counter(a5)\n' + call('do_run_off'))
        emit(' cmp.w #4,velocity(a5)\n bls fail\n'); eq(24, 'vel_max(a5)')

    for victim in ('ferdelance', 'cobra', 'viper'):
        case('Station still scrambles police when the player shoots ' + victim)
        obj(3, victim); emit(' st radar_obj(a6)\n'); laser()
        emit(' tst.w police_hunt(a6)\n beq fail\n tst.w launch_count(a6)\n beq fail\n')
    for npc in (False, True):
        case(('NPC' if npc else 'Player') + ' hunter kill retains legal/score attribution')
        obj(); emit(f' move.w #{1 if npc else 0},npc_kill(a6)\n move.w #7,police_record(a6)\n'
                    ' clr.l score(a6)\n move.l a5,a4\n' + call('explode_object'))
        eq(7 if npc else 71, 'police_record(a6)')
        if npc: eq(0, 'score(a6)', 'l')

    case('Fer-de-Lance retains its escape capsule; abandoned hull cannot resume bounty hunting')
    obj(); emit(' move.w #40,police_record(a6)\n')
    random = s['random']
    emit(f' move.l ${random:x},bh_random\n move.w ${random+4:x},bh_random+4\n'
         f' move.w #$4ef9,${random:x}\n move.l #bh_escape_once,${random+2:x}\n' + call('launch_escape'))
    eq(1, 'obj_ctr+worm(a6)', 'b'); eq('log_abandoned', 'logic(a5)'); eq('act_nothing', 'attack_type(a5)')
    select(); eq('log_abandoned', 'logic(a5)')
    tail += f'''\nbh_escape_once:
 move.l bh_random,${random:x}
 move.w bh_random+4,${random+4:x}
 moveq #0,d0
 rts
bh_fdl_once:
 move.l bh_rand,${rand:x}
 move.w bh_rand+4,${rand+4:x}
 moveq #2,d0
 rts
bh_random: ds.b 6
bh_rand: ds.b 6
bh_steps: dc.w 0
bh_seed: dc.l 0
'''
    return prefix, ''.join(parts), tail, names
