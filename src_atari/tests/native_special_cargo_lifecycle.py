"""Real launch, docking and hyperspace entry points with delivery state."""
from native_special_cargo import make_suite as base_suite

def make_suite(root,s):
    prefix,_,tail,_=base_suite(root,s)
    flight=(root/'asm/flight.m68').read_text()
    prefix+=flight[flight.index('\tq_vars flight'):flight.index('\tq_end_vars flight')]+'\n'
    out=[];names=[];saved=[]
    emit=out.append
    call=lambda n:f' jsr ${s[n]:x}\n'
    def patch(n,label='qa_return'):
        addr=s[n];saved.append(n)
        emit(f' move.l ${addr:x},qa_save_{n}\n move.w ${addr+4:x},qa_save_{n}+4\n move.w #$4ef9,${addr:x}\n move.l #{label},${addr+2:x}\n')
    def case(n):
        names.append(n);emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n bsr qa_courier_world\n move.w #5251,courier_reward(a6)\n move.w #$14ad,courier_x(a6)\n clr.w rating(a6)\n clr.w logo_shown(a6)\n clr.w count_down(a6)\n clr.w mission(a6)\n')
    def eq(v,f,size='w'):emit(f' cmp.{size} #{v},{f}\n bne fail\n')
    # Keep the real docking and story dispatch; skip only the visual transition.
    patch('docking_sequence');patch('wait')
    for story in (0,0x15,0x21):
        for delivered in (False,True):
            case(f'Real docking, story ${story:02X}, destination {delivered}: settle before the ordinary story/status screen')
            emit(f' move.w #{story},mission(a6)\n move.w #45,mission_planet(a6)\n move.w #1,just_docked(a6)\n move.w #1,controls_locked(a6)\n')
            if not delivered:emit(' move.b #21,courier_x(a6)\n')
            emit(call('docking'));eq(0 if delivered else 2625,'courier_reward(a6)');eq(10005251 if delivered else 10000000,'cash(a6)','l')
            eq(story,'mission(a6)');eq(0,'just_docked(a6)');eq(0,'controls_locked(a6)');emit(' tst.w docked(a6)\n beq fail\n')
    # Only the expensive visuals and unrelated world setup are substituted.
    for n in ('hyperspace_effect','create_system','reset_system','instruments','flush_keyboard','disp_message'):patch(n)
    patch('random','qa_random')
    for galaxy in (False,True):
        case(f'Real hyperspace completion, galactic {galaxy}: cancel only on galaxy change')
        emit(f' clr.w docked(a6)\n move.w #45,req_planet(a6)\n move.w #1,jump_trigger(a6)\n move.w #{int(galaxy)},jump_type(a6)\n clr.w fuel_needed(a6)\n move.w #64,jump_count(a6)\n clr.b key_states+$38(a6)\n'+call('hyperspace'))
        eq(0 if galaxy else 5251,'courier_reward(a6)');eq('$14ad','courier_x(a6)');eq(int(galaxy),'galaxy_no(a6)');eq(10000000,'cash(a6)','l')
    case('No triggered jump leaves the active delivery untouched')
    emit(' clr.w jump_trigger(a6)\n move.w #1,jump_type(a6)\n'+call('hyperspace'));eq(5251,'courier_reward(a6)');eq(0,'galaxy_no(a6)')
    # Restore every patched entry before exercising the real launch path.
    for n in saved:
        addr=s[n];emit(f' move.l qa_save_{n},${addr:x}\n move.w qa_save_{n}+4,${addr+4:x}\n')
    case('Real station launch retains the contract and does not depreciate it')
    emit(' bclr #f_sequence,user+1(a6)\n'+call('launch'));eq(5251,'courier_reward(a6)');eq('$14ad','courier_x(a6)');eq(10000000,'cash(a6)','l')
    tail+='qa_return: rts\nqa_random: moveq #0,d0\n move.w #255,d0\n rts\n'
    tail+=''.join(f'qa_save_{n}: ds.b 6\n' for n in saved)
    return prefix,''.join(out),tail,names
