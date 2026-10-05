"""Real 68000 trader recipient selection, addressing and unbiased radio draws."""
from functools import lru_cache
from native_ai_radio import make_suite as base_suite


@lru_cache(None)
def seed_for(pool, index, variant=0):
    """Find a deterministic send roll followed by a draw in the requested bucket."""
    for first in range(10+variant, 65520, 20):
        value = first
        if pool > 1:
            width = 65536 // pool
            while True:
                value = (value*25173+13849) & 65535
                if value < width*pool:
                    break
            if value // width != index:
                continue
        return ((first-13849)*pow(25173, -1, 65536)) & 65535
    raise AssertionError((pool, index, variant))


def make_suite(root, s):
    prefix, _, tail, _ = base_suite(root, s)
    out, names = [], []
    emit = out.append
    call = lambda name: f' jsr ${s[name]:x}\n'

    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')

    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n clr.l qa_seen_recipient\n')

    def spawn(model='cobra', role='typ_trader', slot=3):
        emit(f' lea objects+obj_len*{slot}(a6),a4\n move.b #1,flags(a4)\n'
             f' move.w #{model},type(a4)\n'+call('create_object')+
             f' move.w #{role},ship_type(a4)\n move.w #log_cruise,logic(a4)\n'
             ' move.l #no_target,target(a4)\n move.l #1000,obj_range(a4)\n'
             f' move.l #$4142{slot:02x}00,registration_id(a4)\n')

    def choose(pool=1, index=0, variant=0):
        seed = seed_for(pool, index, variant)
        emit(f' move.w #{seed},ai_comm_seed(a6)\n')
        return seed

    def observe():
        emit(' lea objects+obj_len*3(a6),a5\n'+call('ai_comm_observe'))

    def received(base, recipient=0, hidden=False, pirate=False, variant=0):
        eq(1, 'comm_count(a6)'); eq(1, 'qa_beeps')
        eq(base+variant, 'comm_queue+comm_message(a6)')
        eq('$41420300', 'comm_queue+comm_sender(a6)', 'l')
        eq(int(recipient == 0), 'comm_queue+comm_to_player(a6)')
        expected = ('comm_hidden' if hidden or pirate else
                    '$4a532a00' if recipient == 0 else f'$4142{recipient:02x}00')
        eq(expected, 'comm_queue+comm_recipient(a6)', 'l')
        if recipient:
            emit(f' lea objects+obj_len*{recipient}(a6),a0\n'
                 ' cmpa.l qa_seen_recipient,a0\n bne fail\n')
            eq(0, f'objects+obj_len*{recipient}+radio_cooldown(a6)')
        else:
            eq(0, 'qa_seen_recipient', 'l')
        eq(50, 'radio_cooldown(a5)'); eq('$0100', 'radio_flags(a5)')
        eq('no_target', 'target(a5)', 'l')

    hooks = [('comm_now', 'qa_now'), ('comm_arrival_sound', 'qa_beep')]
    for name, label in hooks:
        a = s[name]
        emit(f' move.l ${a:x},qa_saved_{name}\n move.w ${a+4:x},qa_saved_{name}+4\n'
             f' move.w #$4ef9,${a:x}\n move.l #{label},${a+2:x}\n')

    # Record the actual NPC passed to the original ID formatter, even when all
    # pirates print ??-???. Replay its first non-PC-relative CMP instruction and
    # resume the real formatter; no identity or selection logic is simulated.
    addr = s['comm_id_object']
    eq('$0c6c', f'${addr:x}')
    emit(f' move.l ${addr:x},qa_id_instruction\n move.w ${addr+4:x},qa_id_instruction+4\n'
         f' move.w #$4ef9,${addr:x}\n move.l #qa_id_trace,${addr+2:x}\n')

    for legal in (1, 49, 50, 255):
        for selected in range(3):
            case(f'Legal record {legal}: player and two pirates are equal candidates; trader excluded; index {selected}')
            spawn(); spawn('adder', 'typ_pirate', 4); spawn('mamba', 'typ_pirate', 5)
            spawn(slot=6); emit(f' move.w #{legal},police_record(a6)\n')
            choose(3, selected); observe()
            received(50, 0 if selected == 0 else selected+3, pirate=selected > 0)

    for selected in range(2):
        case(f'Clean player: pirates take priority over the player and friendly traders; index {selected}')
        spawn(); spawn('adder', 'typ_pirate', 4); spawn('mamba', 'typ_pirate', 5)
        spawn(slot=6); choose(2, selected); observe(); received(50, selected+4, pirate=True)

    for selected in range(3):
        case(f'Clean player without pirates: player and other traders are equal candidates; index {selected}')
        spawn(); spawn(slot=4); spawn(slot=5)
        choose(3, selected); observe(); received(40, 0 if selected == 0 else selected+3)

    for legal in (0, 1, 50):
        case(f'No other ships, legal record {legal}: choose the player, never self')
        spawn(); emit(f' move.w #{legal},police_record(a6)\n')
        choose(); observe(); received(50 if legal else 40)

    for legal in (0, 50):
        for selected in range(2):
            case(f'Cloaked player, legal record {legal}: all greetings suppressed until uncloaked; pirate index {selected}')
            spawn(); spawn('adder','typ_pirate',4); spawn('mamba','typ_pirate',5)
            emit(f' move.w #{legal},police_record(a6)\n move.w #1,cloaking_on(a6)\n')
            seed = choose(2, selected); observe()
            eq(0, 'comm_count(a6)'); eq(0, 'qa_beeps'); eq(0, 'radio_flags(a5)')
            eq(seed, 'ai_comm_seed(a6)')
            emit(' clr.w cloaking_on(a6)\n')
            choose(3 if legal else 2, selected+1 if legal else selected)
            observe(); received(50, selected+4, pirate=True)

    case('Cloaked Clean player: AI-to-AI greeting waits until uncloaked')
    spawn(); spawn(slot=4); emit(' move.w #1,cloaking_on(a6)\n')
    seed = choose(); observe(); eq(0, 'comm_count(a6)'); eq(0, 'radio_flags(a5)')
    eq(seed, 'ai_comm_seed(a6)'); emit(' clr.w cloaking_on(a6)\n')
    choose(2, 1); observe(); received(40, 4)

    for legal in (0, 50):
        case(f'No eligible recipient while cloaked, legal record {legal}: preserve chance until player appears')
        spawn()
        if legal: spawn(slot=4)  # wanted players do not unlock friendly-trader fallback
        emit(f' move.w #{legal},police_record(a6)\n move.w #1,cloaking_on(a6)\n')
        seed = choose(); observe()
        eq(0, 'comm_count(a6)'); eq(0, 'radio_flags(a5)'); eq(seed, 'ai_comm_seed(a6)')
        emit(' clr.w cloaking_on(a6)\n'); observe(); received(50 if legal else 40)

    for legal in (0, 50):
        case(f'Scramble ID masks the chosen player without removing them, legal record {legal}')
        spawn(); emit(f' move.w #255,scrambled_id(a6)\n move.w #{legal},police_record(a6)\n')
        if legal: spawn('adder','typ_pirate',4)
        else: spawn(slot=4)
        choose(2, 0); observe(); received(50 if legal else 40, hidden=True)

    case('A pirate elsewhere in the bubble is eligible beyond player scanner range')
    spawn(); spawn('adder','typ_pirate',4)
    emit(' move.l #radar_range+50000,obj_range(a4)\n')
    choose(); observe(); received(50, 4, pirate=True)

    exclusions = [
        ('unused', 'adder', 'typ_pirate', ' clr.b flags(a4)\n'),
        ('removed', 'adder', 'typ_pirate', ' bset #remove,flags(a4)\n'),
        ('zero energy', 'adder', 'typ_pirate', ' clr.w health(a4)\n'),
        ('negative energy', 'adder', 'typ_pirate', ' move.w #-1,health(a4)\n'),
        ('exploding', 'adder', 'typ_pirate', ' move.w #log_exploding,logic(a4)\n'),
        ('abandoned', 'adder', 'typ_pirate', ' move.w #act_nothing,attack_type(a4)\n'),
        ('Thargoid', 'thargoid', 'typ_pirate', ''),
        ('Tharglet', 'thargon', 'typ_pirate', ''),
        ('Constrictor mission hull', 'constr', 'typ_pirate', ''),
        ('Cougar mission hull', 'cougar', 'typ_pirate', ''),
        ('station', 'spacestn', 'typ_pirate', ''),
        ('missile', 'missile', 'typ_pirate', ''),
        ('police Viper', 'viper', 'typ_police', ''),
        ('bounty hunter', 'ferdelance', 'typ_bounty', ''),
        ('shuttle role', 'shuttle', 'typ_shuttle', ''),
    ]
    for label, model, role, setup in exclusions:
        case(label+': not a candidate and cannot displace the friendly player fallback')
        spawn(); spawn(model,role,4); emit(setup)
        choose(); observe(); received(40)

    case('Greeting cooldown consumes the opportunity without selection or chance draws')
    spawn(); spawn('adder','typ_pirate',4)
    emit(' move.w #17,objects+obj_len*3+radio_cooldown(a6)\n')
    seed = choose(); observe(); eq(0, 'comm_count(a6)'); eq(0, 'qa_beeps')
    eq(seed, 'ai_comm_seed(a6)'); eq('$0100', 'radio_flags(a5)'); eq(17, 'radio_cooldown(a5)')
    emit(' moveq #16,d5\nqa_expire:\n'+call('ai_comm_tick')+' dbra d5,qa_expire\n')
    observe(); eq(0, 'comm_count(a6)'); eq(seed, 'ai_comm_seed(a6)')

    case('A silent greeting is consumed; no selection draw, cooldown or retry after pool changes')
    spawn(); spawn(slot=4); choose()
    silent = ((0-13849)*pow(25173,-1,65536)) & 65535
    emit(f' move.w #{silent},ai_comm_seed(a6)\n'); observe()
    eq(0, 'ai_comm_seed(a6)'); eq(0, 'comm_count(a6)'); eq(0, 'radio_cooldown(a5)')
    spawn('adder','typ_pirate',5); seed = choose(); observe()
    eq(0, 'comm_count(a6)'); eq(seed, 'ai_comm_seed(a6)')

    for mission in (0x15, 0x21, 0x41, 0x52):
        case(f'Mission ${mission:02X}: recipient selection does not alter targets, truce or gameplay randomness')
        spawn(); spawn('adder','typ_pirate',4); spawn('mamba','typ_pirate',5)
        emit(f' move.w #{mission},mission(a6)\n move.w #18,pirate_truce(a4)\n'
             ' move.l #$12345678,random_seed(a6)\n move.l #$87654321,rseed1(a6)\n'
             ' move.w #71,comm_seed(a6)\n move.w #37,registration_state(a6)\n')
        choose(2,1); observe(); received(50,5,pirate=True)
        eq(mission,'mission(a6)'); eq(18,'objects+obj_len*5+pirate_truce(a6)')
        eq('no_target','objects+obj_len*5+target(a6)','l')
        eq('$12345678','random_seed(a6)','l'); eq('$87654321','rseed1(a6)','l')
        eq(71,'comm_seed(a6)'); eq(37,'registration_state(a6)')

    for base, role in ((40,'typ_trader'),(50,'typ_pirate')):
        case(f'All ten greeting variants remain available for AI recipients in text set {base}')
        for variant in range(10):
            emit(' bsr qa_world\n clr.l qa_seen_recipient\n')
            spawn(); spawn('adder',role,4)
            choose(2 if base == 40 else 1, 1 if base == 40 else 0, variant)
            observe(); received(base,4,pirate=base == 50,variant=variant)

    for bound in (2,3,30):
        count = (65536//bound)*bound
        case(f'Complete recipient RNG cycle with {bound} candidates: equal buckets, rejected tail')
        emit(' lea qa_pick_histogram,a0\n moveq #29,d5\n'+f'qa_zero_{bound}:\n'
             f' clr.w (a0)+\n dbra d5,qa_zero_{bound}\n clr.w ai_comm_seed(a6)\n'
             f' move.w #{count-1},d5\nqa_cycle_{bound}:\n moveq #{bound},d0\n'+call('ai_comm_pick')+
             f' cmp.w #{bound},d0\n bhs fail\n add.w d0,d0\n lea qa_pick_histogram,a0\n'
             f' addq.w #1,(a0,d0.w)\n dbra d5,qa_cycle_{bound}\n')
        eq(0,'ai_comm_seed(a6)')
        for index in range(bound): eq(65536//bound,f'qa_pick_histogram+{index*2}')

    case('Single candidate selection needs no extra random number')
    emit(' move.w #12345,ai_comm_seed(a6)\n moveq #1,d0\n'+call('ai_comm_pick'))
    eq(0,'d0','l'); eq(12345,'ai_comm_seed(a6)')

    emit(f' move.l qa_id_instruction,${addr:x}\n move.w qa_id_instruction+4,${addr+4:x}\n')
    for name, _ in hooks:
        a = s[name]
        emit(f' move.l qa_saved_{name},${a:x}\n move.w qa_saved_{name}+4,${a+4:x}\n')
    tail += f'''qa_seen_recipient: dc.l 0
qa_pick_histogram: ds.w 30
qa_id_trace:
 cmpa.l a5,a4
 beq.s .sender
 move.l a4,qa_seen_recipient
.sender:
qa_id_instruction: ds.b 6
 jmp ${addr+6:x}
'''
    return prefix, ''.join(out), tail, names
