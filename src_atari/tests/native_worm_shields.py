"""Verify the energy-only escape capsule, damage, recharge and slot reuse."""
from native_missile_collision import make_suite as base_suite


def make_suite(root, s):
    prefix, _, tail, _ = base_suite(root, s)
    out, names = [], []
    emit = out.append
    call = lambda name: f' jsr ${s[name]:x}\n'
    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n')
    def eq(value, field):
        emit(f' cmp.w #{value},{field}\n bne fail\n')
    def victim():
        emit(' lea objects+obj_len*3(a6),a4\n')
    def spawn(model='worm'):
        victim()
        emit(f' move.b #1,flags(a4)\n move.w #{model},type(a4)\n'+call('create_object'))
        emit(' move.w #log_cruise,logic(a4)\n move.l #1000,zpos(a4)\n')
    def unshielded():
        for field in ('ai_front', 'ai_aft', 'ai_front_fraction', 'ai_aft_fraction', 'shield_flash'):
            eq(0, field+'(a4)')
    case('New Worm has 96 energy, no shield stores or flash, unchanged weapon resistance')
    spawn();unshielded()
    for value, field in ((96,'health'),(96,'pre_attack'),(42,'ai_strength'),(77,'ai_missile_strength'),(0,'ai_energy_unit')):
        eq(value,field+'(a4)')
    case('Reused shielded hull loses both shields, fractions, unit and flash when becoming Worm')
    spawn('cobra')
    emit(' move.w #123,ai_front_fraction(a4)\n move.w #456,ai_aft_fraction(a4)\n move.w #789,ai_energy_fraction(a4)\n move.w #2,ai_energy_unit(a4)\n move.w #1,shield_flash(a4)\n move.w #worm,type(a4)\n'+call('create_object'))
    unshielded();eq(0,'ai_energy_fraction(a4)');eq(0,'ai_energy_unit(a4)');eq(96,'health(a4)')
    case('Copy of a shielded ship becomes an unshielded Worm without changing its parent')
    spawn('cobra')
    emit(' move.l a4,a5\n'+call('alloc_object')+' bcc fail\n'+call('copy_object')+' move.w #worm,type(a4)\n'+call('create_object'))
    unshielded();eq(96,'health(a4)');eq(24,'objects+obj_len*3+ai_front(a6)');eq(24,'objects+obj_len*3+ai_aft(a6)')
    case('A Worm slot reused for a Cobra receives full shields again')
    spawn();emit(' move.w #cobra,type(a4)\n'+call('create_object'))
    eq(24,'ai_front(a4)');eq(24,'ai_aft(a4)');eq(96,'health(a4)')
    for unit,period in ((0,24),(1,15),(2,9)):
        case(f'Energy unit {unit}: 720 actual recharge frames never create shields, even at full energy')
        spawn();emit(f' move.w #{unit},ai_energy_unit(a4)\n move.w #90,health(a4)\n move.w #32768,ai_energy_fraction(a4)\n'+call('ship_ai_recharge'))
        eq(91,'health(a4)');eq(32768,'ai_energy_fraction(a4)');eq(period,'ai_charge_count(a4)');unshielded()
        label=f'qa_worm_charge_{unit}'
        emit(f' move.w #719,d6\n{label}:\n'+call('ship_ai_recharge'))
        unshielded();emit(f' dbra d6,{label}\n')
        eq(96,'health(a4)');eq(0,'ai_energy_fraction(a4)')
    for state in ('dead','exploding','removed'):
        case(f'{state} Worm does not recharge or grow shields')
        spawn();emit(' clr.w health(a4)\n' if state=='dead' else ' move.w #90,health(a4)\n')
        if state=='exploding':emit(' move.w #log_exploding,logic(a4)\n')
        if state=='removed':emit(' bset #remove,flags(a4)\n')
        emit(call('ship_ai_recharge'));unshielded();eq(0 if state=='dead' else 90,'health(a4)')
    for rear in (False,True):
        for attacker in ('player','NPC'):
            for power,hits in ((5,6),(7,4),(9,3),(11,3),(60,1)):
                case(f'{attacker} power {power}, {"aft" if rear else "front"}: destroyed by hit {hits}, no shield flash')
                spawn();emit(f' move.w #{"unit" if rear else "-unit"},z_vector+k(a4)\n')
                label=f'qa_worm_hits_{len(names)}'
                emit(f' move.w #{hits-1},d6\n{label}:\n')
                emit(' suba.l a0,a0\n' if attacker=='player' else ' lea objects+obj_len*4(a6),a0\n')
                emit(f' moveq #{power},d0\n'+call('ship_ai_missile_damage' if power==60 else 'ship_ai_damage'))
                emit(f' tst.w d6\n beq.s {label}_last\n tst.w d0\n bne fail\n bra.s {label}_check\n{label}_last:\n cmp.w #1,d0\n bne fail\n{label}_check:\n')
                unshielded();emit(f' dbra d6,{label}\n');eq(0,'health(a4)')
    for rear in (False,True):
        case(f'Collision from {"aft" if rear else "front"} does not flash an unshielded capsule')
        spawn();emit(f' move.w #{"unit" if rear else "-unit"},z_vector+k(a4)\n move.l a4,a5\n'+call('ship_collision_flash'));unshielded();eq(96,'health(a4)')
    return prefix, ''.join(out), tail, names
