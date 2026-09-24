"""Exercise generated ship caches, UI consumers and commander transitions natively."""
def make_suite(root, s):
    call=lambda name:f' jsr ${s[name]:x}\n'
    parts=[]; names=[]
    def emit(text): parts.append(text)
    def case(name):
        names.append(name); emit(f' move.w #{len(names)},qa_case\n')
    def capture(n):
        emit(f'snap_{n}:\n nop\n')
        if s.get('_capture_wait'):
            emit(f' move.w #{n+1},qa_capture\n.wait_{n}:\n tst.w qa_capture\n bne.s .wait_{n}\n')
    def hash_image(address, size):
        return f' lea ${address:x},a0\n move.w #{size//2-1},d1\n bsr qa_hash\n'
    emit(' clr.w display_clock(a6)\n clr.w cockpit_on(a6)\n move.w #1,docked(a6)\n')
    emit(hash_image(s['ship_yard_atlas'],13*1644)+' move.l d0,qa_yard_hash\n')
    for hull in range(13):
        case(f'Hull {hull}: regenerate both player images, Status, Planet, Equipment, Shipyards; cache guards and immutable yard')
        emit(f' move.w #{hull},player_ship(a6)\n'+call('ship_apply'))
        emit(hash_image(s['ship_status_image'],4084)+f' move.l d0,qa_hashes+{hull*8}\n')
        emit(hash_image(s['ship_planet_image'],904)+f' move.l d0,qa_hashes+{hull*8+4}\n')
        emit(call('status')+call('hide_cursor'));capture(hull*3)
        emit(call('data')+call('hide_cursor'));capture(hull*3+1)
        emit(call('equip_ship')+call('shipyards')+call('hide_cursor'));capture(hull*3+2)
        emit(' bsr qa_guards\n')
        emit(hash_image(s['ship_yard_atlas'],13*1644)+' cmp.l qa_yard_hash,d0\n bne fail\n')
    case('Purchase Python updates only player portraits; restore saved Asp and start default Cobra')
    emit(' lea equip(a6),a0\n moveq #equip_len/2-1,d0\n.clear_equip:\n clr.w (a0)+\n dbra d0,.clear_equip\n')
    emit(' lea hold(a6),a0\n moveq #max_products-1,d0\n.clear_hold:\n clr.l (a0)+\n dbra d0,.clear_hold\n')
    emit(' move.w #9,player_ship(a6)\n move.l #$53485031,player_ship_tag(a6)\n'+call('ship_apply')+call('save_state'))
    emit(' move.l #20000000,cash(a6)\n moveq #6,d0\n'+call('ship_purchase')+' tst.w d0\n bne fail\n')
    for h,action in ((6,''),(9,call('restore_state')),(0,call('default_game')+call('restore_state'))):
        emit(action+f' cmp.w #{h},player_ship(a6)\n bne fail\n')
        emit(hash_image(s['ship_status_image'],4084)+f' cmp.l qa_hashes+{h*8},d0\n bne fail\n')
        emit(hash_image(s['ship_planet_image'],904)+f' cmp.l qa_hashes+{h*8+4},d0\n bne fail\n bsr qa_guards\n')
    case('Flight rendering leaves all generated images and boundaries intact')
    emit(' bclr #f_sequence,user+1(a6)\n'+call('launch'))
    for _ in range(3):emit(call('game_logic')+' bsr qa_guards\n')
    emit(hash_image(s['ship_yard_atlas'],13*1644)+' cmp.l qa_yard_hash,d0\n bne fail\n')
    emit(hash_image(s['ship_status_image'],4084)+' cmp.l qa_hashes,d0\n bne fail\n')
    emit(hash_image(s['ship_planet_image'],904)+' cmp.l qa_hashes+4,d0\n bne fail\n')
    tail='qa_guards:\n'
    for name in ('ship_graphics_begin','ship_yard_end','ship_status_end','ship_planet_end'):
        tail+=f' cmp.l #$53484950,${s[name]:x}\n bne fail\n'
    tail+=f' cmp.l #$53484950,${s["ship_graphics_end"]-4:x}\n bne fail\n rts\n'
    tail+='''qa_hash:
 moveq #0,d0
.word:
 rol.l #1,d0
 move.w (a0)+,d2
 eor.w d2,d0
 dbra d1,.word
 rts
qa_case: dc.w 0
qa_capture: dc.w 0
qa_yard_hash: dc.l 0
qa_hashes: ds.l 13*2
'''
    return ' include "common.def"\n include "macros.m68"\n',''.join(parts),tail,names
