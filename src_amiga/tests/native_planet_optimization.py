"""Pixel-comparison captures and repeatable timings for surface optimizations.

Run the same fixture against the before and after binaries. Compare the screen
captures byte-for-byte; qa_perf_* words count VBL ticks for 32 detail passes
(50 Hz in the PAL benchmark).
"""
import math
import re
from native_planet_surface import make_suite as surface_suite


def make_suite(root, s):
    prefix, body, tail, names = surface_suite(root, s)
    shots = len(re.findall(r'^snap_\w+:', body, re.M))
    call = lambda name: '' if name == 'wait_clear' and name not in s else f' jsr ${s[name]:x}\n'
    zx, zy = s['_geometry']['zoom_x'], s['_geometry']['zoom_y']

    def case(name):
        nonlocal body
        names.append(name)
        body += f' move.w #{len(names)},qa_case\n'

    def init(colour, seed_index=0, angle=0):
        nonlocal body
        seed = [(0x5a4a, 0x0248, 0xb753), (0x1234, 0x5678, 0xabcd),
                (0xffff, 0x8000, 0x0001)][seed_index]
        for i, value in enumerate(seed):
            body += f' move.w #${value:x},splanet+seed+{i*2}(a6)\n'
        body += f' lea planet_rec(a6),a4\n move.w #{colour},obj_colour(a4)\n'
        body += call('init_planet_surface') + ' lea planet_rec(a6),a5\n'
        cosine = round(math.cos(math.radians(angle)) * 16384)
        sine = round(math.sin(math.radians(angle)) * 16384)
        body += (f' move.w #{cosine},x_vector+i(a5)\n clr.w x_vector+j(a5)\n'
                 f' move.w #{-sine},x_vector+k(a5)\n move.w #{sine},z_vector+i(a5)\n'
                 f' clr.w z_vector+j(a5)\n move.w #{cosine},z_vector+k(a5)\n'
                 ' bclr #yvector_ok,flags(a5)\n')

    def render(radius=48, x=0, y=0, eye_x=0, eye_y=0):
        nonlocal body
        body += ' bsr qa_fill\n' + call('clear_image') + call('wait_clear')
        body += (f' lea planet_rec(a6),a5\n move.w #{radius*zy},scr_radius(a5)\n'
                 f' move.w #{x*zx},centre_x(a5)\n move.w #{y*zy},centre_y(a5)\n'
                 f' move.l #{eye_x},this_xpos(a5)\n move.l #{eye_y},this_ypos(a5)\n'
                 ' move.l #100000,this_zpos(a5)\n move.w #planet,d0\n')
        body += call('draw_point') + ' bsr qa_guard_check\n'

    def snapshot(label):
        nonlocal body, shots
        shots += 1
        body += ' movem.l d0-d7/a0-a5,-(sp)\n move.l scr_base(a6),qa_frame\n' + call('swap_screen') + ' movem.l (sp)+,d0-d7/a0-a5\n'
        body += f'snap_{label}:\n nop\n move.w #{shots},qa_snapshot\nqa_opt_wait_{shots}:\n tst.w qa_snapshot\n bne.s qa_opt_wait_{shots}\n'

    body += ' bset #f_planets,user+1(a6)\n' + call('prepare_cockpit') + call('front_view')
    body+=' st game_frozen(a6)\n clr.l game_time(a6)\n clr.l game_time+4(a6)\n'
    for seed_index in range(3):
        for colour in (8, 1):
            for angle in range(0, 360, 45):
                label = f'opt_seed{seed_index}_colour{colour}_yaw{angle}'
                case(label)
                init(colour, seed_index, angle)
                render(48, eye_x=17000 * seed_index, eye_y=-13000 * seed_index)
                snapshot(label)

    for i, (radius, x, y) in enumerate([(11, 0, 0), (12, 0, 0), (13, 0, 0),
                                      (60, -110, 0), (100, 100, 40), (200, 0, 0),
                                      (500, 450, 0), (1200, -1100, 600), (4000, 3900, 0)]):
        for colour in (8, 1):
            label = f'opt_bounds{i}_colour{colour}'
            case(label)
            init(colour, 1, 45)
            render(radius, x, y)
            snapshot(label)

    for colour in (8, 1):
        for radius, angle in [(48, angle) for angle in range(0, 360, 45)] + [(12, 0), (120, 0)]:
            label = f'qa_perf_c{colour}_r{radius}_a{angle}'
            case(f'Timing: colour {colour}, radius {radius}, yaw {angle}, 32 detail passes')
            init(colour, 0, angle)
            render(radius)
            body += ' clr.w frame_count(a6)\n move.w #31,qa_repeat\n'
            body += label + '_loop:\n' + call('draw_planet_surface')
            body += (f' subq.w #1,qa_repeat\n bpl {label}_loop\n'
                     f' move.w frame_count(a6),{label}\n')
            tail += label + ': dc.w 0\n'
    snapshot('opt_timing_complete')
    # The combined capture suite exceeds a signed PC-relative displacement.
    body = re.sub(r'(qa_\w+)\(pc\)', r'\1', body)
    return prefix, body, tail, names
