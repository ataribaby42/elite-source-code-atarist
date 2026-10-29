"""Native status-clock rotation and accelerated Planet Data animation checks."""
import random
import re
from native_planet_spans import make_suite as surface_suite


def make_suite(root, s):
    prefix, body, tail, names = surface_suite(root, s)
    shots = len(re.findall(r'^snap_\w+:', body, re.M))
    call = lambda name: '' if name == 'wait_clear' and name not in s else f' jsr ${s[name]:x}\n'
    zx, zy = (s['_geometry']['zoom_x'], s['_geometry']['zoom_y']) if root.name == 'src_amiga' else (1, 1)

    def case(name):
        nonlocal body
        names.append(name)
        body += f' move.w #{len(names)},qa_case\n'

    def snapshot(name, present=False):
        nonlocal body, shots
        shots += 1
        if root.name == 'src_amiga':
            body += ' movem.l d0-d7/a0-a5,-(sp)\n move.l scr_base(a6),qa_frame\n'
            if present:
                body += call('swap_screen')
            body += ' movem.l (sp)+,d0-d7/a0-a5\n'
        body += f'snap_{name}:\n nop\n'
        if root.name == 'src_amiga':
            body += f' move.w #{shots},qa_snapshot\nqa_spin_wait_{shots}:\n tst.w qa_snapshot\n bne.s qa_spin_wait_{shots}\n'

    def due():
        nonlocal body
        body += call('comm_now')+' subq.l #3,d0\n move.l d0,ps_portrait_tick(a6)\n'

    def render(minutes, direction):
        nonlocal body
        body += f' st game_frozen(a6)\n clr.l game_time(a6)\n clr.w game_time+6(a6)\n move.w #{minutes%60},game_time+2(a6)\n move.w #{minutes//60},game_time+4(a6)\n move.w #{direction},ps_spin_direction(a6)\n'
        body += ' bsr qa_fill\n'+call('clear_image')+call('wait_clear')
        body += f' lea planet_rec(a6),a5\n move.w #{48*zy},scr_radius(a5)\n clr.w centre_x(a5)\n clr.w centre_y(a5)\n clr.l this_xpos(a5)\n clr.l this_ypos(a5)\n move.l #100000,this_zpos(a5)\n move.w #planet,d0\n'
        body += call('draw_point')+' bsr qa_guard_check\n'

    case('Exact clock phase for every 30..120-minute period, both directions and clock boundaries')
    rows=[]
    rng=random.Random(20261030)
    for minutes in range(30,121):
        period=minutes*60
        for seconds in (0,period//4,period-1,period,86399,86400,2073599,rng.randrange(2073600)):
            days, rem=divmod(seconds,86400)
            hour, rem=divmod(rem,3600)
            minute, second=divmod(rem,60)
            phase=((seconds%period)*65536//period)&65535
            rows.append((minutes,second,minute,hour,days,phase))
    # Reuse each clock vector for both directions to keep the native payload
    # within the Amiga harness allocation on a 1 MB machine.
    body += f' st game_frozen(a6)\n lea qa_spin_vectors,a0\n move.w #{len(rows)-1},d7\nqa_spin_clock_case:\n move.w (a0)+,ps_spin_minutes(a6)\n move.l (a0)+,game_time(a6)\n move.l (a0)+,game_time+4(a6)\n move.w #1,ps_spin_direction(a6)\n'+call('ps_clock_phase')+' cmp.w (a0),d0\n bne fail\n move.w #-1,ps_spin_direction(a6)\n'+call('ps_clock_phase')+' neg.w d0\n cmp.w (a0)+,d0\n bne fail\n dbra d7,qa_spin_clock_case\n'
    tail += 'qa_spin_vectors:\n'+''.join(' dc.w '+','.join(str(v) for v in row)+'\n' for row in rows)

    case('Flight spin keeps the random arrival orientation and immutable seeded map')
    body += ' bset #f_planets,user+1(a6)\n move.l #$5a4a0248,splanet+seed(a6)\n move.w #$b753,splanet+seed+4(a6)\n move.l #$12345678,random_seed(a6)\n lea planet_rec(a6),a4\n move.w #8,obj_colour(a4)\n'
    body += call('init_planet_surface')+call('turn_planet_surface')
    body += ' lea planet_rec(a6),a5\n'+call('calc_yvector')
    body += ' lea x_vector(a5),a0\n lea qa_spin_basis,a1\n moveq #8,d7\nqa_spin_save_basis:\n move.w (a0)+,(a1)+\n dbra d7,qa_spin_save_basis\n lea ps_map(a6),a0\n lea qa_map,a1\n move.w #ps_features*ps_feature_bytes/2-1,d7\nqa_spin_save_map:\n move.w (a0)+,(a1)+\n dbra d7,qa_spin_save_map\n move.w #120,ps_spin_minutes(a6)\n'
    for direction, label in ((1,'positive'),(-1,'negative')):
        for minutes in (0,30,60,90,120):
            case(f'Flight {label} rotation at minute {minutes} of a two-hour period')
            render(minutes,direction)
            body += ' lea x_vector(a5),a0\n lea qa_spin_basis,a1\n moveq #8,d7\n'
            tag=f'{label}_{minutes}'
            body += f'qa_spin_check_basis_{tag}:\n move.w (a0)+,d0\n cmp.w (a1)+,d0\n bne fail\n dbra d7,qa_spin_check_basis_{tag}\n'
            snapshot('spin_'+tag,True)
    body += ' lea ps_map(a6),a0\n lea qa_map,a1\n move.w #ps_features*ps_feature_bytes/2-1,d7\nqa_spin_check_map:\n move.w (a0)+,d0\n cmp.w (a1)+,d0\n bne fail\n dbra d7,qa_spin_check_map\n cmp.l #$12345678,random_seed(a6)\n bne fail\n'

    case('F7 opens a separate cached portrait at zero phase')
    body += ' clr.w game_over(a6)\n move.w #8,req_planet(a6)\n moveq #8,d0\n'+call('get_planet_info')+call('data')+call('hide_cursor')
    body += ' tst.w ps_portrait_phase(a6)\n bne fail\n tst.w ps_portrait_cached(a6)\n beq fail\n lea ps_map(a6),a0\n lea qa_live,a1\n move.w #ps_work_bytes/2-1,d7\nqa_spin_save_live:\n move.w (a0)+,(a1)+\n dbra d7,qa_spin_save_live\n lea planet_rec(a6),a0\n move.w #obj_len/2-1,d7\nqa_spin_save_object:\n move.w (a0)+,(a1)+\n dbra d7,qa_spin_save_object\n move.l random_seed(a6),qa_spin_rng\n move.l splanet+seed(a6),qa_seed\n move.w splanet+seed+4(a6),qa_seed+4\n move.l w_view_ptr(a6),qa_view\n'
    snapshot('f7_start')
    case('F7 rate limit prevents an extra step in the same frame')
    body += call('comm_now')+' move.l d0,ps_portrait_tick(a6)\n'+call('update_planet_data')+' tst.w ps_portrait_phase(a6)\n bne fail\n'
    case('F7 uses the selected planet direction and preserves input events and live state')
    body += ' move.w ps_portrait_cache+ps_spin_direction-ps_map(a6),d0\n asl.w #8,d0\n move.w d0,qa_spin_step\n move.w #7,move_x(a6)\n move.w #-5,move_y(a6)\n move.w #1,button_pressed(a6)\n'
    due();body+=call('update_planet_data')
    body += ' move.w qa_spin_step,d0\n cmp.w ps_portrait_phase(a6),d0\n bne fail\n cmp.w #7,move_x(a6)\n bne fail\n cmp.w #-5,move_y(a6)\n bne fail\n cmp.w #1,button_pressed(a6)\n bne fail\n clr.w button_pressed(a6)\n'
    snapshot('f7_step')
    # Poison the selected seed: animation must use the prepared cache, without
    # regenerating geometry or selecting colours again on every frame.
    body += ' move.l cplanet+seed(a6),qa_spin_selected\n move.w cplanet+seed+4(a6),qa_spin_selected+4\n clr.l cplanet+seed(a6)\n clr.w cplanet+seed+4(a6)\n'
    for step in range(2,9):
        due();body+=call('update_planet_data')
        snapshot(f'f7_step_{step}')
    body += ' move.l qa_spin_selected,cplanet+seed(a6)\n move.w qa_spin_selected+4,cplanet+seed+4(a6)\n move.w qa_spin_step,d0\n lsl.w #3,d0\n cmp.w ps_portrait_phase(a6),d0\n bne fail\n'
    body += ' lea ps_map(a6),a0\n lea qa_live,a1\n move.w #ps_work_bytes/2-1,d7\nqa_spin_check_live:\n move.w (a0)+,d0\n cmp.w (a1)+,d0\n bne fail\n dbra d7,qa_spin_check_live\n lea planet_rec(a6),a0\n move.w #obj_len/2-1,d7\nqa_spin_check_object:\n move.w (a0)+,d0\n cmp.w (a1)+,d0\n bne fail\n dbra d7,qa_spin_check_object\n move.l qa_spin_rng,d0\n cmp.l random_seed(a6),d0\n bne fail\n move.l qa_seed,d0\n cmp.l splanet+seed(a6),d0\n bne fail\n move.w qa_seed+4,d0\n cmp.w splanet+seed+4(a6),d0\n bne fail\n move.l qa_view,d0\n cmp.l w_view_ptr(a6),d0\n bne fail\n'
    for label,condition,undo in [('paused',' st game_frozen(a6)\n',' clr.w game_frozen(a6)\n'),('off',' bclr #f_planets,user+1(a6)\n',' bset #f_planets,user+1(a6)\n'),('cockpit',' st cockpit_on(a6)\n',' clr.w cockpit_on(a6)\n')]:
        case(f'F7 stops while {label}')
        body+=' move.w ps_portrait_phase(a6),qa_spin_phase\n'+condition
        due();body+=call('update_planet_data')
        body+=' move.w qa_spin_phase,d0\n cmp.w ps_portrait_phase(a6),d0\n bne fail\n'+undo
    case('Leaving F7 stops animation on another UI page')
    body+=call('restore_cursor')+call('status')+call('hide_cursor')
    # Pixel comparison permits the normal ticking/flashing status-clock row.
    snapshot('f7_status_before')
    body+=' move.w ps_portrait_phase(a6),qa_spin_phase\n'
    due();body+=call('update_planet_data')
    body+=' move.w qa_spin_phase,d0\n cmp.w ps_portrait_phase(a6),d0\n bne fail\n'
    snapshot('f7_status_after')
    body+=call('restore_cursor')
    tail += 'qa_spin_basis: ds.w 9\nqa_spin_rng: dc.l 0\nqa_spin_step: dc.w 0\nqa_spin_phase: dc.w 0\nqa_spin_selected: ds.b 6\n'
    body=re.sub(r'(qa_\w+)\(pc\)',r'\1',body)
    return prefix,body,tail,names
