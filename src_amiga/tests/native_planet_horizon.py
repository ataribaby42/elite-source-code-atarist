"""Pixel/timing regressions plus exact native horizon arithmetic comparison."""
import random
from native_planet_optimization import make_suite as optimization_suite


def make_suite(root, s):
    prefix, body, tail, names = optimization_suite(root, s)
    pairs = [
        ((0, 0, -4096), (0, 0, 4096)),
        ((0, 0, 0), (0, 0, 4096)),
        ((4096, 0, 0), (0, 0, 4096)),
        ((0, -4096, 0), (0, 0, 4096)),
        ((-4096, 0, -1), (4096, 0, 1)),
        ((0, -4096, -1), (0, 4096, 1)),
        ((1, 1, -1), (0, 0, 1)),
        ((-1, -1, -1), (0, 0, 1)),
    ]
    # Exact-horizon, tiny and large signed coordinates exercise truncation,
    # the zero-vector fallback and division remainders in both edge directions.
    for x, y in [(1, 0), (-1, 0), (0, 1), (0, -1), (4097, -4097),
                 (-4097, 4097), (16384, 0), (0, -16384)]:
        for z in (-4096, -1, 0):
            pairs.append(((x, y, z), (-x, -y, 4096)))
    rng = random.Random(20261028)
    while len(pairs) < 512:
        pairs.append(((rng.randint(-4097, 4097), rng.randint(-4097, 4097),
                       rng.randint(-4097, 0)),
                      (rng.randint(-4097, 4097), rng.randint(-4097, 4097),
                       rng.randint(1, 4097))))
    names.append('1024 directed horizon intersections match the original 3D normalizer and preserve registers')
    body += f' move.w #{len(names)},qa_case\n'
    body += ''' lea qa_limb_pairs,a0
 move.l a0,qa_limb_next
 move.w #511,qa_limb_remaining
qa_limb_loop:
 move.l qa_limb_next,a0
 lea 6(a0),a1
 bsr qa_limb_compare
 exg a0,a1
 bsr qa_limb_compare
 add.l #12,qa_limb_next
 subq.w #1,qa_limb_remaining
 bpl qa_limb_loop
'''
    tail += f'''qa_limb_compare:
 movem.l qa_limb_initial,d0-d7
 bsr qa_limb_reference
 movem.l d0-d7/a0-a5,qa_limb_expected
 movem.l qa_limb_initial,d0-d7
 jsr ${s['ps_intersection']:x}
 movem.l d0-d7/a0-a5,qa_limb_actual
 lea qa_limb_expected,a2
 lea qa_limb_actual,a3
 moveq #13,d7
qa_limb_check:
 move.l (a2)+,d0
 cmp.l (a3)+,d0
 bne fail
 dbra d7,qa_limb_check
 rts
; Frozen pre-optimization intersection, using the unchanged general normalizer.
qa_limb_reference:
 movem.l d3-d7,-(sp)
 move.w 4(a0),d6
 move.w 4(a1),d5
 sub.w d6,d5
 move.w (a1),d0
 sub.w (a0),d0
 muls.w d6,d0
 divs.w d5,d0
 neg.w d0
 add.w (a0),d0
 move.w 2(a1),d1
 sub.w 2(a0),d1
 muls.w d6,d1
 divs.w d5,d1
 neg.w d1
 add.w 2(a0),d1
 clr.w d2
 jsr ${s['ps_normalize']:x}
 movem.l (sp)+,d3-d7
 rts
qa_limb_initial:
 dc.l $12345678,$87654321,$89abcdef,$13579bdf
 dc.l $a5a55a5a,$fedcba98,$10203040,$f0e0d0c0
qa_limb_expected: ds.l 14
qa_limb_actual: ds.l 14
qa_limb_next: dc.l 0
qa_limb_remaining: dc.w 0
qa_limb_pairs:
'''
    for first, second in pairs:
        tail += ' dc.w ' + ','.join(map(str, first + second)) + '\n'
    return prefix, body, tail, names
