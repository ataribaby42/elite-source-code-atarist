"""Native viewport regression: extreme lines, bounded text."""
import random,re


def clipped(coords):
    # Python integers avoid the signed-word overflow under test.
    x, y, u, v = coords
    def code(x, y):
        return (x < -128) | ((x > 127) << 1) | ((y < -56) << 2) | ((y > 55) << 3)
    def ratio(delta, distance, span):
        value = abs(delta * distance) // abs(span)
        return -value if delta * distance * span < 0 else value
    for _ in range(8):
        a, b = code(x, y), code(u, v)
        if not a | b:
            return x + 160, 63 - y, u + 160, 63 - v
        if a & b:
            return None
        if not a:
            x, y, u, v, a, b = u, v, x, y, b, a
        if a & 8:
            x, y = x + ratio(u-x, 55-y, v-y), 55
        elif a & 4:
            x, y = x + ratio(u-x, -56-y, v-y), -56
        elif a & 2:
            x, y = 127, y + ratio(v-y, 127-x, u-x)
        else:
            x, y = -128, y + ratio(v-y, -128-x, u-x)
    raise AssertionError(coords)


def make_suite(root, s):
    call = lambda name: f' jsr ${s[name]:x}\n'
    prefix = ' include "common.def"\n include "macros.m68"\n'
    graphics = (root/'asm/graphics.m68').read_text()
    prefix += re.search(r'max_vert: equ \d+',graphics).group(0)+'\n'
    prefix += graphics[graphics.index('\tq_vars graphics'):graphics.index('\tq_end_vars graphics')]+'\n'
    body = ' clr.w csr_on(a6)\n clr.w display_clock(a6)\n clr.w player_ship(a6)\n'
    body += call('ship_apply') + call('reset_system') + call('prepare_cockpit') + call('front_view')
    body += ' moveq #15,d0\n' + call('set_colour')
    rng = random.Random(20260924)
    extremes = [-32768,-32767,-16000,-129,-128,-57,-56,-1,0,1,55,56,127,128,16000,32767]
    lines = [(x,y,u,v) for x,y,u,v in [(-32768,-32768,32767,32767),(-32768,32767,32767,-32768),(-32768,0,32767,0),(0,-32768,0,32767),(-128,-56,127,55),(0,0,0,0)]]
    lines += [tuple(rng.choice(extremes) for _ in range(4)) for _ in range(186)]
    names = ['line '+str(c) for c in lines]
    body += ' lea qa_lines(pc),a0\n move.l a0,qa_next\n move.w #191,qa_remaining\nqa_line_loop:\n addq.w #1,qa_case\n bsr qa_fill\n'
    body += call('clear_image')
    body += ' move.l qa_next(pc),a3\n movem.w (a3),d0-d3\n'
    body += call('c_line') + ' bsr qa_guard_check\n' + call('swap_screen') + ' bsr qa_fill\n' + call('clear_image')
    body += ' move.l qa_next(pc),a3\n tst.w 8(a3)\n beq.s qa_no_line\n movem.w 10(a3),d0-d3\n'
    body += call('line') + 'qa_no_line:\n bsr qa_guard_check\n bsr qa_compare\n add.l #18,qa_next\n subq.w #1,qa_remaining\n bpl qa_line_loop\n'
    tail = 'qa_lines:\n'
    for coords in lines:
        expected = clipped(coords)
        tail += ' dc.w '+','.join(map(str, (*coords, int(expected is not None), *(expected or (0,0,0,0)))))+'\n'
    messages = [b'',b'GAME OVER',b'X'*31,b'X'*32,b'X'*33,b'X'*127,b'X'*255,b'AB\rCD\nEF\x1fGH']
    for row in (0,13):
        for msg in messages:
            index = len(names)+1
            names.append(f'text row {row}, length {len(msg)}')
            expected = bytes(max(c,32) for c in msg[:32])
            body += f' move.w #{index},qa_case\n bsr qa_fill\n'
            body += call('clear_image')
            body += ' lea text_buffer(a6),a0\n moveq #31,d7\n'
            body += f'qa_text_clear_{index}:\n move.l #$cccccccc,(a0)+\n dbra d7,qa_text_clear_{index}\n'
            body += f' lea qa_message_{index}(pc),a0\n'+call('disp_message')
            body += f' cmp.w #{(33-len(expected))//2},text_offset(a6)\n bne fail\n'
            body += ' lea text_buffer(a6),a0\n'
            for c in expected+b'\0':
                body += f' cmp.b #{c},(a0)+\n bne fail\n'
            body += ' cmp.l #$cccccccc,text_buffer+124(a6)\n bne fail\n'
            body += f' move.w #{row},text_row(a6)\n moveq #15,d0\n'+call('text_blatt')+' bsr qa_guard_check\n'
            tail += f'qa_message_{index}: dc.b '+','.join(map(str,msg+b'\0'))+'\n even\n'
    tail += GUARDS + 'qa_case: dc.w 0\nqa_remaining: dc.w 0\nqa_next: dc.l 0\n'
    return prefix, body, tail, names


GUARDS = """qa_fill:
 movem.l d0/d7/a0,-(sp)
 move.l scr_base(a6),a0
 move.w #7999,d7
qa_fill_loop:
 move.l #$55aa33cc,(a0)+
 dbra d7,qa_fill_loop
 movem.l (sp)+,d0/d7/a0
 rts
qa_guard_check:
 movem.l d0-d3/d7/a0,-(sp)
 move.l scr_base(a6),a0
 moveq #0,d1
qa_check_row:
 moveq #0,d2
qa_check_word:
 cmp.w #8,d1
 blo.s qa_check_outside
 cmp.w #120,d1
 bhs.s qa_check_outside
 ; Platform-specific viewport byte spans are selected below.
  cmp.w #16,d2
 blo.s qa_check_outside
 cmp.w #144,d2
 blo.s qa_check_next
qa_check_outside:
 cmp.l #$55aa33cc,(a0)
 bne fail
qa_check_next:
 addq.l #4,a0
 addq.w #4,d2
 cmp.w #160,d2
 blo qa_check_word
 addq.w #1,d1
 cmp.w #200,d1
 blo qa_check_row
 movem.l (sp)+,d0-d3/d7/a0
 rts
qa_compare:
 movem.l d0/d7/a0-a1,-(sp)
 move.l screen1_ptr(a6),a0
 move.l screen2_ptr(a6),a1
 move.w #7999,d7
qa_compare_loop:
 move.l (a0)+,d0
 cmp.l (a1)+,d0
 bne fail
 dbra d7,qa_compare_loop
 movem.l (sp)+,d0/d7/a0-a1
 rts
"""
