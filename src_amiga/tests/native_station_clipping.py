"""Native extreme clipping intersections and guarded near-camera station rendering."""
def make_suite(root, s):
    call = lambda name: f' jsr ${s[name]:x}\n'
    prefix = ' include "common.def"\n include "macros.m68"\n'
    body = ' clr.w csr_on(a6)\n clr.w display_clock(a6)\n move.w #3,player_ship(a6)\n'
    body += call('ship_apply') + call('reset_system') + call('prepare_cockpit') + call('front_view')
    body += call('clear_objects') + call('alloc_object')
    body += ' move.b #1,flags(a4)\n move.w #spacestn,type(a4)\n move.w #unit,x_vector+i(a4)\n move.w #unit,y_vector+j(a4)\n move.w #unit,z_vector+k(a4)\n'
    body += call('create_object')
    body += ' move.w #15,qa_rotations\nqa_rotation:\n lea qa_positions(pc),a0\n move.l a0,qa_next\nqa_position:\n move.l qa_next(pc),a0\n move.l (a0)+,d0\n cmp.l #$7fffffff,d0\n beq qa_rotated\n move.l d0,objects+xpos(a6)\n move.l (a0)+,objects+ypos(a6)\n move.l (a0)+,objects+zpos(a6)\n move.l a0,qa_next\n addq.w #1,qa_case\n'
    body += call('clear_image') + ' bsr qa_guard_set\n lea objects(a6),a5\n clr.w this_obj(a6)\n'
    body += call('get_range') + call('draw_object') + call('draw_all') + ' bsr qa_guard_check\n' + call('swap_screen') + ' bra qa_position\nqa_rotated:\n lea objects(a6),a5\n move.w #71,d0\n'
    body += call('local_z_rotate') + ' move.w #37,d0\n' + call('local_x_rotate') + call('orthogonal')
    body += ' subq.w #1,qa_rotations\n bpl qa_rotation\n'
    tail = '''qa_guard_set:
 movem.l d0/d7/a0,-(sp)
 move.l scr_base(a6),a0
 move.w #y_size-1,d7
 lea y_top*160(a0),a0
qa_set_row:
 move.l #$55aa33cc,0(a0)
 move.l #$55aa33cc,36(a0)
 move.l #$55aa33cc,40(a0)
 move.l #$55aa33cc,76(a0)
 move.l #$55aa33cc,80(a0)
 move.l #$55aa33cc,116(a0)
 move.l #$55aa33cc,120(a0)
 move.l #$55aa33cc,156(a0)
 lea 160(a0),a0
 dbra d7,qa_set_row
 movem.l (sp)+,d0/d7/a0
 rts
qa_guard_check:
 movem.l d0/d7/a0,-(sp)
 move.l scr_base(a6),a0
 move.w #y_size-1,d7
 lea y_top*160(a0),a0
qa_check_row:
 cmp.l #$55aa33cc,0(a0)
 bne fail
 cmp.l #$55aa33cc,36(a0)
 bne fail
 cmp.l #$55aa33cc,40(a0)
 bne fail
 cmp.l #$55aa33cc,76(a0)
 bne fail
 cmp.l #$55aa33cc,80(a0)
 bne fail
 cmp.l #$55aa33cc,116(a0)
 bne fail
 cmp.l #$55aa33cc,120(a0)
 bne fail
 cmp.l #$55aa33cc,156(a0)
 bne fail
 lea 160(a0),a0
 dbra d7,qa_check_row
 movem.l (sp)+,d0/d7/a0
 rts
qa_case: dc.w 0
qa_rotations: dc.w 0
qa_next: dc.l 0
qa_positions:
'''
    names = []
    for rot in range(16):
        for z in (1,50,200,800):
            for x in (-600,0,600):
                for y in (-600,-200,-50,50,200,600):
                    names.append(f'Coriolis rotation {rot}, x={x}, y={y}, z={z}')
                    if rot == 0:
                        tail += f' dc.l {x},{y},{z}\n'
    tail += ' dc.l $7fffffff\n'
    import random
    rng = random.Random(20260924)
    cases = []
    for edge, boundary, vertical in [('top',55,False),('bottom',-56,False),('right',127,True),('left',-128,True)]:
        for index in range(48):
            positive = edge in ('top','right')
            outer = rng.randint(boundary+1,32767) if positive else rng.randint(-32768,boundary-1)
            inner = rng.randint(-32768,boundary) if positive else rng.randint(boundary,32767)
            first, last = rng.choice([-32768,-32000,-1,0,1,32000,32767]), rng.choice([-32768,-32000,-1,0,1,32000,32767])
            delta = last-first
            value = first+(1 if delta >= 0 else -1)*(abs(delta)*abs(boundary-outer)//abs(inner-outer))
            coords = [outer,first,inner,last] if vertical else [first,outer,last,inner]
            expected = [boundary,value] if vertical else [value,boundary]
            cases.append((edge,coords,expected))
    check=' lea qa_intersections(pc),a3\n move.w #191,d5\nqa_intersection:\n addq.w #1,qa_case\n movem.w (a3)+,d0-d3\n move.l (a3)+,a0\n jsr (a0)\n cmp.w (a3)+,d0\n bne fail\n cmp.w (a3)+,d1\n bne fail\n dbra d5,qa_intersection\n'
    body=check+body
    tail+='qa_intersections:\n'
    for edge,coords,expected in cases:
        tail+=' dc.w '+','.join(map(str,coords))+'\n'
        tail+=f' dc.l ${s["intersect_"+edge]:x}\n'
        tail+=' dc.w '+','.join(map(str,expected))+'\n'
    names=[f'{edge} intersection {coords}' for edge,coords,_ in cases]+names
    return prefix, body, tail, names
