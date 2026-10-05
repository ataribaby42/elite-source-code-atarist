"""Exercise per-ship radio suppression and slot lifecycle in the real 68000 code."""
from native_ai_radio import make_suite as base_suite


def make_suite(root, s):
    prefix, _, tail, _ = base_suite(root, s)
    out, names = [], []
    emit = out.append
    call = lambda name: f' jsr ${s[name]:x}\n'

    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')

    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n')

    def spawn(model='cobra', role='typ_trader', slot=3):
        emit(f' lea objects+obj_len*{slot}(a6),a4\n move.b #1,flags(a4)\n'
             f' move.w #{model},type(a4)\n'+call('create_object')+
             f' move.w #{role},ship_type(a4)\n move.w #log_cruise,logic(a4)\n'
             ' move.l #no_target,target(a4)\n move.l #1000,obj_range(a4)\n'
             ' move.l #$41420300,registration_id(a4)\n')

    def ship(slot=3, reg='a5'):
        emit(f' lea objects+obj_len*{slot}(a6),{reg}\n')

    def roll(sent=True):
        seed = (((10 if sent else 0)-13849)*pow(25173, -1, 65536)) % 65536
        emit(f' move.w #{seed},ai_comm_seed(a6)\n')
        return seed

    def observe(slot=3):
        ship(slot); emit(call('ai_comm_observe'))

    def ticks(n, slot=3):
        ship(slot)
        if n == 1:
            emit(call('ai_comm_tick'))
        else:
            label = f'qa_ticks_{len(names)}_{len(out)}'
            emit(f' move.w #{n}-1,d5\n{label}:\n'+call('ai_comm_tick')+
                 f' dbra d5,{label}\n')

    def count(n):
        eq(n, 'comm_count(a6)'); eq(n, 'qa_beeps')

    def hit(attacker=None):
        ship(reg='a4')
        emit(' suba.l a0,a0\n' if attacker is None else
             f' lea objects+obj_len*{attacker}(a6),a0\n')
        emit(' moveq #1,d0\n'+call('ship_ai_damage'))

    hooks = [('comm_now', 'qa_now'), ('comm_arrival_sound', 'qa_beep')]
    for name, label in hooks:
        a = s[name]
        emit(f' move.l ${a:x},qa_saved_{name}\n move.w ${a+4:x},qa_saved_{name}+4\n'
             f' move.w #$4ef9,${a:x}\n move.l #{label},${a+2:x}\n')

    for model, role, kind in [('cobra','typ_trader','greeting'),
                             ('cobra','typ_trader','cautious'),
                             ('cobra','typ_pirate','friend'),
                             ('cobra','typ_pirate','threat'),
                             ('thargoid','typ_alien','threat'),
                             ('viper','typ_police','threat'),
                             ('cobra','typ_trader','protest')]:
        case(f'{model}/{kind}: a sent message arms exactly 50 game frames')
        spawn(model, role)
        if kind == 'cautious': emit(' move.w #50,police_record(a6)\n')
        if kind == 'friend': emit(' move.w #18,pirate_truce(a4)\n')
        if kind == 'threat': emit(' move.w #log_attack,logic(a4)\n clr.l target(a4)\n')
        roll()
        if kind == 'protest': hit()
        else: observe()
        count(1); eq(50, 'objects+obj_len*3+radio_cooldown(a6)')

    for frames in (1, 49, 50):
        case(f'Cooldown {frames}: new threat is consumed silently without a radio RNG draw')
        spawn(role='typ_pirate')
        emit(f' move.w #{frames},radio_cooldown(a4)\n'
             ' move.w #log_attack,logic(a4)\n clr.l target(a4)\n')
        seed = roll(); observe(); count(0)
        eq(seed, 'ai_comm_seed(a6)'); eq(frames, 'radio_cooldown(a5)')
        eq(0, 'radio_target(a5)', 'l')
        ticks(frames); eq(0, 'radio_cooldown(a5)'); observe(); count(0)
        eq(seed, 'ai_comm_seed(a6)')

    case('Zero saturates; fifty tick calls expire the cooldown exactly')
    spawn(); roll(); observe(); ticks(49); eq(1, 'radio_cooldown(a5)')
    ticks(1); eq(0, 'radio_cooldown(a5)'); ticks(8); eq(0, 'radio_cooldown(a5)')

    case('A different ship can transmit during another sender cooldown')
    spawn(); roll(); observe()
    spawn(slot=4); roll(); observe(4); count(2)
    eq(50, 'objects+obj_len*3+radio_cooldown(a6)')
    eq(50, 'objects+obj_len*4+radio_cooldown(a6)')
    ticks(1); eq(49, 'radio_cooldown(a5)')
    eq(50, 'objects+obj_len*4+radio_cooldown(a6)')

    case('Silent 50 percent roll does not arm a cooldown or block another event')
    spawn(); roll(False); observe(); count(0); eq(0, 'radio_cooldown(a5)')
    roll(); hit(); count(1); eq(50, 'radio_cooldown(a4)')

    case('Greeting then survived hit: suppressed protest never retries after expiry')
    spawn(); roll(); observe(); roll(); hit(); count(1)
    eq(50, 'radio_cooldown(a4)'); eq('$0300', 'radio_flags(a4)')
    ticks(50); roll(); hit(); count(1); eq(0, 'radio_cooldown(a4)')

    case('Greeting then player missile launch: cooldown suppresses radio, not hostility')
    spawn(); roll(); observe()
    emit(' move.b #1,objects+flags(a6)\n move.b #1,objects+obj_len+flags(a6)\n'
         ' move.b #1,objects+obj_len*2+flags(a6)\n move.w #2,missile_state(a6)\n'
         ' move.w #2,equip+missiles(a6)\n')
    ship(reg='a4'); emit(' move.l a4,target_ptr(a6)\n')
    roll(); emit(call('fire_missile')); count(1)
    ship(reg='a4'); eq(50, 'radio_cooldown(a4)'); eq('log_attack', 'logic(a4)')
    emit(' btst #angry,flags(a4)\n beq fail\n'); eq(1, 'equip+missiles(a6)')

    case('AI shooter identity resolution arms the victim cooldown, not the attacker')
    spawn(); spawn('adder','typ_pirate',4)
    emit(' move.w #17,radio_cooldown(a4)\n')
    roll(); hit(4); count(1)
    eq(50, 'objects+obj_len*3+radio_cooldown(a6)')
    eq(17, 'objects+obj_len*4+radio_cooldown(a6)')
    eq('comm_hidden', 'comm_queue+comm_recipient(a6)', 'l')

    case('A pirate greeting and threat in the same observer pass send only the greeting')
    spawn(role='typ_pirate')
    emit(' move.w #18,pirate_truce(a4)\n move.w #log_attack,logic(a4)\n')
    spawn(slot=4); emit(' move.l a4,objects+obj_len*3+target(a6)\n')
    roll(); observe(); count(1); eq(70, 'comm_queue+comm_message(a6)')
    eq(50, 'radio_cooldown(a5)'); ticks(50); roll(); observe(); count(1)
    emit(' clr.l target(a5)\n'); observe(); count(2)
    eq(60, 'comm_queue+comm_size+comm_message(a6)')

    for cockpit in (0, 1):
        case(f'cockpit={cockpit}: queue time updates do not decrement game-frame cooldowns')
        spawn(); roll(); observe()
        emit(f' move.w #{cockpit},cockpit_on(a6)\n move.l #100,qa_time\n'+call('comm_update'))
        eq(50, 'radio_cooldown(a5)'); ticks(1); eq(49, 'radio_cooldown(a5)')

    for reset in ('create_object', 'alloc_object', 'remove_objects', 'clear_objects'):
        case(reset+': stale slot cooldown cannot reach the next occupant')
        spawn(); emit(' move.w #37,radio_cooldown(a4)\n')
        if reset == 'alloc_object':
            emit(' clr.b flags(a4)\n move.b #1,objects+flags(a6)\n'
                 ' move.b #1,objects+obj_len+flags(a6)\n move.b #1,objects+obj_len*2+flags(a6)\n')
        if reset == 'remove_objects': emit(' bset #remove,flags(a4)\n')
        emit(call(reset)); eq(0, 'objects+obj_len*3+radio_cooldown(a6)')
        spawn(); roll(); observe(); count(1); eq(50, 'radio_cooldown(a5)')

    for parent, child in (('cobra', 'cobra'), ('thargoid', 'thargon'), ('cobra', 'missile')):
        case(f'Actual {parent}-to-{child} copy: creation clears the inherited cooldown, preserves parent')
        spawn(parent); emit(' move.w #37,radio_cooldown(a4)\n')
        ship(); ship(4, 'a4'); emit(call('copy_object'))
        eq(37, 'radio_cooldown(a4)')
        emit(f' move.w #{child},type(a4)\n'+call('create_object'))
        eq(0, 'radio_cooldown(a4)'); eq(37, 'radio_cooldown(a5)')
        emit(' move.l radio_instance(a4),d0\n cmp.l radio_instance(a5),d0\n beq fail\n')

    case('Whole bubble clearing resets every slot, including unused ones')
    emit(' lea objects(a6),a4\n moveq #max_objects-1,d7\nqa_fill:\n'
         ' move.w #50,radio_cooldown(a4)\n lea obj_len(a4),a4\n dbra d7,qa_fill\n'+call('clear_objects')+
         ' lea objects(a6),a4\n moveq #max_objects-1,d7\nqa_empty:\n'
         ' tst.w radio_cooldown(a4)\n bne fail\n lea obj_len(a4),a4\n dbra d7,qa_empty\n')

    # Execute the game's actual per-object loop. Bypass unrelated geometry,
    # movement and collision work so only the real scheduling path is isolated.
    bypass = ('get_range','collision','draw_object','radar','mini_radar','retarget',
              'do_logic','queue_ai_laser','check_hit','orthogonal','move','q_main_m68_10')
    for name in bypass:
        emit(f' move.w ${s[name]:x},qa_loop_saved_{name}\n move.w #$4e75,${s[name]:x}\n')
        tail += f'qa_loop_saved_{name}: dc.w 0\n'
    for cockpit in (0, 1):
        case(f'Actual object loop cockpit={cockpit}: ticks each live off-screen ship once')
        spawn(); spawn(slot=4)
        emit(f' move.w #{cockpit},cockpit_on(a6)\n clr.w roll_angle(a6)\n clr.w climb_angle(a6)\n'
             ' move.w #50,objects+obj_len*3+radio_cooldown(a6)\n'
             ' move.w #1,objects+obj_len*4+radio_cooldown(a6)\n'
             ' move.w #21,objects+obj_len*5+radio_cooldown(a6)\n'
             ' move.l #radar_range+1000,objects+obj_len*3+obj_range(a6)\n'
             ' move.l #radar_range+1000,objects+obj_len*4+obj_range(a6)\n'
             ' lea objects(a6),a5\n clr.w this_obj(a6)\n'+call('q_main_m68_9'))
        eq(49, 'objects+obj_len*3+radio_cooldown(a6)')
        eq(0, 'objects+obj_len*4+radio_cooldown(a6)')
        eq(21, 'objects+obj_len*5+radio_cooldown(a6)'); count(0)
    for name in bypass:
        emit(f' move.w qa_loop_saved_{name},${s[name]:x}\n')
    for name, _ in hooks:
        a = s[name]
        emit(f' move.l qa_saved_{name},${a:x}\n move.w qa_saved_{name}+4,${a+4:x}\n')
    return prefix, ''.join(out), tail, names
