"""Run real missile impacts, effect lifetime and composed pixels on the 68000."""
from native_shield_flash import make_suite as flash_suite


def make_suite(root, s):
    prefix, _, tail, _ = flash_suite(root, s)
    out, names = [], []
    call = lambda name: f' jsr ${s[name]:x}\n'
    def emit(code): out.append(code)
    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')
    def flag(name, field, expected=True):
        emit(f' btst #{name},flags({field})\n {"beq" if expected else "bne"} fail\n')
    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n clr.w police_record(a6)\n')
    def victim(): emit(' lea objects+obj_len*3(a6),a4\n')
    def missile(): emit(' lea objects+obj_len*4(a6),a5\n')
    def spawn(role, rear=False, shield=24, model='cobra'):
        victim()
        emit(f' move.b #1,flags(a4)\n move.w #{model},type(a4)\n'+call('create_object'))
        emit(f' move.w #log_cruise,logic(a4)\n move.w #act_nothing,attack_type(a4)\n clr.w ecm_fitted(a4)\n move.l #1000,zpos(a4)\n move.w #unit,x_vector+i(a4)\n move.w #unit,y_vector+j(a4)\n move.w #{"unit" if rear else "-unit"},z_vector+k(a4)\n move.w #{shield},{"ai_aft" if rear else "ai_front"}(a4)\n bsr qa_missile\n move.l #900,zpos(a5)\n lea objects+obj_len*3(a6),a4\n move.l a4,target(a5)\n move.w #{role},logic(a5)\n')
    def effect():
        missile()
        eq('log_exploding','logic(a5)'); eq('exp_dur','exp_timer(a5)')
        eq(15,'force(a5)'); eq('rate','force_timer(a5)')
        eq(0,'exp_rad(a5)'); eq(0,'velocity(a5)'); eq(0,'shield_flash(a5)')
        eq('no_target','target(a5)','l')
        for bit in ('in_use','point','invincible','no_radar','no_bounty'): flag(bit,'a5')
        flag('remove','a5',False)
    def no_credit():
        eq(0,'score(a6)','l'); eq(0,'kill_count(a6)'); eq(100000,'cash(a6)','l')
        eq(0,'police_record(a6)'); eq('$41','mission(a6)')
        eq(0,'obj_ctr+platlet(a6)','b'); eq(0,'obj_ctr+barrel(a6)','b')
        eq(0,'npc_kill(a6)')
    for role in ('log_locked','log_ai_missile'):
        for rear in (False,True):
            for shield in (0,24):
                case(f'{role}, rear={rear}, shield={shield}: one impact, visible lifetime, no false kill')
                spawn(role,rear,shield)
                emit(call('do_locked')); effect(); victim()
                eq(36+shield,'health(a4)'); eq(0,('ai_aft' if rear else 'ai_front')+'(a4)')
                eq(24,('ai_front' if rear else 'ai_aft')+'(a4)')
                eq(int(shield>0),'shield_flash(a4)'); eq('log_cruise','logic(a4)'); no_credit()
                emit(call('do_logic')); eq('exp_dur-1','exp_timer(a5)'); eq(15,'exp_rad(a5)')
                victim(); eq(36+shield,'health(a4)')
                emit(' move.w #exp_dur-2,qa_frames\nqa_life_'+str(len(names))+':\n'+call('do_logic')+' subq.w #1,qa_frames\n bne qa_life_'+str(len(names))+'\n')
                eq(1,'exp_timer(a5)'); flag('remove','a5',False)
                emit(call('do_logic')); flag('remove','a5')
                emit(call('remove_objects')); missile(); flag('in_use','a5',False)
                victim(); flag('in_use','a4'); eq(36+shield,'health(a4)'); no_credit()
        for model in ('spacestn','cobra'):
            case(f'{role}: immune {model} still detonates the missile')
            spawn(role,model=model)
            emit(' bset #invincible,flags(a4)\n move.w #72,health(a4)\n'+call('do_locked'))
            effect(); victim(); eq(72,'health(a4)'); eq(0,'shield_flash(a4)'); no_credit()
        case(f'{role}: full object bubble needs no extra slot for the impact')
        spawn(role)
        emit(' lea objects(a6),a0\n moveq #max_objects-1,d7\nqa_full_'+str(len(names))+':\n bset #in_use,flags(a0)\n lea obj_len(a0),a0\n dbra d7,qa_full_'+str(len(names))+'\n'+call('do_locked'))
        effect(); no_credit()
        case(f'{role}: survivor lock and other incoming missile remain valid')
        spawn(role)
        emit(' lea objects+obj_len*5(a6),a0\n move.b #1,flags(a0)\n move.w #missile,type(a0)\n move.w #log_ai_missile,logic(a0)\n move.l a4,target(a0)\n move.w #2,missile_state(a6)\n move.l a4,target_ptr(a6)\n'+call('do_locked'))
        effect(); victim(); eq(2,'missile_state(a6)')
        emit(' cmp.l target_ptr(a6),a4\n bne fail\n lea objects+obj_len*5(a6),a0\n cmp.l target(a0),a4\n bne fail\n')
        flag('remove','a0',False)
        emit(call('check_missile')+' tst.w d7\n bpl fail\n')
        case(f'{role}: missiles targeting the spent missile are detached')
        spawn(role)
        emit(' lea objects+obj_len*5(a6),a0\n move.b #1,flags(a0)\n move.w #missile,type(a0)\n move.w #log_ai_missile,logic(a0)\n move.l a5,target(a0)\n'+call('do_locked'))
        effect()
        emit(' lea objects+obj_len*5(a6),a0\n'); flag('remove','a0'); victim(); flag('remove','a4',False)
        case(f'{role}: cosmetic detonation preserves gameplay RNG')
        spawn(role)
        emit(' move.l random_seed(a6),qa_seed\n bset #remove,flags(a5)\n'+call('missile_impact')+' move.l random_seed(a6),d0\n cmp.l qa_seed,d0\n bne fail\n')
        effect(); no_credit()
        case(f'{role}: rendered explosion and blue surviving hull coexist')
        spawn(role)
        emit(call('do_locked')+' clr.w csr_on(a6)\n clr.w display_clock(a6)\n clr.b loop_ctr(a6)\n'+call('prepare_cockpit')+call('front_view'))
        missile()
        # Build a visible radius while retaining the hit-frame shield state.
        for _ in range(8): emit(call('do_logic'))
        eq('exp_dur-8','exp_timer(a5)')
        victim(); eq(1,'shield_flash(a4)'); eq(60,'health(a4)')
        emit(' bsr qa_render\n moveq #1,d6\n bsr qa_pixels\n tst.w d4\n beq fail\n')
        missile(); emit(call('get_range')+call('draw_object')+call('draw_all')+' bsr qa_impact_pixels\n tst.w d4\n beq fail\n tst.w d5\n beq fail\n')
        victim(); eq(1,'shield_flash(a4)'); eq(60,'health(a4)')
    tail += 'qa_frames: dc.w 0\nqa_seed: dc.l 0\n'
    tail += '''qa_impact_pixels:
 moveq #0,d4
 moveq #0,d5
 move.l scr_base(a6),a0
 lea y_top*row_stride+x_left/8(a0),a0
 move.w #y_size-1,d7
.row:
 move.w #x_size/16-1,d3
.word:
 move.w 0(a0),d0
 or.w plane2(a0),d0
 move.w plane1(a0),d1
 move.w plane3(a0),d2
 eor.w d2,d1
 or.w d1,d0
 or.w d0,d5
 not.w d0
 and.w plane1(a0),d0
 and.w plane3(a0),d0
 or.w d0,d4
 addq.l #2,a0
 dbra d3,.word
 lea row_stride-x_size/8(a0),a0
 dbra d7,.row
 rts
'''
    return prefix, ''.join(out), tail, names
