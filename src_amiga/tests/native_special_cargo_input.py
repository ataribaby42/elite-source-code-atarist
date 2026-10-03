"""Receipt navigation must interrupt the timer and survive story dispatch."""
from native_special_cargo_ui import make_suite as ui_suite


def make_suite(root, s):
    prefix, _, tail, _ = ui_suite(root, s)
    out, names = [], []
    emit = out.append
    call = lambda n: f' jsr ${s[n]:x}\n'

    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n bsr qa_courier_world\n'
             ' clr.l courier_next_action(a6)\n clr.w button_pressed(a6)\n'
             ' clr.w key_used(a6)\n clr.w key_head(a6)\n clr.w key_tail(a6)\n'
             ' clr.w qa_waits\n clr.w qa_inject\n')

    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')

    def queue(key):
        emit(f' move.b #{key},key_buffer(a6)\n move.w #1,key_head(a6)\n move.w #1,key_used(a6)\n')

    nav = [('1', 'launch'), ('2', 'buy_cargo'), ('3', 'sell_cargo'), ('4', 'equip_ship'),
           ('5', 'galactic_chart'), ('6', 'local_chart'), ('7', 'data'),
           ('8', 'market_prices'), ('9', 'status'), ('0', 'inventory')]
    keys = [(ord(key), name) for key, name in nav]
    keys += [(128 + i, name) for i, (_, name) in enumerate(nav)]
    keys += [(ord(key), name) for key, name in
             [('-', 'disk'), ('=', 'options'), ('F', 'find_planet'), ('B', 'home_cursor'), ('D', 'disp_distance')]]
    for key, name in keys:
        case(f'Receipt key {key} queues {name}, consumes the key and dismisses immediately')
        queue(key)
        emit(call('courier_poll_receipt'))
        eq(1, 'd0'); eq(f'${s[name]:x}', 'courier_next_action(a6)', 'l')
        eq(0, 'courier_next_function(a6)'); eq(0, 'key_used(a6)')

    icons = [(36, 178, 'launch'), (68, 178, 'buy_cargo'), (96, 178, 'sell_cargo'),
             (128, 178, 'equip_ship'), (162, 178, 'shipyards'), (202, 178, 'galactic_chart'),
             (240, 178, 'local_chart'), (278, 178, 'data'), (38, 186, 'market_prices'),
             (86, 186, 'inventory'), (136, 186, 'status'), (174, 186, 'disk'),
             (204, 186, 'find_planet'), (234, 186, 'home_cursor'), (272, 186, 'options')]
    for x, y, name in icons:
        case(f'Receipt icon {name}: actual hit testing queues navigation')
        emit(call('prepare_text') + f' lea ${s["courier_receipt_actions"]:x},a0\n' + call('init_cursor'))
        zx = '*zoom_x' if root.name == 'src_amiga' else ''
        zy = '*zoom_y' if root.name == 'src_amiga' else ''
        emit(call('hide_cursor') + f' move.w #({x}-10){zx},cursor_spr+sp_xpos(a6)\n'
             f' move.w #({y}-8){zy},cursor_spr+sp_ypos(a6)\n' + call('restore_cursor'))
        emit(call('single_click') + call('courier_poll_receipt'))
        eq(1, 'd0'); eq(f'${s[name]:x}', 'courier_next_action(a6)', 'l'); eq(0, 'button_pressed(a6)')
        emit(call('hide_cursor'))

    case('Unrelated keys do not dismiss the receipt or execute flight actions')
    queue(ord('M'))
    emit(call('courier_poll_receipt')); eq(0, 'd0'); eq(0, 'courier_next_action(a6)', 'l')

    # Replace only the clock wait: inject events after three elapsed ticks.
    wait = s['wait']
    emit(f' move.l ${wait:x},qa_wait_original\n move.w ${wait+4:x},qa_wait_original+4\n'
         f' move.w #$4ef9,${wait:x}\n move.l #qa_wait,${wait+2:x}\n')
    for mode, label in ((0, 'timeout'), (1, 'keyboard'), (2, 'mouse')):
        case(f'Receipt timer: {label} takes {96 if mode == 0 else 3} ticks')
        emit(f' move.w #{mode},qa_inject\n' + call('courier_wait_receipt'))
        eq(96 if mode == 0 else 3, 'qa_waits')
        eq(0 if mode == 0 else f'${s["buy_cargo"]:x}', 'courier_next_action(a6)', 'l')

    # Real docking + native dock_check + native Status + selected Buy screen.
    dockseq = s['docking_sequence']
    emit(f' move.l ${dockseq:x},qa_dock_original\n move.w ${dockseq+4:x},qa_dock_original+4\n'
         f' move.w #$4ef9,${dockseq:x}\n move.l #qa_return,${dockseq+2:x}\n')
    for mode in (0, 1, 2):
        case(f'Real docking navigation mode {mode}: pay once, run story/status, keep the chosen screen')
        emit(' move.w #5250,courier_reward(a6)\n move.w #$14ad,courier_x(a6)\n'
             ' clr.w rating(a6)\n clr.w logo_shown(a6)\n clr.w mission(a6)\n'
             f' move.w #{mode},qa_inject\n' + call('docking'))
        eq(0, 'courier_reward(a6)'); eq(10005250, 'cash(a6)', 'l')
        eq(0, 'courier_next_action(a6)', 'l')
        eq('icon_buy' if mode else 'icon_status', 'last_icon(a6)')
        emit(call('courier_continue')); eq(10005250, 'cash(a6)', 'l')

    # Route a simultaneous original mission before the requested menu. The
    # mission offer itself is substituted to avoid an interactive Y/N dialog.
    offer = s['offer1']
    emit(f' move.l ${offer:x},qa_offer_original\n move.w ${offer+4:x},qa_offer_original+4\n'
         f' move.w #$4ef9,${offer:x}\n move.l #qa_offer,${offer+2:x}\n')
    case('Simultaneous Thargoid mission is dispatched after payment and before the chosen Buy screen')
    emit(' move.w #5250,courier_reward(a6)\n move.w #$14ad,courier_x(a6)\n'
         ' clr.w rating(a6)\n clr.w logo_shown(a6)\n move.w #$20,mission(a6)\n'
         ' move.w #1,qa_inject\n clr.w qa_story\n' + call('docking'))
    eq(1, 'qa_story'); eq('icon_buy', 'last_icon(a6)'); eq(0, 'courier_next_action(a6)', 'l')
    for address, label in ((wait, 'qa_wait_original'), (dockseq, 'qa_dock_original'), (offer, 'qa_offer_original')):
        emit(f' move.l {label},${address:x}\n move.w {label}+4,${address+4:x}\n')
    emit(call('hide_cursor'))
    tail += f'''qa_wait:
 addq.w #1,qa_waits
 cmp.w #3,qa_waits
 bne.s qa_return
 tst.w qa_inject
 beq.s qa_return
 cmp.w #1,qa_inject
 bne.s qa_mouse
 move.b #'2',key_buffer(a6)
 clr.w key_tail(a6)
 move.w #1,key_head(a6)
 move.w #1,key_used(a6)
 rts
qa_mouse:
 move.l #${s['buy_cargo']:x},action_ptr(a6)
 clr.w function(a6)
 st button_pressed(a6)
qa_return: rts
qa_offer:
 cmp.l #10005250,cash(a6)
 bne fail
 tst.w courier_reward(a6)
 bne fail
 cmp.l #${s['buy_cargo']:x},courier_next_action(a6)
 bne fail
 addq.w #1,qa_story
 rts
qa_waits: dc.w 0
qa_inject: dc.w 0
qa_story: dc.w 0
qa_wait_original: ds.b 6
qa_dock_original: ds.b 6
qa_offer_original: ds.b 6
'''
    return prefix, ''.join(out), tail, names
