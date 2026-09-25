"""Native portrait palette fitting across every alien palette and slot conflict."""


def make_suite(root, symbols):
    source = (root / 'asm/pdata.m68').read_text()
    prefix = ' include "common.def"\n include "macros.m68"\n'
    prefix += source[source.index('\tq_vars pdata'):source.index('\tq_end_vars pdata')] + '\n'
    call = lambda name: f' jsr ${symbols[name]:x}\n'
    body = ' clr.w csr_on(a6)\n clr.w display_clock(a6)\n clr.w player_ship(a6)\n'
    body += call('ship_apply') + call('reset_system')
    body += ' clr.w galaxy_no(a6)\n clr.w mission(a6)\n move.l #$5a4a0248,gal_seed(a6)\n move.w #$b753,gal_seed+4(a6)\n'
    names, shots = [], 0

    def case(label):
        nonlocal body
        names.append(label)
        body += f' move.w #{len(names)},qa_case\n'

    def data(planet, enabled=False):
        nonlocal body
        body += (' bset' if enabled else ' bclr') + ' #f_planets,user+1(a6)\n'
        body += f' move.w #{planet},req_planet(a6)\n' + call('data') + call('hide_cursor')

    def snapshot(label):
        nonlocal body, shots
        shots += 1
        body += ' move.l scr_base(a6),qa_frame\n'
        body += f' lea ${symbols["palette"]:x},a0\n lea qa_palette(pc),a1\n moveq #15,d7\nqa_palette_{shots}:\n move.w (a0)+,(a1)+\n dbra d7,qa_palette_{shots}\n'
        body += f'snap_{label}:\n nop\n'
        if root.name == 'src_amiga':
            body += f' move.w #{shots},qa_snapshot\nqa_wait_{shots}:\n tst.w qa_snapshot\n bne.s qa_wait_{shots}\n'
        body += call('restore_cursor')

    # One actual head/body pair for each class; class 6 is the reported Learorce.
    planets = (50, 14, 12, 5, 39, 22, 61, 28)
    for colour_class, planet in enumerate(planets):
        case(f'Class {colour_class}: original character and palette')
        data(planet)
        snapshot(f'inh_{colour_class}_off')
        for mask in (0, 0x80, 0x100, 0x200, 0x180, 0x280, 0x300):
            case(f'Class {colour_class}: reserve green slots ${mask:03x}')
            data(planet)
            body += f' move.w #${mask:x},portrait_colours(a6)\n bset #f_planets,user+1(a6)\n'
            body += call('match_planet_palette')
            snapshot(f'inh_{colour_class}_mask_{mask:03x}')
    for planet in (7, *planets):
        for enabled in (False, True):
            state = 'on' if enabled else 'off'
            case(f'Actual Planet Data {planet}, Planets {state}')
            data(planet, enabled)
            snapshot(f'real_{planet}_{state}')
    tail = 'qa_case: dc.w 0\nqa_snapshot: dc.w 0\nqa_palette: ds.w 16\nqa_frame: dc.l 0\n'
    return prefix, body, tail, names
