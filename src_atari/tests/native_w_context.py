"""Native W/V dispatch: cargo charts, nonblocking UI feedback, 3D-only credits."""
from native_special_cargo_ui import make_suite as base_suite


def make_suite(root, s):
    prefix, _, tail, _ = base_suite(root, s)
    out, names = [], []
    emit = out.append
    call = lambda name: f' jsr ${s[name]:x}\n'
    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')
    def case(name, docked, reward):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n bsr qa_courier_world\n'
             f' move.w #{docked},docked(a6)\n move.w #{reward},courier_reward(a6)\n'
             ' move.w #$025a,courier_x(a6)\n clr.w count_down(a6)\n'
             ' clr.w check_key(a6)\n clr.w game_frozen(a6)\n')
    def press(key='W'):
        emit(' clr.w qa_info_calls\n clr.w qa_wait_calls\n clr.w qa_errors\n'
             f" moveq #'{key}',d0\n" + call('check'))
        eq(0, 'game_frozen(a6)'); eq(0, 'qa_wait_calls')
    # Count blocking endpoints so regressions fail instead of hanging. Keyboard
    # dispatch, contract lookup, chart drawing and prompt pixels remain native.
    hooks = [('game_info', 'qa_info'), ('wait', 'qa_wait'), ('fx', 'qa_fx')]
    for name, replacement in hooks:
        addr = s[name]
        emit(f' move.l ${addr:x},qa_saved_{name}\n move.w ${addr+4:x},qa_saved_{name}+4\n'
             f' move.w #$4ef9,${addr:x}\n move.l #{replacement},${addr+2:x}\n')
    for docked in (0, 1):
        for reward in (0, 5250):
            for screen in ('status', 'inventory'):
                case(f'{screen}, docked={docked}, cargo={bool(reward)}: W and V only beep', docked, reward)
                emit(call(screen)+call('hide_cursor')+' clr.w display_clock(a6)\n bsr qa_prompt_hash\n move.l d0,qa_expected_prompt\n')
                for key in ('W', 'V'):
                    press(key); eq(0, 'qa_info_calls'); eq(1, 'qa_errors')
                emit(' bsr qa_prompt_hash\n cmp.l qa_expected_prompt,d0\n bne fail\n')
            for chart, display in (('local_chart','disp_local'), ('galactic_chart','disp_galactic')):
                for countdown in (0, 3):
                    case(f'{chart}, docked={docked}, cargo={bool(reward)}, countdown={countdown}: target/feedback without waiting', docked, reward)
                    emit(call(chart)+call('hide_cursor')+call('clear_input'))
                    if docked and not reward and not countdown:
                        emit(' lea qa_docked_text,a0\n'+call('print_string'))
                    emit(' bsr qa_prompt_hash\n move.l d0,qa_expected_prompt\n'+call('clear_input'))
                    emit(f' move.w #45,req_planet(a6)\n move.w #{countdown},count_down(a6)\n')
                    press('V'); eq(0, 'qa_info_calls'); eq(1, 'qa_errors'); eq(45, 'req_planet(a6)')
                    press(); eq(0, 'qa_info_calls')
                    eq(int(not docked and not reward and not countdown), 'qa_errors')
                    eq(0 if reward and not countdown else 45, 'req_planet(a6)')
                    eq(display, 'disp_type(a6)'); eq(reward, 'courier_reward(a6)')
                    if not reward or countdown:
                        emit(' bsr qa_prompt_hash\n cmp.l qa_expected_prompt,d0\n bne fail\n')
    for reward in (0, 5250):
        for view in ('front_view', 'rear_view', 'left_view', 'right_view'):
            case(f'{view}, cargo={bool(reward)}: V opens credits and W only beeps', 0, reward)
            emit(call('prepare_cockpit')+call(view))
            press('W'); eq(0, 'qa_info_calls'); eq(1, 'qa_errors')
            press('V'); eq(1, 'qa_info_calls'); eq(0, 'qa_errors')
    for name, _ in hooks:
        addr = s[name]
        emit(f' move.l qa_saved_{name},${addr:x}\n move.w qa_saved_{name}+4,${addr+4:x}\n')
    stride = 'row_stride' if root.name == 'src_amiga' else '160'
    tail += f'''qa_prompt_hash:
 move.l scr_base(a6),a0
 lea prompt_y*{stride}(a0),a0
 move.w #8*{stride}/2-1,d7
 moveq #0,d0
.loop:
 rol.l #1,d0
 move.w (a0)+,d1
 eor.w d1,d0
 dbra d7,.loop
 rts
qa_info:
 addq.w #1,qa_info_calls
 rts
qa_wait:
 addq.w #1,qa_wait_calls
 rts
qa_fx:
 cmp.w #sfx_error,d0
 bne.s .done
 addq.w #1,qa_errors
.done:
 rts
qa_info_calls: dc.w 0
qa_wait_calls: dc.w 0
qa_errors: dc.w 0
qa_expected_prompt: dc.l 0
qa_docked_text: dc.b 'Docked!',0
 even
'''
    for name, _ in hooks:
        tail += f'qa_saved_{name}: ds.b 6\n'
    return prefix, ''.join(out), tail, names
