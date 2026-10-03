"""Full pirate waves, encounter groups and mission waves with Scramble ID active."""
from native_spawn_paths import make_suite as base_suite


def make_suite(root,s):
    prefix,_,tail,_=base_suite(root,s)
    out,names=[],[]
    emit=out.append
    call=lambda n:f' jsr ${s[n]:x}\n'
    def case(n):
        names.append(n);emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n'
            ' move.w #255,scrambled_id(a6)\n move.w #100,police_record(a6)\n'
            ' move.w #8,rating(a6)\n move.w #$ffff,qa_fraction\n'
            ' clr.w qa_alternate\n clr.w qa_roll\n clr.w qa_rng_calls\n')
    def eq(v,f,size='w'):emit(f' cmp.{size} #{v},{f}\n bne fail\n')
    for n,label in [('random','qa_scramble_random'),('rand','qa_rand'),('ai_laser_roll','qa_loadout_roll')]:
        a=s[n];emit(f' move.l ${a:x},qa_saved_{n}\n move.w ${a+4:x},qa_saved_{n}+4\n'
                  f' move.w #$4ef9,${a:x}\n move.l #{label},${a+2:x}\n')
    for mode in (0,1,2):
        for route in ('pirate_attack','attack'):
            case(f'{route}: full wing, '+('all neutral','all hostile','mixed')[mode])
            emit(f' move.w #{255 if mode==1 else 0},qa_roll\n move.w #{int(mode==2)},qa_alternate\n'+call(route)+ ' bsr qa_check\n')
            eq(5,'qa_count');eq(5,'pirate_count(a6)')
            for slot in range(3,8):
                neutral=mode==0 or (mode==2 and slot%2==1)
                f=f'objects+obj_len*{slot}'
                eq('wolf',f+'+type(a6)')
                emit(f' tst.w {f}+pirate_truce(a6)\n '+('beq' if neutral else 'bne')+' fail\n')
                emit(f' lea {f}(a6),a5\n move.l #1000,obj_range(a5)\n'+call('pick_target'))
                eq('no_target' if neutral else 0,'target(a5)','l')
    for state,model,count in ((0x15,'constr',1),(0x21,'thargoid',5),(0x41,'cougar',3),(0x52,'thargoid',5)):
        for route in ('create_pirates','attack'):
            case(f'{route}, mission ${state:02x}: original ships, escorts, targets and RNG remain intact')
            emit(f' move.w #{state},mission(a6)\n'+call(route)+' bsr qa_check\n bsr qa_attacking\n')
            eq(count,'qa_count');eq(model,'objects+obj_len*3+type(a6)');eq(0,'qa_rng_calls')
            for slot in range(3,3+count):eq(0,f'objects+obj_len*{slot}+pirate_truce(a6)')
    # Build the actual pirate role used in random encounter groups.
    for roll in (0,255):
        case(f'Encounter pirate role, roll {roll}: same neutrality rule as ordinary ambushes')
        emit(f' move.w #{roll},qa_roll\n clr.l encounter_lead(a6)\n clr.w encounter_seat(a6)\n'
             ' move.w #1,encounter_role(a6)\n'+call('encounter_member'))
        emit(' bcc fail\n tst.w pirate_truce(a4)\n'+(' beq fail\n' if roll==0 else ' bne fail\n'))
        eq('typ_pirate','ship_type(a4)')
    case('Witch-space Thargoids and launched Tharglets never inherit neutrality')
    emit(' move.w #1,witch_space(a6)\n move.w #4,tharg_max(a6)\n'+call('create_thargoids'))
    # Existing source labels vary by platform only in implementation, not API.
    emit(' lea objects+obj_len*3(a6),a5\n move.w #3,this_obj(a6)\n'+call('thargons'))
    emit(' lea objects+obj_len*3(a6),a0\n moveq #max_objects-4,d7\nqa_alien_slots:\n'
         ' tst.w pirate_truce(a0)\n bne fail\n lea obj_len(a0),a0\n dbra d7,qa_alien_slots\n')
    for n in ('random','rand','ai_laser_roll'):
        a=s[n];emit(f' move.l qa_saved_{n},${a:x}\n move.w qa_saved_{n}+4,${a+4:x}\n')
    tail+=f'''
qa_scramble_random:
 cmp.l #${s['scramble_pirate']:x},(sp)
 blo.s qa_other_random
 cmp.l #${s['scramble_title']:x},(sp)
 bhs.s qa_other_random
 addq.w #1,qa_rng_calls
 move.w qa_roll,d0
 tst.w qa_alternate
 beq.s qa_scramble_random_done
 eori.w #255,qa_roll
qa_scramble_random_done:
 move.w #$ff,d1
 rts
qa_other_random:
 moveq #0,d0
 rts
qa_alternate: dc.w 0
'''
    return prefix,''.join(out),tail,names
