"""Real cloak toggles during encounter replays; compare every gameplay frame."""
from native_ai_radio_parity import make_suite as base_suite


def make_suite(root, s):
    prefix, body, tail, names = base_suite(root, s)
    call = lambda name: f' jsr ${s[name]:x}\n'
    # The existing replay covers all three actual encounter creation routes,
    # both ID states, two gameplay seeds and the special mission states.
    # Start cloaked before spawning, then use the real keyboard action six
    # times during each replay. Radio-disabled controls use the same schedule.
    tail = tail.replace(' clr.w cloaking_on(a6)\n',
                        ' clr.w cloaking_on(a6)\n'
                        ' move.w #1,equip+cloaking_device(a6)\n' +
                        call('cloaking_toggle') +
                        ' clr.l qa_trace1\n clr.l qa_trace2\n')
    tail = tail.replace('qa_step:\n', '''qa_step:
 moveq #0,d0
 move.w qa_steps,d0
 divu #15,d0
 swap d0
 tst.w d0
 bne.s .no_toggle
''' + call('cloaking_toggle') + '''.no_toggle:
 moveq #0,d0
 move.w qa_steps,d0
 divu #11,d0
 swap d0
 tst.w d0
 bne.s .no_ui
 not.w cockpit_on(a6)
.no_ui:
''')
    # Hash every frame, not only the final state: transient gameplay changes
    # must also be detected. Reuse the existing scratch snapshot, never the
    # saved control result. Radio fields alone are intentionally excluded.
    needle = call('remove_objects') + ' rts\nqa_capture:\n'
    assert tail.count(needle) == 1
    tail = tail.replace(needle, call('remove_objects') + '''
 lea qa_second,a1
 bsr qa_capture
 lea qa_second,a0
 move.w #qa_snapshot_size/2-1,d7
.hash:
 moveq #0,d0
 move.w (a0)+,d0
 move.l qa_trace1,d1
 rol.l #1,d1
 eor.l d0,d1
 move.l d1,qa_trace1
 add.l d0,qa_trace2
 dbra d7,.hash
 rts
qa_capture:
''')
    control = ' lea qa_first,a1\n bsr qa_capture\n'
    observed = ' lea qa_second,a1\n bsr qa_capture\n'
    assert body.count(control) == body.count(observed) == len(names)
    body = body.replace(control, control +
                        ' move.l qa_trace1,qa_control1\n'
                        ' move.l qa_trace2,qa_control2\n')
    body = body.replace(observed, observed +
                        ' move.l qa_trace1,d0\n cmp.l qa_control1,d0\n bne fail\n'
                        ' move.l qa_trace2,d0\n cmp.l qa_control2,d0\n bne fail\n'
                        ' cmp.w #$ffff,cloaking_on(a6)\n bne fail\n')
    tail += '''qa_trace1: dc.l 0
qa_trace2: dc.l 0
qa_control1: dc.l 0
qa_control2: dc.l 0
'''
    names = ['Cloak active at spawn, six real toggles, UI/3D, per-frame parity: ' + n
             for n in names]
    return prefix, body, tail, names
