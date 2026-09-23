"""Black-box scenarios executed against the linked 68000 game, not a Python model."""
def make_suite(root,s):
    prefix=' include "common.def"\n include "macros.m68"\n'
    parts=[];names=[]
    def emit(v):parts.append(v)
    def call(n):return f' jsr ${s[n]:x}\n'
    def case(name):
        names.append(name);emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n')
    def eq(v,f,size='w'):emit(f' cmp.{size} #{v},{f}\n bne fail\n')
    def hull(n):emit(f' move.w #{n},player_ship(a6)\n'+call('ship_apply'))
    def trans(item,sell=0,mount=0):emit(f' moveq #{item},d0\n moveq #{mount},d1\n moveq #{sell},d2\n'+call('ship_equip_transaction'))
    prices=[1000000,270000,325000,360000,395000,1435000,2050000,2400000,4000000,8950000,205000,305000,375000]
    capacities=[4,1,2,2,3,3,4,6,16,1,1,0,2]
    speeds=[22,19,24,20,20,24,16,19,11,31,29,24,25]
    fuels=[70,60,70,80,60,85,80,90,100,125,50,60,60]
    holds=[25,8,9,11,14,9,106,132,215,6,4,10,10]
    shield=[7,4,5,6,5,8,11,10,13,10,2,3,4]
    rolls=[40,34,40,40,28,34,16,22,16,34,41,34,40]
    pitches=[40,34,40,40,29,34,17,23,17,34,40,34,40]
    for n in range(13):
        case(f'Hull {n}: purchase, trade-in, full fuel, stats and empty cargo')
        hull(1 if n==0 else 0)
        oldprice=prices[1 if n==0 else 0]
        emit(f' moveq #{n},d0\n'+call('ship_purchase'));eq(0,'d0');eq(n,'player_ship(a6)')
        eq(10000000+oldprice*3//5-prices[n],'cash(a6)','l')
        eq(speeds[n],'hull_speed(a6)');eq(fuels[n],'equip+fuel(a6)');eq(capacities[n],'hull_missiles(a6)')
        emit(call('ship_cargo_spare'));eq(holds[n]*1000000,'d3','l')
        case(f'Hull {n}: missile capacity and half-price resale')
        hull(n)
        for _ in range(capacities[n]):trans(1);eq(0,'d0')
        trans(1);eq(5,'d0');eq(capacities[n],'equip+missiles(a6)')
        if capacities[n]:trans(1,1);eq(0,'d0');eq(10000000-capacities[n]*250+125,'cash(a6)','l')
        case(f'Hull {n}: resistance uses rounded Cobra-relative damage')
        hull(n)
        for amount in (0,1,10,40,96):
            emit(f' move.l #$ff123456,d1\n moveq #{amount},d0\n'+call('ship_shield_damage'))
            eq((amount*7+shield[n]//2)//shield[n],'d0');eq('$ff123456','d1','l')
    for n in range(13):
        case(f'Hull {n}: manual speed, roll and pitch reach their exact limits')
        hull(n)
        emit(' clr.w speed(a6)\n clr.w roll_angle(a6)\n clr.w climb_angle(a6)\n')
        emit(f' move.w #99,d6\nqa_controls_{n}:\n move.w d6,-(sp)\n'+call('increase_speed')+call('roll_right')+call('climb')+f' move.w (sp)+,d6\n dbra d6,qa_controls_{n}\n')
        eq(speeds[n],'speed(a6)');eq(rolls[n],'roll_angle(a6)');eq(pitches[n],'climb_angle(a6)')
    case('No purchase with installed laser; complete transaction remains unchanged')
    emit(' move.w #$8001,equip+pulse_lasers(a6)\n moveq #8,d0\n'+call('ship_purchase'));eq(2,'d0');eq(10000000,'cash(a6)','l');eq(0,'player_ship(a6)');eq('$8001','equip+pulse_lasers(a6)')
    case('All ordinary devices, including cargo bay and retro rockets, block exchange')
    for item in (2,3,6,7,8,9,10,11,14):
        emit(f' move.w #1,equip+{item*2}(a6)\n moveq #8,d0\n'+call('ship_purchase'));eq(2,'d0');emit(f' clr.w equip+{item*2}(a6)\n')
    case('Cargo plus all three unique rewards transfer at the exact capacity boundary')
    emit(' move.w #2,equip+energy_unit(a6)\n move.w #1,equip+ecm_jammer(a6)\n move.w #1,equip+cloaking_device(a6)\n move.l #3000000,hold(a6)\n move.w #1,equip+missiles(a6)\n moveq #9,d0\n'+call('ship_purchase'))
    eq(0,'d0');eq(2,'equip+energy_unit(a6)');eq(1,'equip+cloaking_device(a6)');eq(1,'equip+ecm_jammer(a6)');eq(3000000,'hold(a6)','l');emit(call('ship_cargo_spare'));eq(0,'d3','l')
    case('One gram over the new hold capacity rejects without charging')
    emit(' move.l #6000001,hold(a6)\n moveq #9,d0\n'+call('ship_purchase'));eq(3,'d0');eq(10000000,'cash(a6)','l')
    case('Too many carried missiles reject the smaller hull')
    emit(' move.w #2,equip+missiles(a6)\n moveq #9,d0\n'+call('ship_purchase'));eq(4,'d0')
    case('Insufficient trade-in plus cash rejects the expensive hull')
    emit(' clr.l cash(a6)\n moveq #9,d0\n'+call('ship_purchase'));eq(1,'d0');eq(0,'player_ship(a6)');eq(0,'cash(a6)','l')
    case('Lasers occupy one tonne per mount and sell separately at 50 percent')
    trans(4,0,0);eq(0,'d0');trans(4,0,1);eq(0,'d0');emit(call('ship_equipment_mass'));eq(2,'d0')
    trans(4,1,0);eq(0,'d0');eq('$8002','equip+pulse_lasers(a6)');eq(9994000,'cash(a6)','l')
    case('Replacement retains one tonne and refunds half the previous laser price')
    trans(4);trans(5);eq(0,'d0');eq('$8000','equip+pulse_lasers(a6)');eq('$8001','equip+beam_lasers(a6)');eq(9988000,'cash(a6)','l');emit(call('ship_equipment_mass'));eq(1,'d0')
    case('Unaffordable replacement leaves the old laser and cash intact')
    trans(4);emit(' clr.l cash(a6)\n');trans(13);eq(1,'d0');eq('$8001','equip+pulse_lasers(a6)');eq('$8000','equip+military_lasers(a6)');eq(0,'cash(a6)','l')
    case('Cargo full: reject new equipment, allow same-slot laser replacement')
    trans(4);emit(' move.l #24000000,hold(a6)\n');trans(3);eq(2,'d0');trans(5);eq(0,'d0')
    case('Unsupported side mount rejected on Adder and all rear mounts on Asp')
    hull(1);trans(4,0,2);eq(4,'d0');trans(4,0,1);eq(0,'d0');hull(9);trans(4,0,1);eq(4,'d0')
    case('Cargo bay sale blocked while overloaded, then succeeds after unloading')
    trans(2);emit(' move.l #25000001,hold(a6)\n');trans(2,1);eq(2,'d0');eq(1,'equip+cargo_bay(a6)');emit(' clr.l hold(a6)\n');trans(2,1);eq(0,'d0')
    case('Naval energy unit cannot be sold as ordinary equipment')
    emit(' move.w #2,equip+energy_unit(a6)\n');trans(9,1);eq(6,'d0');eq(2,'equip+energy_unit(a6)')
    case('Legacy and invalid saved hull IDs migrate to Cobra; valid ID survives')
    emit(' clr.l player_ship_tag(a6)\n move.w #9,player_ship(a6)\n'+call('ship_validate'));eq(0,'player_ship(a6)');eq(22,'hull_speed(a6)')
    emit(' move.w #13,player_ship(a6)\n'+call('ship_validate'));eq(0,'player_ship(a6)')
    emit(' move.w #8,player_ship(a6)\n'+call('ship_validate'));eq(8,'player_ship(a6)');eq(16,'hull_missiles(a6)')
    normal=[1,2,3,4,0,5,6,7,8,9];anarchy=[10,1,11,2,3,12,4,0,5,6,7,8,9];mid=[10,1,11,2,3,4,0]
    for gov in (0,1,7):
        for econ in range(8):
            case(f'Government {gov}, economy {econ}: exact C64 offer list')
            counts=[10,8,6,5,4,4,3,1]
            count=counts[econ]+([3,3,3,2,2,2,1,0][econ] if gov==0 else 0)
            offers=normal if gov else (anarchy if econ<3 else mid if econ<6 else [10,1,2,3] if econ==6 else normal)
            emit(f' move.w #{gov},splanet+govern(a6)\n move.w #{econ},splanet+econ(a6)\n'+call('ship_build_offers'));eq(count,'yard_count(a6)')
            for i,n in enumerate(offers[:count]):eq(n,f'yard_offers+{2*i}(a6)')
    case('Equal hull collision is 10; smaller hits scale down; larger by two classes is fatal')
    emit(' lea objects(a6),a5\n move.w #cobra,type(a5)\n move.w #72,health(a5)\n'+call('ship_collision_damage'));eq(10,'d0')
    hull(10);emit(call('ship_collision_damage'));eq(-1,'d0')
    hull(8);emit(' move.w #adder,type(a5)\n'+call('ship_collision_damage'));eq(2,'d0')
    case('Missile inflicts 40 damage: Cobra survives once, kill on second; station immune')
    emit(' lea objects(a6),a4\n clr.w flags(a4)\n move.w #cobra,type(a4)\n move.w #72,health(a4)\n'+call('ship_missile_damage'));eq(0,'d0');eq(32,'health(a4)')
    emit(call('ship_missile_damage'));eq(1,'d0');eq(0,'health(a4)')
    emit(' move.w #spacestn,type(a4)\n move.w #72,health(a4)\n'+call('ship_missile_damage'));eq(0,'d0');eq(72,'health(a4)')
    case('Save and reload retain hull, rewards, fuel, cash and registration')
    hull(8);emit(' move.w #12,equip+missiles(a6)\n move.w #96,equip+fuel(a6)\n move.l #$53485031,player_ship_tag(a6)\n'+call('save_state'))
    hull(10);emit(' clr.w equip+missiles(a6)\n'+call('restore_state'));eq(8,'player_ship(a6)');eq(12,'equip+missiles(a6)');eq(96,'equip+fuel(a6)');eq(16,'hull_missiles(a6)')
    tail='''
qa_world:
 lea equip(a6),a0
 moveq #16,d7
.equip:
 clr.w (a0)+
 dbra d7,.equip
 move.w #$8000,equip+pulse_lasers(a6)
 move.w #$8000,equip+beam_lasers(a6)
 move.w #$8000,equip+mining_lasers(a6)
 move.w #$8000,equip+military_lasers(a6)
 lea hold(a6),a0
 moveq #max_products-1,d7
.hold:
 clr.l (a0)+
 dbra d7,.hold
 move.l #10000000,cash(a6)
 clr.w player_ship(a6)
 clr.w equip_sell_mode(a6)
 move.w #1,docked(a6)
'''+call('ship_apply')+''' rts
qa_case: dc.w 0
'''
    return prefix,''.join(parts),tail,names
