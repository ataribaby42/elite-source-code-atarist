"""Lost missile targets: visible detonation, bounded cleanup and no extra damage."""
from native_shield_flash import make_suite as base_suite


def make_suite(root, s):
    prefix, _, tail, _ = base_suite(root, s)
    out, names = [], []
    call = lambda name: f' jsr ${s[name]:x}\n'
    def emit(code): out.append(code)
    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')
    def pointer(slot, reg='a4'):
        emit(f' lea objects+obj_len*{slot}(a6),{reg}\n')
    def flag(bit, reg='a4', value=True):
        emit(f' btst #{bit},flags({reg})\n {"beq" if value else "bne"} fail\n')
    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n'+call('quiet')+
             ' bclr #f_fx,user(a6)\n bsr qa_world\n clr.w police_record(a6)\n'
             ' clr.w text_frames(a6)\n clr.b text_buffer(a6)\n')
    def spawn(slot, model='cobra'):
        pointer(slot)
        emit(f' move.b #1,flags(a4)\n move.w #{model},type(a4)\n'+call('create_object')+
             ' move.w #log_cruise,logic(a4)\n move.w #act_nothing,attack_type(a4)\n'
             ' clr.w ecm_fitted(a4)\n move.l #1000,zpos(a4)\n move.l #1000,obj_range(a4)\n'
             ' move.w #unit,x_vector+i(a4)\n move.w #unit,y_vector+j(a4)\n move.w #-unit,z_vector+k(a4)\n'
             ' move.l #no_target,target(a4)\n')
    def missile(slot, target, role):
        spawn(slot, 'missile')
        pointer(target, 'a0')
        emit(f' move.l a0,target(a4)\n move.w #{role},logic(a4)\n'
             ' move.l #120,xpos(a4)\n move.l #-70,ypos(a4)\n move.l #1400,zpos(a4)\n')
    def lost(slot=3):
        pointer(slot)
        emit(call('target_lost'))
    def effect(slot=4):
        pointer(slot)
        eq('log_exploding', 'logic(a4)'); eq('exp_dur', 'exp_timer(a4)')
        eq('no_target', 'target(a4)', 'l'); eq(0, 'velocity(a4)')
        for bit in ('in_use', 'point', 'invincible', 'no_radar', 'no_bounty'):
            flag(bit)
        flag('remove', value=False)
    def no_credit():
        eq(0, 'score(a6)', 'l'); eq(0, 'kill_count(a6)')
        eq(100000, 'cash(a6)', 'l'); eq(0, 'police_record(a6)')
        eq('$41', 'mission(a6)'); eq(0, 'obj_ctr+barrel(a6)', 'b')
        eq(0, 'obj_ctr+platlet(a6)', 'b')

    for role in ('log_locked', 'log_ai_missile'):
        case(f'{role}: lost target detonates in place, preserves RNG and nearby ships')
        spawn(3); missile(4, 3, role); spawn(5)
        emit(' move.l random_seed(a6),qa_seed\n')
        lost(); effect()
        eq(120, 'xpos(a4)', 'l'); eq(-70, 'ypos(a4)', 'l'); eq(1400, 'zpos(a4)', 'l')
        emit(' move.l random_seed(a6),d0\n cmp.l qa_seed,d0\n bne fail\n')
        for slot in (3, 5):
            pointer(slot); eq(96, 'health(a4)'); eq(24, 'ai_front(a4)'); eq(24, 'ai_aft(a4)')
        no_credit()
        emit(' tst.w text_frames(a6)\n'+(' beq' if role == 'log_locked' else ' bne')+' fail\n')

        case(f'{role}: complete explosion lifetime, repeated invalidation does not restart it')
        spawn(3); missile(4, 3, role); lost(); effect()
        emit(' move.l a4,a5\n'+call('do_explosion'))
        lost(); pointer(4); eq('exp_dur-1', 'exp_timer(a4)')
        emit(' move.l a4,a5\n move.w #exp_dur-2,qa_frames\n'
             f'qa_life_{len(names)}:\n'+call('do_explosion')+
             f' subq.w #1,qa_frames\n bne qa_life_{len(names)}\n')
        flag('remove', 'a5', False); eq(1, 'exp_timer(a5)')
        emit(call('do_explosion')+call('remove_objects')); pointer(4)
        flag('in_use', value=False); eq(0, 'obj_ctr+missile(a6)', 'b'); no_credit()

        case(f'{role}: target leaving the bubble also detaches its missile')
        spawn(3); missile(4, 3, role); pointer(3, 'a5')
        emit(' move.l #radar_range+1,obj_range(a5)\n'+call('do_abandoned'))
        flag('remove', 'a5'); effect(); emit(call('remove_objects'))
        pointer(3); flag('in_use', value=False); effect()

        case(f'{role}: an NPC laser kills the target before the missile arrives')
        spawn(3); missile(4, 3, role); spawn(5)
        emit(' move.l a4,a5\n lea objects+obj_len*3(a6),a4\n move.l a4,target(a5)\n'
             ' clr.w ai_front(a4)\n clr.w ai_aft(a4)\n move.w #1,health(a4)\n'
             ' moveq #60,d0\n'+call('damage_target'))
        effect(); pointer(3); eq('log_exploding', 'logic(a4)')
        eq(0, 'score(a6)', 'l'); eq(0, 'kill_count(a6)'); eq(0, 'police_record(a6)')

        case(f'{role}: another missile kills the target; the spent impactor stays consumed')
        spawn(3); missile(4, 3, role); missile(5, 3, 'log_ai_missile')
        pointer(3)
        emit(' clr.w ai_front(a4)\n clr.w ai_aft(a4)\n move.w #1,health(a4)\n')
        pointer(5, 'a5')
        emit(' clr.l xpos(a5)\n clr.l ypos(a5)\n move.l #1000,zpos(a5)\n'+call('do_locked'))
        effect(); pointer(5); flag('remove'); pointer(3); eq('log_exploding', 'logic(a4)')
        eq(0, 'score(a6)', 'l'); eq(0, 'kill_count(a6)')

        case(f'{role}: full object bubble keeps the explosion in the existing slot')
        spawn(3); missile(4, 3, role)
        emit(' lea objects(a6),a0\n moveq #max_objects-1,d7\n'
             f'qa_fill_{len(names)}:\n bset #in_use,flags(a0)\n lea obj_len(a0),a0\n'
             f' dbra d7,qa_fill_{len(names)}\n')
        lost(); effect(); no_credit()

        case(f'{role}: lost-target explosion produces visible pixels')
        spawn(3); missile(4, 3, role); lost()
        emit(' clr.w csr_on(a6)\n clr.w display_clock(a6)\n clr.b loop_ctr(a6)\n'+
             call('prepare_cockpit')+call('front_view'))
        pointer(4, 'a5')
        for _ in range(8): emit(call('do_explosion'))
        pointer(4)
        emit(call('clear_image')+call('wait_clear')+' bsr qa_blank\n'
             ' lea objects+obj_len*4(a6),a5\n'+call('get_range')+call('draw_object')+call('draw_all')+
             ' moveq #0,d6\n bsr qa_pixels\n tst.l d5\n beq fail\n')

    case('Mixed incoming missiles detonate; unrelated targets and player-directed AI missiles survive')
    spawn(3); spawn(8)
    for slot, target, role in ((4, 3, 'log_locked'), (5, 3, 'log_ai_missile'),
                                (6, 8, 'log_ai_missile'), (7, 8, 'log_missile')):
        missile(slot, target, role)
    pointer(7); emit(' clr.l target(a4)\n')
    lost(); effect(4); effect(5)
    pointer(6); eq('log_ai_missile', 'logic(a4)'); flag('remove', value=False)
    pointer(7); eq('log_missile', 'logic(a4)'); flag('remove', value=False)
    no_credit()

    case('Lock on a secondary missile is disarmed; chains propagate without recursive target cleanup')
    spawn(3); missile(4, 3, 'log_ai_missile'); missile(5, 4, 'log_ai_missile')
    missile(6, 5, 'log_locked'); pointer(5)
    emit(' move.w #2,missile_state(a6)\n move.l a4,target_ptr(a6)\n')
    lost()
    for slot in (4, 5, 6): effect(slot)
    eq(0, 'missile_state(a6)'); emit(' tst.w text_frames(a6)\n beq fail\n'); no_credit()

    case('Missile target cycle terminates and does not restart the original explosion')
    missile(3, 4, 'log_locked'); missile(4, 5, 'log_ai_missile'); missile(5, 3, 'log_ai_missile')
    pointer(3, 'a5'); emit(call('missile_impact'))
    for slot in (3, 4, 5): effect(slot)
    no_credit()

    case('Maximum reverse-order missile chain fits a bounded queue and preserves caller registers')
    spawn(29)
    for slot in range(29): missile(slot, slot+1, 'log_ai_missile')
    pointer(29); pointer(0, 'a5')
    emit(' move.l sp,qa_sp\n move.l a5,qa_a5\n move.l a4,qa_a4\n move.l #$12345678,d7\n'+call('target_lost')+
         ' cmpa.l qa_sp,sp\n bne fail\n cmpa.l qa_a5,a5\n bne fail\n cmpa.l qa_a4,a4\n bne fail\n')
    eq('$12345678', 'd7', 'l')
    for slot in range(29): effect(slot)
    no_credit()

    case('A missile already marked for removal is not resurrected as an explosion')
    spawn(3); missile(4, 3, 'log_locked'); emit(' bset #remove,flags(a4)\n')
    lost(); pointer(4); flag('remove'); eq('log_locked', 'logic(a4)')
    emit(' tst.w text_frames(a6)\n bne fail\n')

    return prefix, ''.join(out), tail+'qa_frames: dc.w 0\nqa_seed: dc.l 0\nqa_sp: dc.l 0\nqa_a4: dc.l 0\nqa_a5: dc.l 0\n', names
