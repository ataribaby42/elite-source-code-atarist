"""Cloaked S-entry scans stay pending without bypassing the exit hysteresis."""
from native_station_radio import make_suite as station_suite


def make_suite(root, s):
    prefix, _, tail, _ = station_suite(root, s)
    out, names = [], []
    emit = out.append
    call = lambda n: f' jsr ${s[n]:x}\n'

    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')

    def case(name, cockpit=0, hidden=0, government=7):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_radio_world\n'
             ' move.w #1,equip+cloaking_device(a6)\n'
             ' move.l #1000000,hold+slaves*4(a6)\n'
             f' move.w #{cockpit},cockpit_on(a6)\n move.w #{hidden},scrambled_id(a6)\n'
             f' move.w #{government},splanet+govern(a6)\n')

    def step(distance=None):
        if distance is not None: emit(f' move.l #${distance:x},planet_range(a6)\n')
        emit(call('radar_lock'))

    def toggle():
        emit(call('cloaking_toggle'))

    def pending(record=0, count=0):
        eq(0, 'checkpoint+1(a6)', 'b'); eq(record, 'police_record(a6)')
        eq(count, 'comm_count(a6)'); eq(count, 'qa_beeps')

    def checked(record=4, count=1, hidden=0):
        eq(255, 'checkpoint+1(a6)', 'b'); eq(record, 'police_record(a6)')
        eq(count, 'comm_count(a6)'); eq(count, 'qa_beeps')
        if count:
            q = f'comm_queue+{count-1}*comm_size+'
            emit(f' cmp.w #comm_contraband_text,{q}comm_message(a6)\n blo fail\n'
                 f' cmp.w #comm_contraband_text+10,{q}comm_message(a6)\n bhs fail\n')
            eq('comm_hidden' if hidden else '$4a532a00', q+'comm_recipient(a6)', 'l')
            eq(1, q+'comm_to_player(a6)')

    emit(call('hide_cursor')+' clr.w display_clock(a6)\n clr.w player_ship(a6)\n'+call('ship_apply'))
    hooks = [('comm_now', 'qa_radio_now'), ('comm_arrival_sound', 'qa_radio_beep'),
             ('check_police', 'qa_radio_police')]
    for name, label in hooks:
        addr = s[name]
        emit(f' move.l ${addr:x},qa_radio_saved_{name}\n move.w ${addr+4:x},qa_radio_saved_{name}+4\n'
             f' move.w #$4ef9,${addr:x}\n move.l #{label},${addr+2:x}\n')

    for cockpit in (0, 1):
        for hidden in (0, 255):
            for government in range(8):
                case(f'Cloaked entry deferred to actual uncloak: UI/3D={cockpit}, ID={hidden}, gov={government}',
                     cockpit, hidden, government)
                toggle(); step(); pending()
                eq(1, 'radar_obj(a6)'); eq(0, 'comm_arrival_sent(a6)'); eq(0, 'no_entry(a6)')
                eq(1, 'qa_police_calls'); eq(0, 'qa_seen_record')
                eq(0, 'comm_seed(a6)')
                for _ in range(2):
                    step(); pending()
                emit(' clr.w radar_obj(a6)\n')  # Flight-menu compass reset is not a new entry.
                step(); pending(); eq(1, 'radar_obj(a6)')
                toggle(); step(); checked(hidden=hidden)
                eq(1, 'qa_police_calls')  # Keep the independent once-per-system decision.
                eq(0, 'no_entry(a6)'); eq(0, 'comm_arrival_sent(a6)')
                toggle(); step(); checked(hidden=hidden)
                toggle(); step(); checked(hidden=hidden)
                eq(1, 'qa_police_calls')

    for distance in (0x22500, 0x226ff, 0x22700, 0x22701):
        for cloaked_exit in (False, True):
            case(f'Completed scan: exit at {distance:x}, cloaked exit={cloaked_exit}')
            step(); checked()
            if cloaked_exit: toggle()
            step(distance)
            eq(0, 'radar_obj(a6)')
            eq(0 if distance >= 0x22700 else 255, 'checkpoint+1(a6)', 'b')
            if not cloaked_exit: toggle()
            step(0x224ff)
            if distance >= 0x22700: pending(record=4, count=1)
            else: checked()
            toggle(); step()
            checked(record=8 if distance >= 0x22700 else 4,
                    count=2 if distance >= 0x22700 else 1)
            eq(1, 'qa_police_calls')

    for distance in (0x22500, 0x226ff, 0x22700, 0x22701):
        case(f'Pending scan: uncloak outside S at {distance:x}; inspect only on re-entry')
        toggle(); step(); pending()
        step(distance); pending(); eq(0, 'radar_obj(a6)')
        toggle(); step(); pending()
        step(0x224ff); checked()
        step(); checked()

    case('Cargo removed while cloaked is absent at the deferred inspection')
    toggle(); step(); pending()
    emit(' clr.l hold+slaves*4(a6)\n')
    toggle(); step(); checked(record=0, count=0)
    emit(' move.l #1000000,hold+slaves*4(a6)\n')
    toggle(); step(); toggle(); step(); checked(record=0, count=0)

    case('New cargo collected while cloaked is included when visibility returns')
    emit(' clr.l hold+slaves*4(a6)\n')
    toggle(); step(); pending()
    emit(' move.l #2000000,hold+narcotics*4(a6)\n')
    toggle(); step(); checked(record=8)

    case('A capped legal record still waits until uncloak before sending one warning')
    emit(' move.w #255,police_record(a6)\n')
    toggle(); step(); pending(record=255)
    toggle(); step(); checked(record=255)
    step(); checked(record=255)

    for hidden in (0, 255):
        case(f'Deferred inspection precedes close-approach clearance/denial, ID={hidden}', hidden=hidden)
        emit(' move.l #2000,station_range(a6)\n')
        toggle(); step(); pending()
        # Scrambled-ID docking policy remains independent of cargo visibility.
        eq(0, 'comm_arrival_sent(a6)')
        toggle(); step()
        eq(4, 'police_record(a6)'); eq(255, 'checkpoint+1(a6)', 'b')
        eq(2, 'comm_count(a6)'); eq(2, 'qa_beeps')
        eq(2 if hidden else 1, 'comm_arrival_sent(a6)')
        begin = 'comm_denied_text' if hidden else 'comm_unwelcome_text'
        count = 5 if hidden else 10
        emit(f' cmp.w #{begin},comm_queue+comm_size+comm_message(a6)\n blo fail\n'
             f' cmp.w #{begin}+{count},comm_queue+comm_size+comm_message(a6)\n bhs fail\n')
        step(); eq(2, 'qa_beeps'); eq(4, 'police_record(a6)')

    case('A destroyed station cannot complete a pending scan after uncloak')
    toggle(); step(); pending()
    emit(' move.w #1,station_destroyed(a6)\n')
    toggle(); step(); pending(); eq(0, 'radar_obj(a6)')

    case('Alien mission station remains silent after a deferred scan')
    emit(' move.w #$52,mission(a6)\n move.w #dodec,station_rec+type(a6)\n')
    toggle(); step(); pending()
    toggle(); step(); checked(record=4, count=0)
    eq(0x52, 'mission(a6)')

    for consumed in (0, 255):
        case(f'Reset clears a pending or completed visit, prior cargo checkpoint={consumed}')
        emit(f' move.w #$ff00+{consumed},checkpoint(a6)\n move.w #-1,cloaking_on(a6)\n'
             +call('reset_system'))
        eq(0, 'checkpoint(a6)'); eq(0, 'cloaking_on(a6)')

    case('Real launch remains exempt; toggling cloak inside S does not create a scan')
    emit(' move.w #1,docked(a6)\n bclr #f_sequence,user(a6)\n'+call('launch'))
    eq('$ffff', 'checkpoint(a6)'); eq(0, 'police_record(a6)')
    emit(' move.l #$224ff,planet_range(a6)\n move.l #5000,station_range(a6)\n')
    eq(1, 'comm_count(a6)'); eq(1, 'qa_beeps')
    toggle(); step(); toggle(); step()
    eq(0, 'police_record(a6)'); eq(1, 'comm_count(a6)'); eq(1, 'qa_beeps')

    for name, _ in hooks:
        addr = s[name]
        emit(f' move.l qa_radio_saved_{name},${addr:x}\n move.w qa_radio_saved_{name}+4,${addr+4:x}\n')
    return prefix, ''.join(out), tail, names
