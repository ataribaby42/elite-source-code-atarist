"""Exercise real click timing with a visible cursor and large Shipyards balances."""
def make_suite(root, s):
    prefix = ' include "common.def"\n include "macros.m68"\n'
    call = lambda name: f' jsr ${s[name]:x}\n'
    serial = 0
    def tick(count):
        nonlocal serial
        serial += 1
        label = f'click_tick_{serial}'
        return (f' move.w frame_count(a6),-(sp)\n add.w #{count},(sp)\n{label}:\n'
                + call('check_keys')
                + f' move.w frame_count(a6),d0\n cmp.w (sp),d0\n blo.s {label}\n addq.l #2,sp\n')
    def click(x, y, kind):
        # Space is the cursor trigger in the actual VBL input handler. Releasing
        # it before the click delay expires exercises foreground action dispatch.
        return (f' move.w #{kind},cursor_type(a6)\n move.w #{x},cursor_spr+sp_xpos(a6)\n'
                + f' move.w #{y},cursor_spr+sp_ypos(a6)\n' + call('restore_cursor')
                + tick(3) + ' st key_states+$40(a6)\n' + tick(2)
                + ' clr.b key_states+$40(a6)\n' + tick(25) + call('hide_cursor'))
    parts = []
    for case, (hull, cash) in enumerate([(0, 10000000), (9, 0xffffffff)]):
        # Match the reported million-credit commander, then the largest trade-in
        # combined with every decimal digit supported by the unsigned cash field.
        parts += [f' clr.w cockpit_on(a6)\n move.w #1,docked(a6)\n move.w #{hull},player_ship(a6)\n'
                  + call('ship_apply') + f' move.l #${cash:x},cash(a6)\n'
                  + call('shipyards') + call('hide_cursor') + f'snap_balance_{case}_base:\n nop\n']
        # Changing cash must not alter the trade-in-only prompt on a click.
        parts += [f' move.l #${(0xffffffff if case == 0 else 10000000):x},cash(a6)\n']
        for kind in range(3):
            for index, (x, y) in enumerate([(40, 110), (150, 120), (260, 130), (32, 155)]):
                parts += [click(x, y, kind) + f'snap_balance_{case}_cursor_{kind}_{index}:\n nop\n']
            parts += [click(113, 168, kind)
                      + f' cmp.l #${s["equip_ship"]:x},action_ptr(a6)\n bne fail\n'
                      + click(149, 168, kind)
                      + f' cmp.l #${s["shipyards"]:x},action_ptr(a6)\n bne fail\n'
                      + f'snap_balance_{case}_cursor_{kind}_menu:\n nop\n']
        parts += [call('restore_cursor')]
    return prefix, ''.join(parts), 'qa_case: dc.w 0\n', []
