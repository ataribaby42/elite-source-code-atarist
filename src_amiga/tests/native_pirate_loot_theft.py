"""Execute successful/failed player scoops and encounter-only retaliation."""
from native_pirate_loot import make_suite as helpers


def make_suite(root, s):
    prefix, _, tail, _ = helpers(root, s)
    call = lambda n: f' jsr ${s[n]:x}\n'
    body = call('gen_prices')
    names = []

    def emit(text):
        nonlocal body
        body += text

    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_theft_world\n')

    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')

    def scoop(change=''):
        emit(' lea objects+5*obj_len(a6),a5\n move.l #100,zpos(a5)\n move.l #-20,ypos(a5)\n'+change+call('salvage'))

    def angry(slot):
        emit(f' lea objects+{slot}*obj_len(a6),a5\n')
        eq(0, 'loot_mode(a5)'); eq('log_attack', 'logic(a5)')
        eq(0, 'target(a5)', 'l'); eq(0, 'pirate_truce(a5)')
        eq(0, 'loot_target(a5)', 'l')
        emit(' btst #angry,flags(a5)\n beq fail\n')

    def peaceful(slot):
        eq('loot_encounter', f'objects+{slot}*obj_len+loot_mode(a6)')
        eq('log_loot', f'objects+{slot}*obj_len+logic(a6)')
        eq('no_target', f'objects+{slot}*obj_len+target(a6)', 'l')

    for commodity in range(16):
        case(f'Successful commodity {commodity} scoop immediately angers both group members, including Scramble ID')
        scoop(f' move.w #{commodity},cargo_type(a5)\n')
        emit(f' tst.l hold+{commodity*4}(a6)\n beq fail\n')
        angry(3); angry(4); peaceful(7)
        eq(0, 'objects+5*obj_len+loot_owner(a6)', 'l')
        eq(0, 'objects+6*obj_len+loot_owner(a6)', 'l')
        eq(0, 'police_record(a6)')

    case('Exact payload pickup transfers every gram and provokes both members')
    scoop(' move.l #123456,cargo_mass(a5)\n')
    eq(123456, 'hold+4(a6)', 'l'); angry(3); angry(4)

    for name, change in (
        ('full hold', ' move.l #20000000,hold(a6)\n'),
        ('exact payload exceeds remaining room', ' move.l #19999900,hold(a6)\n move.l #101,cargo_mass(a5)\n'),
        ('no scoop equipment', ' clr.w equip+fuel_scoop(a6)\n'),
        ('container behind player', ' move.l #-100,zpos(a5)\n'),
        ('container above player', ' move.l #20,ypos(a5)\n'),
    ):
        case('Failed scoop leaves both pirates and their reservations alone: '+name)
        scoop(change)
        eq(0, 'hold+4(a6)', 'l'); peaceful(3); peaceful(4)
        emit(' btst #remove,flags(a5)\n bne fail\n tst.l objects+3*obj_len+loot_target(a6)\n beq fail\n tst.l objects+4*obj_len+loot_target(a6)\n beq fail\n')

    for mode in ('loot_encounter', 'loot_departing', 'combat'):
        case('Theft angers a group member in state '+mode)
        if mode == 'loot_departing':
            emit(' lea objects+4*obj_len(a6),a5\n'+call('loot_finish'))
        elif mode == 'combat':
            emit(' lea objects+4*obj_len(a6),a4\n lea objects+9*obj_len(a6),a0\n'+call('loot_hit'))
        scoop(); angry(3); angry(4)

    case('Unreserved encounter cargo still provokes the entire group')
    emit(' lea objects+3*obj_len(a6),a5\n'+call('loot_release'))
    scoop(); angry(3); angry(4)

    for state in ('destroyed', 'removed', 'recycled', 'police'):
        case('Theft skips group records that are '+state)
        emit(' lea objects+4*obj_len(a6),a4\n')
        if state == 'destroyed': emit(' st npc_kill(a6)\n'+call('explode_object')+' clr.w npc_kill(a6)\n')
        elif state == 'removed': emit(' bset #remove,flags(a4)\n')
        elif state == 'recycled': emit(call('create_object'))
        else: emit(' move.w #typ_police,ship_type(a4)\n')
        scoop(); angry(3)
        if state == 'destroyed': eq('log_exploding', 'objects+4*obj_len+logic(a6)')
        elif state == 'recycled': eq(0, 'objects+4*obj_len+loot_group(a6)', 'l')
        else: peaceful(4)

    for provenance in ('ordinary', 'wreck', 'other encounter'):
        case('Scooping '+provenance+' cargo does not provoke unrelated group members')
        change = ' clr.l loot_group(a5)\n'
        if provenance == 'wreck': change += ' move.l #$1234,loot_origin(a5)\n'
        if provenance == 'other encounter': change = ' move.l #$5678,loot_group(a5)\n'
        scoop(change); peaceful(3); peaceful(4)
        if provenance == 'other encounter': angry(7)
        else: peaceful(7)

    case('NPC collection never triggers group theft retaliation')
    emit(' move.l #10080,objects+5*obj_len+zpos(a6)\n lea objects+3*obj_len(a6),a5\n'+call('do_logic'))
    eq(1, 'loot_count(a5)'); peaceful(3); peaceful(4)

    case('After theft, Vipers still acquire the hostile pirate faction')
    scoop()
    emit(' lea objects+9*obj_len(a6),a5\n move.w #9,this_obj(a6)\n move.w #9,retarget_slot(a6)\n'+call('retarget'))
    eq('log_attack', 'logic(a5)')
    emit(' move.l target(a5),a0\n cmpa.l #0,a0\n beq fail\n cmpa.l #no_target,a0\n beq fail\n cmp.w #typ_pirate,ship_type(a0)\n bne fail\n')

    case('Real maximum-size encounter: first player scoop angers both spawned pirates immediately')
    emit(' bsr qa_world\n st qa_force_cargo\n move.w #4,qa_cargo_roll\n move.w #1,qa_small_left\n move.w #1,qa_small_second\n')
    r=s['rand']
    emit(f' move.l ${r:x},qa_saved_rand\n move.w ${r+4:x},qa_saved_rand+4\n move.w #$4ef9,${r:x}\n move.l #qa_rand,${r+2:x}\n'+call('spawn_loot_encounter')+f' move.l qa_saved_rand,${r:x}\n move.w qa_saved_rand+4,${r+4:x}\n')
    eq(8, 'obj_ctr+barrel(a6)', 'b'); eq(2, 'pirate_count(a6)')
    emit(' lea objects+3*obj_len(a6),a5\n move.l #100,zpos(a5)\n move.l #-20,ypos(a5)\n'+call('salvage'))
    angry(11); angry(12)

    case('Removing the first cargo and reusing its slot does not erase the encounter identity')
    emit(' lea objects+5*obj_len(a6),a4\n bset #remove,flags(a4)\n'+call('remove_objects')+' move.w #barrel,type(a4)\n'+call('create_object')+' lea objects+6*obj_len(a6),a5\n move.l #100,zpos(a5)\n move.l #-20,ypos(a5)\n'+call('salvage'))
    angry(3); angry(4)

    tail += '''qa_theft_world:
 bsr qa_world
 lea hold(a6),a0
 moveq #max_products-1,d7
.hold:
 clr.l (a0)+
 dbra d7,.hold
 move.w #1,equip+fuel_scoop(a6)
 clr.w equip+cargo_bay(a6)
 clr.w police_record(a6)
'''+call('ship_equipment_mass')+''' add.w #20,d0
 move.w d0,hull_cargo(a6)
'''
    for slot, model, x, z, group in (
        (3,'krait',0,10000,0x1234), (4,'gecko',500,10000,0x1234),
        (5,'barrel',0,11000,0x1234), (6,'barrel',500,11000,0x1234),
        (7,'mamba',-500,10000,0x5678), (9,'viper',700,10500,0),
    ):
        tail += f' lea objects+{slot}*obj_len(a6),a4\n move.w #{model},d0\n move.l #{x},d4\n moveq #0,d5\n move.l #{z},d6\n bsr qa_create\n move.l #${group:x},loot_group(a4)\n'
        if model in ('krait', 'gecko', 'mamba'):
            tail += ' move.w #loot_encounter,loot_mode(a4)\n move.w #log_loot,logic(a4)\n move.w #17,pirate_truce(a4)\n'
        if model=='barrel': tail += ' move.w #1,cargo_type(a4)\n'
    for slot in (3,4):
        tail += f' lea objects+{slot}*obj_len(a6),a5\n move.w #{slot},this_obj(a6)\n move.w #{slot},retarget_slot(a6)\n'+call('retarget')
    tail += ' rts\n'
    return prefix, body, tail, names
