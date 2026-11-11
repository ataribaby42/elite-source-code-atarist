"""Cargo retaliation must never reactivate a hull after its pilot escapes."""
from native_pirate_loot_theft import make_suite as helpers


def make_suite(root, s):
    prefix, _, tail, _ = helpers(root, s)
    call = lambda name: f' jsr ${s[name]:x}\n'
    body = call('gen_prices')
    names = []
    random = s['random']
    for event in ('scoop', 'laser', 'missile'):
        names.append('Actual pilot escape: cargo ' + event + ' never reactivates the abandoned hull')
        body += f' move.w #{len(names)},qa_case\n bsr qa_theft_world\n'
        # A Viper interrupts collection; the pirate then really launches a pod.
        body += ' lea objects+4*obj_len(a6),a4\n lea objects+9*obj_len(a6),a0\n'
        body += call('loot_hit') + ' move.l a4,a5\n'
        body += f' move.l ${random:x},qa_escape_random\n move.w ${random+4:x},qa_escape_random+4\n'
        body += f' move.w #$4ef9,${random:x}\n move.l #qa_escape_zero,${random+2:x}\n'
        body += call('launch_escape')
        body += f' move.l qa_escape_random,${random:x}\n move.w qa_escape_random+4,${random+4:x}\n'
        body += ' cmp.b #1,obj_ctr+worm(a6)\n bne fail\n bsr qa_assert_abandoned\n'
        body += ' lea objects+5*obj_len(a6),a5\n'
        if event == 'scoop':
            body += ' move.l #100,zpos(a5)\n move.l #-20,ypos(a5)\n' + call('salvage')
            body += ' btst #remove,flags(a5)\n beq fail\n'
        elif event == 'laser':
            body += ''' clr.w ai_front(a5)
 clr.w ai_aft(a5)
 move.w #1,health(a5)
 clr.l this_xpos(a5)
 clr.l this_ypos(a5)
 move.l #4000,this_zpos(a5)
 st in_sights(a6)
 clr.w obj_hit(a6)
 move.w #1,hit_check(a6)
 move.w #20,laser_power(a6)
''' + call('check_hit')
        else:
            body += ''' clr.w ai_front(a5)
 clr.w ai_aft(a5)
 move.w #1,health(a5)
 lea objects+10*obj_len(a6),a4
 move.w #missile,d0
 moveq #0,d4
 moveq #0,d5
 move.l #10990,d6
 bsr qa_create
 move.l a4,a5
 lea objects+5*obj_len(a6),a4
 move.l a4,target(a5)
 move.w #log_locked,logic(a5)
''' + call('do_locked')
        if event != 'scoop':
            body += ' cmp.w #log_exploding,objects+5*obj_len+logic(a6)\n bne fail\n'
        body += ''' bsr qa_assert_abandoned
 cmp.w #log_attack,objects+3*obj_len+logic(a6)
 bne fail
 tst.l objects+3*obj_len+target(a6)
 bne fail
 tst.w objects+3*obj_len+loot_mode(a6)
 bne fail
 cmp.w #loot_encounter,objects+7*obj_len+loot_mode(a6)
 bne fail
'''
    tail += '''qa_assert_abandoned:
 cmp.w #log_abandoned,objects+4*obj_len+logic(a6)
 bne fail
 cmp.w #act_nothing,objects+4*obj_len+attack_type(a6)
 bne fail
 tst.w objects+4*obj_len+no_missiles(a6)
 bne fail
 tst.w objects+4*obj_len+loot_mode(a6)
 bne fail
 tst.l objects+4*obj_len+loot_target(a6)
 bne fail
 rts
qa_escape_zero:
''' + f' move.l qa_escape_random,${random:x}\n move.w qa_escape_random+4,${random+4:x}\n' + '''
 moveq #0,d0
 rts
qa_escape_random: ds.b 6
'''
    return prefix, body, tail, names
