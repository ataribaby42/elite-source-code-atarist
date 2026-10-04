"""Compare full native screen bytes with independently wrapped reference text."""
import textwrap
from native_comm import TEXTS

def make_suite(root,s):
    amiga=root.name=='src_amiga'
    cols=s['_geometry']['no_cols'] if amiga else 32
    count='scr_bytes' if amiga else '32000'
    x='x_left/char_w' if amiga else 'x_left/8'
    call=lambda n: f' jsr ${s[n]:x}\n' if n in s else ''
    prefix=' include "common.def"\n include "macros.m68"\n'
    out,names=[],[]
    emit=out.append
    now=s['comm_now'];fx=s['fx']
    emit(call('hide_cursor')+' clr.w display_clock(a6)\n clr.w player_ship(a6)\n'+call('ship_apply')+call('prepare_cockpit')+call('front_view')+call('wait_clear'))
    for n,label in [('comm_now','qa_now'),('comm_arrival_sound','qa_quiet')]:
        a=s[n];emit(f' move.l ${a:x},qa_saved_{n}\n move.w ${a+4:x},qa_saved_{n}+4\n move.w #$4ef9,${a:x}\n move.l #{label},${a+2:x}\n')
    tail=''
    ordinary = ((0,1,2,3),(4,2,1,4),(0,),(),(0,5,2,14),(0,5,15,24),(15,25,29),
                *((i,) for i in range(5,40)))
    profiles = [(ids, (False,)*len(ids)) for ids in ordinary]
    profiles += [((0,), (True,)), ((4,), (True,)),
                 ((15,25,29), (True,True,True)),
                 ((0,5,2,14), (False,True,False,True)),
                 ((0,5,15,24), (True,False,True,False)),
                 ((15,25,29), (True,False,True)),
                 *(( (i,), (True,) ) for i in range(30,40))]
    for ids,players in profiles:
        for hidden in (False,True):
            for visible in (False,True):
                names.append(f'Full-screen reference: {cols} columns, messages={ids}, player={players}, hidden={hidden}, cockpit={visible}')
                n=len(names)
                emit(f' move.w #{n},qa_case\n'+call('comm_reset')+' bsr qa_clear\n')
                for i,player in zip(ids,players):
                    enqueue='comm_enqueue_player' if player else 'comm_enqueue'
                    emit(f' moveq #{i},d0\n move.l #$43316b00,d1\n move.l #{"comm_hidden" if hidden else "$4a532a00"},d2\n'+call(enqueue))
                # Audience and display ID are receipt snapshots, independent of later changes.
                emit(' move.l #$58590100,player_registration(a6)\n move.w #255,scrambled_id(a6)\n')
                emit(f' move.w #{int(visible)},cockpit_on(a6)\n moveq #red,d0\n moveq #trans,d1\n'+call('text_colour')+' moveq #3,d0\n moveq #120,d1\n'+call('locate')+' move.l text_addr(a6),qa_text_addr\n'+call('comm_draw'))
                emit(' bsr qa_check_render\n')
                if visible:
                    row=0
                    for i,player in list(zip(ids,players))[-3:]:
                        lines=textwrap.wrap(f'C1-107:{"??-???" if hidden else "JS-042"}, {TEXTS[i]}',width=cols)
                        for local_row,line in enumerate(lines):
                            chunks=[(line,'yellow')]
                            if player and local_row==0:
                                chunks=[(line[:7],'yellow'),(line[7:13],'pulse'),(line[13:],'yellow')]
                            emit(f' move.w #{x},d0\n move.w #{8+8*row},d1\n'+call('locate'))
                            for chunk,(text,ink) in enumerate(chunks):
                                label=f'qa_line_{n}_{row}_{chunk}'
                                emit(f' moveq #{ink},d0\n moveq #trans,d1\n'+call('text_colour')+f' lea {label},a0\n'+call('print_string'))
                                tail+=f"{label}: dc.b '{text}',0\n"
                            row+=1
                    assert row<=9
                emit(' bsr qa_hash\n cmp.l qa_hash1,d0\n bne fail\n cmp.l qa_hash2,d1\n bne fail\n')
    for n in ('comm_now','comm_arrival_sound'):
        a=s[n];emit(f' move.l qa_saved_{n},${a:x}\n move.w qa_saved_{n}+4,${a+4:x}\n')
    tail+=' even\nqa_case: dc.w 0\nqa_hash1: dc.l 0\nqa_hash2: dc.l 0\nqa_text_addr: dc.l 0\nqa_saved_comm_now: ds.b 6\nqa_saved_comm_arrival_sound: ds.b 6\n'
    tail+='qa_check_render:\n cmp.w #red,text_ink(a6)\n bne fail\n cmp.w #trans,text_paper(a6)\n bne fail\n cmp.w #3,column(a6)\n bne fail\n cmp.w #120,row(a6)\n bne fail\n move.l text_addr(a6),d0\n cmp.l qa_text_addr,d0\n bne fail\n bsr qa_hash\n move.l d0,qa_hash1\n move.l d1,qa_hash2\n bsr qa_clear\n rts\n'
    tail+=f'''qa_now:
 moveq #0,d0
 rts
qa_quiet:
 rts
qa_clear:
'''+call('wait_clear')+f''' move.l scr_base(a6),a0
 move.w #{count}/4-1,d7
.loop:
 clr.l (a0)+
 dbra d7,.loop
 rts
qa_hash:
 move.l scr_base(a6),a0
 moveq #0,d0
 moveq #0,d1
 move.w #{count}/4-1,d7
.loop:
 rol.l #1,d0
 move.l (a0)+,d2
 eor.l d2,d0
 add.l d2,d1
 dbra d7,.loop
 rts
'''
    return prefix,''.join(out),tail,names
