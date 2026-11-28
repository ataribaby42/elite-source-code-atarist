"""Identify contacts in all Sidewinder views, including its three empty mounts."""
from native_missile_collision import make_suite as base_suite


def make_suite(root, s):
    prefix, _, tail, _ = base_suite(root, s)
    out, names = [], []
    emit = out.append
    call = lambda name: f' jsr ${s[name]:x}\n'
    views = ('front_view', 'rear_view', 'left_view', 'right_view')
    positions = ((0, 0, 1500), (0, 0, -1500), (-1500, 0, 0), (1500, 0, 0))
    for view, func in enumerate(views):
        for equipped in (0, 1):
            for model in ('cobra', 'spacestn', 'dodec'):
                case = len(names) + 1
                names.append(f'Sidewinder view {view}, IFF {equipped}, {model}: standalone identification')
                emit(f' move.w #{case},qa_case\n bsr qa_world\n'
                     ' clr.w csr_on(a6)\n clr.w display_clock(a6)\n clr.w id_trigger(a6)\n'
                     ' move.w #10,player_ship(a6)\n move.w #1,equip+pulse_lasers(a6)\n'
                     ' clr.w equip+mining_lasers(a6)\n clr.w equip+beam_lasers(a6)\n'
                     ' clr.w equip+military_lasers(a6)\n move.w #1,equip+missiles(a6)\n'
                     f' move.w #{equipped},equip+iff_unit(a6)\n' + call('ship_apply')
                     + ' move.w hull_fuel(a6),equip+fuel(a6)\n clr.w speed(a6)\n')
                if case == 1:
                    emit(call('prepare_cockpit'))
                emit(call(func) + ' lea objects+obj_len*3(a6),a4\n move.b #1,flags(a4)\n'
                     f' move.w #{model},type(a4)\n' + call('create_object'))
                for axis, value in zip(('xpos', 'ypos', 'zpos'), positions[view]):
                    emit(f' move.l #{value},{axis}(a4)\n')
                emit(" clr.w check_key(a6)\n moveq #'I',d0\n" + call('check'))
                emit(call('clear_image') + ' lea objects+obj_len*3(a6),a5\n'
                     + call('get_range') + call('draw_object'))
                emit(' tst.w id_trigger(a6)\n bne fail\n tst.w missile_state(a6)\n bne fail\n'
                     ' cmp.w #1,equip+missiles(a6)\n bne fail\n')
                if equipped:
                    # Match the actual model name at the beginning of the ID message.
                    emit(' move.l text(a5),a0\n lea text_buffer(a6),a1\n'
                         f'qa_name_{case}:\n move.b (a0)+,d0\n beq.s qa_name_done_{case}\n'
                         ' cmp.b (a1)+,d0\n bne fail\n'
                         f' bra.s qa_name_{case}\nqa_name_done_{case}:\n')
                else:
                    for index, char in enumerate('I.F.F. Not Installed\0'):
                        emit(f' cmp.b #{ord(char)},text_buffer+{index}(a6)\n bne fail\n')
    return prefix, ''.join(out), tail, names
