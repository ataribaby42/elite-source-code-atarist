"""Native delivery/UI/save checks against an independent Unbound reference."""
from math import isqrt
from native_player_ships import make_suite as player_suite


def galaxy(number):
    values=[0x5a4a,0x0248,0xb753]
    for _ in range(number):
        values=[(((w&0x7f7f)<<1)|((w&0x8080)>>7)) for w in values]
    return values


def worlds(number):
    seed=galaxy(number);out=[]
    for _ in range(256):
        out.append(tuple(seed))
        for _ in range(4):seed=[seed[1],seed[2],sum(seed)&65535]
    return out


def offers(gal,current,market,legal,kills,hull,oldxy):
    """6502 byte/carry arithmetic, with the source's fee/reward distinction."""
    systems=worlds(gal);home=systems[current]
    x,y=home[1]>>8,home[0]>>8
    skip=market^x^y^legal^(kills&255)
    acc=legal+gal+1
    acc=(acc&255)+hull+(acc>>8)
    stride=acc&255
    acc=stride+skip+(acc>>8)
    carry=acc>>8;acc=(acc&255)-oldxy[0]-(1-carry)
    carry=int(acc>=0);acc=(acc&255)-oldxy[1]-(1-carry)
    limit=acc&15
    rows=[]
    for i,(a,b,c) in enumerate(systems[1:],1):
        if len(rows)>=limit:break
        skip=(skip-1)&255
        if skip:continue
        dx,dy=b>>8,a>>8
        if (dx,dy)!=(x,y):
            risk=dx^(c>>8)^stride
            if risk>=legal:risk=0
            distance=isqrt(((dx-x)**2+(abs(dy-y)//2)**2)&65535)
            high=max((dy^(c>>8)^stride)>>3,distance)|risk
            fee=(high*257)>>3
            reward=(high<<8)|(fee&255)
            rows.append((i,(dx<<8)|dy,risk,fee,reward))
        skip=stride
    return rows


def make_suite(root,s):
    prefix,_,base_tail,_=player_suite(root,s)
    out=[];names=[];data=[]
    emit=out.append
    call=lambda n:f' jsr ${s[n]:x}\n'
    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n bsr qa_courier_world\n')
    def eq(v,field,size='w'):emit(f' cmp.{size} #{v},{field}\n bne fail\n')
    # A bounded table walk keeps the payload well below 64 KB on Amiga.
    configs=[(g,(g*31+h*17)&255,(g*73+h*29)&255,(g*47+h*13)&255,
              (g*89+h*31)&255,h,((h*19)&255,(g*37)&255)) for g in range(8) for h in range(13)]
    configs += [(0,7,market,legal,score,0,old) for market,legal,score,old in
        [(0,0,0,(0,0)),(255,0,255,(255,255)),(255,255,255,(255,255)),
         (0,255,0,(0,0)),(33,254,201,(1,255)),(17,1,0,(0,1)),
         *[(i,0,0,(0,0)) for i in range(32)]]]
    emit(' bsr qa_world\n bsr qa_courier_world\n lea qa_vectors,a4\n')
    emit(f' move.w #{len(configs)-1},qa_remaining\n clr.w qa_case\nqa_vector_loop:\n addq.w #1,qa_case\n')
    emit(' move.l (a4)+,gal_seed(a6)\n move.w (a4)+,gal_seed+4(a6)\n move.l (a4)+,splanet+seed(a6)\n move.w (a4)+,splanet+seed+4(a6)\n')
    for field in ('current','galaxy_no','fluctuation','police_record','score+2','player_ship','courier_x'):
        emit(f' move.w (a4)+,{field}(a6)\n')
    emit(' clr.w courier_reward(a6)\n move.l #$12345678,random_seed(a6)\n'+call('courier_generate'))
    emit(' cmp.l #$12345678,random_seed(a6)\n bne fail\n move.w (a4)+,d0\n cmp.w courier_count(a6),d0\n bne fail\n')
    emit(' mulu.w #5,d0\n subq.w #1,d0\n bmi.s qa_vector_next\n lea courier_offers(a6),a0\nqa_compare_offer:\n move.w (a4)+,d1\n cmp.w (a0)+,d1\n bne fail\n dbra d0,qa_compare_offer\nqa_vector_next:\n subq.w #1,qa_remaining\n bpl qa_vector_loop\n')
    for g,cur,market,legal,score,hull,old in configs:
        names.append(f'Unbound offers: galaxy {g}, system {cur}, market {market}, legal {legal}, kills {score}, hull {hull}, previous {old}')
        rows=offers(g,cur,market,legal,score,hull,old)
        words=[*galaxy(g),*worlds(g)[cur],cur,g,market,legal,score,hull,(old[0]<<8)|old[1],len(rows)]
        words.extend(v for row in rows for v in row)
        data.append(' dc.w '+','.join(map(str,words))+'\n')
    # Controlled on-screen offer data; transactions must not depend on tonnage.
    def setup_offer():
        emit(' move.w #1,courier_count(a6)\n lea courier_offers(a6),a0\n move.w #7,(a0)\n move.w #$14ad,2(a0)\n move.w #20,4(a0)\n move.w #1234,6(a0)\n move.w #9876,8(a0)\n')
    for amount in (0,1233,1234,10000000):
        case(f'Acceptance with {amount} tenths: atomic fee deduction and wrapping legal status')
        setup_offer();emit(f' move.l #{amount},cash(a6)\n move.w #250,police_record(a6)\n moveq #0,d0\n'+call('courier_accept'))
        if amount<1234:
            eq(1,'d0');eq(amount,'cash(a6)','l');eq(0,'courier_reward(a6)');eq(250,'police_record(a6)')
        else:
            eq(0,'d0');eq(amount-1234,'cash(a6)','l');eq(9876,'courier_reward(a6)');eq(14,'police_record(a6)');eq('$14ad','courier_x(a6)')
            emit(' moveq #0,d0\n'+call('courier_accept'));eq(2,'d0');eq(amount-1234,'cash(a6)','l')
    for index in (-1,1,15,255):
        case(f'Invalid click index {index} is ignored')
        setup_offer();emit(f' move.w #{index},d0\n'+call('courier_accept'));eq(2,'d0');eq(10000000,'cash(a6)','l');eq(0,'courier_reward(a6)')
    case('In-flight acceptance is rejected')
    setup_offer();emit(' clr.w docked(a6)\n moveq #0,d0\n'+call('courier_accept'));eq(2,'d0')
    case('Special Cargo takes no hold space and survives a ship purchase')
    setup_offer();emit(call('ship_used_hold')+' move.l d0,qa_used\n moveq #0,d0\n'+call('courier_accept')+call('ship_used_hold'))
    emit(' cmp.l qa_used,d0\n bne fail\n moveq #1,d0\n'+call('ship_purchase'));eq(0,'d0');eq(9876,'courier_reward(a6)')
    for reward in (0,1,2,3,5250,65535):
        for matching in (False,True):
            case(f'Docking reward {reward}, destination match {matching}: exact payout/halving, story and hold preserved')
            emit(f' move.w #{reward},courier_reward(a6)\n move.w #$14ad,courier_x(a6)\n move.b #{20 if matching else 21},splanet+seed+2(a6)\n move.b #173,splanet+seed(a6)\n move.w #$16,mission(a6)\n move.l #12345,hold(a6)\n'+call('courier_settle'))
            eq(0 if not reward else 2 if matching else 1,'d0')
            eq(10000000+(reward if matching else 0),'cash(a6)','l')
            eq(0 if matching else reward//2,'courier_reward(a6)');eq('$14ad','courier_x(a6)');eq('$16','mission(a6)');eq(12345,'hold(a6)','l')
            if matching:emit(call('courier_settle'));eq(0,'d0');eq(10000000+reward,'cash(a6)','l')
    case('Save/load keeps the tagged reward and old coordinates without depreciation')
    emit(' move.w #5250,courier_reward(a6)\n move.w #$14ad,courier_x(a6)\n'+call('save_state')+' clr.l courier_reward(a6)\n'+call('restore_state'))
    eq(5250,'courier_reward(a6)');eq('$14ad','courier_x(a6)');eq(10000000,'cash(a6)','l')
    case('An absent legacy save extension becomes an empty tagged delivery')
    emit(' clr.l courier_tag(a6)\n move.l #-1,courier_reward(a6)\n'+call('courier_validate'));eq(0,'courier_reward(a6)','l');eq('$53434731','courier_tag(a6)','l')
    case('Invalid saved coordinates clear the active reward; bounded lookup returns -1')
    emit(' move.w #5250,courier_reward(a6)\n move.w #$ffff,courier_x(a6)\n'+call('courier_validate'));eq(0,'courier_reward(a6)')
    case('Default commander resets the contract and initializes its save extension')
    emit(' move.l #-1,courier_reward(a6)\n'+call('default_game')+call('restore_state'));eq(0,'courier_reward(a6)','l');eq('$53434731','courier_tag(a6)','l');eq(1,'player_ship(a6)')
    tail=base_tail+'''
qa_courier_world:
 clr.w csr_on(a6)
 clr.w display_clock(a6)
 clr.w cockpit_on(a6)
 clr.w disp_type(a6)
 clr.w witch_space(a6)
 move.l #$5a4a0248,gal_seed(a6)
 move.w #$b753,gal_seed+4(a6)
 clr.w galaxy_no(a6)
 move.w #7,current(a6)
 move.l #$53434731,courier_tag(a6)
 clr.l courier_reward(a6)
 clr.w courier_count(a6)
 clr.w courier_paid(a6)
 clr.w courier_mode(a6)
'''+call('gen_prices')+''' rts
qa_remaining: dc.w 0
qa_used: dc.l 0
qa_vectors:
'''+''.join(data)
    return prefix,''.join(out),tail,names
