"""Native F7 cursor visibility, movement and saved-background regressions."""


def make_suite(root, s):
    source = (root / 'asm/planet.m68').read_text()
    prefix = ' include "common.def"\n include "macros.m68"\n'
    prefix += source[source.index('ps_features:'):source.index('    q_end_vars planet_surface')] + '\n'
    call = lambda name: f' jsr ${s[name]:x}\n'
    amiga = root.name == 'src_amiga'
    body = ' st game_frozen(a6)\n bset #f_planets,user+1(a6)\n clr.w game_over(a6)\n move.w #8,req_planet(a6)\n moveq #8,d0\n'
    body += call('get_planet_info') + call('data')
    body += ''' bsr qa_hide
 move.l scr_base(a6),qa_screen
 bsr qa_render
 move.l scr_base(a6),a0
 lea qa_reference,a1
 move.w #7999,d7
qa_save_reference:
 move.l (a0)+,(a1)+
 dbra d7,qa_save_reference
'''
    # Wrap the game's actual VBL sound call, after its cursor update. The probe
    # observes every flyback during rendering; final screenshots alone missed
    # the original bug, in which the cursor was absent for most of each frame.
    body += f''' lea ${s['vblank']:x},a0
 move.w #127,d7
qa_find_vbl_call:
 cmp.w #$4eb9,(a0)
 bne.s qa_next_vbl_call
 cmp.l #${s['sound']:x},2(a0)
 beq.s qa_hook_vbl
qa_next_vbl_call:
 addq.l #2,a0
 dbra d7,qa_find_vbl_call
 bra fail
qa_hook_vbl:
 addq.l #2,a0
 move.l a0,qa_hook
 move.l #qa_probe,(a0)
'''
    names = []
    positions = [(256 + x, 70) for x in range(16)]
    positions += [(208 + x, 34) for x in range(16)]
    positions += [(296 + x, 106) for x in range(16)]
    positions += [(0, -8), (232, -8), (232, 18), (232, 33), (232, 34),
                  (232, 113), (232, 114), (232, 160), (310, 70), (-10, 74),
                  (272, 0), (272, 191), (272, 120)]
    rows = []
    for kind in range(3):
        for x, y in positions:
            names.append(f'Cursor {kind} at ({x},{y}): visible during F7 render, clean movement and exact background')
            rows.append((kind, x, y, 1))
    if amiga:
        for kind in range(3):
            for shift in range(16):
                names.append(f'General sprite fallback, cursor {kind}, shift {shift}: exact saved background')
                rows.append((kind, 256 + shift, 70, 0))
    body += f''' lea qa_cases,a0
 move.l a0,qa_next_case
 move.w #{len(rows)},qa_remaining
qa_case_loop:
 addq.w #1,qa_case
 move.l qa_next_case,a0
 move.w (a0)+,cursor_type(a6)
 move.w (a0)+,cursor_spr+sp_xpos(a6)
 move.w (a0)+,cursor_spr+sp_ypos(a6)
{f' move.w (a0)+,${s["cursor_cache_ready"]:x}' if amiga else ' addq.l #2,a0'}
 move.l a0,qa_next_case
 ; Put a different phase underneath the cursor before each tested transition.
 clr.w ps_portrait_phase(a6)
 bsr qa_due
 move.w #272,d0
 moveq #74,d1
{call('animate_planet_portrait')}
 clr.l move_x(a6)
 st csr_on(a6)
 bsr qa_wait
 move.w #1,button_pressed(a6)
 st qa_monitor
 bsr qa_render
 clr.w qa_monitor
 tst.w qa_missing
 bne fail
 btst #back_saved,cursor_spr+sp_flags(a6)
 beq fail
 tst.w csr_on(a6)
 beq fail
 cmp.w #1,button_pressed(a6)
 bne fail
 ; Let the normal VBL consume the updated background, then move and remove.
 bsr qa_wait
 move.w #3,move_x(a6)
 move.w #-2,move_y(a6)
 bsr qa_wait
 bsr qa_hide
 move.l scr_base(a6),a0
 lea qa_reference,a1
 move.w #7999,d7
qa_compare:
 move.l (a0)+,d0
 cmp.l (a1)+,d0
 bne fail
 dbra d7,qa_compare
 subq.w #1,qa_remaining
 bne qa_case_loop
 tst.l qa_samples
 beq fail
 move.l qa_hook,a0
 move.l #${s['sound']:x},(a0)
'''
    # Exercise movement while the expensive offscreen draw is running as well.
    if amiga:
        body += f' move.w #$ff00,${s["cursor_cache_ready"]:x}\n'
    names.append('Mouse input is serviced by real VBLs while F7 renders offscreen')
    body += f''' addq.w #1,qa_case
 move.w #80,cursor_spr+sp_xpos(a6)
 move.w #70,cursor_spr+sp_ypos(a6)
 st csr_on(a6)
 bsr qa_wait
 move.w #7,move_x(a6)
 bsr qa_render
 bsr qa_wait
 cmp.w #87,cursor_spr+sp_xpos(a6)
 bne fail
 bsr qa_hide
 move.w qa_samples+2,qa_perf_cursor_samples
'''
    body += 'snap_cursor_clean:\n nop\n'
    if root.name == 'src_amiga':
        body += ''' move.l scr_base(a6),qa_frame
 move.w #1,qa_snapshot
qa_snapshot_wait:
 tst.w qa_snapshot
 bne.s qa_snapshot_wait
'''
    tail = f'''
qa_hide:
 clr.w csr_on(a6)
 lea cursor_spr(a6),a4
{call('remove_sprite')} rts
qa_wait:
 move.w frame_count(a6),d0
 addq.w #2,d0
qa_wait_vbl:
 cmp.w frame_count(a6),d0
 bne.s qa_wait_vbl
 rts
qa_due:
{call('comm_now')} subq.l #3,d0
 move.l d0,ps_portrait_tick(a6)
 rts
qa_render:
 move.w #$3000,ps_portrait_phase(a6)
 bsr qa_due
 move.w #272,d0
 moveq #74,d1
{call('animate_planet_portrait')} rts
qa_probe:
 movem.l d0-d4/a0-a1,-(sp)
 tst.w qa_monitor
 beq.s qa_probe_done
 addq.l #1,qa_samples
 btst #back_saved,cursor_spr+sp_flags(a6)
 beq.s qa_probe_missing
 move.l cursor_spr+video_ptr(a6),d0
 sub.l qa_screen,d0
 cmp.l #32000,d0
 bhs qa_probe_missing
 ; All three cursor assets have an opaque pixel at (10,8). Check its actual
 ; four screen-plane bits on every monitored flyback, including copy stalls.
 move.w cursor_spr+sp_xpos(a6),d0
 add.w #10,d0
 cmp.w #320,d0
 bhs.s qa_probe_done
 move.w cursor_spr+sp_ypos(a6),d1
 addq.w #8,d1
 cmp.w #200,d1
 bhs.s qa_probe_done
 move.w d0,d2
 and.w #15,d2
 eor.w #15,d2
 lsr.w #4,d0
 lsl.w #{1 if amiga else 3},d0
 mulu.w #160,d1
 add.l d1,d0
 move.l qa_screen,a0
 adda.l d0,a0
 move.l cursor_spr+data_ptr(a6),a1
 adda.w #4+8*20+2,a1
 moveq #3,d0
qa_probe_pixel:
 move.w (a1)+,d3
 lsr.w #5,d3
 move.w (a0),d4
 lsr.w d2,d4
 eor.w d3,d4
 btst #0,d4
 bne.s qa_probe_missing
 adda.w #{40 if amiga else 2},a0
 dbra d0,qa_probe_pixel
 bra.s qa_probe_done
qa_probe_missing:
 st qa_missing
qa_probe_done:
 movem.l (sp)+,d0-d4/a0-a1
 jmp ${s['sound']:x}
qa_case: dc.w 0
qa_remaining: dc.w 0
qa_missing: dc.w 0
qa_monitor: dc.w 0
qa_samples: dc.l 0
qa_perf_cursor_samples: dc.w 0
qa_next_case: dc.l 0
qa_screen: dc.l 0
qa_hook: dc.l 0
qa_ticks_8: dc.w 0
qa_ticks_1: dc.w 0
qa_snapshot: dc.w 0
qa_frame: dc.l 0
qa_cases:
'''
    tail += ''.join(' dc.w ' + ','.join(map(str, row)) + '\n' for row in rows)
    tail += 'qa_reference: ds.b 32000\n'
    return prefix, body, tail, names
