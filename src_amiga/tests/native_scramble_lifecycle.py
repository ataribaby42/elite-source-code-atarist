"""Scramble ID persists across real docking, launch and both jump types."""
from native_special_cargo_lifecycle import make_suite as base_suite

def make_suite(root,s):
    prefix,body,tail,names=base_suite(root,s)
    body=body.replace(' move.w #5251,courier_reward(a6)', ' move.w #255,scrambled_id(a6)\n move.w #5251,courier_reward(a6)')
    for routine in ('docking','hyperspace','launch'):
        call=f' jsr ${s[routine]:x}\n'
        body=body.replace(call,call+' cmp.w #255,scrambled_id(a6)\n bne fail\n')
    return prefix,body,tail,['Hidden ID retained: '+name for name in names]
