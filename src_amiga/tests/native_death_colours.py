"""Death scenes use the purchasable model variant, independent of random seed."""

from native_station_death import GUARDS


def make_suite(root, s, view=None):
    if view is not None:
        return full_animation_suite(s, view)
    call = lambda name: f' jsr ${s[name]:x}\n'
    loop = s['q_effects_m68_1']
    prefix = ' include "common.def"\n include "macros.m68"\n'
    body = ' clr.w csr_on(a6)\n clr.w display_clock(a6)\n'
    body += call('reset_system') + call('launch_system')
    body += call('prepare_cockpit') + call('front_view')
    # Return at the first frame, after the real END_GAME object setup.
    # Restore the instruction after checking every purchasable hull.
    body += f' move.w ${loop:x},qa_loop_opcode\n move.w #$4e75,${loop:x}\n'
    names = []
    for hull in range(13):
        body += f' move.w #{hull},player_ship(a6)\n' + call('ship_apply')
        for seed in (0x12345678, 0xabcdef01, 0x5a4a0248):
            names.append(f'Hull {hull}, seed {seed:08x}: death model matches first UI material variant')
            body += f' move.w #{len(names)},qa_case\n move.l #${seed:x},random_seed(a6)\n'
            body += call('end_game')
            body += f''' lea objects(a6),a4
 btst #in_use,flags(a4)
 beq fail
 move.w hull_model(a6),d0
 cmp.w type(a4),d0
 bne fail
 lsl.w #2,d0
 lea ${s['obj_data']:x},a0
 move.l (a0,d0.w),a0
 move.l (a0),d1
 cmp.l nodes(a4),d1
 bne fail
 move.l 4(a0),a0
 move.l 2(a0),d1
 cmp.l surfaces(a4),d1
 bne fail
 cmp.w #-1,obj_colour(a4)
 bne fail
'''
    body += f' move.w qa_loop_opcode,${loop:x}\n'
    return prefix, body, 'qa_case: dc.w 0\nqa_stage: dc.w 0\nqa_loop_opcode: dc.w 0\n', names


def full_animation_suite(s, view):
    # Sidewinder is persistent hull 10. Exercise the entire animation with
    # viewport guards. Each view runs in a fresh emulator: END_GAME normally
    # returns to ATTRACT, rather than directly into another death animation.
    assert view in ('front_view', 'rear_view')
    call = lambda name: f' jsr ${s[name]:x}\n'
    prefix = ' include "common.def"\n include "macros.m68"\n'
    body = ' clr.w csr_on(a6)\n clr.w display_clock(a6)\n'
    body += ' move.w #1,qa_case\n move.w #10,player_ship(a6)\n'
    body += call('ship_apply') + call('reset_system') + call('launch_system')
    body += call('prepare_cockpit') + call(view)
    body += ' bsr qa_guard_set\n' + call('swap_screen') + ' bsr qa_guard_set\n'
    body += ' st game_over(a6)\n move.w #no_energy,reason(a6)\n clr.w energy(a6)\n'
    body += call('end_game') + ' bsr qa_guard_check\n'
    body += call('swap_screen') + ' bsr qa_guard_check\n'
    body += ' btst #in_use,objects+flags(a6)\n bne fail\n'
    return prefix, body, GUARDS + 'qa_case: dc.w 0\nqa_stage: dc.w 0\n', [
        f'Sidewinder: complete death animation from {view}']
