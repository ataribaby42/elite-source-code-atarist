"""Native interval-union regressions, in addition to the pixel/timing suite."""
import random
from native_planet_horizon import make_suite as horizon_suite


def make_suite(root, s):
    prefix, body, tail, names = horizon_suite(root, s)
    graphics = (root / 'asm/graphics.m68').read_text()
    prefix += ('\nmax_vert: equ 16\n' +
               graphics[graphics.index('\tq_vars graphics'):
                        graphics.index('\tq_end_vars graphics')] + '\n')
    sparse = [(3 + 19*i, 3 + 19*i) for i in range(12)]
    cases = [sparse, list(reversed(sparse)), sparse[::2] + sparse[1::2],
             [(0, 255)] * 12, [(255, 0)] * 12,
             [(20*i, 20*i+9) for i in range(12)],
             [(20*i, 20*i+19) for i in range(12)],
             sparse[:11] + [(0, 255)],
             [(0, 3), (10, 13), (20, 23), (30, 33), (40, 43), (50, 53),
              (60, 63), (70, 73), (80, 83), (90, 93), (100, 103), (2, 101)]]
    rng = random.Random(20261029)
    while len(cases) < 24:
        cases.append([(rng.randrange(256), rng.randrange(256)) for _ in range(12)])
    names.append('24 native span unions: disjoint, touching, reversed, bridge merges, capacity 12 and row reuse')
    body += f''' move.w #{len(names)},qa_case
 lea qa_batch_cases,a0
 move.l a0,qa_batch_next
 move.w #23,qa_batch_cases_left
qa_batch_case:
 jsr ${s['begin_polygon_batch']:x}
 move.l qa_batch_next,a0
 move.w (a0)+,qa_batch_row
 move.w #11,qa_batch_inputs
 move.l a0,qa_batch_next
qa_batch_input:
 move.l qa_batch_next,a0
 move.w (a0)+,${s['left_arm']:x}
 move.w (a0)+,${s['right_arm']:x}
 move.l a0,qa_batch_next
 move.w qa_batch_row,top_y(a6)
 move.w qa_batch_row,bottom_y(a6)
 jsr ${s['polygon_batch_collect']:x}
 subq.w #1,qa_batch_inputs
 bpl qa_batch_input
 bsr qa_batch_address
 move.l qa_batch_next,a1
 move.w (a1)+,d7
 cmp.w (a0),d7
 bne fail
 subq.w #1,d7
qa_batch_expected:
 move.l (a1)+,d0
 lea 2(a0),a2
 move.w (a0),d1
 subq.w #1,d1
qa_batch_find:
 cmp.l (a2)+,d0
 beq qa_batch_found
 dbra d1,qa_batch_find
 bra fail
qa_batch_found:
 dbra d7,qa_batch_expected
 move.l a1,qa_batch_next
 jsr ${s['end_polygon_batch']:x}
 bsr qa_batch_address
 tst.w (a0)
 bne fail
 tst.w batch_active(a6)
 bne fail
 subq.w #1,qa_batch_cases_left
 bpl qa_batch_case
 ; Empty batches must reset their flag without touching the screen.
 jsr ${s['begin_polygon_batch']:x}
 jsr ${s['end_polygon_batch']:x}
 tst.w batch_active(a6)
 bne fail
 bsr qa_guard_check
'''
    tail += f'''qa_batch_address:
 move.w qa_batch_row,d0
 sub.w #y_top,d0
 mulu.w #50,d0
 lea ${s['polygon_spans']:x},a0
 adda.l d0,a0
 rts
qa_batch_next: dc.l 0
qa_batch_row: dc.w 0
qa_batch_cases_left: dc.w 0
qa_batch_inputs: dc.w 0
qa_batch_cases:
'''
    for i, spans in enumerate(cases):
        merged = []
        for left, right in sorted(tuple(sorted(span)) for span in spans):
            if merged and left <= merged[-1][1] + 1:
                merged[-1][1] = max(merged[-1][1], right)
            else:
                merged.append([left, right])
        row = ['y_top', 'y_top+y_size-1', 'y_top+1', 'y_top+y_size-2'][i % 4]
        values = [f'x_left+{x}' for pair in spans for x in pair]
        values += [str(len(merged))]
        values += [f'x_left+{x}' for pair in merged for x in pair]
        tail += ' dc.w ' + ','.join([row] + values) + '\n'
    return prefix, body, tail, names
