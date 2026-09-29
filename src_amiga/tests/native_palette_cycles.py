"""Native colour-cycle endpoints, cadence and isolation from other palette slots."""


def make_suite(root, s):
    source = (root / 'asm/except.m68').read_text()
    prefix = ' include "common.def"\n include "macros.m68"\n'
    prefix += source[source.index('\tq_vars except'):source.index('\tq_end_vars except')] + '\n'
    call = lambda name: f' jsr ${s[name]:x}\n'
    palette = s['palette']
    # Keep the real VBL from advancing FAST_TICKER during these short calls.
    body = ' move.w $dff01c,qa_intena\n move.w #$0020,$dff09a\n'
    body += f' lea ${palette:x},a0\n lea qa_palette,a1\n moveq #15,d7\nqa_save:\n move.w (a0)+,(a1)+\n dbra d7,qa_save\n'
    body += ' clr.w engine_port(a6)\n clr.w engine_dir(a6)\n'
    names = []

    def case(name):
        nonlocal body
        names.append(name)
        body += f' move.w #{len(names)},qa_case\n'

    def colour(expected):
        nonlocal body
        body += f' cmp.w #${expected:03x},${palette + 28:x}\n bne fail\n bsr qa_other_colours\n'

    levels = (0, 2, 4, 6, 9, 11, 13, 15)
    for index, level in enumerate((*range(1, 8), *range(6, 1, -1), *range(3, 8))):
        case(f'Engine step {index + 1}: ST intensity {level} maps to OCS {levels[level]}')
        body += ' clr.w fast_ticker(a6)\n' + call('engine_pulse')
        colour(levels[level] << 8)
        body += f' cmp.w #${level << 8:03x},engine_port(a6)\n bne fail\n'
    case('Engine skips odd VBL ticks without changing its colour or phase')
    body += ' move.w #1,fast_ticker(a6)\n' + call('engine_pulse')
    colour(0xf00)
    body += ' cmp.w #$700,engine_port(a6)\n bne fail\n'
    case('Stopped colour cycling preserves the palette and engine phase')
    body += ' st stop_cycle(a6)\n clr.w cycle_type(a6)\n clr.w fast_ticker(a6)\n'
    body += call('colour_cycle')
    colour(0xf00)
    body += ' cmp.w #$700,engine_port(a6)\n bne fail\n'
    body += ' clr.w csr_state(a6)\n clr.w csr_clock(a6)\n'
    for number, expected in enumerate((0xfff, 0xf00, 0xfff)):
        case(f'Cursor phase {number}: unchanged for 29 ticks, then full RGB {expected:03x}')
        body += f' move.w ${palette + 28:x},qa_previous\n'
        for _ in range(29):
            body += call('flash_colour')
            body += f' move.w qa_previous,d0\n cmp.w ${palette + 28:x},d0\n bne fail\n'
        body += call('flash_colour')
        colour(expected)
        body += ' tst.w csr_clock(a6)\n bne fail\n'
    body += f' lea qa_palette,a0\n lea ${palette:x},a1\n moveq #15,d7\nqa_restore:\n move.w (a0)+,(a1)+\n dbra d7,qa_restore\n'
    body += ' move.w qa_intena,d0\n and.w #$0020,d0\n or.w #$8000,d0\n move.w d0,$dff09a\n'
    tail = 'qa_other_colours:\n'
    for slot in range(16):
        if slot != 14:
            tail += f' move.w qa_palette+{slot*2},d0\n cmp.w ${palette + slot*2:x},d0\n bne fail\n'
    tail += ' rts\nqa_case: dc.w 0\nqa_intena: dc.w 0\nqa_previous: dc.w 0\n'
    tail += 'qa_palette: ds.w 16\nqa_snapshot: dc.w 0\nqa_frame: dc.l 0\n'
    return prefix, body, tail, names
