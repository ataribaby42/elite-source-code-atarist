"""Execute departure selection and real S-entry cargo warnings on the 68000."""
from native_spawn_paths import make_suite as spawn_suite


def make_suite(root, s):
    prefix, _, tail, _ = spawn_suite(root, s)
    out, names = [], []
    emit = out.append
    call = lambda n: f' jsr ${s[n]:x}\n'

    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')

    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_radio_world\n')

    def message(first, count=1, hidden=False):
        eq(count, 'comm_count(a6)'); eq(count, 'qa_beeps')
        q = f'comm_queue+{count-1}*comm_size+'
        eq('$43316b00', q+'comm_sender(a6)', 'l')
        eq('comm_hidden' if hidden else '$4a532a00', q+'comm_recipient(a6)', 'l')
        eq(1, q+'comm_to_player(a6)')
        emit(f' cmp.w #{first},{q}comm_message(a6)\n blo fail\n'
             f' cmp.w #{first}+10,{q}comm_message(a6)\n bhs fail\n')

    def silent():
        eq(0, 'comm_count(a6)'); eq(0, 'qa_beeps'); eq(0, 'comm_seed(a6)')

    emit(call('hide_cursor')+' clr.w display_clock(a6)\n clr.w player_ship(a6)\n'+call('ship_apply'))
    hooks = [('comm_now', 'qa_radio_now'), ('comm_arrival_sound', 'qa_radio_beep'),
             ('check_police', 'qa_radio_police')]
    for name, label in hooks:
        addr = s[name]
        emit(f' move.l ${addr:x},qa_radio_saved_{name}\n move.w ${addr+4:x},qa_radio_saved_{name}+4\n'
             f' move.w #$4ef9,${addr:x}\n move.l #{label},${addr+2:x}\n')
        tail += f'qa_radio_saved_{name}: ds.b 6\n'

    for record in (0, 1, 49, 50, 255):
        for government in range(8):
            for hidden in (False, True):
                case(f'Player departure: record={record}, government={government}, hidden={hidden}')
                emit(f' move.w #{record},police_record(a6)\n move.w #{government},splanet+govern(a6)\n'
                     f' move.w #{255 if hidden else 0},scrambled_id(a6)\n'+call('comm_departure_player'))
                message('comm_departure_caution_text' if record and government else 'comm_departure_text', hidden=hidden)
                eq(record, 'police_record(a6)'); eq(0, 'no_entry(a6)'); eq(0, 'comm_arrival_sent(a6)')

    for record in (1, 255):
        case(f'Civilian AI departure keeps the original set with player record={record}')
        emit(f' move.w #{record},police_record(a6)\n lea objects+obj_len*3(a6),a4\n'
             ' move.w #cobra,type(a4)\n move.w #typ_trader,ship_type(a4)\n'
             ' move.l #$41427f00,registration_id(a4)\n'+call('comm_departure_ship'))
        eq(1, 'comm_count(a6)'); eq(1, 'qa_beeps'); eq(0, 'comm_queue+comm_to_player(a6)')
        eq('$41427f00', 'comm_queue+comm_recipient(a6)', 'l')
        emit(' cmp.w #comm_departure_text,comm_queue+comm_message(a6)\n blo fail\n'
             ' cmp.w #comm_arrival_text,comm_queue+comm_message(a6)\n bhs fail\n')

    for mission in (0, 0x16, 0x30, 0x52, 0x53):
        case(f'Real offender launch retains mission progression and one greeting: {mission:02x}')
        emit(f' move.w #{mission},mission(a6)\n move.w #1,police_record(a6)\n'
             ' move.w #1,docked(a6)\n bclr #f_sequence,user(a6)\n'+call('launch'))
        eq(0x17 if mission == 0x16 else mission, 'mission(a6)'); eq(1, 'police_record(a6)')
        if mission == 0x52:
            silent()
        else:
            message('comm_departure_caution_text')
        emit(call('launch')); eq(0 if mission == 0x52 else 1, 'qa_beeps')

    # All hold slots, including mission freight. One whole tonne is inspected.
    for index in range(20):
        case(f'S-entry cargo type {index}: law factors and mission freight exclusions')
        emit(f' move.l #1000000,hold+{index}*4(a6)\n'+call('radar_lock'))
        penalty = 4 if index in (3, 6) else 2 if index == 10 else 0
        if penalty:
            message('comm_contraband_text')
        else:
            silent()
        eq(penalty, 'police_record(a6)'); eq(penalty, 'qa_seen_record')
        eq(1, 'qa_police_calls'); eq(0, 'comm_arrival_sent(a6)'); eq(0, 'no_entry(a6)')
        eq(1000000, f'hold+{index}*4(a6)', 'l')

    for amount, penalty in ((0,0), (999999,0), (1000000,4), (1999999,4), (2000000,8), (0xffffffff,255)):
        case(f'Cargo scan whole-tonne rounding, mass={amount}')
        emit(f' move.l #${amount:x},hold+narcotics*4(a6)\n'+call('radar_lock'))
        if penalty: message('comm_contraband_text')
        else: silent()
        eq(penalty, 'police_record(a6)'); eq(f'${amount:x}', 'hold+narcotics*4(a6)', 'l')

    for government in range(8):
        case(f'Cargo inspection still applies in government={government}, with a hidden player ID')
        emit(f' move.w #{government},splanet+govern(a6)\n move.w #255,scrambled_id(a6)\n'
             ' move.l #1000000,hold+firearms*4(a6)\n'+call('radar_lock'))
        message('comm_contraband_text', hidden=True); eq(2, 'police_record(a6)')
        eq(0, 'no_entry(a6)'); eq(0, 'comm_arrival_sent(a6)')

    for record in (0, 250, 255):
        case(f'Mixed contraband sends only one warning, initial record={record}')
        emit(f' move.w #{record},police_record(a6)\n'
             ' move.l #1000000,hold+slaves*4(a6)\n move.l #2000000,hold+narcotics*4(a6)\n'
             ' move.l #3000000,hold+firearms*4(a6)\n'+call('radar_lock'))
        message('comm_contraband_text'); eq(min(255, record+18), 'police_record(a6)')
        eq(min(255, record+18), 'qa_seen_record')

    exclusions = [
        ('cloak', ' move.w #1,cloaking_on(a6)\n'),
        ('alien mission', ' move.w #$52,mission(a6)\n'),
        ('alien model', ' move.w #dodec,station_rec+type(a6)\n'),
        ('destroyed station', ' move.w #1,station_destroyed(a6)\n'),
        ('missing station', ' clr.b station_rec+flags(a6)\n'),
        ('witch space', ' move.w #1,witch_space(a6)\n'),
    ]
    for label, setup in exclusions:
        for event in ('comm_departure_player', 'check_cargo'):
            case(f'{event}, {label}: no message, beep or cosmetic random draw')
            emit(setup+' move.w #1,police_record(a6)\n move.l #1000000,hold+slaves*4(a6)\n'+call(event))
            silent(); eq(5 if event == 'check_cargo' else 1, 'police_record(a6)')

    for cockpit in (0, 1):
        case(f'S-entry warning and checkpoint persist across frames and compass reset, cockpit={cockpit}')
        emit(f' move.w #{cockpit},cockpit_on(a6)\n move.l #1000000,hold+slaves*4(a6)\n'+call('radar_lock'))
        message('comm_contraband_text'); eq(4, 'police_record(a6)')
        emit(' move.w comm_seed(a6),qa_saved_seed\n')
        for _ in range(3):
            emit(' clr.w radar_obj(a6)\n'+call('radar_lock'))
            message('comm_contraband_text'); eq(4, 'police_record(a6)')
            emit(' move.w comm_seed(a6),d0\n cmp.w qa_saved_seed,d0\n bne fail\n')
        for distance in (0x22500, 0x226ff):
            emit(f' move.l #${distance:x},planet_range(a6)\n'+call('radar_lock')
                 +' move.l #$224ff,planet_range(a6)\n'+call('radar_lock'))
            message('comm_contraband_text'); eq(4, 'police_record(a6)')
        emit(' move.l #$22700,planet_range(a6)\n'+call('radar_lock')
             +' move.l #$224ff,planet_range(a6)\n'+call('radar_lock'))
        message('comm_contraband_text', count=2); eq(8, 'police_record(a6)'); eq(1, 'qa_police_calls')

    case('Entry at close range adds cargo warning before the existing docking clearance')
    emit(' move.l #1000000,hold+slaves*4(a6)\n move.l #2000,station_range(a6)\n'+call('radar_lock'))
    eq(2, 'comm_count(a6)'); eq(2, 'qa_beeps'); eq(1, 'comm_arrival_sent(a6)')
    emit(' cmp.w #comm_contraband_text,comm_queue+comm_message(a6)\n blo fail\n'
         ' cmp.w #comm_unwelcome_text,comm_queue+comm_size+comm_message(a6)\n blo fail\n'
         ' cmp.w #comm_unwelcome_text+10,comm_queue+comm_size+comm_message(a6)\n bhs fail\n')
    eq(4, 'police_record(a6)'); eq(0, 'no_entry(a6)')

    case('Scrambled close approach retains the existing denial after the separate cargo warning')
    emit(' move.w #255,scrambled_id(a6)\n move.l #1000000,hold+slaves*4(a6)\n'
         ' move.l #2000,station_range(a6)\n'+call('radar_lock'))
    eq(2, 'comm_count(a6)'); eq(2, 'qa_beeps'); eq(2, 'comm_arrival_sent(a6)')
    emit(' tst.w no_entry(a6)\n beq fail\n'
         ' cmp.w #comm_denied_text,comm_queue+comm_size+comm_message(a6)\n blo fail\n'
         ' cmp.w #comm_unwelcome_text,comm_queue+comm_size+comm_message(a6)\n bhs fail\n')
    eq(4, 'police_record(a6)')

    case('UI overflow retains the new cargo warning and starts a fresh seven-second head interval')
    for i in (0, 5, 15):
        emit(f' move.w #{i},d0\n move.l #$43316b00,d1\n move.l #$4a532a00,d2\n'+call('comm_enqueue_player'))
    emit(' move.l #9999,qa_time\n move.l #1000000,hold+slaves*4(a6)\n'+call('radar_lock'))
    eq(3, 'comm_count(a6)'); eq(4, 'qa_beeps'); eq(5, 'comm_queue+comm_message(a6)')
    eq(15, 'comm_queue+comm_size+comm_message(a6)'); eq(0, 'comm_clock(a6)', 'l')
    emit(' move.w #1,cockpit_on(a6)\n'+call('comm_lifetime')+' add.l d0,qa_time\n'+call('comm_update'))
    eq(2, 'comm_count(a6)'); eq(15, 'comm_queue+comm_message(a6)')

    case('Purchase penalty does not send the S-entry cargo warning')
    emit(' lea products+slaves*product_len(a6),a5\n moveq #2,d1\n'+call('illegal'))
    silent(); eq(8, 'police_record(a6)')

    case('Cargo warning preserves all registers, market, docking flags and gameplay RNG')
    emit(' move.l #1000000,hold+slaves*4(a6)\n'
         ' move.l #$12345678,random_seed(a6)\n move.w #99,registration_state(a6)\n'
         ' move.w #1,no_entry(a6)\n move.w #2,comm_arrival_sent(a6)\n'
         ' move.w #42,products+slaves*product_len+price(a6)\n'
         ' move.l #$12345678,d0\n move.l #$23456789,d1\n move.l #$34567890,d2\n'
         ' move.l #$456789ab,d7\n lea hold(a6),a0\n lea products(a6),a1\n'+call('check_cargo'))
    for val, reg in (('$12345678','d0'), ('$23456789','d1'), ('$34567890','d2'), ('$456789ab','d7')):
        eq(val, reg, 'l')
    emit(' lea hold(a6),a2\n cmpa.l a2,a0\n bne fail\n'
         ' lea products(a6),a2\n cmpa.l a2,a1\n bne fail\n')
    eq('$12345678', 'random_seed(a6)', 'l'); eq(99, 'registration_state(a6)')
    eq(42, 'products+slaves*product_len+price(a6)'); eq(1, 'no_entry(a6)'); eq(2, 'comm_arrival_sent(a6)')
    message('comm_contraband_text')

    for name, first in (('comm_departure_player', 'comm_departure_caution_text'),
                        ('check_cargo', 'comm_contraband_text')):
        case(f'{name}: all ten variants exactly 25 times in 250 draws, with no gameplay RNG changes')
        emit(' move.w #255,police_record(a6)\n move.l #1000000,hold+slaves*4(a6)\n'
             ' move.l #$12345678,random_seed(a6)\n move.w #99,registration_state(a6)\n'
             ' move.w #1,comm_seed(a6)\n lea qa_histogram,a0\n moveq #9,d0\n'
             f'qa_clear_{name}:\n clr.w (a0)+\n dbra d0,qa_clear_{name}\n'
             f' move.w #249,d7\nqa_dist_{name}:\n clr.w comm_count(a6)\n'+call(name)
             +f' move.w comm_queue+comm_message(a6),d0\n sub.w #{first},d0\n'
             ' cmp.w #9,d0\n bhi fail\n add.w d0,d0\n lea qa_histogram,a0\n'
             f' addq.w #1,(a0,d0.w)\n dbra d7,qa_dist_{name}\n')
        for i in range(10): eq(25, f'qa_histogram+{i*2}')
        eq(250, 'qa_beeps'); eq(1, 'comm_seed(a6)'); eq(255, 'police_record(a6)')
        eq('$12345678','random_seed(a6)','l'); eq(99,'registration_state(a6)')

    for name, _ in hooks:
        addr = s[name]
        emit(f' move.l qa_radio_saved_{name},${addr:x}\n move.w qa_radio_saved_{name}+4,${addr+4:x}\n')
    tail += '''qa_radio_world:
 bsr qa_world
 clr.w docked(a6)
 clr.w just_docked(a6)
 clr.w no_entry(a6)
 clr.w cockpit_on(a6)
 clr.w scrambled_id(a6)
 clr.w police_record(a6)
 clr.w checkpoint(a6)
 clr.w radar_obj(a6)
 move.l #$224ff,planet_range(a6)
 move.l #5000,station_range(a6)
 lea hold(a6),a0
 lea products(a6),a1
 moveq #max_products-1,d0
.clear:
 clr.l (a0)+
 clr.w naughty(a1)
 lea product_len(a1),a1
 dbra d0,.clear
 move.w #4,products+slaves*product_len+naughty(a6)
 move.w #4,products+narcotics*product_len+naughty(a6)
 move.w #2,products+firearms*product_len+naughty(a6)
 clr.l qa_time
 clr.w galaxy_no(a6)
 move.w #107,current(a6)
 move.l #$4a532a00,player_registration(a6)
'''+call('comm_reset')+''' clr.w qa_beeps
 clr.w qa_police_calls
 move.w #-1,qa_seen_record
 rts
qa_radio_now:
 move.l qa_time,d0
 rts
qa_radio_beep:
 addq.w #1,qa_beeps
 rts
qa_radio_police:
 addq.w #1,qa_police_calls
 move.w police_record(a6),qa_seen_record
 rts
qa_time: dc.l 0
qa_beeps: dc.w 0
qa_police_calls: dc.w 0
qa_seen_record: dc.w 0
qa_saved_seed: dc.w 0
qa_histogram: ds.w 10
'''
    return prefix, ''.join(out), tail, names
