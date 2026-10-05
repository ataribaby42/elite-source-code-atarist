"""Cloaking mutes radio receipts and exempts real cargo ejections from station law."""
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
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n'
             ' clr.w just_docked(a6)\n clr.w station_destroyed(a6)\n clr.w no_entry(a6)\n'
             ' move.b #1,station_rec+flags(a6)\n move.w #spacestn,station_rec+type(a6)\n'
             ' move.l #$224ff,planet_range(a6)\n move.l #2000,station_range(a6)\n'
             ' move.w #3,splanet+govern(a6)\n move.w #71,comm_seed(a6)\n'
             ' move.w #12345,ai_comm_seed(a6)\n move.w #1,cloaking_on(a6)\n')

    def spawn(model='cobra', role='typ_trader', slot=3):
        emit(f' lea objects+obj_len*{slot}(a6),a4\n move.b #1,flags(a4)\n'
             f' move.w #{model},type(a4)\n'+call('create_object')+
             f' move.w #{role},ship_type(a4)\n move.w #log_cruise,logic(a4)\n'
             ' move.l #no_target,target(a4)\n move.l #1000,obj_range(a4)\n'
             ' move.l #$41420300,registration_id(a4)\n')

    def quiet():
        eq(0,'comm_count(a6)'); eq(0,'qa_beeps')
        eq(71,'comm_seed(a6)'); eq(12345,'ai_comm_seed(a6)')

    def roll():
        seed = ((10-13849)*pow(25173,-1,65536)) & 65535
        emit(f' move.w #{seed},ai_comm_seed(a6)\n')

    def observe():
        emit(' lea objects+obj_len*3(a6),a5\n'+call('ai_comm_observe'))

    hooks = [('comm_now','qa_now'), ('comm_arrival_sound','qa_beep')]
    for name, label in hooks:
        a=s[name]
        emit(f' move.l ${a:x},qa_saved_{name}\n move.w ${a+4:x},qa_saved_{name}+4\n'
             f' move.w #$4ef9,${a:x}\n move.l #{label},${a+2:x}\n')

    for cockpit in (0,1):
        for entry in ('comm_enqueue','comm_enqueue_player'):
            case(f'cockpit={cockpit}, {entry}: all 110 message IDs suppressed with registers intact')
            emit(f' move.w #{cockpit},cockpit_on(a6)\n')
            for text in range(110):
                emit(f' moveq #{text},d0\n move.l #$41420300,d1\n'
                     ' move.l #$4a532a00,d2\n move.l #$12345678,d7\n'+call(entry))
                eq(text,'d0'); eq('$41420300','d1','l'); eq('$4a532a00','d2','l')
                eq('$12345678','d7','l')
            quiet()

    case('Previously received messages survive cloaking; muted arrivals cannot evict them')
    emit(' clr.w cloaking_on(a6)\n')
    for text in range(3):
        emit(f' moveq #{text},d0\n move.l #$41420300,d1\n'
             ' move.l #$4a532a00,d2\n'+call('comm_enqueue_player'))
    eq(3,'comm_count(a6)'); eq(3,'qa_beeps')
    emit(' move.w #$ffff,cloaking_on(a6)\n moveq #50,d0\n'+call('comm_enqueue_player'))
    eq(3,'comm_count(a6)'); eq(3,'qa_beeps')
    for index in range(3): eq(index,f'comm_queue+{index}*comm_size+comm_message(a6)')
    emit(' move.w #1,cockpit_on(a6)\n'+call('comm_lifetime')+
         ' move.l d0,qa_time\n'+call('comm_update'))
    eq(2,'comm_count(a6)'); eq(3,'qa_beeps'); eq(1,'comm_queue+comm_message(a6)')

    for model,role,kind in [('cobra','typ_trader','friendly'),
                            ('cobra','typ_trader','cautious'),
                            ('cobra','typ_pirate','friend'),
                            ('cobra','typ_pirate','threat'),
                            ('viper','typ_police','threat'),
                            ('thargoid','typ_alien','threat')]:
        for npc in ((False,True) if kind=='threat' else (False,)):
            case(f'{model}/{kind}, NPC={npc}: no message, event consumption, cooldown or RNG while cloaked')
            spawn(model,role)
            if kind=='cautious': emit(' move.w #50,police_record(a6)\n')
            if kind=='friend': emit(' move.w #18,pirate_truce(a4)\n')
            if kind=='threat':
                emit(' move.w #log_attack,logic(a4)\n clr.l target(a4)\n')
                if npc:
                    spawn(slot=4); emit(' move.l a4,objects+obj_len*3+target(a6)\n')
            observe(); quiet(); eq(0,'radio_flags(a5)'); eq(0,'radio_cooldown(a5)')
            eq('no_target','radio_target(a5)','l')
            emit(' clr.w cloaking_on(a6)\n'); roll(); observe()
            eq(1,'comm_count(a6)'); eq(1,'qa_beeps'); eq(50,'radio_cooldown(a5)')

    for npc in (False,True):
        case(f'Survived hit, NPC attacker={npc}: damage still applies, protest resumes on a later visible hit')
        spawn()
        if npc: spawn('adder','typ_pirate',4)
        emit(' lea objects+obj_len*3(a6),a4\n')
        emit(' lea objects+obj_len*4(a6),a0\n' if npc else ' suba.l a0,a0\n')
        emit(' moveq #5,d0\n'+call('ship_ai_damage'))
        quiet(); eq(0,'d0'); eq(19,'ai_front(a4)'); eq(0,'radio_flags(a4)')
        emit(' clr.w cloaking_on(a6)\n'); roll()
        emit(' moveq #5,d0\n'+call('ship_ai_damage'))
        eq(1,'comm_count(a6)'); eq(1,'qa_beeps'); eq(100,'comm_queue+comm_message(a6)')

    case('Player missile launch under cloak still provokes and cancels a pirate truce, without radio')
    spawn('cobra','typ_pirate')
    emit(' move.w #18,pirate_truce(a4)\n move.l a4,target_ptr(a6)\n'
         ' move.b #1,objects+flags(a6)\n move.b #1,objects+obj_len*2+flags(a6)\n'
         ' move.w #2,missile_state(a6)\n move.w #2,equip+missiles(a6)\n'+call('fire_missile'))
    observe(); quiet(); eq(0,'pirate_truce(a5)'); eq('log_attack','logic(a5)')
    emit(' btst #angry,flags(a5)\n beq fail\n'); eq(1,'equip+missiles(a6)')

    for denied,legal in ((0,0),(0,50),(1,0)):
        case(f'Station arrival denied={denied}, record={legal}: silence without consuming the arrival latch')
        emit(f' move.w #{denied},no_entry(a6)\n move.w #{legal},police_record(a6)\n'
             ' move.w #7,splanet+govern(a6)\n'+call('comm_arrival_check'))
        quiet(); eq(0,'comm_arrival_sent(a6)'); eq(denied,'no_entry(a6)')
        emit(' clr.w cloaking_on(a6)\n'+call('comm_arrival_check'))
        eq(1,'comm_count(a6)'); eq(1,'qa_beeps'); eq(2 if denied else 1,'comm_arrival_sent(a6)')
        eq(legal,'police_record(a6)')

    case('Scramble ID docking ban remains independent of cloaking radio silence')
    emit(' move.w #255,scrambled_id(a6)\n move.w #7,splanet+govern(a6)\n'+call('comm_arrival_check'))
    quiet(); eq(0,'comm_arrival_sent(a6)'); eq(0,'police_record(a6)')
    emit(' tst.w no_entry(a6)\n beq fail\n clr.w cloaking_on(a6)\n'+call('comm_arrival_check'))
    eq(1,'comm_count(a6)'); eq(2,'comm_arrival_sent(a6)')

    case('A station-hit warning waits for uncloaking and uses the existing sent latch')
    emit(' move.w #1,no_entry(a6)\n move.w #1,comm_arrival_sent(a6)\n'+call('comm_station_hit'))
    quiet(); eq(1,'comm_arrival_sent(a6)'); eq(1,'no_entry(a6)')
    emit(' clr.w cloaking_on(a6)\n'+call('comm_arrival_check'))
    eq(1,'comm_count(a6)'); eq(2,'comm_arrival_sent(a6)')

    case('Leaving S resets the visit latch even while all messages are muted')
    emit(' move.w #2,comm_arrival_sent(a6)\n move.l #$22500,planet_range(a6)\n'+call('comm_arrival_check'))
    quiet(); eq(0,'comm_arrival_sent(a6)')

    for entry in ('comm_departure_ship','comm_departure_player','comm_jettison'):
        case(entry+': station messages consume no cosmetic RNG while cloaked')
        spawn(); emit(call(entry)); quiet()
        emit(' clr.w cloaking_on(a6)\n'+call(entry))
        eq(1,'comm_count(a6)'); eq(1,'qa_beeps')

    for government in range(8):
        for record in (0,245):
            case(f'Real cargo ejection: government={government}, record={record}; cloak exempts penalty only while active')
            emit(f' move.w #{government},splanet+govern(a6)\n move.w #{record},police_record(a6)\n'
                 f' move.w #{1 if record == 0 else 65535},cloaking_on(a6)\n'
                 ' move.b #1,objects+flags(a6)\n move.b #1,objects+obj_len*2+flags(a6)\n'
                 ' move.l #500000,hold(a6)\n moveq #0,d0\n'+call('jettison_cargo'))
            eq(1,'d0'); eq(0,'hold(a6)','l'); eq(record,'police_record(a6)'); quiet()
            eq(500000,'objects+obj_len*3+cargo_mass(a6)','l')
            eq('barrel','objects+obj_len*3+type(a6)')
            emit(' clr.w cloaking_on(a6)\n move.l #1000000,hold(a6)\n moveq #0,d0\n'+call('jettison_cargo'))
            eq(1,'d0'); eq(0,'hold(a6)','l')
            eq(min(record+15,255) if government else record,'police_record(a6)')
            eq(int(government != 0),'comm_count(a6)'); eq(int(government != 0),'qa_beeps')

    case('Existing ship cooldown still counts down during radio silence')
    spawn(); emit(' move.w #2,radio_cooldown(a4)\n move.l a4,a5\n'+call('ai_comm_tick'))
    eq(1,'radio_cooldown(a5)'); observe(); eq(1,'radio_cooldown(a5)'); quiet()
    emit(call('ai_comm_tick')); eq(0,'radio_cooldown(a5)'); observe(); quiet()

    for name, _ in hooks:
        a=s[name]
        emit(f' move.l qa_saved_{name},${a:x}\n move.w qa_saved_{name}+4,${a+4:x}\n')
    return prefix, ''.join(out), tail, names
