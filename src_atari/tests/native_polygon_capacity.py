"""Native regression for the largest clipped mesh and vertex workspace limits."""
import re


def make_suite(root, s):
    call = lambda name: f' jsr ${s[name]:x}\n'
    graphics = (root/'asm/graphics.m68').read_text()
    capacity = int(re.search(r'max_vert: equ (\d+)',graphics).group(1))
    prefix = ' include "common.def"\n include "macros.m68"\n'
    prefix += f'max_vert: equ {capacity}\n'
    prefix += graphics[graphics.index('\tq_vars graphics'):graphics.index('\tq_end_vars graphics')]+'\n'
    # Actual Letter I face, scaled, rotated and translated in screen space.
    points = [(147,44),(95,57),(82,5),(-72,44),(-59,96),(-110,109),(-149,-45),(-98,-58),(-85,-6),(69,-45),(56,-97),(107,-110)]
    body = ' move.w #1,qa_case\n lea qa_vertices(pc),a4\n lea 11*node_len(a4),a3\n clr.w clip_panel(a6)\n'
    tail = 'qa_case: dc.w 0\nqa_vertices:\n'
    for i,(x,y) in enumerate(points):
        flags = (x < -128) | ((x > 127)<<1) | ((y < -56)<<2) | ((y > 55)<<3)
        tail += f' dc.b {flags},0\n dc.w {x},{y}\n dc.l qa_vertices+{(i-1)%12}*node_len,qa_vertices+{(i+1)%12}*node_len\n dc.w 0\n'
    for index,(edge,bit) in enumerate([('left',0),('right',1),('bottom',2),('top',3)]):
        dest = 'vertex_list'+str(index%2+1)
        body += f' move.w #{dest},which_list(a6)\n move.w #$cafe,which_list+2(a6)\n move.l #$55aa33cc,which_list+4(a6)\n moveq #{bit},d4\n lea {dest}(a6),a0\n move.l #${s["intersect_"+edge]:x},a2\n'
        body += call('clip_edge')
        body += f' cmp.w #{dest},which_list(a6)\n bne fail\n cmp.w #$cafe,which_list+2(a6)\n bne fail\n cmp.l #$55aa33cc,which_list+4(a6)\n bne fail\n'
    body += ' move.l a0,d0\n sub.l a4,d0\n cmp.l #16*node_len,d0\n bne fail\n'
    # One past the list must be rejected without touching adjacent variables.
    body += ' move.w #2,qa_case\n lea vertex_list2+max_vert*node_len(a6),a0\n moveq #1,d0\n moveq #2,d1\n moveq #0,d2\n moveq #-1,d5\n'
    body += call('add_vertex')
    body += ' cmp.w #vertex_list2,which_list(a6)\n bne fail\n cmp.w #$cafe,which_list+2(a6)\n bne fail\n cmp.l #$55aa33cc,which_list+4(a6)\n bne fail\n tst.b clip_panel(a6)\n bpl fail\n'
    return prefix,body,tail,['Letter I clips to 16 vertices','Full clipping workspace rejects another vertex']
