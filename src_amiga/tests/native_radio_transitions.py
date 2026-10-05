"""Recipient pool churn, real cloak actions and repeated complete greeting events."""
from native_ai_radio import make_suite as base_suite
from native_trader_greetings import seed_for


def distribution(pool, events=16384):
    """Independent expected histogram for successive complete greeting events."""
    seed, silent, histogram = 31, 0, [0]*pool
    for _ in range(events):
        while True:
            seed = (25173*seed+13849) % 65536
            if seed < 65520:
                break
        if seed % 20 < 10:
            silent += 1
            continue
        if pool > 1:
            width = 65536 // pool
            while True:
                seed = (25173*seed+13849) % 65536
                if seed < width*pool:
                    break
            index = seed // width
        else:
            index = 0
        histogram[index] += 1
    return seed, silent, histogram


def make_suite(root, s):
    prefix, _, tail, _ = base_suite(root, s)
    out, names = [], []
    emit = out.append
    call = lambda name: f' jsr ${s[name]:x}\n'

    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')

    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n'
             ' move.w #1,equip+cloaking_device(a6)\n')

    def spawn(slot=3, role='typ_trader'):
        emit(f' lea objects+obj_len*{slot}(a6),a4\n move.b #1,flags(a4)\n'
             ' move.w #cobra,type(a4)\n'+call('create_object')+
             f' move.w #{role},ship_type(a4)\n move.w #log_cruise,logic(a4)\n'
             ' move.l #no_target,target(a4)\n move.l #1000,obj_range(a4)\n'
             f' move.l #$4142{slot:02x}00,registration_id(a4)\n')

    def observe(pool=1, selected=0):
        emit(f' move.w #{seed_for(pool, selected)},ai_comm_seed(a6)\n'
             ' lea objects+obj_len*3(a6),a5\n'+call('ai_comm_observe'))

    def received(base=40, recipient=0, hidden=False):
        eq(1,'comm_count(a6)'); eq(1,'qa_beeps')
        eq(base,'comm_queue+comm_message(a6)')
        eq(int(recipient == 0),'comm_queue+comm_to_player(a6)')
        target = 'comm_hidden' if hidden else (
            '$4a532a00' if recipient == 0 else f'$4142{recipient:02x}00')
        eq(target,'comm_queue+comm_recipient(a6)','l')
        eq(50,'radio_cooldown(a5)')
        eq('no_target','target(a5)','l')

    hooks = [('comm_now','qa_now'), ('comm_arrival_sound','qa_beep')]
    for name,label in hooks:
        addr = s[name]
        emit(f' move.l ${addr:x},qa_saved_{name}\n move.w ${addr+4:x},qa_saved_{name}+4\n'
             f' move.w #$4ef9,${addr:x}\n move.l #{label},${addr+2:x}\n')

    case('Cloak key without the device cannot mute greetings')
    spawn(); emit(' clr.w equip+cloaking_device(a6)\n'+call('cloaking_toggle'))
    eq(0,'cloaking_on(a6)'); observe(); received()

    for legal_before, legal_after in ((0,1),(0,50),(50,0)):
        case(f'Legal record changes while masked: {legal_before} to {legal_after}, current pool used')
        spawn(); spawn(4,'typ_pirate'); spawn(5)
        emit(f' move.w #{legal_before},police_record(a6)\n'+call('cloaking_toggle'))
        observe(); eq(0,'comm_count(a6)'); eq(0,'radio_flags(a5)')
        emit(f' move.w #{legal_after},police_record(a6)\n'+call('cloaking_toggle'))
        observe(2 if legal_after else 1)
        received(50,0 if legal_after else 4,hidden=not legal_after)

    for replace in (False, True):
        case('Last pirate '+('replaced by trader' if replace else 'removed')+' while masked: rebuild friendly pool')
        spawn(); spawn(4,'typ_pirate'); emit(call('cloaking_toggle'))
        observe(); eq(0,'comm_count(a6)')
        emit(' bset #remove,objects+obj_len*4+flags(a6)\n'+call('remove_objects'))
        if replace:
            spawn(4)
        emit(call('cloaking_toggle')); observe(2 if replace else 1, int(replace))
        received(40,4 if replace else 0)

    case('Pirate enters while masked: greeting priority uses the newly populated bubble')
    spawn(); spawn(4); emit(call('cloaking_toggle')); observe()
    spawn(29,'typ_pirate'); emit(call('cloaking_toggle')); observe()
    received(50,29,hidden=True)

    case('Sparse bubble: removed, abandoned and exploding pirates cannot hide the final live pirate')
    spawn()
    for slot,setup in ((4,' bset #remove,flags(a4)\n'),
                       (17,' move.w #act_nothing,attack_type(a4)\n'),
                       (28,' move.w #log_exploding,logic(a4)\n'),(29,'')):
        spawn(slot,'typ_pirate'); emit(setup)
    observe(); received(50,29,hidden=True)

    for selected in (0,1,26):
        case(f'Full normal flight bubble: select index {selected} from player plus 26 other traders')
        spawn()
        for slot in range(4,30):
            spawn(slot)
        observe(27,selected); received(40,selected+3 if selected else 0)

    case('Recreated sender cannot inherit consumed greeting or cooldown from its prior lifetime')
    spawn(); observe(); received()
    emit(call('cloaking_toggle')+' bset #remove,objects+obj_len*3+flags(a6)\n'+
         call('remove_objects')+call('comm_reset')+' clr.w qa_beeps\n')
    spawn(); eq(0,'radio_flags(a4)'); eq(0,'radio_cooldown(a4)')
    observe(); eq(0,'comm_count(a6)'); emit(call('cloaking_toggle')); observe(); received()

    case('Queued AI addressee is a snapshot even after its slot becomes a pirate')
    spawn(); spawn(4); observe(2,1); received(40,4)
    emit(' bset #remove,objects+obj_len*4+flags(a6)\n'+call('remove_objects'))
    spawn(4,'typ_pirate'); eq('$41420400','comm_queue+comm_recipient(a6)','l')
    eq(0,'comm_queue+comm_to_player(a6)')

    for cockpit in (0,1):
        case(f'Real cloak toggle with cockpit={cockpit}: no new receipt, normal queue timer policy')
        spawn(); observe(); received()
        emit(f' move.w #{cockpit},cockpit_on(a6)\n'+call('comm_update')+
             call('cloaking_toggle'))
        spawn(4); emit(' move.l a4,a5\n'+call('ai_comm_observe'))
        eq(1,'comm_count(a6)'); eq(1,'qa_beeps'); eq(0,'radio_flags(a5)')
        emit(call('comm_lifetime')+' move.l d0,qa_time\n'+call('comm_update'))
        eq(0 if cockpit else 1,'comm_count(a6)')
        emit(call('cloaking_toggle'))
        eq(0,'cloaking_on(a6)')

    # Exercise the whole observer repeatedly: chance, text selection, recipient
    # pool, IDs, queue and cooldown, rather than testing RNG helpers in isolation.
    for pool in (2,3,27):
        case(f'16384 successive complete greetings: {pool} candidates, full chance/recipient histogram')
        spawn()
        for slot in range(4,pool+3):
            spawn(slot)
        seed, silent, histogram = distribution(pool)
        assert abs(silent/16384-.5) < .02
        assert min(histogram) > 0
        emit(' lea qa_distribution,a0\n moveq #26,d5\n'+f'qa_zero_{pool}:\n'
             f' clr.w (a0)+\n dbra d5,qa_zero_{pool}\n clr.w qa_silence\n'
             ' move.w #31,ai_comm_seed(a6)\n move.w #16383,d5\n'
             ' lea objects+obj_len*3(a6),a5\n'+f'qa_draw_{pool}:\n'
             ' clr.w comm_count(a6)\n clr.w radio_flags(a5)\n clr.w radio_cooldown(a5)\n'+
             call('ai_comm_observe')+f' tst.w comm_count(a6)\n bne qa_sent_{pool}\n'
             ' tst.w radio_cooldown(a5)\n bne fail\n addq.w #1,qa_silence\n'+
             f' bra qa_next_{pool}\nqa_sent_{pool}:\n')
        eq(50,'radio_cooldown(a5)'); eq(1,'comm_count(a6)')
        emit(' moveq #0,d0\n tst.w comm_queue+comm_to_player(a6)\n'+
             f' bne qa_record_{pool}\n'
             ' move.l comm_queue+comm_recipient(a6),d0\n lsr.l #8,d0\n'
             ' and.w #255,d0\n subq.w #3,d0\n ble fail\n'+
             f' cmp.w #{pool},d0\n bhs fail\nqa_record_{pool}:\n'
             ' add.w d0,d0\n lea qa_distribution,a0\n addq.w #1,(a0,d0.w)\n'+
             f'qa_next_{pool}:\n dbra d5,qa_draw_{pool}\n')
        eq(silent,'qa_silence'); eq(16384-silent,'qa_beeps'); eq(seed,'ai_comm_seed(a6)')
        for index,count in enumerate(histogram):
            eq(count,f'qa_distribution+{index*2}')

    for name,_ in hooks:
        addr = s[name]
        emit(f' move.l qa_saved_{name},${addr:x}\n move.w qa_saved_{name}+4,${addr+4:x}\n')
    tail += 'qa_distribution: ds.w 27\nqa_silence: dc.w 0\n'
    return prefix, ''.join(out), tail, names
