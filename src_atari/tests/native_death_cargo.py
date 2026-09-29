"""Count actual death canisters from cargo mass, independently of equipment."""


def make_suite(root, s):
    call = lambda name: f" jsr ${s[name]:x}\n"
    prefix = ' include "common.def"\n include "macros.m68"\n'
    loop = s['q_effects_m68_1']
    body = ' clr.w csr_on(a6)\n clr.w display_clock(a6)\n'
    body += call('reset_system') + call('launch_system')
    body += call('prepare_cockpit') + call('front_view')
    body += f' move.w ${loop:x},qa_opcode\n move.w #$4e75,${loop:x}\n'
    # Equipment remains installed even for the empty-hold case.
    body += ' move.w #1,equip+ecm_system(a6)\n'
    scenarios = [
        ('Empty hold with installed equipment', {}, 0),
        ('One kilogram of gold', {13: 1000}, 1),
        ('Just below one tonne', {15: 999999}, 1),
        ('Exactly one tonne', {0: 1000000}, 1),
        ('One tonne plus one gram', {0: 1000000, 15: 1}, 2),
        ('Exactly two tonnes', {0: 2000000}, 2),
        ('Two tonnes plus one gram', {0: 2000000, 15: 1}, 3),
        ('Exactly three tonnes', {0: 3000000}, 3),
        ('Three tonnes plus one gram', {0: 3000000, 15: 1}, 4),
        ('Exactly four tonnes', {0: 4000000}, 4),
        ('Large cargo capped at four', {0: 250000000}, 4),
        ('Mixed kilograms and grams total exactly one tonne', {13: 500000, 14: 499000, 15: 1000}, 1),
        ('Mixed kilograms and grams cross one tonne', {13: 500000, 14: 500000, 15: 1}, 2),
        ('Several small holdings cross the cap', {0: 2000000, 1: 2000000, 2: 2000000}, 4),
        ('Unsigned large holding cannot wrap the total', {0: 1, 1: 0xffffffff}, 4),
    ]
    scenarios += [(f'One gram in cargo slot {i}, including mission cargo', {i: 1}, 1)
                  for i in range(20)]
    for index, (name, cargo, expected) in enumerate(scenarios, 1):
        body += f' move.w #{index},qa_case\n bsr qa_clear_hold\n'
        for item, grams in cargo.items():
            body += f' move.l #${grams:x},hold+{item}*4(a6)\n'
        body += call('end_game')
        body += ' lea objects(a6),a5\n move.l #1000,zpos(a5)\n'
        body += call('do_endgame1')
        body += ' bsr qa_count\n'
        body += f' cmp.w #{expected},d0\n bne fail\n'
        # The death animation must not consume or rewrite the player's hold.
        for item in range(20):
            body += f' cmp.l #${cargo.get(item, 0):x},hold+{item}*4(a6)\n bne fail\n'
    body += f' move.w qa_opcode,${loop:x}\n'
    tail = """
qa_clear_hold:
 lea hold(a6),a0
 moveq #max_products-1,d0
.clear:
 clr.l (a0)+
 dbra d0,.clear
 rts
qa_count:
 cmp.w #log_exploding,objects+logic(a6)
 bne fail
 moveq #0,d0
 moveq #0,d1
 lea objects+obj_len(a6),a0
 moveq #max_objects-2,d2
.scan:
 btst #in_use,flags(a0)
 beq.s .next
 cmp.w #log_twisting,logic(a0)
 bne fail
 cmp.w #barrel,type(a0)
 bne.s .fragment
 addq.w #1,d0
 bra.s .next
.fragment:
 cmp.w #platlet,type(a0)
 bne fail
 addq.w #1,d1
.next:
 lea obj_len(a0),a0
 dbra d2,.scan
 cmp.w #5,d1
 bne fail
 rts
qa_case: dc.w 0
qa_stage: dc.w 0
qa_opcode: dc.w 0
"""
    return prefix, body, tail, [name for name, _, _ in scenarios]
