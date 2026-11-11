"""Native spherical station contacts, safe fly-bys and all 13 player hulls."""

MODELS = ('cobra', 'adder', 'gecko', 'moray', 'cobra_mk1', 'ferdelance',
          'python', 'boa', 'anaconda', 'asp', 'sidewinder', 'krait', 'mamba')


def make_suite(root, s, stations=(('spacestn', 227), ('dodec', 248)), hulls=range(13), probe=False):
    prefix = ' include "common.def"\n include "macros.m68"\n'
    parts, names, data = [], [], []
    emit = parts.append
    call = lambda name: f' jsr ${s[name]:x}\n'

    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr sc_world\n')

    def position(x, y, z):
        emit(f' move.l #{x},xpos(a5)\n move.l #{y},ypos(a5)\n move.l #{z},zpos(a5)\n')

    # Ship profiles are applied normally; only their cosmetic bitmap refresh
    # and communication beep are suppressed in this collision-only fixture.
    for routine in ('ship_refresh', 'comm_arrival_sound'):
        addr = s[routine]
        emit(f' move.w ${addr:x},sc_saved_{routine}\n move.w #$4e75,${addr:x}\n')

    for station, radius in stations:
        for hull in hulls:
            emit(f' move.w #{hull},player_ship(a6)\n' + call('ship_apply') +
                 f' move.w #{station},sc_model\n')
            case(f'{MODELS[hull]} / {station}: just outside the enclosing sphere is safe')
            position(radius + 1, 0, 0)
            emit(' bsr sc_safe\n')
            if probe:
                continue
            for banned in (0, 1):
                points = []
                for distance in (radius + 1, radius + 50, radius + 99):
                    for axis in range(3):
                        for sign in (-1, 1):
                            point = [0, 0, 0]; point[axis] = sign * distance
                            points.append(tuple(point))
                case(f'{MODELS[hull]} / {station}: 18 near misses on all six sides, docking ban={banned}')
                emit(f' move.w #{banned},no_entry(a6)\n lea sc_points_{station},a0\n'
                     ' move.l a0,sc_next\n move.w #17,sc_remaining\n')
                loop = f'sc_sides_{station}_{hull}_{banned}'
                emit(f'{loop}:\n move.l sc_next,a0\n movem.l (a0)+,d0-d2\n'
                     ' move.l a0,sc_next\n movem.l d0-d2,xpos(a5)\n bsr sc_safe\n'
                     f' subq.w #1,sc_remaining\n bpl {loop}\n')
                if hull == hulls[0] and not banned:
                    data.append(f'sc_points_{station}:\n' + ''.join(' dc.l ' + ','.join(map(str,p)) + '\n' for p in points))

            case(f'{MODELS[hull]} / {station}: 41-frame grazing pass causes no cumulative damage')
            position(radius + 1, 0, -400)
            loop = f'sc_pass_{station}_{hull}'
            emit(f' move.w #40,sc_remaining\n{loop}:\n bsr sc_safe\n'
                 f' add.l #20,zpos(a5)\n subq.w #1,sc_remaining\n bpl {loop}\n')

            for distance in (radius - 1, radius):
                case(f'{MODELS[hull]} / {station}: actual contact at radius {distance} retains damage')
                position(distance, 0, 0)
                emit(' st no_entry(a6)\n bsr sc_contact\n')

    if not probe:
        for model in ('cobra', 'barrel', 'asteroid', 'worm'):
            emit(' clr.w player_ship(a6)\n' + call('ship_apply') + f' move.w #{model},sc_model\n')
            case(f'{model}: non-station contact still includes the original 100-unit allowance')
            emit(' moveq #0,d0\n move.w obj_rad(a5),d0\n add.w #100,d0\n move.l d0,xpos(a5)\n'
                 ' clr.l ypos(a5)\n clr.l zpos(a5)\n bsr sc_contact\n')
            case(f'{model}: outside the original non-station sphere remains safe')
            emit(' moveq #0,d0\n move.w obj_rad(a5),d0\n add.w #101,d0\n move.l d0,xpos(a5)\n'
                 ' clr.l ypos(a5)\n clr.l zpos(a5)\n bsr sc_safe\n')

    for routine in ('ship_refresh', 'comm_arrival_sound'):
        emit(f' move.w sc_saved_{routine},${s[routine]:x}\n')
    tail = '''sc_world:
'''+call('clear_objects')+call('comm_reset')+'''
 clr.w docked(a6)
 clr.w just_docked(a6)
 clr.w no_entry(a6)
 clr.w controls_locked(a6)
 clr.w computer_on(a6)
 clr.w game_over(a6)
 clr.w reason(a6)
 clr.w mission(a6)
 clr.w npc_hit(a6)
 clr.w npc_kill(a6)
 clr.w collided(a6)
 clr.w hit_check(a6)
 clr.w cabin_temp(a6)
 clr.w cockpit_on(a6)
 clr.w equip+fuel_scoop(a6)
 move.w #48,altitude(a6)
 move.w #1,shields_fx(a6)
 move.w #10,speed(a6)
 move.w #max_shield,front_shield(a6)
 move.w #max_shield,aft_shield(a6)
 move.w #max_energy,energy(a6)
 clr.w energy_fraction(a6)
 clr.w front_fraction(a6)
 clr.w aft_fraction(a6)
 bclr #f_fx,user(a6)
 lea station_rec(a6),a4
 move.b #1,flags(a4)
 move.w sc_model,type(a4)
 move.w #log_rotating,logic(a4)
 move.w #unit,x_vector+i(a4)
 move.w #unit,y_vector+j(a4)
 move.w #unit,z_vector+k(a4)
'''+call('create_object')+'''
 move.l a4,a5
 rts

sc_safe:
'''+call('get_range')+call('collision')+call('is_game_over')+'''
 tst.w game_over(a6)
 bne fail
 tst.w just_docked(a6)
 bne fail
 cmp.w #max_shield,front_shield(a6)
 bne fail
 cmp.w #max_shield,aft_shield(a6)
 bne fail
 cmp.w #max_energy,energy(a6)
 bne fail
 cmp.w #log_rotating,logic(a5)
 bne fail
 btst #remove,flags(a5)
 bne fail
 rts

sc_contact:
'''+call('get_range')+call('collision')+'''
 tst.w just_docked(a6)
 bne fail
 tst.w game_over(a6)
 bne.s .detected
 cmp.w #max_shield,front_shield(a6)
 bne.s .detected
 cmp.w #max_shield,aft_shield(a6)
 bne.s .detected
 cmp.w #max_energy,energy(a6)
 beq fail
.detected:
 rts

qa_case: dc.w 0
sc_model: dc.w 0
sc_remaining: dc.w 0
sc_next: dc.l 0
sc_saved_ship_refresh: dc.w 0
sc_saved_comm_arrival_sound: dc.w 0
'''+''.join(data)
    return prefix, ''.join(parts), tail, names
