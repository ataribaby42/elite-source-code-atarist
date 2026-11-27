"""Run shot energy, fractional reserves and AI firing limits on real 68000 code."""
from native_ai_bursts import make_suite as burst_suite


def make_suite(root, s):
    prefix, _, tail, _ = burst_suite(root, s)
    out, names = [], []
    call = lambda n: f' jsr ${s[n]:x}\n'
    def emit(text): out.append(text)
    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n bsr qe_player\n')
    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')
    def store(actual, field, debt):
        whole = (actual + 65535) // 65536
        eq(whole, field)
        eq(whole*65536-actual, debt)
    def patch(name, target):
        addr = s[name]
        emit(f' move.l ${addr:x},qa_saved_{name}\n move.w ${addr+4:x},qa_saved_{name}+4\n'
             f' move.w #$4ef9,${addr:x}\n move.l #{target},${addr+2:x}\n')
    def restore(name):
        addr = s[name]
        emit(f' move.l qa_saved_{name},${addr:x}\n move.w qa_saved_{name}+4,${addr+4:x}\n')
    def setup(power, model='cobra', npc=False):
        emit(f' move.w #{power},qa_power\n move.w #{int(npc)},qa_npc\n'
             ' move.w #1,qa_side\n move.w #18,qa_length\n move.w #199,qa_roll\n'
             ' bsr qa_setup\n move.l a5,a4\n')
        emit(f' move.w #{model},type(a4)\n'+call('ship_ai_init'))
        emit(f' move.w #{power},ai_laser_loadout(a5)\n')
    cost = 24576  # 3/8 of one local energy point = 1/256 full banks.
    full = 96*65536
    minimum = (full+19)//20  # First representable energy at or above 5%.
    patch('random', 'qa_random')
    patch('ai_burst_length', 'qa_length_roll')
    patch('laser_impact_sound', 'qa_impact')

    for kind, rate in enumerate((10, 8, 6, 3)):
        case(f'Player laser {kind}: eight accepted shots cost exactly three points')
        emit(f' move.w #{kind},laser_type(a6)\n move.w #{rate},laser_rate(a6)\n')
        for shot in range(1, 9):
            emit(' clr.w firing(a6)\n'+call('fire'))
            store(full-shot*cost, 'energy(a6)', 'energy_fraction(a6)')
            eq(shot, 'laser_temp(a6)'); eq(rate, 'firing(a6)')
            eq(24, 'front_shield(a6)'); eq(24, 'aft_shield(a6)')
            eq(0, 'f_energy(a6)')
            emit(' tst.w laser_pending(a6)\n beq fail\n')
            # Repeated held-trigger calls before the next firing tick cost zero.
            emit(call('fire')+call('fire'))
            store(full-shot*cost, 'energy(a6)', 'energy_fraction(a6)')
            eq(shot, 'laser_temp(a6)')

    guards = [('frozen', ' st game_frozen(a6)\n'),
              ('docked', ' st docked(a6)\n'),
              ('no laser', ' move.w #-1,laser_type(a6)\n'),
              ('overheated', ' move.w #48,laser_temp(a6)\n'),
              ('cooldown', ' move.w #1,firing(a6)\n'),
              ('destroyed', ' clr.w energy(a6)\n')]
    for name, change in guards:
        case('Player rejected shot does not drain energy: '+name)
        emit(change+call('fire'))
        eq(0 if name=='destroyed' else 96, 'energy(a6)')
        eq(0, 'energy_fraction(a6)'); eq(0, 'laser_pending(a6)')
        eq(48 if name=='overheated' else 0, 'laser_temp(a6)')

    for initial in (0, 1, cost-1, cost, cost+1, 2*cost-1, 2*cost, 65536,
                    96*65536-1, 40*65536+12345):
        for ai in (False, True):
            case(f'Energy drain keeps C64 reserve and never heals: {initial}/65536, AI={ai}')
            if ai:
                setup(9)
                field, debt = 'health(a5)', 'ai_energy_fraction(a5)'
            else:
                field, debt = 'energy(a6)', 'energy_fraction(a6)'
            whole = (initial+65535)//65536
            emit(f' move.w #{whole},{field}\n move.w #{whole*65536-initial},{debt}\n'
                 f' lea {field},a0\n lea {debt},a1\n'
                 ' move.l #$12345678,d0\n move.l #$87654321,d1\n'+call('ship_laser_energy'))
            store(min(initial, max(cost, initial-cost)), field, debt)
            eq('$12345678', 'd0', 'l'); eq('$87654321', 'd1', 'l')
            eq(0, 'game_over(a6)')

    case('Player can keep firing at the reserve; incoming damage remains fatal')
    emit(' move.w #1,energy(a6)\n move.w #40960,energy_fraction(a6)\n'
         ' moveq #7,d6\nqe_reserve_loop:\n clr.w firing(a6)\n'+call('fire')+
         ' dbra d6,qe_reserve_loop\n')
    store(cost, 'energy(a6)', 'energy_fraction(a6)')
    eq(8, 'laser_temp(a6)')
    emit(' clr.w front_shield(a6)\n clr.w aft_shield(a6)\n'
         ' lea objects+obj_len*4(a6),a5\n move.l #1000,zpos(a5)\n'
         ' moveq #1,d0\n'+call('reduce_laser_shields'))
    eq(0, 'energy(a6)')
    emit(' clr.w firing(a6)\n clr.w laser_pending(a6)\n'+call('fire'))
    eq(0, 'energy(a6)'); eq(0, 'laser_pending(a6)')

    for model in ('cobra', 'viper', 'ferdelance', 'krait'):
        for power in (5, 9, 11):
            for initial in (minimum-1, minimum, minimum+1, 5*65536, 0):
                case(f'{model} laser {power}: exact 5% boundary at {initial}/65536')
                setup(power, model)
                whole=(initial+65535)//65536
                emit(f' move.w #{whole},health(a5)\n'
                     f' move.w #{whole*65536-initial},ai_energy_fraction(a5)\n'+call('ai_fire_laser'))
                allowed=initial>=minimum
                store(initial-(cost if allowed else 0), 'health(a5)', 'ai_energy_fraction(a5)')
                eq(2 if allowed else 0, 'ai_laser(a5)')
                eq(24-power if allowed else 24, 'front_shield(a6)')
                eq(24, 'ai_front(a5)'); eq(24, 'ai_aft(a5)')
                if not allowed:
                    eq(0, 'ai_laser_burst(a5)'); eq(0, 'ai_laser_cooldown(a5)')

    for power, interval in ((5, 10), (9, 6), (11, 3)):
        for npc in (False, True):
            for miss in ('hit', 'random miss', 'cone miss'):
                case(f'AI {power}, NPC={npc}, {miss}: only actual firing ticks consume energy')
                setup(power, npc=npc)
                if miss=='random miss': emit(' clr.w qa_roll\n')
                if miss=='cone miss': emit(' move.w #-15000,z_vector+k(a5)\n')
                for frame in range(18):
                    emit(' bsr qa_reset_stores\n'+call('ai_laser_tick')+call('ai_fire_laser'))
                    shots=frame//interval+1
                    store(full-shots*cost, 'health(a5)', 'ai_energy_fraction(a5)')
                    visual=power!=5 or frame%interval==0
                    eq(2 if visual and frame%interval==0 and miss=='hit' else int(visual), 'ai_laser(a5)')

    for npc in (False, True):
        case(f'AI burst interrupted below 5%, then resumes after recharge; NPC={npc}')
        setup(11, model='viper', npc=npc)
        emit(' move.w #5,health(a5)\n'+call('ai_fire_laser'))
        store(5*65536-cost, 'health(a5)', 'ai_energy_fraction(a5)')
        emit(call('ai_laser_tick')+call('ai_fire_laser'))
        eq(0, 'ai_laser(a5)'); eq(0, 'ai_laser_burst(a5)'); eq(0, 'ai_laser_target(a5)', 'l')
        emit(' move.w #1,ai_charge_count(a5)\n'+call('ship_ai_recharge'))
        emit(call('ai_laser_tick')+call('ai_laser_tick')+call('ai_fire_laser'))
        eq(2, 'ai_laser(a5)')
        store(6*65536-2*cost, 'health(a5)', 'ai_energy_fraction(a5)')

    for model in ('viper','ferdelance','cobra'):
        case(f'{model}: incoming hull damage cancels an active burst before its next shot')
        setup(11, model=model)
        emit(' move.w #6,health(a5)\n'+call('ai_fire_laser')+
             ' clr.w ai_front(a5)\n clr.w ai_aft(a5)\n move.l a5,a4\n'
             ' suba.l a0,a0\n moveq #1,d0\n'+call('ship_ai_damage')+
             call('ai_laser_tick')+call('ai_fire_laser'))
        eq(0,'ai_laser(a5)'); eq(0,'ai_laser_burst(a5)')
        eq('log_attack','logic(a5)')

    case('AI never charges a rejected trigger, invalid target or out-of-range shot')
    setup(11)
    emit(' clr.w mood(a5)\n'+call('ai_fire_laser'))
    store(full,'health(a5)','ai_energy_fraction(a5)')
    emit(' move.w #255,mood(a5)\n move.l #12289,target_range(a6)\n'+call('ai_fire_laser'))
    store(full,'health(a5)','ai_energy_fraction(a5)')
    emit(' move.l #1000,target_range(a6)\n move.l #no_target,target(a5)\n'+call('ai_fire_laser'))
    store(full,'health(a5)','ai_energy_fraction(a5)')
    eq(0,'ai_laser_cooldown(a5)')

    case('Player energy unit replenishes fractional shot expenditure without changing shields')
    emit(' move.w #1,hull_recharge(a6)\n move.w #2,equip+energy_unit(a6)\n'
         ' move.w #1,recharge_count(a6)\n'+call('fire')+call('recharge'))
    store(full,'energy(a6)','energy_fraction(a6)')
    eq(24,'front_shield(a6)'); eq(24,'aft_shield(a6)')

    restore('random'); restore('ai_burst_length'); restore('laser_impact_sound')
    tail+='''
qe_player:
 clr.w game_frozen(a6)
 clr.w firing(a6)
 clr.w laser_temp(a6)
 clr.w laser_pending(a6)
 clr.w laser_beam(a6)
 clr.w laser_flash(a6)
 move.w #2,laser_type(a6)
 move.w #6,laser_rate(a6)
 move.w #-1,f_energy(a6)
 rts
'''
    return prefix, ''.join(out), tail, names
