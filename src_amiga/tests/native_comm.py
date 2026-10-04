"""Run the linked comm/jettison routines, with a controlled clock and audio spy."""
from native_player_ships import make_suite as base_suite

TEXTS = [
    'Dumping cargo near this station is illegal.',
    'Cargo dumping is prohibited in the station zone.',
    'Illegal cargo disposal detected. This offence has been recorded.',
    'Keep the station zone clear. Do not dump cargo here.',
    'Unauthorized cargo dumping. Your legal record has been updated.',
    'Have a good flight.',
    'Fly safe.',
    'Safe travels.',
    'Good luck out there.',
    'Until next time.',
    'Have a safe journey.',
    'Watch your six.',
    'See you again soon.',
    'Departure confirmed. Fly safe.',
    'Have a profitable trip.',
    'Permission to dock granted.',
    'Cleared to dock.',
    'Docking clearance granted.',
    'Welcome. You may dock.',
    'Docking permission approved.',
    'Approach approved. Proceed to dock.',
    'Dock when ready.',
    'You may begin your docking approach.',
    'Clearance confirmed. Approach safely.',
    'Welcome to the station. Docking approved.',
    'Vacate the area immediately.',
    'Docking denied. Leave the station area.',
    'You are not cleared to dock. Move away.',
    'Keep clear of the station. Docking denied.',
    'Docking access revoked. Leave immediately.',
    'Docking granted, but you are not welcome here.',
    'You may dock, despite your criminal record.',
    'Docking approved. We have checked your record.',
    'Cleared to dock. Keep your visit brief.',
    'Docking permitted. You are being watched.',
    'You may dock, but do not cause trouble.',
    'Docking granted. Your record is a concern.',
    'Clearance granted. We know your reputation.',
    'Docking approved. Stay out of trouble.',
    'You may dock. We will be watching you.',
]

