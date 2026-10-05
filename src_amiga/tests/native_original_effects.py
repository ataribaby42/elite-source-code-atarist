"""Compare the linked Paula envelopes with executable Elite 2.0 handler bytes.

The original handler runs on private scratch state, with only its absolute data
references relocated. This oracle does not reimplement the new player's logic.
"""
import struct
import sys


def make_suite(root, s):
    sys.path.insert(0, str(root))
    from tools.amiga_assets import ofs_file
    game = ofs_file((root.parent/'resources/amiga/Elite 2.0.adf').read_bytes(), 887)
    descriptors = [game[0x5fe4+i*8:0x5fe4+(i+1)*8] for i in range(19)]
    periods = struct.unpack_from('>16H', game, 0x5f5a)
    original = game[0x5b4e+0x1cc:0x5cd0+0x1cc]
    references = {0x5e0a: 'qa_orig_dma', 0x5dc6: 'qa_orig_state',
                  0x5e0c: 'qa_orig_period', 0x5e14: 'qa_orig_channel',
                  0x5d8e: 'qa_orig_periods'}
    relocated = []
    offset = 0
    while offset < len(original):
        value = int.from_bytes(original[offset:offset+4], 'big')
        if value in references:
            relocated.append(' dc.l '+references[value]+'\n')
            offset += 4
        else:
            relocated.append(f' dc.b ${original[offset]:02x},${original[offset+1]:02x}\n')
            offset += 2
    assert len(original) == 386
    prefix = ' include "common.def"\n include "macros.m68"\n'
    call = lambda n: f' jsr ${s[n]:x}\n'
    out = [' move.l a6,-(sp)\n movea.l $4,a6\n jsr -120(a6)\n movea.l (sp)+,a6\n']
    names = []
    def case(name):
        names.append(name)
        out.append(f' move.w #{len(names)},qa_case\n'+call('quiet')+
                   ' bset #f_fx,user(a6)\n clr.w condition(a6)\n clr.w docked(a6)\n'
                   ' clr.w game_over(a6)\n clr.w game_frozen(a6)\n clr.w torus_on(a6)\n')
    def start(event):
        return f' move.w #{event},d0\n'+call('fx')+call('sound')+f' move.w #{event},d3\n bsr qa_find\n cmp.w #1,d0\n bne fail\n move.l a0,qa_voice\n'
    def no_voice(event):
        return f' move.w #{event},d3\n bsr qa_find\n tst.w d0\n bne fail\n'
    mapping = [0,1,15,3,7,6,4,16,17,12,11,14,13,10,None,16,8,None,None,18,9]
    for event, effect in enumerate(mapping):
        if effect is None:
            continue
        desc = descriptors[effect]
        sustained = desc[7] == 255
        ticks = 700 if sustained else (desc[5]+1)*(desc[7]+2)+(desc[3]//desc[6] if desc[6] else 0)
        # Original initialization leaves DMA off. Pulse first becomes audible
        # after its first envelope update, with nine services left, not ten.
        # The enhanced player skips that silent startup service for low latency.
        if event == 3:
            ticks -= 1
        case(f'Event {event}, original effect {effect}: every period, volume and stop service matches ADF ({ticks} services)')
        if event == 5:
            out.append(' move.w #2,condition(a6)\n')
        if event == 10:
            out.append(' st torus_on(a6)\n')
        out.append(' lea qa_orig_state,a0\n moveq #18,d7\nqa_clear_'+str(event)+':\n clr.l (a0)+\n dbra d7,qa_clear_'+str(event)+'\n')
        for i, value in enumerate(desc):
            out.append(f' move.b #{value},qa_orig_state+{i*4}\n')
        out.append(f' move.b #{desc[5]},qa_orig_state+32\n move.b #{int(sustained)},qa_orig_state+36\n'
                   f' move.b #1,qa_orig_state+40\n move.w #{periods[desc[1]]},qa_orig_period\n')
        if event == 3:
            out.append(' bsr qa_original_tick\n')
        out.append(start(event)+' bsr qa_compare\n'+f' move.w #{ticks-1},qa_repeat\nqa_tick_{event}:\n'
                   ' bsr qa_original_tick\n'+call('sound')+' bsr qa_compare\n'
                   f' subq.w #1,qa_repeat\n bpl qa_tick_{event}\n')
        if not sustained:
            out.append(no_voice(event))

    case('I identification selects effect 9 while an armed missile keeps its distinct lock event')
    out.append(' lea objects+obj_len*3(a6),a4\n move.b #1,flags(a4)\n move.w #cobra,type(a4)\n'+call('create_object')+
               ' move.l a4,a5\n move.l #1000,obj_range(a5)\n clr.l this_xpos(a5)\n clr.l this_ypos(a5)\n'
               ' move.l #1000,this_zpos(a5)\n move.w #-1,laser_type(a6)\n st id_trigger(a6)\n'+call('check_sights')+call('sound')+
               ' tst.w id_trigger(a6)\n bne fail\n moveq #sfx_identify,d3\n bsr qa_find\n cmp.w #1,d0\n bne fail\n'+
               no_voice('sfx_locked')+' moveq #sfx_locked,d0\n'+call('fx')+call('sound')+
               ' moveq #sfx_locked,d3\n bsr qa_find\n cmp.w #1,d0\n bne fail\n')
    for stop in ('torus_on', 'docked', 'game_over', 'effects'):
        case('Torus sustains beyond 0.8 seconds and stops on '+stop)
        out.append(' st torus_on(a6)\n'+start('sfx_spacejump')+' move.w #99,qa_repeat\nqa_torus_'+stop+':\n'+call('sound')+
                   ' moveq #sfx_spacejump,d3\n bsr qa_find\n cmp.w #1,d0\n bne fail\n cmpa.l qa_voice,a0\n bne fail\n'
                   ' subq.w #1,qa_repeat\n bpl qa_torus_'+stop+'\n')
        out.append({'torus_on': ' clr.w torus_on(a6)\n', 'docked': ' st docked(a6)\n',
                    'game_over': ' st game_over(a6)\n', 'effects': ' bclr #f_fx,user(a6)\n'}[stop]+call('sound')+no_voice('sfx_spacejump'))
    case('Torus keeps its voice through repeated radio, shield hits and target-lock requests')
    out.append(' st torus_on(a6)\n'+start('sfx_spacejump')+' move.w #99,qa_repeat\nqa_compete:\n'+call('comm_arrival_sound')+
               call('laser_impact_sound')+' moveq #sfx_locked,d0\n'+call('fx')+call('sound')+
               ' moveq #sfx_spacejump,d3\n bsr qa_find\n cmp.w #1,d0\n bne fail\n cmpa.l qa_voice,a0\n bne fail\n'
               ' subq.w #1,qa_repeat\n bpl qa_compete\n')
    case('Quiet cancels torus permission, preventing an automatic restart')
    out.append(' st torus_on(a6)\n'+start('sfx_spacejump')+call('quiet')+call('sound')+no_voice('sfx_spacejump'))
    case('A transient owner change does not permanently lose torus audio')
    out.append(' st torus_on(a6)\n'+start('sfx_spacejump')+' clr.w torus_on(a6)\n'+call('sound')+no_voice('sfx_spacejump')+
               ' st torus_on(a6)\n'+call('sound')+' moveq #sfx_spacejump,d3\n bsr qa_find\n cmp.w #1,d0\n bne fail\n')
    case('Sustained alert ends when condition is no longer red')
    out.append(' move.w #2,condition(a6)\n'+start('sfx_alert')+' clr.w condition(a6)\n'+call('sound')+no_voice('sfx_alert'))
    out.append(call('quiet')+' move.l a6,-(sp)\n movea.l $4,a6\n jsr -126(a6)\n movea.l (sp)+,a6\n')
    tail = f'''qa_case: dc.w 0
qa_repeat: dc.w 0
qa_voice: dc.l 0
qa_orig_state: ds.b 76
qa_orig_dma: dc.w 0
qa_orig_period: dc.w 0,0,0,0
qa_orig_channel: dc.l 0
qa_orig_periods: dc.w {','.join(map(str, periods))}
qa_original_tick:
 tst.b qa_orig_state+40
 beq.s .done
 movem.l d0-d7/a0-a6,-(sp)
 moveq #0,d1
 bsr qa_original_handler
 movem.l (sp)+,d0-d7/a0-a6
.done:
 rts
qa_compare:
 move.l qa_voice,a0
 tst.b qa_orig_state+40
 beq.s .stopped
 tst.w (a0)
 beq fail
 bra.s .envelope
.stopped:
 tst.w (a0)
 bne fail
.envelope:
 move.l a0,d0
 sub.l #${s['effect_ticks']:x},d0
 lsl.w #3,d0
 lea ${s['effect_envelopes']:x},a1
 adda.w d0,a1
 move.w qa_orig_period,d0
 cmp.w (a1),d0
 bne fail
 moveq #0,d0
 move.b qa_orig_state+12,d0
 cmp.w 8(a1),d0
 bne fail
 rts
qa_find:
 moveq #0,d0
 lea ${s['effect_ticks']:x},a1
 lea ${s['effect_ids']:x},a2
 moveq #3,d7
.loop:
 tst.w (a1)
 beq.s .next
 cmp.b (a2),d3
 bne.s .next
 addq.w #1,d0
 move.l a1,a0
.next:
 addq.l #2,a1
 addq.l #1,a2
 dbra d7,.loop
 rts
qa_original_handler:
'''+''.join(relocated)
    return prefix, ''.join(out), tail, names
