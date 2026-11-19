"""Unsigned-cash boundary tests through real hull/equipment transactions."""
from native_player_ships import make_suite as player_suite

MAX_CASH = 0xffffffff
PRICES = [1000000,270000,325000,360000,395000,1435000,2050000,
          2400000,4000000,8950000,205000,305000,375000]
CATEGORIES = [0,1,1,4,1,2,3,3,3,2,4,4,4]
EQUIPMENT = [
    [0,250,6000,6000,4000,10000,5250,3000,25000,15000,15000,50000,8000,60000,80000],
    [0,250,5000,4000,4000,10000,3750,2000,12500,9000,8000,30000,8000,60000,80000],
    [0,250,20000,5000,4000,10000,7000,6000,25000,25000,10000,40000,8000,60000,80000],
    [0,250,60000,8000,4000,10000,6500,4500,18750,19000,20000,60000,8000,60000,80000],
    [0,250,4000,3000,4000,10000,4500,2500,9380,7000,7000,30000,8000,60000,80000],
]
LASERS = (4,5,12,13)


def balances(cost):
    values = {0,0x7fffffff,0x80000000,MAX_CASH}
    edge = cost if cost >= 0 else MAX_CASH + cost
    values.update(v for v in (edge-1,edge,edge+1) if 0 <= v <= MAX_CASH)
    return sorted(values)


def result(cash, cost):
    return (1,cash) if cash < cost else (0,min(MAX_CASH,cash-cost))


def make_suite(root, s):
    prefix, _, tail, _ = player_suite(root,s)
    call = lambda name: f' jsr ${s[name]:x}\n'
    names = []
    ships = []
    equipment = []
    for old, price in enumerate(PRICES):
        for new, new_price in enumerate(PRICES):
            if old == new:
                continue
            cost = new_price - price*3//5
            for cash in balances(cost):
                status, final = result(cash,cost)
                names.append(f'Hull {old} to {new}, cash {cash:#x}: net charge/refund and atomic rejection')
                ships.append(f' dc.w {old},{new}\n dc.l ${cash:x},${final:x}\n dc.w {status}\n')
    ship_count = len(names)

    def equip_case(hull, item, old, sell, cost, cash):
        status, final = result(cash,cost)
        flags = [0x8000 | int(laser == old) for laser in LASERS]
        if not status and item in LASERS:
            flags = [0x8000 | int(not sell and laser == item) for laser in LASERS]
        device = (int(bool(sell)) if status else int(not sell)) if item not in LASERS else 0
        names.append(f'Hull {hull}, item {item}, old laser {old}, sell {sell}, cash {cash:#x}: exact balance and equipment')
        equipment.append(f' dc.w {hull},{item},{old},0,{sell},{status}\n'
                         f' dc.l ${cash:x},${final:x}\n'
                         ' dc.w '+','.join(map(str,flags+[device]))+'\n')

    for hull in range(13):
        prices = EQUIPMENT[CATEGORIES[hull]]
        for old in (0,*LASERS):
            for item in LASERS:
                if old == item:
                    continue
                cost = prices[item] - (prices[old]//2 if old else 0)
                for cash in balances(cost):
                    equip_case(hull,item,old,0,cost,cash)
        for item in LASERS:
            cost = -prices[item]//2
            for cash in balances(cost):
                equip_case(hull,item,item,1,cost,cash)
    # One hull from every price category, including device refunds at the cap.
    for hull in (0,1,3,5,6):
        for item in (1,2,3,6,7,8,9,10,11,14):
            price = EQUIPMENT[CATEGORIES[hull]][item]
            for sell in (0,1):
                cost = -price//2 if sell else price
                for cash in balances(cost):
                    equip_case(hull,item,0,sell,cost,cash)

    body = ''' lea qa_ships(pc),a2
 move.l a2,qa_next
qa_ship_loop:
 addq.w #1,qa_case
 bsr qa_world
 move.l qa_next(pc),a2
 move.w (a2),player_ship(a6)
'''+call('ship_apply')+''' move.l 4(a2),cash(a6)
 move.w 2(a2),d0
'''+call('ship_purchase')+''' move.l qa_next(pc),a2
 cmp.w 12(a2),d0
 bne fail
 move.l cash(a6),d1
 cmp.l 8(a2),d1
 bne fail
 move.w (a2),d1
 tst.w d0
 bne.s qa_same_hull
 move.w 2(a2),d1
qa_same_hull:
 cmp.w player_ship(a6),d1
 bne fail
 add.l #14,qa_next
'''+f' cmp.w #{ship_count},qa_case\n blo qa_ship_loop\n'+''' lea qa_equipment(pc),a2
 move.l a2,qa_next
qa_equip_loop:
 addq.w #1,qa_case
 bsr qa_world
 move.l qa_next(pc),a2
 move.w (a2),player_ship(a6)
'''+call('ship_apply')+''' move.l 12(a2),cash(a6)
 move.w 4(a2),d1
 beq.s qa_no_old_laser
 add.w d1,d1
 lea equip(a6),a0
 move.w #$8001,(a0,d1.w)
qa_no_old_laser:
 move.w 2(a2),d0
 move.w d0,d1
 add.w d1,d1
 lea equip(a6),a0
 tst.w (a0,d1.w)
 bmi.s qa_laser_ready
 move.w 8(a2),(a0,d1.w)
qa_laser_ready:
 move.w 6(a2),d1
 move.w 8(a2),d2
'''+call('ship_equip_transaction')+''' move.l qa_next(pc),a2
 cmp.w 10(a2),d0
 bne fail
 move.l cash(a6),d1
 cmp.l 16(a2),d1
 bne fail
 move.w player_ship(a6),d1
 cmp.w (a2),d1
 bne fail
'''
    for index, laser in enumerate(LASERS):
        body += f' move.w equip+{laser*2}(a6),d1\n cmp.w {20+2*index}(a2),d1\n bne fail\n'
    body += ''' move.w 2(a2),d1
 add.w d1,d1
 lea equip(a6),a0
 move.w (a0,d1.w),d1
 bmi.s qa_equipment_checked
 cmp.w 28(a2),d1
 bne fail
qa_equipment_checked:
 add.l #30,qa_next
'''+f' cmp.w #{len(names)},qa_case\n blo qa_equip_loop\n'
    tail += 'qa_next: dc.l 0\nqa_ships:\n'+''.join(ships)+'qa_equipment:\n'+''.join(equipment)
    return prefix,body,tail,names
