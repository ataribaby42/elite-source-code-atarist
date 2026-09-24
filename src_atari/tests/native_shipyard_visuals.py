"""Capture real ship purchase, laser placement and planet screens in a native emulator."""
def make_suite(root, s):
    source = (root / 'asm/equip.m68').read_text()
    local = source[source.index('\tq_vars equip'):source.index('\tq_end_vars equip')]
    prefix = ' include "common.def"\n include "macros.m68"\n' + local + '\n'
    call = lambda name: f' jsr ${s[name]:x}\n'
    body = ' clr.w cockpit_on(a6)\n move.w #1,docked(a6)\n clr.w player_ship(a6)\n' + call('ship_apply')
    body += ' lea equip(a6),a0\n moveq #16,d7\nqa_clear_equip:\n clr.w (a0)+\n dbra d7,qa_clear_equip\n'
    body += ' move.w #$8000,equip+pulse_lasers(a6)\n move.w #$8000,equip+beam_lasers(a6)\n move.w #$8000,equip+mining_lasers(a6)\n move.w #$8000,equip+military_lasers(a6)\n'
    body += ' move.l #10000000,cash(a6)\n clr.w splanet+econ(a6)\n move.w #1,splanet+govern(a6)\n'
    body += call('shipyards') + ' moveq #2,d0\n' + call('d_yard')
    body += ' cmp.w #3,player_ship(a6)\n bne fail\n' + call('hide_cursor') + 'snap_purchase:\n nop\n' + call('restore_cursor')
    # Bypass only the dialog's input wait, after the real drawing has completed.
    # Restore the original instruction before leaving the suite.
    wait = s['q_equip_m68_23']
    body += f' move.w ${wait:x},qa_wait_opcode\n move.w #$4e75,${wait:x}\n'
    for hull in range(13):
        body += f' move.w #{hull},player_ship(a6)\n' + call('ship_apply')
        for sell in (() if hull == 11 else (0,1)):
            body += f' move.w #{sell},equip_sell_mode(a6)\n move.w #14,splanet+tech(a6)\n'
            body += f' move.w #${0x8001 if sell else 0x8000:x},equip+pulse_lasers(a6)\n'
            body += call('equip_redraw') + ' move.w #pulse_lasers/2,this_equip(a6)\n' + call('find_equip') + call('buy_laser')
            body += call('hide_cursor') + f'snap_laser_{hull}_{sell}:\n nop\n' + call('restore_cursor') + call('remove_mount')
        body += call('data') + call('hide_cursor') + f'snap_planet_{hull}:\n nop\n' + call('restore_cursor')
    body += f' move.w qa_wait_opcode,${wait:x}\n'
    return prefix, body, 'qa_case: dc.w 0\nqa_wait_opcode: dc.w 0\n', []
