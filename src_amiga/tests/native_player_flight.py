def make_suite(root,s):
    call=lambda n:f' jsr ${s[n]:x}\n'
    parts=[];names=[]
    for n in range(13):
        names.append(f'Hull {n}: create departure system, draw cockpit and run 8 live flight frames')
        parts.append(f' move.w #{n+1},qa_case\n move.w #{n},player_ship(a6)\n'+call('ship_apply'))
        parts.append(' move.w hull_fuel(a6),equip+fuel(a6)\n move.w hull_missiles(a6),equip+missiles(a6)\n clr.w game_over(a6)\n')
        parts.append(call('reset_system')+call('launch_system')+call('front_view'))
        parts.append(' move.w hull_speed(a6),speed(a6)\n move.w hull_roll(a6),roll_angle(a6)\n move.w hull_pitch(a6),climb_angle(a6)\n'+call('set_roll_angles')+call('set_climb_angles'))
        parts.append(f' moveq #7,d6\nflight_loop_{n}:\n move.w d6,-(sp)\n clr.w frame_count(a6)\n addq.b #1,loop_ctr(a6)\n'+call('game_logic')+f' tst.w game_over(a6)\n bne fail\n tst.w docked(a6)\n bne fail\n tst.w energy(a6)\n beq fail\n move.w (sp)+,d6\n dbra d6,flight_loop_{n}\n')
    names.append('Anaconda: normal Launch action and cockpit after returning to docked menu')
    parts.append(' move.w #14,qa_case\n move.w #8,player_ship(a6)\n'+call('ship_apply')+' move.w #1,docked(a6)\n'+call('status')+call('launch')+' tst.w docked(a6)\n bne fail\n tst.w game_over(a6)\n bne fail\n'+call('game_logic'))
    return ' include "common.def"\n include "macros.m68"\n',''.join(parts),'qa_case: dc.w 0\n',names
