"""Real manual/automatic docking gates for existing and hidden-ID bans."""
from native_spawn_paths import make_suite as spawn_suite


def make_suite(root, s):
    prefix, _, tail, _ = spawn_suite(root, s)
    out, names = [], []
    emit = out.append
    call = lambda name: f' jsr ${s[name]:x}\n'

    def eq(value, field):
        emit(f' cmp.w #{value},{field}\n bne fail\n')

    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n'
             ' clr.w docked(a6)\n clr.w just_docked(a6)\n clr.w no_entry(a6)\n'
             ' clr.w controls_locked(a6)\n clr.w computer_on(a6)\n clr.w game_over(a6)\n clr.w reason(a6)\n'
             ' clr.w scrambled_id(a6)\n clr.w police_record(a6)\n clr.w qa_impacts\n'
             ' move.w #10,speed(a6)\n'
             ' move.l #$224ff,planet_range(a6)\n move.l #2000,station_range(a6)\n'
             +call('comm_reset'))

    hooks = [('reduce_shields', 'qa_impact'), ('comm_arrival_sound', 'qa_return')]
    emit(call('hide_cursor')+' clr.w display_clock(a6)\n clr.w player_ship(a6)\n'+call('ship_apply'))
    for name, label in hooks:
        a=s[name]
        emit(f' move.l ${a:x},qa_save_{name}\n move.w ${a+4:x},qa_save_{name}+4\n'
             f' move.w #$4ef9,${a:x}\n move.l #{label},${a+2:x}\n')
        tail+=f'qa_save_{name}: ds.b 6\n'

    for ban in ('none', 'existing', 'scrambled'):
        for automatic in (0, 1):
            case(f'Aligned station collision: ban={ban}, active docking computer={automatic}')
            if ban=='existing':emit(' st no_entry(a6)\n')
            if ban=='scrambled':
                emit(' move.w #255,scrambled_id(a6)\n'+call('comm_arrival_check'))
                emit(' tst.w no_entry(a6)\n beq fail\n')
            emit(' lea station_rec(a6),a5\n move.b #1,flags(a5)\n'
                 ' move.w #log_rotating,logic(a5)\n clr.l xpos(a5)\n clr.l ypos(a5)\n'
                 ' move.l #100,zpos(a5)\n move.l #100,obj_range(a5)\n'
                 ' move.w #-unit,z_vector+k(a5)\n move.w #unit,x_vector+j(a5)\n'
                 f' move.w #{automatic},computer_on(a6)\n move.w #{automatic},controls_locked(a6)\n'
                 ' moveq #100,d2\n'+call('collision'))
            if ban=='none':
                emit(' tst.w just_docked(a6)\n beq fail\n'); eq(0, 'qa_impacts'); eq(0, 'game_over(a6)')
            else:
                eq(0, 'just_docked(a6)'); eq(1, 'qa_impacts')
                eq(7, 'qa_damage'); eq(0, 'game_over(a6)')

    for fast in (0, 1):
        case(f'Hidden-ID ban rejects docking-computer activation, instant mode={fast}')
        emit(' move.w #255,scrambled_id(a6)\n'+call('comm_arrival_check')
             +' move.w #1,equip+docking_comp(a6)\n move.w #1,radar_obj(a6)\n'
             ' clr.w count_down(a6)\n'+f' {"bset" if fast else "bclr"} #f_docking,user(a6)\n'
             +call('computer'))
        eq(0, 'computer_on(a6)'); eq(0, 'just_docked(a6)'); eq(0, 'controls_locked(a6)')

    # Exercise the real impact/shield/energy path after the routing checks.
    a=s['reduce_shields']
    emit(f' move.l qa_save_reduce_shields,${a:x}\n move.w qa_save_reduce_shields+4,${a+4:x}\n')
    for hull,strength in ((0,7),(8,13)):
        for ban in ('existing','scrambled'):
            for side in ('front','aft'):
                for speed in (0,1,10,22):
                    case(f'Repeated real station damage: hull={hull}, ban={ban}, side={side}, speed={speed}')
                    damage=((speed//2+2)*7+strength//2)//strength
                    hits=(24+96+damage-1)//damage
                    label=f'qa_station_hits_{len(names)}'
                    z=100 if side=='front' else -100
                    emit(f' move.w #{hull},player_ship(a6)\n'+call('ship_apply')
                         +' move.w #max_shield,front_shield(a6)\n move.w #max_shield,aft_shield(a6)\n'
                         ' move.w #max_energy,energy(a6)\n clr.w energy_fraction(a6)\n'
                         ' clr.w front_fraction(a6)\n clr.w aft_fraction(a6)\n'
                         ' move.w #48,altitude(a6)\n clr.w cabin_temp(a6)\n move.w #1,shields_fx(a6)\n'
                         f' move.w #{speed},speed(a6)\n')
                    if ban=='existing':emit(' st no_entry(a6)\n')
                    else:emit(' move.w #255,scrambled_id(a6)\n'+call('comm_arrival_check'))
                    emit(' tst.w no_entry(a6)\n beq fail\n lea station_rec(a6),a5\n'
                         ' move.b #1,flags(a5)\n move.w #log_rotating,logic(a5)\n'
                         f' move.l #{z},zpos(a5)\n move.l #100,obj_range(a5)\n'
                         +call('collision')+call('is_game_over'))
                    eq(24-damage,side+'_shield(a6)')
                    eq(24,('aft' if side=='front' else 'front')+'_shield(a6)')
                    eq(96,'energy(a6)');eq(0,'game_over(a6)');eq(0,'just_docked(a6)')
                    # Moving clear stops damage; no hidden countdown kills the ship.
                    emit(' move.l #$10000,station_rec+obj_range(a6)\n'+call('collision'))
                    eq(24-damage,side+'_shield(a6)');eq(96,'energy(a6)');eq(0,'game_over(a6)')
                    emit(' move.l #100,station_rec+obj_range(a6)\n'
                         f' move.w #{hits-2},d6\n{label}:\n move.w d6,-(sp)\n'
                         ' lea station_rec(a6),a5\n'+call('collision')+call('is_game_over')
                         +' move.w (sp)+,d6\n')
                    eq(0,'just_docked(a6)')
                    emit(f' tst.w d6\n beq.s {label}_last\n tst.w game_over(a6)\n bne fail\n'
                         f'{label}_last:\n dbra d6,{label}\n')
                    eq(0,side+'_shield(a6)');eq(0,'energy(a6)')
                    eq(24,('aft' if side=='front' else 'front')+'_shield(a6)')
                    emit(' tst.w game_over(a6)\n beq fail\n');eq('no_energy','reason(a6)')

    for name, _ in hooks:
        a=s[name]
        emit(f' move.l qa_save_{name},${a:x}\n move.w qa_save_{name}+4,${a+4:x}\n')
    tail+='qa_impacts: dc.w 0\nqa_damage: dc.w 0\nqa_impact:\n move.w d0,qa_damage\n addq.w #1,qa_impacts\n rts\nqa_return: rts\n'
    return prefix, ''.join(out), tail, names
