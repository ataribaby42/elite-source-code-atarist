"""Verify Unbound-relative weapon durability and retained fractional damage."""
from native_missile_collision import make_suite as base_suite

# User-supplied Pulse and missile impact counts; None denotes a mission hull.
HULLS = [('cobra',11,2),('adder',6,2),('gecko',5,1),('moray',7,2),
         ('cobra_mk1',7,2),('ferdelance',11,2),('python',17,4),('boa',17,4),
         ('anaconda',17,4),('asp',11,2),('sidewinder',5,1),('krait',6,1),
         ('mamba',7,1),('worm',3,1),('thargon',2,1),('viper',10,2),
         ('wolf',13,3),('shuttle',3,1),('transporter',3,1),('thargoid',17,3),
         ('cougar',None,4),('constr',None,4)]


def make_suite(root,s):
    prefix,_,tail,_=base_suite(root,s)
    out,names=[],[]
    def emit(code):out.append(code)
    def call(name):return f' jsr ${s[name]:x}\n'
    def eq(value,field,size='w'):emit(f' cmp.{size} #{value},{field}\n bne fail\n')
    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n')
    def victim():emit(' lea objects+obj_len*3(a6),a4\n')
    def spawn(model='cougar'):
        victim()
        emit(f' move.b #1,flags(a4)\n move.w #{model},type(a4)\n'+call('create_object'))
        emit(' move.l #1000,zpos(a4)\n move.w #-unit,z_vector+k(a4)\n move.w #log_cruise,logic(a4)\n')
    def laser(power):emit(f' suba.l a0,a0\n moveq #{power},d0\n'+call('ship_ai_damage'))
    def stores(energy=96,front=24,aft=24,ef=0,ff=0,af=0):
        for field,value in [('health',energy),('ai_front',front),('ai_aft',aft),('ai_energy_fraction',ef),('ai_front_fraction',ff),('ai_aft_fraction',af)]:eq(value,field+'(a4)')
    for model,pulse,missiles in HULLS:
        resistance=14*pulse if pulse is not None else 51*22
        for power,weapon in [(5,'Pulse'),(7,'Mining'),(9,'Beam'),(11,'Military'),(60,'missile')]:
            scale=missiles*77 if power==60 else resistance
            damage=(power*154*65536+scale-1)//scale
            hits=((96 if model=="worm" else 120)*65536+damage-1)//damage
            case(f'{model}: {hits} {weapon} hits destroy the full ship, with no recharge')
            spawn(model)
            emit(' lea objects+obj_len*4(a6),a5\n move.w #missile,type(a5)\n')
            eq(resistance,'ai_strength(a4)');eq(missiles*77,'ai_missile_strength(a4)')
            label=f'qa_impacts_{len(names)}'
            emit(f' move.w #{hits-1},qa_left\n{label}:\n')
            if power==60:emit(call('ship_missile_damage'))
            else:laser(power)
            emit(f' tst.w qa_left\n beq.s {label}_last\n tst.w d0\n bne fail\n subq.w #1,qa_left\n bra {label}\n{label}_last:\n')
            eq(1,'d0');eq(0,'health(a4)');eq(0,'ai_energy_fraction(a4)');eq(0,'ai_front(a4)');eq(0,'ai_front_fraction(a4)');eq(0 if model=='worm' else 24,'ai_aft(a4)')
    weak=(5*154*65536+1121)//1122
    case('Sub-point hits still flash the shield and preserve separate front/aft fractions')
    spawn();laser(5);stores(ff=weak);eq(1,'shield_flash(a4)')
    emit(' move.w #unit,z_vector+k(a4)\n');laser(5);stores(ff=weak,af=weak)
    emit(' move.w #-unit,z_vector+k(a4)\n');laser(5);stores(front=23,ff=2*weak-65536,af=weak)
    case('Fractional overflow from the struck shield reaches the energy banks exactly')
    spawn();emit(' move.w #1,ai_front(a4)\n move.w #32768,ai_front_fraction(a4)\n');laser(5)
    stores(front=0,ef=weak-32768)
    case('A missile after a fractional laser hit retains the earlier shield damage')
    spawn();laser(5)
    emit(' lea objects+obj_len*4(a6),a5\n'+call('ship_missile_damage'))
    stores(energy=90,front=0,ef=weak)
    case('Slow recharge fills a fractional energy deficit before charging shields')
    spawn();emit(' move.w #95,health(a4)\n move.w #32768,ai_energy_fraction(a4)\n move.w #20,ai_front(a4)\n move.w #32768,ai_front_fraction(a4)\n bsr qa_charge\n')
    stores(energy=96,front=20,ef=32768,ff=32768)
    emit(' bsr qa_charge\n');stores(front=21,ff=32768)
    case('Fractional shield recharge reaches the exact maximum without overflow')
    spawn();emit(' move.w #23,ai_front(a4)\n move.w #32768,ai_front_fraction(a4)\n bsr qa_charge\n');stores(ff=32768)
    emit(' bsr qa_charge\n');stores()
    case('Fast recharge advances energy and shields together and retains sub-point debts')
    spawn();emit(' move.w #2,ai_recharge(a4)\n move.w #95,health(a4)\n move.w #32768,ai_energy_fraction(a4)\n move.w #23,ai_front(a4)\n move.w #32768,ai_front_fraction(a4)\n bsr qa_charge\n')
    stores(ef=32768,ff=32768)
    emit(' bsr qa_charge\n');stores()
    for model in ['cobra','cougar','missile','barrel','thargon']:
        case(f'Reused slot becomes {model}: all fractional damage and the flash reset')
        spawn();emit(' move.w #123,ai_energy_fraction(a4)\n move.w #456,ai_front_fraction(a4)\n move.w #789,ai_aft_fraction(a4)\n move.w #1,shield_flash(a4)\n')
        emit(f' move.w #{model},type(a4)\n'+call('create_object'))
        for field in ['ai_energy_fraction','ai_front_fraction','ai_aft_fraction','shield_flash']:eq(0,field+'(a4)')
    case('Copying a damaged parent does not copy its fractional damage into the child')
    spawn();laser(5);emit(' move.l a4,a5\n'+call('alloc_object')+' bcc fail\n'+call('copy_object')+call('create_object'))
    stores();victim();stores(ff=weak)
    case('Invincible hulls and zero-power hits retain their original fractions and do not flash')
    spawn();emit(' move.w #123,ai_energy_fraction(a4)\n move.w #456,ai_front_fraction(a4)\n bset #invincible,flags(a4)\n');laser(60);stores(ef=123,ff=456);eq(0,'shield_flash(a4)')
    emit(' bclr #invincible,flags(a4)\n');laser(0);stores(ef=123,ff=456);eq(0,'shield_flash(a4)')
    case('Fresh player hull and a system reset clear all fractional damage')
    emit(' move.w #123,energy_fraction(a6)\n move.w #456,front_fraction(a6)\n move.w #789,aft_fraction(a6)\n'+call('ship_apply'))
    for f in ['energy_fraction','front_fraction','aft_fraction']:eq(0,f+'(a6)')
    emit(' move.w #123,energy_fraction(a6)\n move.w #456,front_fraction(a6)\n move.w #789,aft_fraction(a6)\n'+call('reset_system'))
    for f in ['energy_fraction','front_fraction','aft_fraction']:eq(0,f+'(a6)')
    tail+='qa_left: dc.w 0\nqa_charge:\n move.w #1,ai_charge_count(a4)\n'+call('ship_ai_recharge')+' rts\n'
    return prefix,''.join(out),tail,names
