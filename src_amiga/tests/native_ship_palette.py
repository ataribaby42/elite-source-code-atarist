"""Capture real Planet Data colours before/after the ship-only palette mapping."""


def make_suite(root, symbols):
    call = lambda name: f' jsr ${symbols[name]:x}\n'
    body = ' clr.w csr_on(a6)\n clr.w display_clock(a6)\n clr.w player_ship(a6)\n'
    body += call('ship_apply') + call('reset_system')
    body += ' clr.w galaxy_no(a6)\n clr.w mission(a6)\n move.l #$5a4a0248,gal_seed(a6)\n move.w #$b753,gal_seed+4(a6)\n'
    names, shots = [], 0
    def snapshot(label):
        nonlocal body, shots
        shots += 1
        body += ' move.l scr_base(a6),qa_frame\n'
        body += f' lea ${symbols["palette"]:x},a0\n' + f' lea qa_palette(pc),a1\n moveq #15,d7\nqa_palette_{shots}:\n move.w (a0)+,(a1)+\n dbra d7,qa_palette_{shots}\n'
        body += f'snap_{label}:\n nop\n'
        body += f' move.w #{shots},qa_snapshot\nqa_wait_{shots}:\n tst.w qa_snapshot\n bne.s qa_wait_{shots}\n'
    # All hulls on a conflicting palette, all eight alien palettes and humans,
    # with both saved Planets settings. Each pair records the automatic result
    # and the same screen with only the original cached ship redrawn.
    cases = [(h, 61, enabled) for h in range(13) for enabled in (0, 1)]
    cases += [(0, p, enabled) for p in (50, 14, 12, 5, 39, 22, 28, 7) for enabled in (0, 1)]
    for hull, planet, enabled in cases:
        label = f'h{hull}_p{planet}_on{enabled}'
        names.append(label)
        body += f' move.w #{len(names)},qa_case\n move.w #{hull},player_ship(a6)\n' + call('ship_apply')
        body += ' moveq #1,d0\n' + call('ship_bitmap') + ' bsr qa_hash\n move.l d0,qa_cache_hash\n'
        body += (' bset' if enabled else ' bclr') + ' #f_planets,user+1(a6)\n'
        body += f' move.w #{planet},req_planet(a6)\n' + call('data') + call('hide_cursor')
        snapshot(label + '_mapped')
        body += ' moveq #1,d0\n' + call('ship_bitmap') + ' moveq #80,d0\n moveq #52,d1\n' + call('ship_put_bitmap')
        snapshot(label + '_raw')
        body += ' moveq #1,d0\n' + call('ship_bitmap') + ' bsr qa_hash\n cmp.l qa_cache_hash,d0\n bne fail\n'
    tail = """qa_hash:
 moveq #0,d0
 move.w #904/2-1,d1
.word:
 rol.l #1,d0
 move.w (a0)+,d2
 eor.w d2,d0
 dbra d1,.word
 rts
qa_case: dc.w 0
qa_snapshot: dc.w 0
qa_frame: dc.l 0
qa_cache_hash: dc.l 0
qa_palette: ds.w 16
"""
    return ' include "common.def"\n include "macros.m68"\n', body, tail, names
