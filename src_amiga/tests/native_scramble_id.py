"""Exercise Scramble ID against the linked game in an isolated 68000 emulator."""
from native_player_ships import make_suite as player_suite
from native_missile_collision import make_suite as combat_suite


def make_suite(root, s):
    prefix, _, ptail, _ = player_suite(root, s)
    prefix, _, ctail, _ = combat_suite(root, s)
    tail = ptail.replace('qa_world:', 'qa_player_world:').replace('qa_case: dc.w 0', '') + ctail
    out, names, saved = [], [], []
    emit = out.append
    call = lambda n: f' jsr ${s[n]:x}\n'
    def case(n):
        names.append(n)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n bsr qa_player_world\n'
             ' clr.w mission(a6)\n clr.w police_record(a6)\n clr.w scrambled_id(a6)\n'
             ' clr.w splanet+govern(a6)\n clr.w qa_roll\n clr.w qa_calls\n clr.l random_seed(a6)\n'
             ' move.l #$52494431,registration_tag(a6)\n move.l #$4a532a00,player_registration(a6)\n')
    def eq(v, f, size='w'): emit(f' cmp.{size} #{v},{f}\n bne fail\n')
    def patch(n, label):
        a = s[n]; saved.append(n)
        emit(f' move.l ${a:x},qa_save_{n}\n move.w ${a+4:x},qa_save_{n}+4\n'
             f' move.w #$4ef9,${a:x}\n move.l #{label},${a+2:x}\n')
    def restore(n):
        a = s[n]; emit(f' move.l qa_save_{n},${a:x}\n move.w qa_save_{n}+4,${a+4:x}\n')
    def spawn(model, slot=3):
        emit(f' lea objects+obj_len*{slot}(a6),a4\n move.b #1,flags(a4)\n move.w #{model},type(a4)\n'
             ' move.w #log_cruise,logic(a4)\n' + call('create_object') + ' move.l #1000,obj_range(a4)\n')
    patch('random', 'qa_random')
    for gov in range(8):
        for docked in (0, 1):
            for hidden in (0, 255):
                case(f'Availability: government {gov}, docked {docked}, hidden {hidden}')
                emit(f' move.w #{gov},splanet+govern(a6)\n move.w #{docked},docked(a6)\n'
                     f' move.w #{hidden},scrambled_id(a6)\n' + call('scramble_available'))
                eq(int(gov == 0 and docked and not hidden), 'd0')
    for money in (0, 49999, 50000, 50001, 10000000):
        case(f'Purchase at {money} tenths: exact fee, no inventory or legal changes')
        emit(f' move.l #{money},cash(a6)\n move.w #17,police_record(a6)\n'
             ' move.w #5250,courier_reward(a6)\n' + call('scramble_purchase'))
        eq(1 if money >= 50000 else -1, 'd0')
        eq(money-50000 if money >= 50000 else money, 'cash(a6)', 'l')
        eq(255 if money >= 50000 else 0, 'scrambled_id(a6)')
        eq(17, 'police_record(a6)'); eq(5250, 'courier_reward(a6)')
        eq('$4a532a00', 'player_registration(a6)', 'l')
        if money >= 50000:
            emit(call('scramble_purchase')); eq(0, 'd0'); eq(money-50000, 'cash(a6)', 'l')
    case('Purchase is revalidated: unavailable outside Anarchy and in flight')
    for field in ('splanet+govern', 'docked'):
        emit(f' move.w #{1 if field.startswith("splanet") else 0},{field}(a6)\n' + call('scramble_purchase'))
        eq(0, 'd0'); eq(10000000, 'cash(a6)', 'l'); eq(0, 'scrambled_id(a6)')
        emit(' clr.w splanet+govern(a6)\n')
    for tag, value in ((0,255),('$53494431',255),('$53494431',0),('$53494431',1),('$53494431',-1)):
        case(f'Save validation: tag {tag}, flag {value}')
        emit(f' move.l #{tag},scramble_tag(a6)\n move.w #{value},scrambled_id(a6)\n' + call('scramble_validate'))
        eq(255 if tag and value == 255 else 0, 'scrambled_id(a6)'); eq('$53494431', 'scramble_tag(a6)', 'l')
    for hidden in (0,255):
        case(f'Player ID formatting: hidden {hidden}, underlying registration unchanged')
        emit(f' move.w #{hidden},scrambled_id(a6)\n lea qa_buffer,a1\n' + call('registration_player_format'))
        eq('$3f3f2d3f' if hidden else '$4a532d30', 'qa_buffer', 'l')
        eq('$3f3f' if hidden else '$3432', 'qa_buffer+4')
        eq('$4a532a00', 'player_registration(a6)', 'l')
    case('Real 256-byte save/restore preserves SID1, RID1, SHP1 and Special Cargo')
    emit(call('scramble_purchase') + ' move.l #$53485031,player_ship_tag(a6)\n'
         ' move.l #$53434731,courier_tag(a6)\n move.w #5250,courier_reward(a6)\n'
         ' move.w #$14ad,courier_x(a6)\n' + call('save_state'))
    eq('$53494431', 'game_state+200(a6)', 'l'); eq(255, 'game_state+204(a6)')
    emit(' clr.w scrambled_id(a6)\n clr.l player_registration(a6)\n clr.w courier_reward(a6)\n' + call('restore_state'))
    eq(255, 'scrambled_id(a6)'); eq('$4a532a00', 'player_registration(a6)', 'l')
    eq(5250, 'courier_reward(a6)'); eq(9950000, 'cash(a6)', 'l')
    case('Legacy commander without SID1 restores visible ID without touching other extensions')
    emit(call('save_state') + ' clr.l game_state+200(a6)\n move.w #255,game_state+204(a6)\n' + call('restore_state'))
    eq(0, 'scrambled_id(a6)'); eq('$4a532a00', 'player_registration(a6)', 'l')
    case('Invalid RID1 also clears otherwise valid Scramble ID')
    emit(' move.w #255,scrambled_id(a6)\n clr.l registration_tag(a6)\n' + call('registration_validate')); eq(0,'scrambled_id(a6)')
    for hull in range(1,13):
        case(f'Purchasing hull {hull} issues a visible registration')
        emit(call('scramble_purchase') + f' moveq #{hull},d0\n' + call('ship_purchase'))
        eq(0,'d0'); eq(0,'scrambled_id(a6)'); eq(hull,'player_ship(a6)')
    case('Rejected ship exchange keeps the hidden ID')
    emit(call('scramble_purchase') + ' move.w #$8001,equip+pulse_lasers(a6)\n moveq #1,d0\n' + call('ship_purchase'))
    eq(2,'d0');eq(255,'scrambled_id(a6)')
    case('Replacement hull generator clears the hidden ID')
    emit(call('scramble_purchase') + call('registration_new_player')); eq(0,'scrambled_id(a6)')
    for gov in range(8):
        case(f'Station government {gov}: Scramble ID never changes the record or gameplay RNG')
        emit(f' move.w #{gov},splanet+govern(a6)\n clr.w docked(a6)\n move.w #255,scrambled_id(a6)\n'
             ' clr.w station_destroyed(a6)\n move.l #$224ff,planet_range(a6)\n'
             ' move.w #-1,checkpoint(a6)\n move.w #1,radar_obj(a6)\n')
        for record in (0,49,50,99,100,101,255):
            emit(f' move.w #{record},police_record(a6)\n clr.w qa_calls\n' + call('radar_lock'))
            eq(record,'police_record(a6)');eq(0,'qa_calls');eq(255,'scrambled_id(a6)')
            emit(call('radar_lock'));eq(record,'police_record(a6)');eq(0,'qa_calls')
    for hidden,docked in ((0,0),(255,1)):
        case(f'No station penalty with visible ID or while docked: {hidden}/{docked}')
        emit(f' move.w #{hidden},scrambled_id(a6)\n move.w #{docked},docked(a6)\n move.w #7,splanet+govern(a6)\n'
             ' clr.w station_destroyed(a6)\n move.l #$224ff,planet_range(a6)\n'
             ' move.w #-1,checkpoint(a6)\n move.w #1,radar_obj(a6)\n'+call('radar_lock'))
        eq(0,'police_record(a6)');eq(0,'qa_calls')
    case('No legacy Scramble ID penalty warning is formatted on entering station space')
    emit(' clr.w docked(a6)\n move.w #7,splanet+govern(a6)\n move.w #255,scrambled_id(a6)\n'
         ' move.l #$11223344,registration_buffer(a6)\n clr.w station_destroyed(a6)\n'
         ' move.l #$224ff,planet_range(a6)\n move.w #-1,checkpoint(a6)\n'
         ' move.w #1,radar_obj(a6)\n'+call('radar_lock'))
    eq('$11223344','registration_buffer(a6)','l');eq(0,'police_record(a6)');eq(0,'qa_calls')
    patch('check_police','qa_police')
    patch('check_cargo','qa_return')
    for distance in (0x22500,0x224ff):
        for destroyed in (0,1):
            case(f'Real station boundary: distance {distance}, destroyed {destroyed}, police sees unchanged record')
            emit(' clr.w docked(a6)\n move.w #255,scrambled_id(a6)\n move.w #7,splanet+govern(a6)\n'
                 ' clr.w checkpoint(a6)\n clr.w radar_obj(a6)\n move.w #-1,qa_police_record\n'
                 f' move.l #{distance},planet_range(a6)\n move.w #{destroyed},station_destroyed(a6)\n' + call('radar_lock'))
            inside = distance < 0x22500 and not destroyed
            eq(0,'police_record(a6)');eq(0 if inside else -1,'qa_police_record')
    restore('check_police');restore('check_cargo')
    humans=('krait','boa','gecko','moray','adder','mamba','asp','sidewinder','wolf')
    for model in humans:
        case(f'{model}: all 256 byte outcomes, exactly 128 neutral, RNG called once; 16..31 cruise')
        spawn(model)
        emit(' move.w #255,scrambled_id(a6)\n move.w #50,police_record(a6)\n moveq #0,d6\n')
        label=f'qa_chance_{model}'
        emit(label+':\n move.w d6,qa_roll\n move.b d6,random_seed+1(a6)\n'
             ' clr.w qa_calls\n move.w #log_attack,logic(a4)\n clr.l target(a4)\n'
             ' move.w #99,pirate_truce(a4)\n' + call('scramble_pirate'))
        eq(1,'qa_calls');eq('typ_pirate','ship_type(a4)')
        emit(f' cmp.w #128,d6\n bhs.s {label}_hostile\n move.w d6,d0\n and.w #15,d0\n or.w #16,d0\n'
             f' cmp.w vel_max(a4),d0\n bls.s {label}_speed\n move.w vel_max(a4),d0\n{label}_speed:\n'
             ' cmp.w pirate_truce(a4),d0\n bne fail\n cmp.w velocity(a4),d0\n bne fail\n')
        eq('log_cruise','logic(a4)');eq('no_target','target(a4)','l')
        emit(f' bra.s {label}_next\n{label}_hostile:\n')
        eq(0,'pirate_truce(a4)');eq('log_attack','logic(a4)');eq(0,'target(a4)','l')
        emit(f'{label}_next:\n addq.w #1,d6\n cmp.w #256,d6\n blo {label}\n')
    for hidden,record in ((0,255),(255,0),(255,49),(255,50),(255,255)):
        case(f'Pirate eligibility: hidden {hidden}, legal record {record}')
        spawn('krait');emit(f' move.w #{hidden},scrambled_id(a6)\n move.w #{record},police_record(a6)\n clr.w qa_calls\n' + call('scramble_pirate'))
        yes=hidden==255 and record>=50;eq(16 if yes else 0,'pirate_truce(a4)');eq(int(yes),'qa_calls')
    for model in ('thargoid','thargon','cougar','constr','viper','ferdelance','cobra','python','shuttle','transporter','worm','missile','spacestn','dodec'):
        case(f'{model}: excluded; recycled truce cleared; no extra random roll')
        spawn(model);emit(' move.w #255,scrambled_id(a6)\n move.w #255,police_record(a6)\n move.w #31,pirate_truce(a4)\n clr.w qa_calls\n' + call('scramble_pirate'))
        eq(0,'pirate_truce(a4)');eq(0,'qa_calls')
    for state in (0x15,0x21,0x41,0x52):
        case(f'Mission ${state:02x}: human pirate/escort remains hostile, no additional RNG')
        spawn('asp');emit(f' move.w #{state},mission(a6)\n move.w #255,scrambled_id(a6)\n move.w #255,police_record(a6)\n clr.w qa_calls\n' + call('scramble_pirate'))
        eq(0,'pirate_truce(a4)');eq(0,'qa_calls')
    case('CREATE_OBJECT rolls neutrality for a new pirate; copied records never inherit it')
    emit(' move.w #255,scrambled_id(a6)\n move.w #255,police_record(a6)\n');spawn('krait');eq(16,'pirate_truce(a4)')
    emit(' move.l a4,a5\n lea objects+obj_len*4(a6),a4\n' + call('copy_object') + ' move.w #viper,type(a4)\n' + call('create_object'));eq(0,'pirate_truce(a4)')
    case('Allocation, removal and universe reset clear per-slot truce')
    emit(' move.w #31,objects+pirate_truce(a6)\n' + call('alloc_object'));eq(0,'pirate_truce(a4)')
    spawn('krait');emit(' move.w #31,pirate_truce(a4)\n move.l a4,a5\n' + call('remove_object'));eq(0,'pirate_truce(a5)')
    emit(' move.w #31,pirate_truce(a5)\n' + call('clear_objects'));eq(0,'pirate_truce(a5)')
    case('Neutral pirate ignores player across repeated retargets and maintains cruising speed')
    spawn('krait');emit(' move.w #23,pirate_truce(a4)\n move.l a4,a5\n move.w #3,this_obj(a6)\n move.w #3,retarget_slot(a6)\n')
    for _ in range(3):
        emit(call('retarget') + call('do_logic'));eq('no_target','target(a5)','l');eq('log_cruise','logic(a5)');eq(23,'velocity(a5)')
    case('Neutrality towards player preserves AI-versus-AI faction combat')
    spawn('krait');emit(' move.w #23,pirate_truce(a4)\n');spawn('cobra',4)
    emit(' move.l #1100,zpos(a4)\n lea objects+obj_len*3(a6),a5\n move.l #1000,zpos(a5)\n' + call('pick_target'))
    emit(' lea objects+obj_len*4(a6),a0\n cmp.l target(a5),a0\n bne fail\n');eq(23,'pirate_truce(a5)')
    for source in ('player laser','AI laser','player missile','AI missile'):
        case(f'{source}: only a player hit permanently revokes neutrality')
        spawn('boa');emit(' move.w #23,pirate_truce(a4)\n clr.w ecm_fitted(a4)\n move.w #5,laser_power(a6)\n')
        if source=='player laser':
            emit(' move.l a4,a5\n move.w #1,hit_check(a6)\n move.w #1,in_sights(a6)\n clr.w obj_hit(a6)\n move.l #100,this_zpos(a5)\n'
                 ' clr.l this_xpos(a5)\n clr.l this_ypos(a5)\n' + call('check_hit'))
        elif source=='AI laser':
            spawn('cobra',4);emit(' move.l a4,a5\n lea objects+obj_len*3(a6),a0\n move.l a0,target(a5)\n moveq #5,d0\n' + call('damage_target'))
        else:
            emit(' bsr qa_missile\n lea objects+obj_len*3(a6),a4\n move.l #$10000,zpos(a4)\n move.l a4,target(a5)\n'
                 f' move.w #{"log_locked" if source=="player missile" else "log_ai_missile"},logic(a5)\n' + call('do_locked'))
        emit(' lea objects+obj_len*3(a6),a5\n');eq(0 if source.startswith('player') else 23,'pirate_truce(a5)')
        if source.startswith('player'):
            emit(' btst #angry,flags(a5)\n beq fail\n' + call('pick_target'));eq(0,'target(a5)','l')
    for logic in ('log_peel_off','log_escape','log_launch','log_none'):
        case(f'Scripted {logic} pirate-model object cannot become an encounter pirate')
        spawn('adder');emit(f' move.w #{logic},logic(a4)\n move.w #255,scrambled_id(a6)\n move.w #100,police_record(a6)\n clr.w qa_calls\n' + call('scramble_pirate'))
        eq(0,'pirate_truce(a4)');eq(logic,'logic(a4)');eq(0,'qa_calls')
    patch('front_view','qa_return')
    for reason in ('success','not fitted','witch space','mission','full pool'):
        case(f'Real Adder escape, {reason}: only success replaces the scrambled ID')
        emit(' move.w #1,player_ship(a6)\n' + call('ship_apply') +
             ' clr.w docked(a6)\n move.w #255,scrambled_id(a6)\n move.w #100,police_record(a6)\n'
             ' move.w #1,equip+escape_capsule(a6)\n')
        if reason=='not fitted':emit(' clr.w equip+escape_capsule(a6)\n')
        if reason=='witch space':emit(' move.w #1,witch_space(a6)\n')
        if reason=='mission':emit(' move.w #$52,mission(a6)\n')
        if reason=='full pool':emit(' lea objects(a6),a0\n moveq #max_objects-1,d7\nqa_escape_fill:\n move.b #1,flags(a0)\n lea obj_len(a0),a0\n dbra d7,qa_escape_fill\n')
        emit(call('escape'));eq(0 if reason=='success' else 255,'scrambled_id(a6)')
        if reason=='success':
            eq('adder','objects+type(a6)');eq('log_peel_off','objects+logic(a6)')
            eq('log_escape','objects+next_logic(a6)');eq(0,'objects+pirate_truce(a6)')
            eq('$4a532a00','objects+registration_id(a6)','l')
    restore('front_view')
    restore('random')
    # Real generator/loadout interaction: distribution must remain near 50%,
    # including the three distinct rating bands, over 4096 independent spawns.
    for rating in (0,4,8):
        case(f'Real RNG with rating {rating}: 4096 full pirate creations remain within 47..53% neutral')
        emit(f' move.w #{rating},rating(a6)\n move.w #255,scrambled_id(a6)\n move.w #100,police_record(a6)\n'
             ' move.l #$b543a700,random_seed(a6)\n clr.w d5\n move.w #4095,d6\n'
             f'qa_distribution_{rating}:\n lea objects+obj_len*3(a6),a4\n move.w #krait,type(a4)\n'
             ' move.b #1,flags(a4)\n move.w #log_attack,logic(a4)\n' + call('create_object') + ' tst.w pirate_truce(a4)\n'
             f' beq.s qa_dist_next_{rating}\n addq.w #1,d5\nqa_dist_next_{rating}:\n dbra d6,qa_distribution_{rating}\n'
             ' cmp.w #1925,d5\n blo fail\n cmp.w #2171,d5\n bhi fail\n'
             f' move.w d5,qa_histogram+{(rating//4)*2}\n')
    tail += '''
qa_random:
 addq.w #1,qa_calls
 moveq #0,d0
 move.w qa_roll,d0
 rts
qa_police:
 move.w police_record(a6),qa_police_record
 rts
qa_return: rts
qa_roll: dc.w 0
qa_calls: dc.w 0
qa_police_record: dc.w 0
qa_histogram: ds.w 3
qa_buffer: ds.b 8
 even
''' + ''.join(f'qa_save_{n}: ds.b 6\n' for n in saved)
    return prefix, ''.join(out), tail, names
