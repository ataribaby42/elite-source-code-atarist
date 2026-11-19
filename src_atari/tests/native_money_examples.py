"""Exact review reproductions and an unsigned-cash save/restore check."""
from native_player_ships import make_suite as player_suite


def make_suite(root,s):
    prefix,_,tail,_ = player_suite(root,s)
    parts,names = [],[]
    call = lambda name: f' jsr ${s[name]:x}\n'
    def case(name):
        names.append(name)
        parts.append(f' move.w #{len(names)},qa_case\n bsr qa_world\n')
    def eq(value,field,size='w'):
        parts.append(f' cmp.{size} #{value},{field}\n bne fail\n')

    case('Review: maximum cash buys an Asp for the exact net trade-in cost')
    parts.append(' move.l #$ffffffff,cash(a6)\n moveq #9,d0\n'+call('ship_purchase'))
    eq(0,'d0');eq(9,'player_ship(a6)');eq(4286617295,'cash(a6)','l')

    case('Review: Pulse purchase above the signed boundary succeeds')
    parts.append(' move.l #$80010000,cash(a6)\n moveq #4,d0\n moveq #0,d1\n moveq #0,d2\n'+call('ship_equip_transaction'))
    eq(0,'d0');eq('$8001','equip+pulse_lasers(a6)');eq(2147545184,'cash(a6)','l')

    case('Review: Military-to-Pulse refund crosses the signed boundary')
    parts.append(' move.l #$7fffffff,cash(a6)\n move.w #$8001,equip+military_lasers(a6)\n moveq #4,d0\n moveq #0,d1\n moveq #0,d2\n'+call('ship_equip_transaction'))
    eq(0,'d0');eq('$8000','equip+military_lasers(a6)');eq('$8001','equip+pulse_lasers(a6)');eq(2147509647,'cash(a6)','l')

    case('Maximum unsigned cash and purchased laser survive save/restore')
    parts.append(' move.l #$ffffffff,cash(a6)\n move.w #$8001,equip+pulse_lasers(a6)\n move.l #$53485031,player_ship_tag(a6)\n'+call('save_state')+
                 ' clr.l cash(a6)\n move.w #$8000,equip+pulse_lasers(a6)\n'+call('restore_state'))
    eq('$ffffffff','cash(a6)','l');eq('$8001','equip+pulse_lasers(a6)');eq(0,'player_ship(a6)')
    return prefix,''.join(parts),tail,names
