"""Check hyperspace duration against the running Atari VBL clock."""


def make_suite(root, s):
    prefix = ' include "common.def"\n include "macros.m68"\n'
    call = lambda name: f' jsr ${s[name]:x}\n'
    source = (root / 'asm/sounds.m68').read_text()
    start = source.index('\trsset 0', source.index('* Define sound effects record.'))
    prefix += source[start:source.index('\tq_end_vars sounds', start)] + '\n'
    body = ' move.b $ffff820a,qa_video\n'
    names = []

    for video, ticks in ((2, 150), (0, 180)):
        for jump in (0, -1):
            for enabled in (False, True):
                names.append(
                    f'{"Galactic" if jump else "Hyperspace"}, Effects {enabled}, '
                    f'{50 if video else 60} Hz: three seconds')
                number = len(names)
                label = f'qa_wait_{number}'
                body += f' move.w #{number},qa_case\n' + call('quiet')
                body += f' move.w #{jump},jump_type(a6)\n'
                body += (' bset' if enabled else ' bclr') + ' #f_fx,user(a6)\n'
                body += f' move.b #{video},$ffff820a\n move.w #{ticks},qa_ticks\n'
                # Align with the real VBL, then let interrupts expire the timer.
                body += (' move.l frclock,d6\n' + label + '_align:\n'
                         ' cmp.l frclock,d6\n beq.s ' + label + '_align\n'
                         ' move.l frclock,qa_start\n moveq #sfx_hyperspace,d0\n')
                body += call('fx')
                body += (' tst.w end_hyperspace(a6)\n beq fail\n' + label + ':\n'
                         ' tst.w end_hyperspace(a6)\n bne.s ' + label + '\n'
                         ' move.l frclock,d0\n sub.l qa_start,d0\n')
                body += f' move.w d0,qa_elapsed+{(number - 1) * 2}\n'
                # Allow one VBL of interrupt/observation alignment tolerance.
                body += (' moveq #0,d1\n move.w qa_ticks,d1\n subq.l #1,d1\n'
                         ' cmp.l d1,d0\n blo fail\n addq.l #2,d1\n'
                         ' cmp.l d1,d0\n bhi fail\n'
                         ' tst.w warp_ticks(a6)\n bne fail\n')

    names.append('Explicit cinematic/audio shutdown cancels the timer')
    body += f' move.w #{len(names)},qa_case\n moveq #sfx_hyperspace,d0\n'
    body += call('fx') + call('quiet')
    body += (' tst.w warp_ticks(a6)\n bne fail\n'
             ' tst.w end_hyperspace(a6)\n bne fail\n'
             ' move.b qa_video,$ffff820a\n')
    tail = ('qa_case: dc.w 0\nqa_ticks: dc.w 0\nqa_start: dc.l 0\n'
            'qa_video: dc.w 0\nqa_elapsed: dcb.w 8,0\n')
    return prefix, body, tail, names
