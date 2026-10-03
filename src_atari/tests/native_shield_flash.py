"""Exercise real shield hits, frame expiry, collision rules and rendered pixels."""
from native_missile_collision import make_suite as base_suite


def make_suite(root, s):
    prefix, _, tail, _ = base_suite(root, s)
    out, names = [], []
    call = lambda n: f' jsr ${s[n]:x}\n'
    def emit(t): out.append(t)
    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n')
    def eq(value, field): emit(f' cmp.w #{value},{field}\n bne fail\n')
    def victim(): emit(' lea objects+obj_len*3(a6),a4\n')
    def spawn(model='cobra', rear=False):
        victim()
        emit(f' move.b #1,flags(a4)\n move.w #{model},type(a4)\n'+call('create_object'))
        emit(f' move.w #log_cruise,logic(a4)\n move.l #1000,zpos(a4)\n move.w #unit,x_vector+i(a4)\n move.w #unit,y_vector+j(a4)\n move.w #{"unit" if rear else "-unit"},z_vector+k(a4)\n')
    for rear in (False, True):
        shield = 'ai_aft' if rear else 'ai_front'
        other = 'ai_front' if rear else 'ai_aft'
        for route, power in (('player laser', 5), ('NPC laser', 5), ('missile', 60)):
            for before in (0, 1, 5, 24):
                case(f'{route}, {shield}={before}: flash tests the struck shield before damage')
                spawn(rear=rear)
                emit(f' move.w #{before},{shield}(a4)\n')
                if route == 'player laser':
                    emit(' move.l a4,a5\n move.w #1,hit_check(a6)\n move.w #1,in_sights(a6)\n move.l #1000,this_zpos(a5)\n move.w #5,laser_power(a6)\n'+call('check_hit'))
                else:
                    emit(' lea objects+obj_len*4(a6),a5\n move.l a4,target(a5)\n')
                    emit((call('ship_missile_damage') if route == 'missile' else ' moveq #5,d0\n'+call('damage_target')))
                victim()
                eq(int(before > 0), 'shield_flash(a4)')
                eq(max(0, before-power), shield+'(a4)')
                eq(24, other+'(a4)')
                eq(96-max(0, power-before), 'health(a4)')
    for condition in ('zero power', 'invincible', 'non-ship'):
        case(f'{condition}: no shield flash')
        spawn('barrel' if condition == 'non-ship' else 'cobra')
        if condition == 'invincible': emit(' bset #invincible,flags(a4)\n')
        emit(f' suba.l a0,a0\n moveq #{0 if condition == "zero power" else 5},d0\n'+call('ship_ai_damage'))
        eq(0, 'shield_flash(a4)')
    for model in ('cobra', 'barrel'):
        case(f'Reused/copied slot becomes {model}: pending flash resets')
        spawn()
        emit(f' move.w #9,shield_flash(a4)\n move.w #{model},type(a4)\n'+call('create_object'))
        eq(0, 'shield_flash(a4)')
    case('Removal clears the flash immediately and preserves neighbouring live ships')
    spawn()
    emit(' move.w #3,shield_flash(a4)\n move.w #2,objects+obj_len*4+shield_flash(a6)\n move.b #1,objects+obj_len*4+flags(a6)\n move.l a4,a5\n'+call('remove_object'))
    victim(); eq(0, 'shield_flash(a4)')
    emit(' btst #in_use,flags(a4)\n bne fail\n')
    eq(2, 'objects+obj_len*4+shield_flash(a6)')
    case('Deferred bubble removal clears the flash before the slot is reused')
    spawn()
    emit(' move.w #3,shield_flash(a4)\n bset #remove,flags(a4)\n'+call('remove_objects'))
    victim(); eq(0, 'shield_flash(a4)')
    emit(' btst #in_use,flags(a4)\n bne fail\n btst #remove,flags(a4)\n bne fail\n')
    case('Allocation clears stale flash state without touching adjacent active slots')
    emit(' move.w #7,objects+shield_flash(a6)\n move.b #1,objects+obj_len+flags(a6)\n move.w #2,objects+obj_len+shield_flash(a6)\n'+call('alloc_object')+' bcc fail\n')
    eq(0, 'shield_flash(a4)'); eq(2, 'objects+obj_len+shield_flash(a6)')
    case('A new copy of a flashing ship starts clear and leaves the source intact')
    spawn()
    emit(' move.w #3,shield_flash(a4)\n move.l a4,a5\n'+call('alloc_object')+' bcc fail\n'+call('copy_object')+call('create_object'))
    eq(0, 'shield_flash(a4)'); eq(3, 'objects+obj_len*3+shield_flash(a6)')
    case('Clearing the bubble resets flashes in every slot, including unused ones')
    emit(' lea objects(a6),a4\n moveq #max_objects-1,d7\nqa_dirty_slots:\n move.w #5,shield_flash(a4)\n lea obj_len(a4),a4\n dbra d7,qa_dirty_slots\n'+call('clear_objects'))
    emit(' lea objects(a6),a4\n moveq #max_objects-1,d7\nqa_clean_slots:\n tst.w shield_flash(a4)\n bne fail\n lea obj_len(a4),a4\n dbra d7,qa_clean_slots\n')
    case('Multiple hits in one frame refresh to one; all slots expire without underflow')
    spawn()
    emit(' move.w #4,shield_flash(a4)\n suba.l a0,a0\n moveq #5,d0\n'+call('ship_ai_damage'))
    eq(1, 'shield_flash(a4)')
    emit(' move.w #2,objects+obj_len*7+shield_flash(a6)\n'+call('ship_flash_tick'))
    eq(0, 'shield_flash(a4)'); eq(1, 'objects+obj_len*7+shield_flash(a6)')
    emit(call('ship_flash_tick')+call('ship_flash_tick'))
    eq(0, 'shield_flash(a4)'); eq(0, 'objects+obj_len*7+shield_flash(a6)')
    for destroyed in (False, True):
        for shield in (0, 24):
            case(f'Player collision, shield={shield}, AI destroyed={destroyed}: preserve collision result')
            spawn('cobra' if destroyed else 'anaconda')
            emit(f' move.w #{shield},ai_front(a4)\n move.w #1,shield_flash(a4)\n')
            if not destroyed: emit(' clr.w shield_flash(a4)\n move.w #1,hull_class(a6)\n')
            emit(' clr.l obj_range(a4)\n move.l a4,a5\n'+call('collision'))
            victim()
            eq(int(not destroyed and shield > 0), 'shield_flash(a4)')
            eq('log_exploding' if destroyed else 'log_cruise', 'logic(a4)')
            emit(' tst.w game_over(a6)\n'+(' bne fail\n' if destroyed else ' beq fail\n'))
    # Check actual pixels, not merely the selected colour or timer value.
    models = ('cobra','adder','gecko','moray','cobra_mk1','ferdelance','python','boa',
              'anaconda','asp','sidewinder','krait','mamba','thargon','viper',
              'wolf','shuttle','transporter','thargoid','cougar','constr')
    for model in models:
        alien = model in ('thargoid', 'thargon')
        colour = 'orange' if alien else 'blue'
        case(f'{model}: every hull/line pixel flashes {colour}, normal materials return next frame')
        spawn(model)
        emit(' clr.w csr_on(a6)\n clr.w display_clock(a6)\n clr.b loop_ctr(a6)\n'+call('prepare_cockpit')+call('front_view'))
        emit(' bsr qa_render\n moveq #0,d6\n bsr qa_pixels\n move.l d5,qa_normal_hash\n')
        victim(); emit(f' move.w #1,shield_flash(a4)\n bsr qa_render\n moveq #{3 if alien else 1},d6\n bsr qa_pixels\n')
        emit(' tst.w d4\n beq fail\n'+call('ship_flash_tick')+' bsr qa_render\n moveq #0,d6\n bsr qa_pixels\n cmp.l qa_normal_hash,d5\n bne fail\n')
    for model in ('cobra', 'thargoid', 'thargon'):
        for radius in (1, 2, 3):
            colour = 'blue' if model == 'cobra' else 'orange'
            case(f'{model}, distant radius {radius}: dot/cross stay grey, sphere flashes {colour}')
            spawn(model)
            emit(call('prepare_cockpit')+call('front_view')+call('clear_image'))
            victim(); emit(f' move.l a4,a5\n move.w #{radius},scr_radius(a5)\n clr.w centre_x(a5)\n clr.w centre_y(a5)\n move.w #1,shield_flash(a5)\n moveq #{model},d0\n'+call('draw_point'))
            pixel_mode = (1 if model == 'cobra' else 3) if radius == 3 else 2
            emit(f' moveq #{pixel_mode},d6\n bsr qa_pixels\n tst.w d4\n beq fail\n'+call('ship_flash_tick'))
            victim(); eq(0, 'shield_flash(a4)')
    for menu in (False, True):
        case(f'Actual flight frame, off-screen ship, menu={menu}: flash expires')
        emit(call('ship_apply')+call('reset_system')+call('launch_system')+call('front_view'))
        spawn()
        emit(' move.l #-5000,zpos(a4)\n move.w #1,shield_flash(a4)\n clr.w frame_count(a6)\n')
        if menu: emit(' clr.w cockpit_on(a6)\n')
        emit(call('game_logic')); victim(); eq(0, 'shield_flash(a4)')
    case('Lethal shielded laser hit draws blue hull before the explosion')
    spawn()
    emit(call('prepare_cockpit')+call('front_view'))
    victim(); emit(' move.w #1,ai_front(a4)\n move.w #1,health(a4)\n suba.l a0,a0\n moveq #5,d0\n'+call('ship_ai_damage'))
    eq(1, 'd0')
    emit(call('explode_object')+' bsr qa_render\n moveq #1,d6\n bsr qa_pixels\n tst.w d4\n beq fail\n'+call('ship_flash_tick'))
    victim(); eq('log_exploding','logic(a4)'); eq(0,'shield_flash(a4)')
    tail += 'qa_normal_hash: dc.l 0\nqa_render:\n'+call('clear_image')+' lea objects+obj_len*3(a6),a5\n'+call('get_range')+call('draw_object')+call('draw_all')+' rts\n'
    # ST interleaved planes. D6=0 hash, 1 blue, 2 grey, 3 orange (or empty).
    tail += '''qa_pixels:
 moveq #0,d5
 moveq #0,d4
 move.l scr_base(a6),a0
 lea y_top*160+x_left/2(a0),a0
 move.w #y_size-1,d7
.row:
 move.w #x_size/16-1,d3
.word:
 move.w (a0),d0
 move.w 2(a0),d1
 move.w 4(a0),d2
 rol.l #1,d5
 eor.w d0,d5
 rol.l #1,d5
 eor.w d1,d5
 rol.l #1,d5
 eor.w d2,d5
 rol.l #1,d5
 move.w 6(a0),d2
 eor.w d2,d5
 tst.w d6
 beq.s .next
 cmp.w #2,d6
 beq.s .grey
 cmp.w #3,d6
 beq.s .orange
 tst.w d0
 bne fail
 cmp.w d1,d2
 bne fail
 tst.w 4(a0)
 bne fail
 or.w d1,d4
 bra.s .next
.orange:
 cmp.w d0,d1
 bne fail
 tst.w d2
 bne fail
 tst.w 4(a0)
 bne fail
 or.w d0,d4
 bra.s .next
.grey:
 tst.w d1
 bne fail
 tst.w d2
 bne fail
 tst.w 4(a0)
 bne fail
 or.w d0,d4
.next:
 addq.l #8,a0
 dbra d3,.word
 lea 160-x_size/2(a0),a0
 dbra d7,.row
 rts
'''
    return prefix, ''.join(out), tail, names
