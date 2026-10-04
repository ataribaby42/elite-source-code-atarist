"""Exercise station departure greetings through the real launch entry points."""
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
             ' clr.w docked(a6)\n clr.w cockpit_on(a6)\n clr.w scrambled_id(a6)\n'
             ' clr.l qa_time\n clr.w galaxy_no(a6)\n move.w #107,current(a6)\n'
             ' move.l #$4a532a00,player_registration(a6)\n'
             + call('comm_reset') + ' clr.w qa_beeps\n')

    def message(recipient, npc=False, player=True):
        eq(1, 'comm_count(a6)'); eq(1, 'qa_beeps')
        eq(int(player and not npc), 'comm_queue+comm_to_player(a6)')
        emit(' cmp.w #comm_departure_text,comm_queue+comm_message(a6)\n blo fail\n'
             ' cmp.w #comm_arrival_text,comm_queue+comm_message(a6)\n bhs fail\n')
        eq('$43316b00', 'comm_queue+comm_sender(a6)', 'l')
        if npc:
            emit(f' move.l {recipient},d0\n beq fail\n'
                 ' cmp.l comm_queue+comm_recipient(a6),d0\n bne fail\n')
        else:
            eq(recipient, 'comm_queue+comm_recipient(a6)', 'l')

    hooks = [('comm_now', 'qa_now'), ('comm_arrival_sound', 'qa_beep'),
             ('random', 'qa_random'), ('rand', 'qa_rand'),
             ('ai_laser_roll', 'qa_loadout_roll')]
    emit(call('hide_cursor') + ' clr.w display_clock(a6)\n clr.w player_ship(a6)\n'
         + call('ship_apply'))
    for name, label in hooks:
        addr = s[name]
        emit(f' move.l ${addr:x},qa_departure_saved_{name}\n'
             f' move.w ${addr+4:x},qa_departure_saved_{name}+4\n'
             f' move.w #$4ef9,${addr:x}\n move.l #{label},${addr+2:x}\n')
        tail += f'qa_departure_saved_{name}: ds.b 6\n'

    for cockpit in (0, 1):
        for model in range(5):
            case(f'Trader model {model} leaves station in cockpit={cockpit}: one greeting to its new ID')
            fraction = 65535 if model == 4 else model * 16384
            emit(f' move.w #{fraction},qa_fraction\n move.w #{cockpit},cockpit_on(a6)\n'
                 ' move.w #1,radar_obj(a6)\n' + call('create_trader'))
            message('objects+obj_len*3+registration_id(a6)', npc=True)
            eq('log_launch', 'objects+obj_len*3+logic(a6)')
        for model in (0, 1):
            case(f'Shuttle selection {model} leaves station in cockpit={cockpit}: one greeting')
            emit(f' move.w #{model},qa_roll\n move.w #{cockpit},cockpit_on(a6)\n'
                 ' move.w #1,radar_obj(a6)\n' + call('launch_shuttle'))
            message('objects+obj_len*3+registration_id(a6)', npc=True)

    for mission, hunt in ((0, 0), (0, 1), (0x52, 0)):
        case(f'Police launch, mission {mission:02X}, hunt={hunt}: no departure greeting')
        emit(f' move.w #{mission},mission(a6)\n move.w #{hunt},police_hunt(a6)\n'
             ' move.w #1,launch_count(a6)\n move.w #1,launch_rate(a6)\n'
             + call('launch_vipers'))
        eq(0, 'comm_count(a6)'); eq(0, 'qa_beeps'); eq(0, 'comm_seed(a6)')

    for model in range(5):
        case(f'Deep-space trader model {model}: no station departure greeting')
        emit(f' move.w #{65535 if model == 4 else model*16384},qa_fraction\n'
             + call('create_trader'))
        eq(0, 'comm_count(a6)'); eq(0, 'qa_beeps'); eq(0, 'comm_seed(a6)')

    for label, setup in (
            ('destroyed station', ' move.w #1,station_destroyed(a6)\n'),
            ('alien station', ' move.w #dodec,station_rec+type(a6)\n'),
            ('alien mission', ' move.w #$52,mission(a6)\n'),
            ('missing station', ' clr.b station_rec+flags(a6)\n'),
            ('witch space', ' move.w #1,witch_space(a6)\n')):
        case(label + ': no civilian departure greeting')
        emit(setup + ' move.w #1,radar_obj(a6)\n' + call('create_trader'))
        eq(0, 'comm_count(a6)'); eq(0, 'qa_beeps'); eq(0, 'comm_seed(a6)')

    for routine, setup in (
            ('create_trader', ' bsr qa_fill\n move.w #1,radar_obj(a6)\n'),
            ('launch_shuttle', ' bsr qa_fill\n move.w #1,radar_obj(a6)\n'),
            ('create_trader', ' move.w #1,radar_obj(a6)\n move.l #2000,station_range(a6)\n'),
            ('launch_shuttle', ' move.w #1,radar_obj(a6)\n move.l #1000,station_range(a6)\n')):
        case(routine + ': blocked launch does not send a greeting; ' + setup.strip())
        emit(setup + call(routine))
        eq(0, 'comm_count(a6)'); eq(0, 'qa_beeps'); eq(0, 'comm_seed(a6)')

    for hidden in (0, 255):
        for mission in (0, 0x16, 0x30, 0x52, 0x53):
            case(f'Player launch: mission {mission:02X}, scrambled={hidden}; reset, recipient and mission progression')
            emit(' bclr #f_sequence,user(a6)\n move.w #1,docked(a6)\n'
                 ' moveq #0,d0\n move.l #$43316b00,d1\n move.l #$4a532a00,d2\n'
                 + call('comm_enqueue') + ' clr.w qa_beeps\n'
                 f' move.w #{hidden},scrambled_id(a6)\n move.w #{mission},mission(a6)\n'
                 + call('launch'))
            eq(0, 'docked(a6)')
            eq(0x17 if mission == 0x16 else mission, 'mission(a6)')
            if mission == 0x52:
                eq(0, 'comm_count(a6)'); eq(0, 'qa_beeps'); eq(0, 'comm_seed(a6)')
            else:
                message('comm_hidden' if hidden else '$4a532a00')
            emit(call('launch'))  # In-flight view shortcut must not repeat it.
            eq(0 if mission == 0x52 else 1, 'comm_count(a6)')
            eq(0 if mission == 0x52 else 1, 'qa_beeps')

    for role, recipient in (('typ_trader', '$41427f00'), ('typ_pirate', 'comm_hidden')):
        case(f'Anarchy greeting, {role}: identity snapshot, registers and gameplay/registration RNGs unchanged')
        emit(' clr.w splanet+govern(a6)\n lea objects+obj_len*3(a6),a4\n'
             f' move.w #cobra,type(a4)\n move.w #{role},ship_type(a4)\n'
             ' move.l #$41427f00,registration_id(a4)\n'
             ' move.l #$12345678,random_seed(a6)\n move.w #99,registration_state(a6)\n'
             ' move.l #$12345678,d0\n move.l #$23456789,d1\n move.l #$34567890,d2\n'
             + call('comm_departure_ship'))
        eq('$12345678', 'd0', 'l'); eq('$23456789', 'd1', 'l'); eq('$34567890', 'd2', 'l')
        message(recipient, player=False)
        eq('$12345678', 'random_seed(a6)', 'l'); eq(99, 'registration_state(a6)')
        emit(' tst.w comm_seed(a6)\n beq fail\n')
        emit(' clr.l registration_id(a4)\n')
        eq(recipient, 'comm_queue+comm_recipient(a6)', 'l')

    for recipient in ('ship', 'player'):
        case(f'{recipient} departure: 250 arrivals select every greeting exactly 25 times without changing gameplay RNG')
        emit(' lea objects+obj_len*3(a6),a4\n move.w #cobra,type(a4)\n'
             ' move.w #typ_trader,ship_type(a4)\n move.l #$41427f00,registration_id(a4)\n'
             ' move.l #$12345678,random_seed(a6)\n move.w #99,registration_state(a6)\n'
             ' move.w #1,comm_seed(a6)\n')
        for offset in range(0, 20, 4):
            emit(f' clr.l qa_departure_histogram+{offset}\n')
        emit(f' move.w #249,d7\nqa_distribution_{recipient}:\n clr.w comm_count(a6)\n'
             + call('comm_departure_' + recipient))
        eq(1, 'comm_count(a6)')
        eq('$43316b00', 'comm_queue+comm_sender(a6)', 'l')
        eq('$41427f00' if recipient == 'ship' else '$4a532a00',
           'comm_queue+comm_recipient(a6)', 'l')
        emit(' move.w comm_queue+comm_message(a6),d0\n sub.w #comm_departure_text,d0\n'
             ' cmp.w #9,d0\n bhi fail\n add.w d0,d0\n lea qa_departure_histogram,a0\n'
             f' addq.w #1,(a0,d0.w)\n dbra d7,qa_distribution_{recipient}\n')
        for offset in range(10):
            eq(25, f'qa_departure_histogram+{offset*2}')
        eq(250, 'qa_beeps'); eq(1, 'comm_seed(a6)')
        eq('$12345678', 'random_seed(a6)', 'l'); eq(99, 'registration_state(a6)')

    for name, _ in hooks:
        addr = s[name]
        emit(f' move.l qa_departure_saved_{name},${addr:x}\n'
             f' move.w qa_departure_saved_{name}+4,${addr+4:x}\n')
    tail += 'qa_now:\n move.l qa_time,d0\n rts\nqa_beep:\n addq.w #1,qa_beeps\n rts\n'
    tail += 'qa_time: dc.l 0\nqa_beeps: dc.w 0\nqa_departure_histogram: ds.w 10\n'
    return prefix, ''.join(out), tail, names
