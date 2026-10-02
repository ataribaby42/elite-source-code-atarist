"""Execute player/AI parity and mission regressions against the linked 68000 game."""
import importlib.util


def make_suite(root, s):
    spec = importlib.util.spec_from_file_location('missile_cases', root/'tests/native_missile_collision.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    prefix, _, tail, _ = old.make_suite(root, s)
    out, names = [], []
    def emit(v): out.append(v)
    def call(n): return f' jsr ${s[n]:x}\n'
    def case(n):
        names.append(n)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n')
    def eq(v, f, size='w'): emit(f' cmp.{size} #{v},{f}\n bne fail\n')
    def spawn(model, slot=3):
        emit(f' lea objects+obj_len*{slot}(a6),a4\n move.b #1,flags(a4)\n move.w #{model},type(a4)\n'+call('create_object'))
        emit(' move.w #log_cruise,logic(a4)\n move.l #no_target,target(a4)\n')
    def victim(): emit(' lea objects+obj_len*3(a6),a4\n')
    def laser_hit():
        emit(' move.l a4,a5\n move.w #1,hit_check(a6)\n move.w #1,in_sights(a6)\n clr.w obj_hit(a6)\n move.l #1,this_zpos(a5)\n clr.l this_xpos(a5)\n clr.l this_ypos(a5)\n'+call('check_hit'))
    models=['cobra','adder','gecko','moray','cobra_mk1','ferdelance','python','boa','anaconda','asp','sidewinder','krait','mamba']
    pulse=[11,6,5,7,7,11,17,17,17,11,5,6,7]
    strength=[n*14 for n in pulse]
    missile_hits=[2,2,1,2,2,2,4,4,4,2,1,1,1]
    speed=[22,19,24,20,20,24,16,19,11,31,29,24,25]
    roll=[40,34,40,40,28,34,16,22,16,34,41,34,40]
    pitch=[40,34,40,40,29,34,17,23,17,34,40,34,40]
    missiles=[4,1,2,2,3,3,4,6,16,1,1,0,2]
    for n, model in enumerate(models):
        case(f'{model}: shared resistance, recharge, speed, roll, pitch and missile capacity')
        spawn(model)
        for f,v in [('ai_strength',strength[n]),('ai_missile_strength',missile_hits[n]*77),('ai_recharge',2 if n==5 else 1),('vel_max',speed[n]),('ai_roll',roll[n]),('turn_rate',pitch[n]),('no_missiles',missiles[n]),('ai_energy_unit',0),('health',96),('pre_attack',96),('ai_front',24),('ai_aft',24),('ai_charge_count',1)]: eq(v,f'{f}(a4)')
        for power in (5,7,9,11,60):
            for rear in (False,True):
                case(f'{model}: every {power}-point hit matches player, {"aft" if rear else "front"}, including lethal hit')
                spawn(model)
                # The player's attacker is +/-Z; place the AI victim opposite it,
                # facing +Z, so a player at the origin hits the same shield.
                emit(f' move.w #{strength[n]},hull_laser_resistance(a6)\n move.w #{missile_hits[n]*77},hull_missile_resistance(a6)\n move.l #{1000 if rear else -1000},zpos(a4)\n move.w #$4000,z_vector+k(a4)\n lea objects+obj_len*4(a6),a5\n move.w #cobra,type(a5)\n move.l #{-1000 if rear else 1000},zpos(a5)\n')
                resistance=missile_hits[n]*77 if power==60 else strength[n]
                scaled=(power*154*65536+resistance-1)//resistance
                hits=(120*65536+scaled-1)//scaled
                label=f'qa_hits_{len(names)}'
                emit(f' move.w #{hits-1},d6\n{label}:\n move.w d6,-(sp)\n moveq #{power},d0\n'+call('reduce_missile_shields' if power==60 else 'reduce_laser_shields')+' move.w (sp)+,d6\n')
                victim()
                emit(' suba.l a0,a0\n'+f' moveq #{power},d0\n'+call('ship_ai_missile_damage' if power==60 else 'ship_ai_damage'))
                for a,b in [('health(a4)','energy(a6)'),('ai_front(a4)','front_shield(a6)'),('ai_aft(a4)','aft_shield(a6)'),('ai_energy_fraction(a4)','energy_fraction(a6)'),('ai_front_fraction(a4)','front_fraction(a6)'),('ai_aft_fraction(a4)','aft_fraction(a6)')]:emit(f' move.w {a},d1\n cmp.w {b},d1\n bne fail\n')
                emit(f' tst.w d6\n beq.s {label}_last\n tst.w d0\n bne fail\n bra.s {label}_next\n{label}_last:\n cmp.w #1,d0\n bne fail\n{label}_next:\n dbra d6,{label}\n')
                eq(0,'health(a4)')
        for unit in (0,1,2):
            case(f'{model}: 720 flight frames of player/AI recharge match with energy unit {unit}')
            spawn(model)
            grade=2 if n==5 else 1
            emit(f' move.w #{grade},hull_recharge(a6)\n move.w #{unit},equip+energy_unit(a6)\n move.w #{unit},ai_energy_unit(a4)\n move.w #1,recharge_count(a6)\n move.w #90,energy(a6)\n move.w #90,health(a4)\n move.w #19,front_shield(a6)\n move.w #19,ai_front(a4)\n move.w #20,aft_shield(a6)\n move.w #20,ai_aft(a4)\n move.w #719,d6\nqa_charge_{n}_{unit}:\n'+call('recharge'))
            for a,b in [('health(a4)','energy(a6)'),('ai_front(a4)','front_shield(a6)'),('ai_aft(a4)','aft_shield(a6)'),('ai_charge_count(a4)','recharge_count(a6)')]:emit(f' move.w {a},d1\n cmp.w {b},d1\n bne fail\n')
            emit(f' dbra d6,qa_charge_{n}_{unit}\n')
            eq(96,'health(a4)');eq(24,'ai_front(a4)');eq(24,'ai_aft(a4)')
            # Independent expected first tick and period, not just equal stores.
            emit(' move.w #1,recharge_count(a6)\n move.w #90,energy(a6)\n move.w #19,front_shield(a6)\n'+call('recharge'))
            eq(91,'energy(a6)');eq(19 if grade+unit==1 else 20,'front_shield(a6)');eq({1:24,2:15,3:9,4:7}[grade+unit],'recharge_count(a6)')
    for model in ('worm','thargon','viper','wolf','shuttle','transporter','thargoid','cougar','constr'):
        case(f'{model}: AI-only hull uses the agreed weapon ratios and retains original movement and payload')
        spawn(model)
        eq(dict(worm=42,thargon=28,viper=140,wolf=182,shuttle=42,transporter=42,thargoid=238,cougar=1122,constr=1122)[model],'ai_strength(a4)')
        eq(96,'health(a4)');eq(0 if model=='worm' else 24,'ai_front(a4)');eq(0 if model=='worm' else 24,'ai_aft(a4)');eq(0,'ai_energy_unit(a4)')
        # Even sub-point damage kills a hull with only 1/65536 energy remaining.
        emit(' clr.w ai_front(a4)\n clr.w ai_aft(a4)\n move.w #1,health(a4)\n move.w #$ffff,ai_energy_fraction(a4)\n suba.l a0,a0\n moveq #5,d0\n'+call('ship_ai_damage'));eq(1,'d0')
    for model in ('missile','barrel','asteroid','platlet','spacestn','dodec','panels','planet','sun','photon'):
        case(f'{model}: copied object cannot inherit ship shields or energy unit')
        spawn('cobra')
        emit(f' move.w #2,ai_energy_unit(a4)\n move.w #{model},type(a4)\n'+call('create_object'))
        for f in ('ai_strength','ai_missile_strength','ai_front','ai_aft','ai_energy_unit','ai_energy_fraction','ai_front_fraction','ai_aft_fraction'):eq(0,f'{f}(a4)')
    for axis in ('i','j','k'):
        for sign in (-1,1):
            case(f'Victim-oriented {axis} axis {sign}: NPC attacker selects the correct shield')
            spawn('cobra');spawn('adder',4)
            emit(' move.l a4,a0\n');victim()
            emit(' clr.l z_vector(a4)\n clr.w z_vector+k(a4)\n')
            emit(f' move.w #{sign*16384},z_vector+{axis}(a4)\n move.l #$40000000,{dict(i="xpos",j="ypos",k="zpos")[axis]}(a0)\n moveq #5,d0\n'+call('ship_ai_damage'))
            eq(19 if sign==1 else 24,'ai_front(a4)');eq(24 if sign==1 else 19,'ai_aft(a4)')
    for rating in range(9):
        case(f'Rating {rating}: cached AI laser class equals player power against either victim')
        emit(f' move.w #{rating},rating(a6)\n'+call('init_ai_laser_colour'))
        spawn('cobra');emit(' move.l a4,a5\n'+call('ai_laser_power'));eq(5 if rating<3 else 9 if rating<6 else 11,'d0')
        emit(' move.w #8,rating(a6)\n'+call('ai_laser_power'));eq(5 if rating<3 else 9 if rating<6 else 11,'d0')
        emit(' move.w #constr,type(a5)\n'+call('ai_laser_power'));eq(11,'d0')
    for rating,power in ((0,5),(3,9),(6,11)):
        for npc in (False,True):
            case(f'Actual AI attack at rating {rating}: accepted hits deal {power} to {"NPC" if npc else "player"}, misses deal zero')
            spawn('cobra');spawn('cobra',4)
            emit(f' move.w #{rating},rating(a6)\n'+call('init_ai_laser_colour'))
            label=f'qa_shots_{rating}_{int(npc)}'
            emit(' clr.w cloaking_on(a6)\n move.w #7,hull_strength(a6)\n clr.w qa_accepted\n moveq #23,d6\n'+label+':\n lea objects+obj_len*4(a6),a5\n move.l #1000,zpos(a5)\n move.w #255,mood(a5)\n move.l #1000,obj_range(a5)\n move.w #log_attack,logic(a5)\n clr.l z_vector(a5)\n move.w #-unit,z_vector+k(a5)\n clr.w ai_laser(a5)\n move.w #24,front_shield(a6)\n lea objects+obj_len*3(a6),a4\n move.w #24,ai_front(a4)\n move.w #unit,z_vector+k(a4)\n')
            emit(' move.l a4,target(a5)\n' if npc else ' clr.l target(a5)\n')
            emit(' move.w d6,-(sp)\n'+call('do_attack')+' move.w (sp)+,d6\n moveq #24,d0\n cmp.w #2,ai_laser(a5)\n'+f' bne.s {label}_check\n addq.w #1,qa_accepted\n sub.w #{power},d0\n{label}_check:\n')
            field='objects+obj_len*3+ai_front(a6)' if npc else 'front_shield(a6)'
            emit(f' cmp.w {field},d0\n bne fail\n dbra d6,{label}\n tst.w qa_accepted\n beq fail\n')
    for distance, threshold in ((1,20),(1000,20),(2000,30),(3000,40),(4000,50),(5000,60),(6000,80),(7000,100),(12288,100)):
        case(f'Original AI accuracy: distance {distance} retains miss threshold {threshold}/200')
        emit(f' move.l #{distance},target_range(a6)\n'+call('ai_laser_miss_threshold'));eq(threshold,'d2')
    for vector, expected in ((14562,0),(14563,1),(15927,1),(15928,2),(16384,2),(-16384,0)):
        case(f'Original AI aim cones: forward dot factor {vector} gives {expected}')
        spawn('cobra');emit(f' move.l a4,a5\n clr.l target(a5)\n move.l #-1000,zpos(a5)\n clr.l z_vector(a5)\n move.w #{vector},z_vector+k(a5)\n move.l #1000,target_range(a6)\n'+call('ai_laser_aim'));eq(expected,'d0')
    for distance in (0,12289):
        case(f'Original AI range: distance {distance} cannot fire')
        spawn('cobra');emit(f' move.l a4,a5\n clr.l target(a5)\n move.l #{-distance},zpos(a5)\n move.w #16384,z_vector+k(a5)\n move.l #{distance},target_range(a6)\n'+call('ai_laser_aim'));eq(0,'d0')
    for n in (4,6,7,8,10):
        case(f'{models[n]}: AI peel-off uses separate player roll and pitch limits')
        spawn(models[n]);emit(' move.l a4,a5\n'+call('start_peel_off'))
        for f,v in [('peel_x',pitch[n]),('peel_z',roll[n])]:
            emit(f' move.w {f}(a5),d0\n bpl.s qa_abs_{n}_{f}\n neg.w d0\nqa_abs_{n}_{f}:\n');eq(v,'d0')
    case('Destroyed and removed ships never recharge; independent countdowns do not block living ships')
    for slot in (3,4,5):
        spawn('cobra',slot);emit(' move.w #90,health(a4)\n')
    emit(' move.w #log_exploding,objects+obj_len*3+logic(a6)\n bset #remove,objects+obj_len*4+flags(a6)\n'+call('ship_ai_recharge'))
    eq(90,'objects+obj_len*3+health(a6)');eq(90,'objects+obj_len*4+health(a6)');eq(91,'objects+obj_len*5+health(a6)')
    case('Lethal player hit cannot be reversed by recharge before game-over detection')
    emit(' clr.w energy(a6)\n move.w #1,recharge_count(a6)\n move.w #48,altitude(a6)\n clr.w cabin_temp(a6)\n'+call('recharge')+call('is_game_over'))
    eq(0,'energy(a6)');emit(' tst.w game_over(a6)\n beq fail\n')
    eq('no_energy','reason(a6)')
    case('AI laser finishing hit gives no player score, bounty or police penalty')
    spawn('cobra');emit(' clr.w ai_front(a4)\n clr.w ai_aft(a4)\n move.w #5,health(a4)\n');spawn('adder',4)
    emit(' move.l a4,a5\n lea objects+obj_len*3(a6),a0\n move.l a0,target(a5)\n moveq #5,d0\n'+call('damage_target'))
    eq('log_exploding','objects+obj_len*3+logic(a6)');eq(0,'score(a6)','l');eq(0,'npc_kill(a6)')
    emit(' btst #no_bounty,objects+obj_len*3+flags(a6)\n beq fail\n')
    for source in ('player laser','NPC laser','player missile','NPC missile'):
        case(f'Thargoid killed by {source}: only its own Thargons become dormant')
        spawn('thargoid');emit(' clr.w ai_front(a4)\n clr.w ai_aft(a4)\n move.w #1,health(a4)\n move.w #$ffff,ai_energy_fraction(a4)\n clr.w ecm_fitted(a4)\n')
        for slot,mother in ((5,3),(6,7)):
            spawn('thargon',slot);emit(f' move.w #{mother},mother(a4)\n move.w #log_attack,logic(a4)\n')
        spawn('thargoid',7)
        if source=='player laser':
            victim();emit(' move.w #11,laser_power(a6)\n');laser_hit()
        elif source=='NPC laser':
            spawn('cobra',4);emit(' move.l a4,a5\n lea objects+obj_len*3(a6),a0\n move.l a0,target(a5)\n moveq #11,d0\n'+call('damage_target'))
        else:
            emit(' bsr qa_missile\n lea objects+obj_len*3(a6),a4\n move.l #$10000,zpos(a4)\n move.l a4,target(a5)\n')
            emit(f' move.w #{"log_locked" if source=="player missile" else "log_ai_missile"},logic(a5)\n'+call('do_locked'))
        eq('log_exploding','objects+obj_len*3+logic(a6)');eq('log_cruise','objects+obj_len*5+logic(a6)');eq('act_nothing','objects+obj_len*5+attack_type(a6)');eq('log_attack','objects+obj_len*6+logic(a6)')
    case('Thargoid launch initializes every child independently and remembers its mother')
    spawn('thargoid');emit(' move.l a4,a5\n move.w #3,this_obj(a6)\n move.w #2,ai_energy_unit(a5)\n clr.w ai_front(a5)\n'+call('thargons'))
    emit(' moveq #0,d6\n lea objects(a6),a4\n moveq #max_objects-1,d7\nqa_children:\n cmp.w #thargon,type(a4)\n bne.s qa_child_next\n btst #in_use,flags(a4)\n beq.s qa_child_next\n addq.w #1,d6\n')
    eq(3,'mother(a4)');eq(96,'health(a4)');eq(24,'ai_front(a4)');eq(0,'ai_energy_unit(a4)')
    emit('qa_child_next:\n lea obj_len(a4),a4\n dbra d7,qa_children\n cmp.w #4,d6\n blo fail\n cmp.w #7,d6\n bhi fail\n')
    for model,mission,nextstate in [('constr',0x15,0x16),('dodec',0x52,0x53)]:
        case(f'{model}: laser destruction advances the active mission exactly once')
        spawn(model);emit(f' move.w #{mission},mission(a6)\n clr.w ai_front(a4)\n clr.w ai_aft(a4)\n move.w #1,health(a4)\n move.w #$ffff,ai_energy_fraction(a4)\n move.w #11,laser_power(a6)\n');laser_hit();eq(nextstate,'mission(a6)')
        victim();emit(call('explode_object'));eq(nextstate,'mission(a6)')
    case('Mission-2 invincible Constrictor ignores both weapon damage paths')
    spawn('constr');emit(' bset #invincible,flags(a4)\n suba.l a0,a0\n moveq #60,d0\n'+call('ship_ai_damage'));eq(0,'d0');eq(96,'health(a4)');eq(24,'ai_front(a4)')
    emit(' move.l a4,a5\n'+call('ship_missile_damage'));eq(0,'d0');eq(96,'health(a4)')
    case('Energy bomb keeps Thargoid and both mission hulls immune, destroys ordinary ships')
    for slot,model in enumerate(('thargoid','constr','cougar','cobra'),3):spawn(model,slot)
    emit(' move.w #1,equip+energy_bomb(a6)\n'+call('launch_bomb'))
    for slot in (3,4,5):eq('log_cruise',f'objects+obj_len*{slot}+logic(a6)')
    eq('log_exploding','objects+obj_len*6+logic(a6)')
    case('Witch-space drive repair counts a removed Thargoid, not its Thargon')
    spawn('thargoid');spawn('thargon',4)
    emit(' move.w #1,witch_space(a6)\n move.w #2,tharg_count(a6)\n bset #remove,objects+obj_len*3+flags(a6)\n bset #remove,objects+obj_len*4+flags(a6)\n'+call('remove_objects'));eq(1,'tharg_count(a6)')
    return prefix, ''.join(out), tail+'qa_accepted: dc.w 0\n', names
