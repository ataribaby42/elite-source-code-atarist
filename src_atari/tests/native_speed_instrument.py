"""Native launch/jump transitions must refresh both speed gauge buffers."""

def make_suite(root, s):
    call = lambda name: f' jsr ${s[name]:x}\n'
    prefix = ' include "common.def"\n include "macros.m68"\n'
    flight = (root / 'asm/flight.m68').read_text()
    prefix += flight[flight.index('\tq_vars flight'):flight.index('\tq_end_vars flight')] + '\n'
    body = ' clr.w csr_on(a6)\n clr.w display_clock(a6)\n clr.w player_ship(a6)\n'
    body += call('ship_apply')
    names = []
    shots = 0

    def case(name):
        nonlocal body
        names.append(name)
        body += f' move.w #{len(names)},qa_case\n'

    def snapshot(name):
        nonlocal body, shots
        shots += 1
        body += f'snap_{name}:\n nop\n'

    def check_speed(name):
        nonlocal body
        body += ' tst.w docked(a6)\n bne fail\n move.w hull_speed(a6),d0\n mulu #3,d0\n lsr.w #2,d0\n cmp.w speed(a6),d0\n bne fail\n tst.w f_speed(a6)\n bne fail\n'
        for screen in (1, 2):
            body += f' move.l screen{screen}_ptr(a6),scr_base(a6)\n'
            body += call('update_inst')
            snapshot(f'{name}_screen{screen}')
        body += ' cmp.b #3,f_speed(a6)\n bne fail\n cmp.w #yellow,speed_col(a6)\n bne fail\n'

    for sequence, old_speed, name in ((False, 22, 'short_full'), (False, 0, 'short_stopped'), (True, 22, 'full_full')):
        case(f'Launch sequence {sequence}: old speed {old_speed}, no throttle input')
        body += f' move.w #{old_speed},speed(a6)\n st docked(a6)\n'
        body += call('status')
        body += (' bset' if sequence else ' bclr') + ' #f_sequence,user(a6)\n'
        body += call('launch')
        check_speed(name)

    for galactic, name in ((False, 'hyperspace'), (True, 'galactic')):
        case(f'{name}: maximum speed before the jump, no throttle input')
        body += ' move.w hull_speed(a6),speed(a6)\n'
        body += call('instruments')
        for screen in (1, 2):
            body += f' move.l screen{screen}_ptr(a6),scr_base(a6)\n' + call('update_inst')
        body += ' clr.w mission(a6)\n move.w #64,jump_count(a6)\n clr.w count_down(a6)\n clr.w fuel_needed(a6)\n move.w #8,req_planet(a6)\n clr.b key_states+$38(a6)\n'
        body += ' move.w galaxy_no(a6),qa_galaxy\n'
        body += (' st' if galactic else ' clr.w') + ' jump_type(a6)\n st jump_trigger(a6)\n'
        body += call('hyperspace')
        body += ' move.w qa_galaxy(pc),d0\n'
        if galactic:
            body += ' addq.w #1,d0\n and.w #7,d0\n'
        body += ' cmp.w galaxy_no(a6),d0\n bne fail\n'
        check_speed(name)

    tail = 'qa_case: dc.w 0\nqa_galaxy: dc.w 0\nqa_frame: dc.l 0\nqa_snapshot: dc.w 0\nqa_palette: ds.w 16\n'
    return prefix, body, tail, names
