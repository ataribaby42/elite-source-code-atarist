"""Station policy matrix, permission transitions and unchanged legal records."""
from native_spawn_paths import make_suite as spawn_suite


def make_suite(root, s):
    prefix, _, tail, _ = spawn_suite(root, s)
    out, names = [], []
    emit = out.append
    call = lambda name: f' jsr ${s[name]:x}\n'

    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')

    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n'
             ' clr.w docked(a6)\n clr.w just_docked(a6)\n clr.w no_entry(a6)\n'
             ' clr.w cockpit_on(a6)\n clr.w scrambled_id(a6)\n clr.w police_record(a6)\n'
             ' move.w #-1,checkpoint(a6)\n move.w #1,radar_obj(a6)\n'
             ' move.l #$224ff,planet_range(a6)\n move.l #2000,station_range(a6)\n'
             ' clr.l qa_time\n clr.w galaxy_no(a6)\n move.w #107,current(a6)\n'
             ' move.l #$4a532a00,player_registration(a6)\n'
             +call('comm_reset')+' clr.w qa_beeps\n')

    def received(kind, hidden=False, count=1, beeps=1):
        eq(count, 'comm_count(a6)'); eq(beeps, 'qa_beeps')
        eq(2 if kind=='denied' else 1, 'comm_arrival_sent(a6)')
        offset=f'comm_queue+{count-1}*comm_size+'
        eq('$43316b00', offset+'comm_sender(a6)', 'l')
        eq('comm_hidden' if hidden else '$4a532a00', offset+'comm_recipient(a6)', 'l')
        eq(1, offset+'comm_to_player(a6)')
        first,end={'normal':(15,25),'denied':(25,30),'unwelcome':(30,40)}[kind]
        emit(f' cmp.w #{first},{offset}comm_message(a6)\n blo fail\n'
             f' cmp.w #{end},{offset}comm_message(a6)\n bhs fail\n')
        if kind=='denied':emit(' tst.w no_entry(a6)\n beq fail\n')
        else:eq(0, 'no_entry(a6)')

    def silent():
        for field in ('comm_count(a6)','comm_arrival_sent(a6)','comm_seed(a6)','qa_beeps'):
            eq(0, field)

    hooks=[('comm_now','qa_now'),('comm_arrival_sound','qa_beep')]
    emit(call('hide_cursor')+' clr.w display_clock(a6)\n clr.w player_ship(a6)\n'+call('ship_apply'))
    for name,label in hooks:
        addr=s[name]
        emit(f' move.l ${addr:x},qa_policy_save_{name}\n move.w ${addr+4:x},qa_policy_save_{name}+4\n'
             f' move.w #$4ef9,${addr:x}\n move.l #{label},${addr+2:x}\n')
        tail+=f'qa_policy_save_{name}: ds.b 6\n'

    for gov in range(8):
        for hidden in (0,255):
            case(f'Government {gov}, hidden={hidden}: all 256 legal records at ranges 1999/2000/2001')
            label=f'qa_matrix_{gov}_{hidden}'
            emit(f' move.w #{gov},splanet+govern(a6)\n move.w #{hidden},scrambled_id(a6)\n'
                 ' move.l #$12345678,random_seed(a6)\n move.w #99,registration_state(a6)\n'
                 f' moveq #0,d6\n{label}_record:\n moveq #0,d5\n{label}_distance:\n'
                 +call('comm_reset')+' clr.w no_entry(a6)\n clr.w qa_beeps\n'
                 ' move.w d6,police_record(a6)\n move.l #1999,d0\n add.l d5,d0\n'
                 ' move.l d0,station_range(a6)\n'+call('radar_lock')
                 +' cmp.w police_record(a6),d6\n bne fail\n')
            eq('$12345678','random_seed(a6)','l');eq(99,'registration_state(a6)')
            emit(f' cmp.w #2,d5\n beq {label}_far\n')
            if hidden and gov not in (0,1,3):
                received('denied',True)
            elif gov not in (0,1,3):
                emit(f' tst.w d6\n beq {label}_clean\n')
                received('unwelcome',bool(hidden));emit(f' bra {label}_next\n{label}_clean:\n')
                received('normal',bool(hidden))
            else:received('normal',bool(hidden))
            emit(f' bra {label}_next\n{label}_far:\n');silent();eq(0,'no_entry(a6)')
            emit(f'{label}_next:\n addq.w #1,d5\n cmp.w #3,d5\n blo {label}_distance\n'
                 f' addq.w #1,d6\n cmp.w #256,d6\n blo {label}_record\n')

    for label,setup in (
            ('outside S',' move.l #$22500,planet_range(a6)\n'),
            ('docked',' move.w #1,docked(a6)\n'),
            ('docking frame',' move.w #1,just_docked(a6)\n'),
            ('witch space',' move.w #1,witch_space(a6)\n'),
            ('destroyed station',' move.w #1,station_destroyed(a6)\n'),
            ('missing station',' clr.b station_rec+flags(a6)\n'),
            ('alien model',' move.w #dodec,station_rec+type(a6)\n'),
            ('alien mission',' move.w #$52,mission(a6)\n')):
        case('Hidden-ID ban exclusion: '+label)
        emit(' move.w #255,scrambled_id(a6)\n move.w #50,police_record(a6)\n'+setup+call('comm_arrival_check'))
        silent();eq(0,'no_entry(a6)');eq(50,'police_record(a6)')

    for coords,expected in (((1200,1600,0),2000),((0,0,2001),2001)):
        case(f'Hidden-ID ban uses the actual cached distance for {coords}')
        emit(' move.w #255,scrambled_id(a6)\n lea station_rec(a6),a5\n')
        for field,value in zip(('xpos','ypos','zpos'),coords):emit(f' move.l #{value},{field}(a5)\n')
        emit(call('get_range'));eq(expected,'station_range(a6)','l');emit(call('radar_lock'))
        if expected<=2000:received('denied',True)
        else:silent();eq(0,'no_entry(a6)')

    case('A hidden ID after clearance revokes docking only upon reaching 2000')
    emit(call('radar_lock'));received('normal')
    emit(' move.w #255,scrambled_id(a6)\n move.l #2001,station_range(a6)\n'+call('radar_lock'))
    received('normal')
    emit(' move.l #2000,station_range(a6)\n'+call('radar_lock'));received('denied',True,2,2)
    for distance in (1999,2001,10000):
        emit(f' move.l #{distance},station_range(a6)\n'+call('radar_lock'));received('denied',True,2,2)

    case('Banned hidden ID stays banned through UI, expiry and S exit; only the notification rearms')
    emit(' move.w #255,scrambled_id(a6)\n'+call('radar_lock'));received('denied',True)
    emit(call('status')+call('hide_cursor')+call('radar_lock')
         +call('prepare_cockpit')+call('front_view')+call('comm_lifetime')
         +' move.l d0,qa_time\n'+call('comm_update')+call('radar_lock'))
    eq(0,'comm_count(a6)');eq(2,'comm_arrival_sent(a6)');eq(1,'qa_beeps')
    emit(' move.l #$22500,planet_range(a6)\n'+call('radar_lock'))
    eq(0,'comm_arrival_sent(a6)');emit(' tst.w no_entry(a6)\n beq fail\n')
    emit(' move.l #$224ff,planet_range(a6)\n move.l #2001,station_range(a6)\n'+call('radar_lock'))
    eq(0,'comm_count(a6)');eq(0,'comm_arrival_sent(a6)')
    emit(' move.l #2000,station_range(a6)\n'+call('radar_lock'));received('denied',True,beeps=2)

    case('Record changes after clearance do not send another clearance or revoke docking')
    emit(call('radar_lock'));received('normal')
    emit(' move.w #255,police_record(a6)\n'+call('radar_lock'));received('normal')
    emit(' move.l #$22500,planet_range(a6)\n'+call('radar_lock')
         +' move.l #$224ff,planet_range(a6)\n'+call('radar_lock'))
    received('unwelcome',count=2,beeps=2)

    for denied in (False,True):
        case(f'Full cosmetic cycle for {"hidden-ID denial" if denied else "Offender clearance"}')
        count=255 if denied else 250
        first=25 if denied else 30
        choices=5 if denied else 10
        label='qa_policy_distribution_'+str(int(denied))
        emit(f' move.w #{255 if denied else 0},scrambled_id(a6)\n move.w #1,police_record(a6)\n'
             f' move.w #1,comm_seed(a6)\n move.w #{count-1},d7\n{label}:\n'
             ' clr.w no_entry(a6)\n clr.w comm_count(a6)\n clr.w comm_arrival_sent(a6)\n'
             +call('comm_arrival_check'))
        eq(1,'comm_count(a6)');eq(2 if denied else 1,'comm_arrival_sent(a6)')
        emit(f' move.w comm_queue+comm_message(a6),d0\n sub.w #{first},d0\n'
             f' cmp.w #{choices-1},d0\n bhi fail\n add.w d0,d0\n lea {label}_hist,a0\n'
             f' addq.w #1,(a0,d0.w)\n dbra d7,{label}\n')
        for i in range(choices):eq(count//choices,f'{label}_hist+{i*2}')
        eq(count,'qa_beeps');eq(1,'comm_seed(a6)');eq(1,'police_record(a6)')
        tail+=f'{label}_hist: ds.w {choices}\n'

    case('Hidden-ID permission check preserves all caller data/address registers')
    emit(' move.w #255,scrambled_id(a6)\n move.l #$12345678,d0\n move.l #$23456789,d1\n'
         ' move.l #$34567890,d2\n lea station_rec(a6),a4\n move.l a4,a5\n'+call('comm_arrival_check'))
    eq('$12345678','d0','l');eq('$23456789','d1','l');eq('$34567890','d2','l')
    emit(' cmpa.l a4,a5\n bne fail\n');received('denied',True)

    for name,_ in hooks:
        addr=s[name]
        emit(f' move.l qa_policy_save_{name},${addr:x}\n move.w qa_policy_save_{name}+4,${addr+4:x}\n')
    tail+='qa_now:\n move.l qa_time,d0\n rts\nqa_beep:\n addq.w #1,qa_beeps\n rts\nqa_time: dc.l 0\nqa_beeps: dc.w 0\n'
    return prefix,''.join(out),tail,names
