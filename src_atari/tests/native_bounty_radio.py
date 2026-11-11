"""Exercise hunter radio through the linked observer, targeting and formatter."""
from native_ai_radio import make_suite as fixtures

TEXTS = (
    'Your bounty is mine.', "I've come to collect.", 'The hunt ends here.',
    'Consider this contract closed.', 'You can run. I get paid to follow.',
    'Target acquired. Weapons ready.', "You're worth more than your cargo.",
    'Nothing personal. Just business.', 'One less name on my list.',
    "You won't outrun a bounty hunter.",
)


def make_suite(root, s):
    prefix, _, tail, _ = fixtures(root, s)
    parts, names = [], []
    emit = parts.append
    call = lambda name: f' jsr ${s[name]:x}\n'

    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')

    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n'
             ' clr.w police_hunt(a6)\n clr.w launch_count(a6)\n'
             ' move.l #$12345678,rseed1(a6)\n move.l #$87654321,random_seed(a6)\n'
             ' move.w #73,comm_seed(a6)\n')

    def spawn(model='ferdelance', slot=3):
        emit(f' lea objects+obj_len*{slot}(a6),a4\n move.b #1,flags(a4)\n'
             f' move.w #{model},type(a4)\n' + call('create_object') +
             ' move.w #log_attack,logic(a4)\n clr.l target(a4)\n'
             ' move.l #1000,obj_range(a4)\n move.l #1000,zpos(a4)\n'
             ' move.l #$41420300,registration_id(a4)\n')

    def roll(index=0):
        seed = ((10 + index - 13849) * pow(25173, -1, 65536)) % 65536
        emit(f' move.w #{seed},ai_comm_seed(a6)\n')
        return seed

    def observe():
        emit(' lea objects+obj_len*3(a6),a5\n' + call('ai_comm_observe'))

    def count(n):
        eq(n, 'comm_count(a6)'); eq(n, 'qa_beeps')

    def ticks():
        emit(f' move.w #49,d5\nbr_ticks_{len(names)}:\n' + call('ai_comm_tick') +
             f' dbra d5,br_ticks_{len(names)}\n')

    hooks = [('comm_now', 'qa_now'), ('comm_arrival_sound', 'qa_beep')]
    for name, label in hooks:
        addr = s[name]
        emit(f' move.l ${addr:x},qa_saved_{name}\n move.w ${addr+4:x},qa_saved_{name}+4\n'
             f' move.w #$4ef9,${addr:x}\n move.l #{label},${addr+2:x}\n')

    for npc in (False, True):
        for index, text in enumerate(TEXTS):
            case(f'Hunter variant {index+1} to {"NPC pirate" if npc else "player"}: exact text and identity')
            spawn(); eq('typ_bounty', 'ship_type(a4)')
            if npc:
                spawn('sidewinder', 4)
                emit(' move.l a4,objects+obj_len*3+target(a6)\n')
            roll(index); observe(); count(1)
            eq(130 + index, 'comm_queue+comm_message(a6)')
            eq(int(not npc), 'comm_queue+comm_to_player(a6)')
            eq('$41420300', 'comm_queue+comm_sender(a6)', 'l')
            eq('comm_hidden' if npc else '$4a532a00', 'comm_queue+comm_recipient(a6)', 'l')
            eq(50, 'radio_cooldown(a5)')
            label = f'br_text_{int(npc)}_{index}'
            tail += f'{label}: dc.b "AB-003:{"??-???" if npc else "JS-042"}, {text}",0\n even\n'
            emit(' lea comm_queue(a6),a5\n' + call('comm_format') +
                 f' lea {label},a0\n lea comm_buffer(a6),a1\n bsr qa_compare\n')

    for record in (0, 39, 40, 50):
        case(f'Legal record {record}: radio observes the actual hunter targeting decision')
        spawn()
        emit(f' move.w #{record},police_record(a6)\n move.l #no_target,target(a4)\n'
             ' move.w #log_cruise,logic(a4)\n move.l a4,a5\n'
             ' move.w #3,this_obj(a6)\n move.w #3,retarget_slot(a6)\n' + call('retarget'))
        eq(0 if record >= 40 else 'no_target', 'target(a5)', 'l')
        roll(); observe(); count(int(record >= 40))
        if record >= 40: eq(130, 'comm_queue+comm_message(a6)')

    case('A hunter retaliating against a Clean player uses its own threat set')
    spawn(); emit(' bset #angry,flags(a4)\n move.l #no_target,target(a4)\n'
                  ' move.l a4,a5\n move.w #3,this_obj(a6)\n move.w #3,retarget_slot(a6)\n' + call('retarget'))
    roll(); observe(); count(1); eq(130, 'comm_queue+comm_message(a6)')

    for label, setup in (
        ('cloaked player', ' move.w #1,cloaking_on(a6)\n'),
        ('docked player', ' move.w #1,docked(a6)\n'),
        ('game over', ' move.w #1,game_over(a6)\n'),
        ('out of scanner', ' move.l #radar_range+1,obj_range(a4)\n'),
        ('removed sender', ' bset #remove,flags(a4)\n'),
        ('exploding sender', ' move.w #log_exploding,logic(a4)\n'),
        ('abandoned sender', ' move.w #log_abandoned,logic(a4)\n move.w #act_nothing,attack_type(a4)\n'),
        ('station launch', ' move.w #log_launch,logic(a4)\n'),
        ('protected station turn', ' move.w #log_peel_off,logic(a4)\n move.w #log_departure_wait,next_logic(a4)\n move.l #no_target,target(a4)\n'),
        ('peaceful cruise', ' move.w #log_cruise,logic(a4)\n move.l #no_target,target(a4)\n'),
    ):
        case('Hunter stays silent: ' + label)
        spawn(); emit(setup); seed = roll(); observe(); count(0)
        eq(seed, 'ai_comm_seed(a6)')

    case('Scanner boundary and in-flight UI permit an addressed hunter threat')
    spawn(); emit(' move.l #radar_range,obj_range(a4)\n'); roll(); observe(); count(1)
    eq(130, 'comm_queue+comm_message(a6)')

    case('Scrambled player identity remains anonymous and keeps the player blink flag')
    spawn(); emit(' move.w #255,scrambled_id(a6)\n'); roll(); observe(); count(1)
    eq('comm_hidden', 'comm_queue+comm_recipient(a6)', 'l'); eq(1, 'comm_queue+comm_to_player(a6)')

    case('A silent roll consumes the target event without starting a cooldown')
    spawn(); roll(-10); observe(); count(0); eq(0, 'radio_cooldown(a5)')
    roll(); observe(); count(0)
    spawn('sidewinder', 4); emit(' move.l a4,objects+obj_len*3+target(a6)\n')
    roll(); observe(); count(1)

    case('A new target during cooldown is consumed, then another target may transmit after 50 ticks')
    spawn(); roll(); observe(); count(1)
    spawn('sidewinder', 4); emit(' move.l a4,objects+obj_len*3+target(a6)\n')
    seed = roll(); observe(); count(1); eq(seed, 'ai_comm_seed(a6)')
    ticks(); observe(); count(1); eq(0, 'radio_cooldown(a5)')
    emit(' clr.l target(a5)\n'); roll(9); observe(); count(2)
    eq(139, 'comm_queue+comm_size+comm_message(a6)')

    case('Target loss and reacquisition create a fresh hunter radio event')
    spawn(); roll(); observe(); count(1)
    emit(' move.l #no_target,target(a5)\n'); observe(); ticks()
    emit(' clr.l target(a5)\n'); roll(); observe(); count(2)

    for model, role, expected in (('viper', 'typ_police', 90),
                                  ('viper', 'typ_bounty', None),
                                  ('cobra', 'typ_bounty', None),
                                  ('ferdelance', 'typ_police', None)):
        case(f'{model}/{role}: police and hunter message routing stays distinct')
        spawn(model); emit(f' move.w #{role},ship_type(a4)\n'); roll(); observe()
        count(int(expected is not None))
        if expected is not None: eq(expected, 'comm_queue+comm_message(a6)')

    case('Hunter observer preserves gameplay object bytes and all non-radio random streams')
    spawn()
    emit(' move.l #$12345678,rseed1(a6)\n move.l #$87654321,random_seed(a6)\n'
         ' move.w #73,comm_seed(a6)\n lea br_snapshot,a0\n move.l a4,a1\n'
         ' move.w #obj_len/2-1,d7\nbr_copy:\n move.w (a1)+,(a0)+\n dbra d7,br_copy\n')
    roll(); observe(); count(1)
    eq('$12345678', 'rseed1(a6)', 'l'); eq('$87654321', 'random_seed(a6)', 'l'); eq(73, 'comm_seed(a6)')
    emit(' lea br_snapshot,a0\n move.l a5,a1\n move.w #radio_instance/2-1,d7\nbr_compare_before:\n'
         ' move.w (a1)+,d0\n cmp.w (a0)+,d0\n bne fail\n dbra d7,br_compare_before\n'
         ' lea nodes-radio_instance(a0),a0\n lea nodes-radio_instance(a1),a1\n'
         ' move.w #(obj_len-nodes)/2-1,d7\nbr_compare_after:\n'
         ' move.w (a1)+,d0\n cmp.w (a0)+,d0\n bne fail\n dbra d7,br_compare_after\n')
    tail += 'br_snapshot: ds.b obj_len\n'
    for name, _ in hooks:
        addr = s[name]
        emit(f' move.l qa_saved_{name},${addr:x}\n move.w qa_saved_{name}+4,${addr+4:x}\n')
    return prefix, ''.join(parts), tail, names
