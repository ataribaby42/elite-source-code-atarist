"""Missile acquisition through real view transforms, independent of lasers/IFF."""
from native_missile_collision import make_suite as base_suite


def make_suite(root, s):
    prefix, _, tail, _ = base_suite(root, s)
    out, names = [], []
    emit = out.append
    call = lambda name: f' jsr ${s[name]:x}\n'
    views = ('front_view', 'rear_view', 'left_view', 'right_view')
    positions = ((0, 0, 1500), (0, 0, -1500), (-1500, 0, 0), (1500, 0, 0))
    lasers = ('pulse_lasers', 'mining_lasers', 'beam_lasers', 'military_lasers')

    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')

    def key(char):
        emit(f" clr.w check_key(a6)\n moveq #'{char}',d0\n" + call('check'))

    def case(name, iff=0, hull=0):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n'
             ' clr.w csr_on(a6)\n clr.w display_clock(a6)\n clr.w id_trigger(a6)\n'
             ' clr.w in_sights(a6)\n clr.b loop_ctr(a6)\n'
             f' move.w #{iff},equip+iff_unit(a6)\n move.w #{hull},player_ship(a6)\n')
        for laser in lasers:
            emit(f' clr.w equip+{laser}(a6)\n')
        emit(' move.w #1,equip+missiles(a6)\n' + call('ship_apply')
             + ' move.w hull_fuel(a6),equip+fuel(a6)\n clr.w speed(a6)\n')

    def target(model, view):
        emit(' lea objects+obj_len*3(a6),a4\n move.b #1,flags(a4)\n'
             f' move.w #{model},type(a4)\n' + call('create_object'))
        for axis, value in zip(('xpos', 'ypos', 'zpos'), positions[view]):
            emit(f' move.l #{value},{axis}(a4)\n')
        for vector, component in (('x_vector', 'i'), ('y_vector', 'j'), ('z_vector', 'k')):
            emit(f' move.w #unit,{vector}+{component}(a4)\n')
        emit(' move.w #log_cruise,logic(a4)\n')

    def draw(record='objects+obj_len*3'):
        emit(call('clear_image') + f' lea {record}(a6),a5\n')
        emit(call('get_range') + call('draw_object'))

    def locked(record='objects+obj_len*3'):
        eq(2, 'missile_state(a6)')
        emit(f' lea {record}(a6),a0\n cmp.l target_ptr(a6),a0\n bne fail\n')
        eq(1, 'equip+missiles(a6)')
        eq(0, 'id_trigger(a6)')

    def fired(record):
        key('M')
        eq(0, 'missile_state(a6)')
        eq(0, 'equip+missiles(a6)')
        eq(1, 'obj_ctr+missile(a6)', 'b')
        emit(' lea objects(a6),a0\n moveq #max_objects-1,d7\n')
        index = len(names)
        emit(f'qa_find_{index}:\n btst #in_use,flags(a0)\n beq.s qa_next_{index}\n'
             f' cmp.w #missile,type(a0)\n beq.s qa_found_{index}\nqa_next_{index}:\n'
             f' lea obj_len(a0),a0\n dbra d7,qa_find_{index}\n bra fail\nqa_found_{index}:\n')
        eq('log_locked', 'logic(a0)')
        emit(f' lea {record}(a6),a1\n cmp.l target(a0),a1\n bne fail\n')

    # Reproduce the reported path with the real launch, view and T/M controls.
    for iff in (0, 1):
        for model in ('spacestn', 'dodec'):
            case(f'Sidewinder launch, rear {model}, no rear mount, IFF {iff}: lock and fire', iff, 10)
            emit(' move.w #1,equip+pulse_lasers(a6)\n st docked(a6)\n'
                 ' bclr #f_sequence,user(a6)\n' + call('launch'))
            # Lave uses Coriolis; replace only its mesh/header for the Dodec case.
            if model == 'dodec':
                emit(' lea station_rec(a6),a4\n move.w #dodec,type(a4)\n' + call('create_object'))
            eq(1, 'hull_mounts(a6)')
            eq(-2500, 'station_rec+zpos(a6)', 'l')
            emit(call('rear_view'))
            eq(-1, 'laser_type(a6)')
            key('T')
            eq(1, 'missile_state(a6)')
            draw('station_rec')
            locked('station_rec')
            eq(0, 'in_sights(a6)')
            emit(call('draw_space') + call('draw_sight') + call('update_inst'))
            if root.name == 'src_amiga':
                emit(call('wait_clear'))
            if iff == 0 and model == 'spacestn':
                emit(f' lea ${s["palette"]:x},a0\n lea qa_palette,a1\n moveq #15,d7\n'
                     'qa_copy_palette:\n move.w (a0)+,(a1)+\n dbra d7,qa_copy_palette\n'
                     'snap_rear_station:\n nop\n')
            fired('station_rec')

    for view, func in enumerate(views):
        for laser in range(-1, 4):
            for iff in (0, 1):
                for model in ('cobra', 'spacestn', 'dodec'):
                    case(f'View {view}, laser {laser}, IFF {iff}, {model}: lock, ID, cancel', iff)
                    if laser >= 0:
                        emit(f' move.w #{1 << view},equip+{lasers[laser]}(a6)\n')
                    emit(call(func))
                    eq(laser, 'laser_type(a6)')
                    target(model, view)
                    key('I')
                    emit(' tst.w id_trigger(a6)\n' + (' beq' if iff else ' bne') + ' fail\n')
                    key('T')
                    draw()
                    locked()
                    emit(' tst.w in_sights(a6)\n' + (' beq' if laser >= 0 else ' bne') + ' fail\n')
                    emit(call('laser_in_sights'))
                    eq(int(laser >= 0), 'd0')
                    draw()
                    locked()
                    if laser == -1 and iff == 0 and model == 'cobra':
                        fired('objects+obj_len*3')
                    else:
                        key('U')
                        eq(0, 'missile_state(a6)')
                        eq(1, 'equip+missiles(a6)')

    for view, func in enumerate(views):
        for iff in (0, 1):
            for gate in ('invincible', 'off_axis', 'opposite_view', 'own_missile', 'unarmed', 'already_locked'):
                case(f'No laser, view {view}, IFF {iff}: preserve {gate} acquisition guard', iff)
                emit(call(func))
                target('cobra', view)
                key('T')
                if gate == 'invincible':
                    emit(' bset #invincible,flags(a4)\n')
                elif gate == 'off_axis':
                    emit(' move.l #600,ypos(a4)\n')
                elif gate == 'opposite_view':
                    for axis in ('xpos', 'ypos', 'zpos'):
                        emit(f' neg.l {axis}(a4)\n')
                elif gate == 'own_missile':
                    emit(' lea objects+obj_len*4(a6),a0\n move.b #1,flags(a0)\n'
                         ' move.w #missile,type(a0)\n move.w #log_locked,logic(a0)\n move.l a4,target(a0)\n')
                elif gate == 'unarmed':
                    key('U')
                else:
                    emit(' move.w #2,missile_state(a6)\n lea objects+obj_len*5(a6),a0\n move.l a0,target_ptr(a6)\n')
                draw()
                eq(0 if gate == 'unarmed' else 2 if gate == 'already_locked' else 1, 'missile_state(a6)')
                if gate == 'already_locked':
                    emit(' lea objects+obj_len*5(a6),a0\n cmp.l target_ptr(a6),a0\n bne fail\n')
                else:
                    eq(0, 'target_ptr(a6)', 'l')
                eq(1, 'equip+missiles(a6)')
                eq(0, 'in_sights(a6)')

    tail += 'qa_palette: ds.w 16\n'
    return prefix, ''.join(out), tail, names
