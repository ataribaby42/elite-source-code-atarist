"""Validate docking-clearance communications against the linked 68000 game."""
from native_spawn_paths import make_suite as spawn_suite


def make_suite(root, s):
    prefix, _, tail, _ = spawn_suite(root, s)
    out, names = [], []
    emit = out.append
    call = lambda name: f' jsr ${s[name]:x}\n'

    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')

    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n'
             ' clr.w docked(a6)\n clr.w just_docked(a6)\n clr.w no_entry(a6)\n'
             ' clr.w cockpit_on(a6)\n clr.w scrambled_id(a6)\n clr.w police_record(a6)\n'
             ' move.w #-1,checkpoint(a6)\n move.w #1,radar_obj(a6)\n'
             ' move.l #$224ff,planet_range(a6)\n move.l #2000,station_range(a6)\n'
             ' clr.l qa_time\n clr.w galaxy_no(a6)\n move.w #107,current(a6)\n'
             ' move.l #$4a532a00,player_registration(a6)\n'
             + call('comm_reset') + ' clr.w qa_beeps\n')

    def received(recipient='$4a532a00', count=1, beeps=1, denied=False, unwelcome=False):
        eq(count, 'comm_count(a6)'); eq(beeps, 'qa_beeps')
        eq(2 if denied else 1, 'comm_arrival_sent(a6)')
        offset = f'comm_queue+{count-1}*comm_size+'
        eq('$43316b00', offset+'comm_sender(a6)', 'l')
        eq(recipient, offset+'comm_recipient(a6)', 'l')
        eq(1, offset+'comm_to_player(a6)')
        first = 'comm_denied_text' if denied else 'comm_unwelcome_text' if unwelcome else 'comm_arrival_text'
        end = 'comm_unwelcome_text' if denied else 'comm_text_count' if unwelcome else 'comm_denied_text'
        emit(f' cmp.w #{first},{offset}comm_message(a6)\n blo fail\n'
             f' cmp.w #{end},{offset}comm_message(a6)\n bhs fail\n')

    def silent():
        eq(0, 'comm_count(a6)'); eq(0, 'qa_beeps')
        eq(0, 'comm_arrival_sent(a6)'); eq(0, 'comm_seed(a6)')

    def station_shot():
        emit(' lea station_rec(a6),a5\n move.w #1,this_obj(a6)\n'
             ' move.w #1,hit_check(a6)\n clr.w obj_hit(a6)\n'
             ' move.w #5,laser_power(a6)\n'+call('check_hit'))

    hooks = [('comm_now', 'qa_now'), ('comm_arrival_sound', 'qa_beep'),
             ('laser_in_sights', 'qa_in_sights')]
    emit(call('hide_cursor')+' clr.w display_clock(a6)\n clr.w player_ship(a6)\n'
         +call('ship_apply'))
    for name, label in hooks:
        addr = s[name]
        emit(f' move.l ${addr:x},qa_arrival_saved_{name}\n'
             f' move.w ${addr+4:x},qa_arrival_saved_{name}+4\n'
             f' move.w #$4ef9,${addr:x}\n move.l #{label},${addr+2:x}\n')
        tail += f'qa_arrival_saved_{name}: ds.b 6\n'

    for cockpit in (0, 1):
        for distance in (0, 1999, 2000, 2001, 6143, 65536):
            case(f'Close-approach boundary: distance={distance}, cockpit={cockpit}')
            emit(f' move.w #{cockpit},cockpit_on(a6)\n move.l #{distance},station_range(a6)\n'
                 +call('radar_lock'))
            if distance <= 2000: received()
            else: silent()

    for coords, expected in (((2000,0,0),2000), ((0,-2000,0),2000),
                             ((0,0,-2000),2000), ((1200,1600,0),2000),
                             ((-1200,0,-1600),2000), ((1200,1601,0),2000)):
        case(f'Existing GET_RANGE result controls greeting for station at {coords}')
        emit(' lea station_rec(a6),a5\n')
        for field, value in zip(('xpos','ypos','zpos'), coords):
            emit(f' move.l #{value},{field}(a5)\n')
        emit(call('get_range'))
        # Integer square root rounds down; the same cached value gates traders.
        eq(expected, 'station_range(a6)', 'l')
        emit(call('radar_lock')); received()

    for label, setup in (
            ('already docked', ' move.w #1,docked(a6)\n'),
            ('docking in this frame', ' move.w #1,just_docked(a6)\n'),
            ('witch space', ' move.w #1,witch_space(a6)\n'),
            ('destroyed station', ' move.w #1,station_destroyed(a6)\n'),
            ('alien station', ' move.w #dodec,station_rec+type(a6)\n'),
            ('alien mission with human model', ' move.w #$52,mission(a6)\n'),
            ('alien mission with alien model', ' move.w #$52,mission(a6)\n move.w #dodec,station_rec+type(a6)\n'),
            ('absent station', ' clr.b station_rec+flags(a6)\n')):
        case(label+': no message, latch or cosmetic RNG draw')
        emit(setup+call('comm_arrival_check')); silent()

    case('No repeated clearance while circling or leaving the close radius inside S')
    emit(call('radar_lock')); received()
    emit(' move.w comm_seed(a6),qa_saved_seed\n')
    for distance in (0, 1999, 2001, 20000, 2000):
        emit(f' move.l #{distance},station_range(a6)\n'+call('radar_lock'))
        received()
        emit(' move.w comm_seed(a6),d0\n cmp.w qa_saved_seed,d0\n bne fail\n')

    case('Expiry of the message does not rearm its arrival latch')
    emit(call('radar_lock')+' move.w #1,cockpit_on(a6)\n'+call('comm_lifetime')
         +' move.l d0,qa_time\n'+call('comm_update'))
    eq(0, 'comm_count(a6)'); eq(1, 'comm_arrival_sent(a6)')
    emit(call('radar_lock')); eq(0, 'comm_count(a6)'); eq(1, 'qa_beeps')

    case('Exact physical S exit rearms even with a stale compass and inside cargo hysteresis')
    emit(call('radar_lock')); received()
    emit(' move.l #$22500,planet_range(a6)\n clr.w radar_obj(a6)\n'+call('radar_lock'))
    eq(0, 'comm_arrival_sent(a6)'); eq(1, 'comm_count(a6)'); eq(1, 'qa_beeps')
    emit(' move.l #$224ff,planet_range(a6)\n move.w #1,radar_obj(a6)\n'+call('radar_lock'))
    received(count=2, beeps=2)

    case('Outside S cannot greet even if cached station distance is close')
    emit(' move.w #1,comm_arrival_sent(a6)\n move.l #$22501,planet_range(a6)\n'
         +call('radar_lock')); silent()

    case('Flight UI and cockpit changes preserve the sent latch and do not duplicate clearance')
    emit(call('prepare_cockpit')+call('front_view')+call('radar_lock')); received()
    emit(call('status')+call('hide_cursor')+call('radar_lock')); received()
    emit(call('prepare_cockpit')+call('front_view')+call('radar_lock')); received()

    case('Incoming clearance appends immediately in UI and evicts only the oldest queued message')
    for message in (0, 5, 14):
        emit(f' moveq #{message},d0\n move.l #$43316b00,d1\n move.l #$4a532a00,d2\n'
             +call('comm_enqueue'))
    emit(call('radar_lock')); received(count=3, beeps=4)
    eq(5, 'comm_queue+comm_message(a6)')
    eq(14, 'comm_queue+comm_size+comm_message(a6)')
    eq(0, 'comm_clock(a6)', 'l')

    for hidden in (0, 255):
        case(f'Anarchy with legal record 255, scrambled={hidden}: actual docking permission alone decides')
        emit(f' move.w #{hidden},scrambled_id(a6)\n move.w #255,police_record(a6)\n'
             ' clr.w splanet+govern(a6)\n'+call('comm_arrival_check'))
        received('comm_hidden' if hidden else '$4a532a00')

    for cockpit in (0, 1):
        for hidden in (0, 255):
            case(f'Launch then hit at 2500 waits until 2000: cockpit={cockpit}, scrambled={hidden}')
            recipient = 'comm_hidden' if hidden else '$4a532a00'
            emit(' bclr #f_sequence,user(a6)\n move.w #1,docked(a6)\n'
                 f' move.w #{hidden},scrambled_id(a6)\n'+call('launch')
                 +' lea planet_rec(a6),a5\n'+call('get_range')
                 +' lea station_rec(a6),a5\n'+call('get_range')
                 +f' move.w #{cockpit},cockpit_on(a6)\n'+call('radar_lock'))
            eq(2500, 'station_range(a6)', 'l')
            eq(0, 'no_entry(a6)'); eq(0, 'comm_arrival_sent(a6)')
            eq(1, 'comm_count(a6)'); eq(1, 'qa_beeps')
            emit(' move.w comm_seed(a6),qa_saved_seed\n')
            station_shot()
            emit(' tst.w no_entry(a6)\n beq fail\n')
            eq(10, 'police_record(a6)')
            eq(0, 'comm_arrival_sent(a6)'); eq(1, 'comm_count(a6)'); eq(1, 'qa_beeps')
            emit(call('radar_lock')+' move.w comm_seed(a6),d0\n cmp.w qa_saved_seed,d0\n bne fail\n')
            eq(0, 'comm_arrival_sent(a6)'); eq(1, 'comm_count(a6)'); eq(1, 'qa_beeps')
            emit(' move.l #2000,station_range(a6)\n'+call('radar_lock'))
            received(recipient, count=2, beeps=2, denied=True)
            for _ in range(3):
                station_shot(); emit(call('radar_lock'))
                received(recipient, count=2, beeps=2, denied=True)

    for distance in (2001, 5000):
        case(f'First hit at {distance}: immediate ban/penalty, warning deferred to 2000')
        emit(f' move.l #{distance},station_range(a6)\n')
        station_shot(); silent(); eq(10, 'police_record(a6)')
        emit(' tst.w no_entry(a6)\n beq fail\n'+call('radar_lock')); silent()
        station_shot(); silent(); eq(20, 'police_record(a6)')
        emit(' move.l #2001,station_range(a6)\n'+call('radar_lock')); silent()
        emit(' move.l #2000,station_range(a6)\n'+call('radar_lock')); received(denied=True)
        emit(' move.w comm_seed(a6),qa_saved_seed\n')
        for nearby in (1999, 2000, 2001, 5000):
            emit(f' move.l #{nearby},station_range(a6)\n'+call('radar_lock'))
            station_shot(); received(denied=True)
            emit(' move.w comm_seed(a6),d0\n cmp.w qa_saved_seed,d0\n bne fail\n')

    for cockpit in (0, 1):
        for distance in (0, 1999, 2000):
            case(f'First hit at {distance}, cockpit={cockpit}: warning arrives inside CHECK_HIT')
            emit(f' move.w #{cockpit},cockpit_on(a6)\n move.l #{distance},station_range(a6)\n')
            station_shot(); received(denied=True); eq(10, 'police_record(a6)')
            emit(call('radar_lock')); received(denied=True)

    for distance in (2000, 2001, 5000):
        case(f'Station hit at {distance}: legal penalty saturates independently of comm distance')
        emit(f' move.w #250,police_record(a6)\n move.l #{distance},station_range(a6)\n')
        station_shot(); eq(255, 'police_record(a6)')
        if distance <= 2000: received(denied=True)
        else: silent()
        emit(' tst.w no_entry(a6)\n beq fail\n')
        station_shot(); eq(255, 'police_record(a6)')
        if distance <= 2000: received(denied=True)
        else: silent()

    case('Hit warning survives expiry and UI changes; S exit rearms but distance still gates delivery')
    emit(' move.l #2000,station_range(a6)\n move.w #1,cockpit_on(a6)\n')
    station_shot(); received(denied=True)
    emit(call('comm_lifetime')+' move.l d0,qa_time\n'+call('comm_update'))
    eq(0, 'comm_count(a6)'); eq(2, 'comm_arrival_sent(a6)')
    emit(call('status')+call('hide_cursor')+call('radar_lock')
         +call('prepare_cockpit')+call('front_view'))
    station_shot()
    eq(0, 'comm_count(a6)'); eq(1, 'qa_beeps'); eq(2, 'comm_arrival_sent(a6)')
    emit(' move.l #2500,station_range(a6)\n move.l #$22500,planet_range(a6)\n'+call('radar_lock'))
    eq(0, 'comm_arrival_sent(a6)')
    emit(' tst.w no_entry(a6)\n beq fail\n move.l #$224ff,planet_range(a6)\n'
         +call('radar_lock'))
    eq(0, 'comm_count(a6)'); eq(0, 'comm_arrival_sent(a6)')
    station_shot()
    eq(0, 'comm_count(a6)'); eq(0, 'comm_arrival_sent(a6)'); eq(1, 'qa_beeps')
    emit(' move.l #1999,station_range(a6)\n'+call('radar_lock'))
    received(beeps=2, denied=True)

    for label, setup in (
            ('outside S', ' move.l #$22500,planet_range(a6)\n'),
            ('docked', ' move.w #1,docked(a6)\n'),
            ('docking frame', ' move.w #1,just_docked(a6)\n'),
            ('witch space', ' move.w #1,witch_space(a6)\n'),
            ('destroyed station', ' move.w #1,station_destroyed(a6)\n'),
            ('missing station', ' clr.b station_rec+flags(a6)\n'),
            ('alien mission', ' move.w #$52,mission(a6)\n'),
            ('alien station', ' move.w #dodec,station_rec+type(a6)\n')):
        case(f'Station hit exclusions: {label} stays silent')
        emit(setup+' move.l #1999,station_range(a6)\n')
        station_shot(); silent()

    case('Actual player shot at station sets NO_ENTRY: send denial instead of clearance, only once')
    emit(' lea station_rec(a6),a5\n move.w #1,this_obj(a6)\n'
         ' move.w #1,hit_check(a6)\n clr.w obj_hit(a6)\n move.w #5,laser_power(a6)\n'
         +call('check_hit'))
    emit(' tst.w no_entry(a6)\n beq fail\n'+call('radar_lock')); received(denied=True)
    emit(call('radar_lock')); received(denied=True)
    emit(' clr.w no_entry(a6)\n'+call('radar_lock')); received(denied=True)
    emit(' move.l #$22500,planet_range(a6)\n'+call('radar_lock')
         +' move.l #$224ff,planet_range(a6)\n'+call('radar_lock'))
    received(count=2, beeps=2, unwelcome=True)

    for distance in (1999, 2000, 2001, 5000):
        case(f'Arrival with a docking ban at {distance}: deny only inside the close approach radius')
        emit(f' move.w #1,no_entry(a6)\n move.l #{distance},station_range(a6)\n'+call('radar_lock'))
        if distance <= 2000: received(denied=True)
        else: silent()

    for distance in (1999, 2000, 2001, 5000):
        case(f'Hit after clearance at {distance}: one denial, only within 2000')
        emit(call('radar_lock')); received()
        emit(' move.w comm_seed(a6),qa_saved_seed\n')
        emit(f' move.l #{distance},station_range(a6)\n lea station_rec(a6),a5\n'
             ' move.w #1,this_obj(a6)\n move.w #1,hit_check(a6)\n clr.w obj_hit(a6)\n'
             ' move.w #5,laser_power(a6)\n'+call('check_hit'))
        if distance > 2000:
            received(); eq(10, 'police_record(a6)')
            emit(' tst.w no_entry(a6)\n beq fail\n'+call('radar_lock')); received()
            emit(' move.w comm_seed(a6),d0\n cmp.w qa_saved_seed,d0\n bne fail\n'
                 ' move.l #2001,station_range(a6)\n'+call('radar_lock')); received()
            emit(' move.l #2000,station_range(a6)\n'+call('radar_lock'))
        received(count=2, beeps=2, denied=True)
        emit(call('radar_lock')); received(count=2, beeps=2, denied=True)

    case('Thargoid-controlled station never sends a denial, even after an earlier human clearance')
    emit(call('radar_lock')); received()
    emit(' move.w #1,no_entry(a6)\n move.w #$52,mission(a6)\n'
         ' move.w #dodec,station_rec+type(a6)\n'+call('radar_lock'))
    received()

    case('Docking denial conceals a scrambled recipient and preserves the existing legal record')
    emit(' move.w #1,no_entry(a6)\n move.w #255,scrambled_id(a6)\n'
         ' move.w #77,police_record(a6)\n'+call('comm_arrival_check'))
    received('comm_hidden', denied=True); eq(77, 'police_record(a6)')

    case('Leaving S rearms the greeting without clearing a docking ban')
    emit(' move.w #1,no_entry(a6)\n move.w #1,comm_arrival_sent(a6)\n'
         ' move.l #$22500,planet_range(a6)\n'+call('radar_lock'))
    eq(0, 'comm_arrival_sent(a6)'); eq(1, 'no_entry(a6)')
    emit(' move.l #$224ff,planet_range(a6)\n'+call('radar_lock')); received(denied=True)

    case('Arrival preserves data/address registers and gameplay/registration RNGs')
    emit(' move.l #$12345678,random_seed(a6)\n move.w #99,registration_state(a6)\n'
         ' move.l #$12345678,d0\n move.l #$23456789,d1\n move.l #$34567890,d2\n'
         ' lea station_rec(a6),a4\n move.l a4,a5\n'+call('comm_arrival_check'))
    eq('$12345678','d0','l'); eq('$23456789','d1','l'); eq('$34567890','d2','l')
    emit(' cmpa.l a4,a5\n bne fail\n')
    eq('$12345678','random_seed(a6)','l'); eq(99,'registration_state(a6)')
    received()

    case('250 separately rearmed approaches choose all ten arrival texts exactly 25 times')
    emit(' move.w #1,comm_seed(a6)\n move.w #249,d7\nqa_arrival_distribution:\n'
         ' move.l #$22500,planet_range(a6)\n'+call('comm_arrival_check')
         +' clr.w comm_count(a6)\n move.l #$224ff,planet_range(a6)\n'
         +call('comm_arrival_check'))
    eq(1, 'comm_count(a6)'); eq(1, 'comm_arrival_sent(a6)')
    emit(' move.w comm_queue+comm_message(a6),d0\n sub.w #comm_arrival_text,d0\n'
         ' cmp.w #9,d0\n bhi fail\n add.w d0,d0\n lea qa_arrival_histogram,a0\n'
         ' addq.w #1,(a0,d0.w)\n dbra d7,qa_arrival_distribution\n')
    for index in range(10): eq(25, f'qa_arrival_histogram+{index*2}')
    eq(250, 'qa_beeps'); eq(1, 'comm_seed(a6)')

    case('255 separately rearmed denied approaches choose all five warnings exactly 51 times')
    emit(' move.w #1,no_entry(a6)\n move.w #1,comm_seed(a6)\n move.w #254,d7\n'
         'qa_denied_distribution:\n move.l #$22500,planet_range(a6)\n'+call('comm_arrival_check')
         +' clr.w comm_count(a6)\n move.l #$224ff,planet_range(a6)\n'+call('comm_arrival_check'))
    eq(1, 'comm_count(a6)'); eq(2, 'comm_arrival_sent(a6)')
    emit(' move.w comm_queue+comm_message(a6),d0\n sub.w #comm_denied_text,d0\n'
         ' cmp.w #4,d0\n bhi fail\n add.w d0,d0\n lea qa_denied_histogram,a0\n'
         ' addq.w #1,(a0,d0.w)\n dbra d7,qa_denied_distribution\n')
    for index in range(5): eq(51, f'qa_denied_histogram+{index*2}')
    eq(255, 'qa_beeps'); eq(1, 'comm_seed(a6)')

    for name, _ in hooks:
        addr = s[name]
        emit(f' move.l qa_arrival_saved_{name},${addr:x}\n'
             f' move.w qa_arrival_saved_{name}+4,${addr+4:x}\n')
    tail += ('qa_now:\n move.l qa_time,d0\n rts\nqa_beep:\n addq.w #1,qa_beeps\n rts\n'
             'qa_in_sights:\n moveq #1,d0\n rts\nqa_time: dc.l 0\nqa_beeps: dc.w 0\n'
             'qa_saved_seed: dc.w 0\nqa_arrival_histogram: ds.w 10\nqa_denied_histogram: ds.w 5\n'
             'qa_unwelcome_histogram: ds.w 10\n')
    return prefix, ''.join(out), tail, names
