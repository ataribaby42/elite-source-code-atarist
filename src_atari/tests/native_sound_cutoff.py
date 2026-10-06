"""Check actual YM muting at every effect's end and when voices are reused."""


def make_suite(root, s):
    source = (root/'asm/sounds.m68').read_text()
    start = source.index('\trsset 0', source.index('* Define sound effects record.'))
    prefix = ' include "common.def"\n include "macros.m68"\n'
    prefix += source[start:source.index('\tq_end_vars sounds', start)]+'\n'
    call = lambda name: f' jsr ${s[name]:x}\n'
    # Service real linked effects deterministically without a second VBL tick.
    body = f' move.w ${s["sound"]:x},qa_opcode\n move.w #$4e75,${s["sound"]:x}\n'
    names = []

    def case(name):
        nonlocal body
        names.append(name)
        body += f' move.w #{len(names)},qa_case\n'+call('quiet')
        body += ' bset #f_fx,user(a6)\n'

    def start_effect(effect, channel):
        nonlocal body
        for _ in range(channel):
            body += ' moveq #sfx_locked,d0\n'+call('fx')
        body += f' moveq #sfx_{effect},d0\n'+call('fx')
        body += f' lea chan_1+{channel}*fx_len(a6),a5\n'
        body += ' tst.w chn_active(a5)\n beq fail\n'
        # Distinct tones/levels make accidental writes to another voice visible.
        for other in range(3):
            if other == channel:
                continue
            for reg, value in ((other*2, 75+other), (other*2+1, 2), (other+8, 7+other)):
                body += f' moveq #{reg},d0\n moveq #{value},d1\n'+call('psg_output')

    def check_silent(channel):
        nonlocal body
        body += ' tst.w chn_active(a5)\n bne fail\n tst.w hold_chan(a5)\n bne fail\n'
        body += ' tst.w clear_env(a5)\n bne fail\n tst.w flag_ptr(a5)\n bne fail\n'
        for other in range(3):
            values = (0, 0, 0) if other == channel else (75+other, 2, 7+other)
            for reg, value in zip((other*2, other*2+1, other+8), values):
                body += f' moveq #{reg},d0\n bsr qa_read_psg\n cmp.b #{value},d0\n bne fail\n'
        body += ' moveq #7,d0\n bsr qa_read_psg\n cmp.b #$f8,d0\n bne fail\n'

    effects = (
        ('keyclick', 2), ('locked', 10), ('explosion', 300), ('laser', 17),
        ('shields', 25), ('alert', 16), ('error', 7), ('hexagon', 9),
        ('ecm', 116), ('hit', 8), ('spacejump', 166), ('missile', 100),
        ('hyperspace', 475), ('cargo', 30), ('doors', 61), ('teletype', 2),
        ('launch', 234), ('comm', 10),
    )
    for effect, ticks in effects:
        for channel in range(3):
            case(f'{effect}, voice {channel+1}: original lifetime and silent YM completion')
            start_effect(effect, channel)
            body += ' clr.w qa_steps\n move.w #64,hex_tone(a6)\n'
            label = f'qa_service_{len(names)}'
            body += label+':\n'
            if effect in ('hexagon', 'doors'):
                flag = 'kill_hexagon' if effect == 'hexagon' else 'fx_off'
                body += f' cmp.w #{ticks-1},qa_steps\n bne.s {label}_tick\n st {flag}(a6)\n{label}_tick:\n'
            body += ' move.l service(a5),a0\n jsr (a0)\n addq.w #1,qa_steps\n'
            body += f' cmp.w #1000,qa_steps\n bhi fail\n tst.w chn_active(a5)\n bne {label}\n'
            body += f' cmp.w #{ticks},qa_steps\n bne fail\n'
            check_silent(channel)
            if effect in ('shields', 'alert'):
                body += f' tst.w {effect}_fx(a6)\n bne fail\n'

    for channel in range(3):
        case(f'Voice {channel+1}: forced stop preserves other noise gates and shared envelope')
        start_effect('error', channel)
        # Enable noise on the other voices, leave the target noise disabled.
        mixer = 0xc0 | (1 << (channel+3))
        for reg, value in ((6, 19), (7, mixer), (11, 123), (12, 4), (13, 8)):
            body += f' move.w #{reg},d0\n move.w #{value},d1\n'+call('psg_output')
        body += call('silence_effect')
        # Stop must leave the global noise/envelope settings untouched.
        for reg, value in ((6, 19), (7, mixer), (11, 123), (12, 4), (13, 8), (channel+8, 0)):
            body += f' moveq #{reg},d0\n bsr qa_read_psg\n cmp.b #{value},d0\n bne fail\n'

    for effect, flag in (('shields', 'shields_fx'), ('alert', 'alert_fx'), ('hyperspace', None)):
        case(f'{effect}: occupied voice is safely replaced by a new receipt')
        start_effect(effect, 0)
        body += (' st chan_2+chn_active(a6)\n st chan_3+chn_active(a6)\n'
                 ' st chan_2+hold_chan(a6)\n st chan_3+hold_chan(a6)\n'
                 ' clr.w alloc_ctr(a6)\n')
        body += call('comm_arrival_sound')
        body += f' cmp.l #${s["comm_time"]:x},service(a5)\n bne fail\n'
        if flag:
            body += f' tst.w {flag}(a6)\n bne fail\n'
        if effect == 'hyperspace':
            body += ' tst.w warp_ticks(a6)\n beq fail\n tst.w end_hyperspace(a6)\n beq fail\n'
        body += ' moveq #9,d6\n'+f'qa_receipt_{len(names)}:\n'+call('comm_time')
        body += f' dbra d6,qa_receipt_{len(names)}\n'
        check_silent(0)

    for kind in ('beam', 'military', 'rcs', 'engine'):
        case(f'{kind}: continuous voice releases without leaving audible output')
        body += (' clr.w docked(a6)\n clr.w game_over(a6)\n clr.w game_frozen(a6)\n'
                 ' clr.w controls_locked(a6)\n clr.w jettison_pending(a6)\n'
                 ' move.w #1,cockpit_on(a6)\n bclr #f_no_rcs,user(a6)\n'
                 ' clr.w laser_temp(a6)\n')
        if kind in ('beam', 'military'):
            number = 2 if kind == 'beam' else 3
            update, owner = 'update_beam_sound', 'beam_channel'
            body += f' move.w #{number},laser_type(a6)\n move.w #{number},laser_audio_request(a6)\n'
            release = ' clr.w laser_audio_request(a6)\n'
        elif kind == 'rcs':
            update, owner = 'update_rcs_sound', 'rcs_channel'
            body += ' move.w #1,rcs_request(a6)\n'
            release = ' clr.w rcs_request(a6)\n'
        else:
            update, owner = 'update_engine_sound', 'engine_channel'
            body += (' move.w #1,engine_request(a6)\n st key_states+$39(a6)\n'
                     ' clr.b key_states+$35(a6)\n move.w #10,speed(a6)\n move.w #100,hull_speed(a6)\n')
            release = ' clr.b key_states+$39(a6)\n clr.w engine_request(a6)\n'
        body += call(update)*6+f' move.l {owner}(a6),a5\n move.l a5,d0\n beq fail\n'
        body += ' move.w reg_volume(a5),d0\n bsr qa_read_psg\n tst.b d0\n beq fail\n'
        body += release+call(update)*6+f' tst.l {owner}(a6)\n bne fail\n'
        body += ' lea chan_1(a6),a5\n tst.w chn_active(a5)\n bne fail\n'
        body += ' moveq #8,d0\n bsr qa_read_psg\n tst.b d0\n bne fail\n'
        body += ' moveq #7,d0\n bsr qa_read_psg\n cmp.b #$f8,d0\n bne fail\n'

    body += call('quiet')+f' move.w qa_opcode,${s["sound"]:x}\n'
    tail = '''qa_case: dc.w 0
qa_opcode: dc.w 0
qa_steps: dc.w 0
qa_read_psg:
 move.b d0,psg_select
 moveq #0,d0
 move.b psg_read,d0
 rts
'''
    return prefix, body, tail, names