def make_suite(root, s):
    prefix, _, tail, _ = base_suite(root, s)
    out, names = [], []
    emit = out.append
    call = lambda n: f' jsr ${s[n]:x}\n'
    def eq(v, f, size='w'):
        emit(f' cmp.{size} #{v},{f}\n bne fail\n')
    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n')
    def enqueue(i, t):
        emit(f' move.l #{t},qa_time\n moveq #{i},d0\n move.l #$43316b00,d1\n move.l #$4a532a00,d2\n'+call('comm_enqueue'))
    hooks=[('comm_now','qa_now'),('comm_arrival_sound','qa_fx')]
    emit(call('hide_cursor')+' clr.w display_clock(a6)\n bsr qa_world\n')
    for name, replacement in hooks:
        a=s[name]
        emit(f' move.l ${a:x},qa_saved_{name}\n move.w ${a+4:x},qa_saved_{name}+4\n move.w #$4ef9,${a:x}\n move.l #{replacement},${a+2:x}\n')
    emit(call('comm_lifetime')+' move.l d0,qa_life\n')
    case('Shared seven-second interval is 350 or 420 hardware flybacks')
    emit(' cmp.l #350,d0\n beq.s qa_life_ok\n cmp.l #420,d0\n bne fail\nqa_life_ok:\n')
    for g in range(8):
        for system in (0,107,255):
            case(f'Station snapshot C{g+1}-{system:03d}')
            emit(f' move.w #{g},galaxy_no(a6)\n move.w #{system},current(a6)\n'+call('comm_id_station'))
            eq(hex((ord('C')<<24)|((ord('1')+g)<<16)|(system<<8)).replace('0x','$'),'d0','l')
    for hidden in (0,255):
        case(f'Player snapshot, scrambled={bool(hidden)}')
        emit(f' move.l #$4a532a00,player_registration(a6)\n move.w #{hidden},scrambled_id(a6)\n'+call('comm_id_player'))
        eq('comm_hidden' if hidden else '$4a532a00','d0','l')
    for model,role,hidden in [('cobra','typ_trader',False),('cobra','typ_pirate',True),('thargoid','typ_trader',True),('thargon','typ_trader',True),('dodec','typ_trader',True)]:
        case(f'Object identity: {model}, {role}, hidden={hidden}')
        emit(f' lea objects(a6),a4\n move.w #{model},type(a4)\n move.w #{role},ship_type(a4)\n move.l #$41427f00,registration_id(a4)\n'+call('comm_id_object'))
        eq('comm_hidden' if hidden else '$41427f00','d0','l')
    for i,text in enumerate(TEXTS):
        case(f'Variant {i}: complete English text and visible/hidden prefix')
        emit(call('comm_reset'))
        enqueue(i,0)
        emit(' lea comm_queue(a6),a5\n'+call('comm_format')+f' lea qa_text_{i},a0\n lea comm_buffer(a6),a1\n bsr qa_compare\n')
        emit(' move.l #comm_hidden,comm_queue+comm_sender(a6)\n move.l #comm_hidden,comm_queue+comm_recipient(a6)\n'+call('comm_format')+f' lea qa_hidden_{i},a0\n lea comm_buffer(a6),a1\n bsr qa_compare\n')
        tail+=f"qa_text_{i}: dc.b 'C1-107:JS-042, {text}',0\nqa_hidden_{i}: dc.b '??-???:??-???, {text}',0\n even\n"
    case('Explicit player audience survives anonymous IDs, overflow and expiry')
    emit(' clr.l qa_time\n clr.w cockpit_on(a6)\n'+call('comm_reset'))
    for i,player in enumerate((1,0,1,0)):
        emit(f' moveq #{i},d0\n move.l #comm_hidden,d1\n move.l #comm_hidden,d2\n'
             ' move.l #$12345678,d7\n'+call('comm_enqueue_player' if player else 'comm_enqueue'))
        eq('$12345678','d7','l');eq('comm_hidden','d1','l');eq('comm_hidden','d2','l');eq(i,'d0')
    for i,player in enumerate((0,1,0)):
        eq(player,f'comm_queue+{i}*comm_size+comm_to_player(a6)')
    emit(' move.l #$58590100,player_registration(a6)\n move.w #255,scrambled_id(a6)\n'
         ' move.w #1,cockpit_on(a6)\n move.l qa_life,qa_time\n'+call('comm_update'))
    eq(2,'comm_count(a6)');eq(1,'comm_queue+comm_to_player(a6)')
    eq(0,'comm_queue+comm_size+comm_to_player(a6)')
    case('Invalid player message cannot retag the last NPC message')
    emit(' clr.w qa_beeps\n moveq #-1,d0\n'+call('comm_enqueue_player'))
    eq(2,'comm_count(a6)');eq(0,'qa_beeps');eq(0,'comm_queue+comm_size+comm_to_player(a6)')
    case('Queue preserves all registers, snapshots, order and newest three entries')
    emit(' clr.l qa_time\n'+call('comm_reset')+' clr.w qa_beeps\n move.w #1,cockpit_on(a6)\n')
    for i in range(4):enqueue(i,i*10)
    eq(3,'comm_count(a6)');eq(4,'qa_beeps')
    for i in range(3):
        eq(i+1,f'comm_queue+{i}*comm_size+comm_message(a6)')
        eq('$43316b00',f'comm_queue+{i}*comm_size+comm_sender(a6)','l')
        eq('$4a532a00',f'comm_queue+{i}*comm_size+comm_recipient(a6)','l')
    eq('$43316b00','d1','l');eq('$4a532a00','d2','l');eq(3,'d0')
    emit(' move.l #$58590100,player_registration(a6)\n move.w #255,scrambled_id(a6)\n move.w #4,galaxy_no(a6)\n move.w #3,current(a6)\n'+call('clear_objects'))
    eq('$4a532a00','comm_queue+comm_recipient(a6)','l');eq('$43316b00','comm_queue+comm_sender(a6)','l')
    case('Shared 3D interval expires exactly; a stalled frame removes only one entry')
    emit(' move.l qa_life,d0\n addi.l #29,d0\n move.l d0,qa_time\n'+call('comm_update'));eq(3,'comm_count(a6)')
    emit(' addq.l #1,qa_time\n'+call('comm_update'));eq(2,'comm_count(a6)');eq(2,'comm_queue+comm_message(a6)')
    emit(' move.l #10000,qa_time\n'+call('comm_draw'));eq(1,'comm_count(a6)');eq(3,'comm_queue+comm_message(a6)');eq(4,'qa_beeps')
    emit(call('comm_update'));eq(1,'comm_count(a6)')
    emit(' move.l qa_life,d0\n add.l d0,qa_time\n'+call('comm_update'));eq(0,'comm_count(a6)')
    case('UI time freezes old messages; new arrivals still shift a full queue and beep')
    emit(' clr.l qa_time\n'+call('comm_reset')+' move.w #1,cockpit_on(a6)\n clr.w qa_beeps\n')
    enqueue(0,0)
    emit(' move.l #100,qa_time\n'+call('comm_update')+' clr.w cockpit_on(a6)\n')
    for i in range(1,5):
        enqueue(i,10000+i*10000)
        eq(min(3,i+1),'comm_count(a6)')
        for index,message in enumerate(range(max(0,i-2),i+1)):
            eq(message,f'comm_queue+{index}*comm_size+comm_message(a6)')
    eq(3,'comm_count(a6)');eq(5,'qa_beeps');eq(100,'comm_clock(a6)','l')
    emit(' move.l #100000,qa_time\n'+call('comm_update'));eq(3,'comm_count(a6)');eq(100,'comm_clock(a6)','l')
    emit(' move.w #1,cockpit_on(a6)\n move.l qa_life,d0\n add.l #99999,d0\n move.l d0,qa_time\n'+call('comm_update'));eq(3,'comm_count(a6)')
    emit(' addq.l #1,qa_time\n'+call('comm_update'));eq(2,'comm_count(a6)');eq(3,'comm_queue+comm_message(a6)');eq(5,'qa_beeps')
    emit(' move.l qa_life,d0\n subq.l #1,d0\n add.l d0,qa_time\n'+call('comm_update'));eq(2,'comm_count(a6)')
    emit(' addq.l #1,qa_time\n'+call('comm_update'));eq(1,'comm_count(a6)');eq(4,'comm_queue+comm_message(a6)')
    emit(' move.l qa_life,d0\n add.l d0,qa_time\n'+call('comm_update'));eq(0,'comm_count(a6)');eq(5,'qa_beeps')
    case('Three quick UI arrivals disappear separately after 7, 14 and 21 seconds in 3D')
    emit(' clr.l qa_time\n clr.w cockpit_on(a6)\n'+call('comm_reset')+' clr.w qa_beeps\n')
    for i in range(3):enqueue(i,i)
    emit(' move.l #10000,qa_time\n'+call('comm_update')+' move.w #1,cockpit_on(a6)\n')
    for remaining in (2,1,0):
        emit(' move.l qa_life,d0\n subq.l #1,d0\n add.l d0,qa_time\n'+call('comm_update'));eq(remaining+1,'comm_count(a6)')
        emit(' addq.l #1,qa_time\n'+call('comm_update'));eq(remaining,'comm_count(a6)')
        if remaining:eq(3-remaining,'comm_queue+comm_message(a6)')
    eq(3,'qa_beeps')
    case('A new arrival after the queue has emptied starts a fresh shared interval')
    enqueue(0,50000)
    emit(call('comm_update'));eq(1,'comm_count(a6)')
    emit(' move.l qa_life,d0\n add.l d0,qa_time\n'+call('comm_update'));eq(0,'comm_count(a6)')
    case('Clock wrap does not expire a message early')
    emit(' move.l #$ffffff80,qa_time\n'+call('comm_reset'))
    enqueue(0,'$ffffff80')
    emit(' move.l qa_life,d0\n subi.l #129,d0\n move.l d0,qa_time\n'+call('comm_update'));eq(1,'comm_count(a6)')
    emit(' addq.l #1,qa_time\n'+call('comm_update'));eq(0,'comm_count(a6)')
    case('Real Status/3D transitions preserve the shared interval; appending does not reset it')
    emit(' clr.w docked(a6)\n clr.w witch_space(a6)\n clr.l qa_time\n'+call('prepare_cockpit')+call('front_view')+call('comm_reset'))
    enqueue(0,0)
    emit(' move.l #100,qa_time\n'+call('status')+call('hide_cursor'));eq(100,'comm_clock(a6)','l');eq(1,'comm_count(a6)')
    enqueue(1,10000);eq(100,'comm_clock(a6)','l');eq(2,'comm_count(a6)')
    emit(' move.l #20000,qa_time\n'+call('comm_update')+call('prepare_cockpit')+call('front_view'));eq(100,'comm_clock(a6)','l');eq(2,'comm_count(a6)')
    emit(' move.l qa_life,d0\n add.l #19899,d0\n move.l d0,qa_time\n'+call('comm_update'));eq(2,'comm_count(a6)')
    emit(' addq.l #1,qa_time\n'+call('comm_update'));eq(1,'comm_count(a6)');eq(1,'comm_queue+comm_message(a6)')
    emit(' add.l #100,qa_time\n'+call('comm_update'));eq(1,'comm_count(a6)')
    emit(' move.l qa_life,d0\n sub.l #100,d0\n add.l d0,qa_time\n'+call('comm_update'));eq(0,'comm_count(a6)')
    case('Invalid message ID is ignored without a beep or queue write')
    emit(' clr.w qa_beeps\n moveq #-1,d0\n'+call('comm_enqueue'));eq(0,'qa_beeps');eq(0,'comm_count(a6)')
    case('All five variants occur 51 times per cycle without changing other RNGs')
    emit(' move.l #$12345678,random_seed(a6)\n move.w #99,registration_state(a6)\n move.w #1,comm_seed(a6)\n move.w #254,d7\nqa_random_loop:\n'+call('comm_random')+' cmp.w #4,d0\n bhi fail\n add.w d0,d0\n lea qa_histogram,a0\n addq.w #1,(a0,d0.w)\n dbra d7,qa_random_loop\n')
    for i in range(5):eq(51,f'qa_histogram+{i*2}')
    eq(1,'comm_seed(a6)');eq('$12345678','random_seed(a6)','l');eq(99,'registration_state(a6)')
    for category,first in (('departure',5),('arrival',15),('unwelcome',30)):
        case(f'{category} lottery rejects all five biased bytes before accepting 250; sender and recipient survive retries')
        a=s['comm_random_byte']
        emit(f' move.l ${a:x},qa_saved_random_byte\n move.w ${a+4:x},qa_saved_random_byte+4\n'
             f' move.w #$4ef9,${a:x}\n move.l #qa_departure_byte,${a+2:x}\n'
             ' clr.w qa_departure_draws\n move.l #$43316b00,d1\n move.l #$4a532a00,d2\n'
             +call('comm_random_'+category))
        eq(6,'qa_departure_draws');eq(first,'d0')
        eq('$43316b00','d1','l');eq('$4a532a00','d2','l')
        emit(f' move.l qa_saved_random_byte,${a:x}\n move.w qa_saved_random_byte+4,${a+4:x}\n')
    configs=[(g,0,'spacestn',0,0x224ff,record,0) for g in range(8) for record in (0,245,255)]
    configs += [(3,mission,model,dead,dist,0,radar) for mission,model,dead,dist,radar in [
        (0,'spacestn',0,0x22500,1),(0,'spacestn',0,0x22501,1),
        (0,'spacestn',1,0x22000,1),(0,'dodec',0,0x22000,1),
        (0x52,'spacestn',0,0x22000,1),(0x52,'dodec',0,0x22000,1),
        (0x53,'spacestn',0,0x22000,1)]]
    for g,mission,model,dead,dist,record,radar in configs:
        illegal=g!=0 and mission!=0x52 and model!='dodec' and not dead and dist<0x22500
        case(f'Jettison: gov={g}, mission={mission:02x}, {model}, destroyed={dead}, range={dist:x}, record={record}, compass={radar}')
        emit(call('clear_objects')+call('comm_reset')+f' clr.w docked(a6)\n clr.w qa_beeps\n move.w #{g},splanet+govern(a6)\n move.w #{mission},mission(a6)\n move.w #{model},station_rec+type(a6)\n move.w #{dead},station_destroyed(a6)\n move.l #{dist},planet_range(a6)\n move.w #{record},police_record(a6)\n move.w #{radar},radar_obj(a6)\n move.l #1000000,hold(a6)\n moveq #0,d0\n'+call('jettison_cargo'))
        eq(1,'d0');eq(0,'hold(a6)','l');eq(min(record+15,255) if illegal else record,'police_record(a6)');eq(int(illegal),'comm_count(a6)');eq(int(illegal),'qa_beeps')
        if illegal:eq(1,'comm_queue+comm_to_player(a6)')
    case('Witch space has no station law, even if old range data is still near')
    emit(call('clear_objects')+call('comm_reset')+' clr.w docked(a6)\n clr.w mission(a6)\n clr.w station_destroyed(a6)\n clr.w police_record(a6)\n clr.w qa_beeps\n move.w #3,splanet+govern(a6)\n clr.l planet_range(a6)\n move.w #spacestn,station_rec+type(a6)\n move.w #1,witch_space(a6)\n move.l #1000000,hold(a6)\n moveq #0,d0\n'+call('jettison_cargo'))
    eq(1,'d0');eq(0,'comm_count(a6)');eq(0,'qa_beeps');eq(0,'police_record(a6)')
    emit(' clr.w witch_space(a6)\n')
    for rejection in ('empty','docked','mission cargo','full pool'):
        case(f'Rejected jettison ({rejection}) cannot send or penalize')
        emit(call('clear_objects')+call('comm_reset')+' clr.w docked(a6)\n clr.w mission(a6)\n clr.w station_destroyed(a6)\n clr.w police_record(a6)\n clr.w qa_beeps\n move.w #3,splanet+govern(a6)\n clr.l planet_range(a6)\n move.w #spacestn,station_rec+type(a6)\n move.l #1000000,hold(a6)\n moveq #0,d0\n')
        if rejection=='empty':emit(' clr.l hold(a6)\n')
        if rejection=='docked':emit(' move.w #1,docked(a6)\n')
        if rejection=='mission cargo':emit(' moveq #refugees,d0\n')
        if rejection=='full pool':emit(' lea objects(a6),a0\n moveq #max_objects-1,d7\nqa_fill:\n move.b #1,flags(a0)\n lea obj_len(a0),a0\n dbra d7,qa_fill\n')
        emit(call('jettison_cargo'));eq(0,'comm_count(a6)');eq(0,'qa_beeps');eq(0,'police_record(a6)')
    for routine in ('reset_system','restore_state'):
        for sent in (1, 2):
            case(f'{routine} discards queued communications and sent state {sent}')
            enqueue(0,0);emit(f' move.w #{sent},comm_arrival_sent(a6)\n'+call(routine))
            eq(0,'comm_count(a6)');eq(0,'comm_arrival_sent(a6)')
    for name,_ in hooks:
        a=s[name];emit(f' move.l qa_saved_{name},${a:x}\n move.w qa_saved_{name}+4,${a+4:x}\n')
    tail+='''qa_now:
 move.l qa_time,d0
 rts
qa_fx:
 addq.w #1,qa_beeps
.done:
 rts
qa_compare:
 move.b (a0)+,d0
 cmp.b (a1)+,d0
 bne fail
 tst.b d0
 bne.s qa_compare
 rts
qa_time: dc.l 0
qa_life: dc.l 0
qa_beeps: dc.w 0
qa_histogram: ds.w 5
qa_saved_comm_now: ds.b 6
qa_saved_comm_arrival_sound: ds.b 6
qa_saved_random_byte: ds.b 6
qa_departure_draws: dc.w 0
qa_departure_byte:
 addq.w #1,qa_departure_draws
 move.l #250,d0
 cmp.w #5,qa_departure_draws
 bhi.s .done
 add.w qa_departure_draws,d0
.done:
 rts
'''
    return prefix,''.join(out),tail,names
