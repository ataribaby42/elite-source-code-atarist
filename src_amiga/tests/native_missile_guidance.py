"""Native interceptions: full missile speed through turns and real impacts."""
import native_missile_collision


def make_suite(root, s):
    prefix, _, tail, _ = native_missile_collision.make_suite(root, s)
    parts, names = [], []
    call = lambda name: f' jsr ${s[name]:x}\n'
    fixtures = []
    for role in ('log_locked', 'log_ai_missile', 'log_missile'):
        models = ('cobra',) if role == 'log_missile' else ('cobra', 'thargon')
        for model in models:
            for speed in (0, 22, 32):
                for direction, xyz in (
                    ('straight', (0, 0, -4000)),
                    ('pitch 90', (0, -4000, 0)),
                    ('roll then pitch 90', (-4000, 0, 0)),
                    ('reverse 180', (0, 0, 4000)),
                    ('close crossing', (-400, 0, 0)),
                    ('diagonal crossing', (-600, -500, -1500)),
                ):
                    fixtures.append((role, model, speed, direction, xyz, 0))
        for motion, name in ((1, 'zigzag'), (2, 'two-axis evasion'), (3, 'reversal')):
            fixtures.append((role, 'cobra', 22, name, (-1000, -500, -4000), motion))

    for role, model, speed, direction, xyz, motion in fixtures:
        names.append(f'{role} -> {model}, speed {speed}, {direction}: full speed and impact')
        idx = len(names)
        parts.append(f''' move.w #{idx},qa_case
 bsr qa_world
 clr.w mission(a6)
 clr.w police_record(a6)
 move.w #{speed},speed(a6)
 clr.w retro_count(a6)
 lea objects+obj_len*3(a6),a4
 move.b #1,flags(a4)
 move.w #{model},type(a4)
''' + call('create_object') + ''' clr.w ecm_fitted(a4)
 move.w #act_nothing,attack_type(a4)
 move.w #32767,health(a4)
 move.w #unit,x_vector+i(a4)
 move.w #unit,y_vector+j(a4)
 move.w #unit,z_vector+k(a4)
 lea objects+obj_len*4(a6),a4
 move.b #1,flags(a4)
 move.w #missile,type(a4)
 st velocity(a4)
''' + call('create_object') + f''' cmp.w #42,velocity(a4)
 bne fail
 move.w #unit,x_vector+i(a4)
 move.w #unit,y_vector+j(a4)
 move.w #unit,z_vector+k(a4)
 move.l #{xyz[0]},xpos(a4)
 move.l #{xyz[1]},ypos(a4)
 move.l #{xyz[2]},zpos(a4)
 move.w #{role},logic(a4)
 lea objects+obj_len*3(a6),a0
 move.l a0,target(a4)
 move.l a4,a5
 move.w #4,this_obj(a6)
 move.w #{motion},qa_motion
 move.w #{int(role == 'log_missile')},qa_player
 lea qa_results+{(idx - 1) * 2},a0
 move.l a0,qa_write
 clr.w qa_steps
 bsr qa_chase
''')
    tail += '''
; The observer follows the victim: its position remains at the origin and
; its motion is subtracted from the missile. MOVE performs the forward part.
; This keeps fast, prolonged pursuit inside the ordinary scanner boundary.
qa_chase:
 addq.w #1,qa_steps
 movem.l xpos(a5),d0-d2
 movem.l d0-d2,qa_old
''' + call('get_range') + call('do_logic') + '''
 cmp.w #log_exploding,logic(a5)
 beq .hit
 btst #remove,flags(a5)
 bne fail
 cmp.w #42,velocity(a5)
 bne fail
''' + call('orthogonal') + call('move') + '''
 tst.w qa_motion
 beq.s .moved
 cmp.w #3,qa_motion
 bne.s .sideways
 cmp.w #50,qa_steps
 bne.s .moved
 neg.w speed(a6)
 bra.s .moved
.sideways:
 moveq #16,d0
 move.w qa_steps,d1
 btst #5,d1
 beq.s .xsign
 neg.w d0
.xsign:
 ext.l d0
 sub.l d0,xpos(a5)
 cmp.w #2,qa_motion
 bne.s .moved
 moveq #16,d0
 btst #6,d1
 beq.s .ysign
 neg.w d0
.ysign:
 ext.l d0
 sub.l d0,ypos(a5)
.moved:
 move.l xpos(a5),d0
 cmp.l qa_old,d0
 bne.s .continue
 move.l ypos(a5),d0
 cmp.l qa_old+4,d0
 bne.s .continue
 move.l zpos(a5),d0
 cmp.l qa_old+8,d0
 beq fail
.continue:
 cmp.w #1200,qa_steps
 bhs fail
 bra qa_chase
.hit:
 tst.w qa_player
 beq.s .npc
 cmp.w #96,energy(a6)
 bhs fail
 bra.s .record
.npc:
 lea objects+obj_len*3(a6),a4
 cmp.w #32767,health(a4)
 bhs fail
.record:
 move.l qa_write,a0
 move.w qa_steps,(a0)
 rts
qa_steps: dc.w 0
qa_motion: dc.w 0
qa_player: dc.w 0
qa_write: dc.l 0
qa_old: ds.l 3
qa_results: ds.w ''' + str(len(names)) + '\n'
    return prefix, ''.join(parts), tail, names
