"""I.F.F. purchase, saved-slot compatibility, controls and actual scanner pixels."""
from native_id_indicator import make_suite as targeting_suite


def make_suite(root, s):
    prefix, _, tail, _ = targeting_suite(root, s)
    source = (root/'asm/radar.m68').read_text()
    prefix += source[source.index('\tq_vars radar'):source.index('\tq_end_vars radar')]+'\n'
    out, names = [], []
    emit = out.append
    call = lambda name: f' jsr ${s[name]:x}\n'
    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_iff_world\n')
    def eq(value, field, size='w'):
        emit(f' cmp.{size} #{value},{field}\n bne fail\n')
    def key(value):
        emit(f' moveq #{value},d0\n'+call('check'))
    def trans(sell=0):
        emit(f' moveq #iff_unit/2,d0\n moveq #0,d1\n moveq #{sell},d2\n'+call('ship_equip_transaction'))
    def text(expected):
        emit(' lea text_buffer(a6),a0\n')
        for i, char in enumerate(expected+'\0'):
            eq(ord(char), f'{i}(a0)', 'b')

    categories = (0,1,1,4,1,2,3,3,3,2,4,4,4)
    prices = (25000,12500,25000,18750,9380)
    for hull, category in enumerate(categories):
        price = prices[category]
        case(f'Hull {hull}: I.F.F. retains its category price, one-tonne mass, single install and half-price sale')
        emit(f' move.w #{hull},player_ship(a6)\n'+call('ship_apply'))
        eq(category, 'hull_category(a6)')
        emit(' moveq #iff_unit/2,d0\n'+call('ship_equipment_price'))
        eq(price, 'd0', 'l')
        trans();eq(0,'d0');eq(1,'equip+iff_unit(a6)');eq(100000-price,'cash(a6)','l')
        emit(call('ship_equipment_mass'));eq(1,'d0')
        trans();eq(3,'d0');eq(100000-price,'cash(a6)','l')
        trans(1);eq(0,'d0');eq(0,'equip+iff_unit(a6)');eq(100000-price//2,'cash(a6)','l')
        emit(call('ship_equipment_mass'));eq(0,'d0')
    for reason in ('cash','hold'):
        case('Rejected I.F.F. purchase leaves equipment and cash intact: '+reason)
        if reason=='cash':emit(' move.l #1,cash(a6)\n')
        else:emit(' move.l #25000000,hold(a6)\n')
        trans();eq(1 if reason=='cash' else 2,'d0');eq(0,'equip+iff_unit(a6)')
        eq(1 if reason=='cash' else 100000,'cash(a6)','l')

    for equipped in (0,1):
        for missile in (0,1,2):
            case(f'I key, I.F.F. {equipped}, missile state {missile}: correct message and unchanged missile targeting')
            emit(f' move.w #{equipped},equip+iff_unit(a6)\n move.w #{missile},missile_state(a6)\n')
            key(ord('I'));eq(missile,'missile_state(a6)');eq(equipped,'equip+iff_unit(a6)')
            if equipped:emit(' tst.w id_trigger(a6)\n beq fail\n');text('ID active')
            else:eq(0,'id_trigger(a6)');text('I.F.F. Not Installed')
            key(ord('U'));eq(0,'id_trigger(a6)');eq(0,'missile_state(a6)')
        case(f'Tab is unbound with I.F.F. {equipped}; targets and missions survive')
        emit(f' move.w #{equipped},equip+iff_unit(a6)\n')
        for slot, model in enumerate(('cobra','thargoid','thargon','constr','cougar','dodec'),3):
            emit(f' lea objects+obj_len*{slot}(a6),a4\n move.b #1,flags(a4)\n move.w #{model},type(a4)\n'+call('create_object')+' move.w #log_cruise,logic(a4)\n')
        key(9);eq(equipped,'equip+iff_unit(a6)');eq('$41','mission(a6)');eq(0,'score(a6)','l')
        for slot in range(3,9):eq('log_cruise',f'objects+obj_len*{slot}+logic(a6)')
        case(f'256-byte commander round trip preserves I.F.F. {equipped} and adjacent equipment')
        emit(f' move.w #{equipped},equip+iff_unit(a6)\n move.w #1,equip+escape_capsule(a6)\n move.w #2,equip+energy_unit(a6)\n'+call('save_state'))
        eq(equipped,'game_state+34(a6)')
        emit(' clr.w equip+iff_unit(a6)\n clr.w equip+escape_capsule(a6)\n clr.w equip+energy_unit(a6)\n'+call('restore_state'))
        eq(equipped,'equip+iff_unit(a6)');eq(1,'equip+escape_capsule(a6)');eq(2,'equip+energy_unit(a6)')
    case('Legacy saved equipment slot 8 is interpreted as I.F.F. without shifting other fields')
    emit(call('save_state')+' move.w #1,game_state+34(a6)\n'+call('restore_state'));eq(1,'equip+iff_unit(a6)')

    colours = ('yellow','lgt_blue','lgt_green','magenta','mid_blue','orange','red','lgt_grey')
    for buffer in (1,2):
        for equipped in (0,1):
            for role, colour in enumerate(colours):
                for angry in (0,1):
                    for phase in (0,4):
                        visible = not (equipped and angry and phase==0)
                        case(f'Scanner buffer {buffer}, role {role}, I.F.F. {equipped}, hostile {angry}, blink {phase}: '+('draw '+(colour if equipped else 'yellow') if visible else 'hidden blink phase'))
                        emit(f' move.w #{equipped},equip+iff_unit(a6)\n move.b #{phase},loop_ctr(a6)\n move.l screen{buffer}_ptr(a6),scr_base(a6)\n'+call('remove_radar'))
                        emit(' lea objects+obj_len*3(a6),a5\n move.b #1,flags(a5)\n'+f' move.w #{role},ship_type(a5)\n')
                        if angry:emit(' bset #angry,flags(a5)\n')
                        emit(' bsr qa_blip_pixel\n move.w d0,qa_old_pixel\n'+call('radar'))
                        if visible:
                            emit(' tst.l last_ptr(a6)\n beq fail\n bsr qa_blip_pixel\n');eq(colour if equipped else 'yellow','d0')
                            emit(f' move.l last_ptr(a6),last{buffer}_ptr(a6)\n'+call('remove_radar')+' bsr qa_blip_pixel\n cmp.w qa_old_pixel,d0\n bne fail\n')
                        else:emit(' tst.l last_ptr(a6)\n bne fail\n bsr qa_blip_pixel\n cmp.w qa_old_pixel,d0\n bne fail\n')
    for gate in ('no_radar','invisible','cockpit','range'):
        case('Without I.F.F. existing scanner visibility still applies: '+gate)
        emit(' move.l screen1_ptr(a6),scr_base(a6)\n'+call('remove_radar')+' lea objects+obj_len*3(a6),a5\n move.b #1,flags(a5)\n')
        emit({'no_radar':' bset #no_radar,flags(a5)\n', 'invisible':' st invisible(a6)\n', 'cockpit':' clr.w cockpit_on(a6)\n', 'range':' move.l #radar_range+1,xpos(a5)\n'}[gate]+call('radar')+' tst.l last_ptr(a6)\n bne fail\n')
    # One point on the native radar head; scaled only where the Amiga display is.
    amiga=root.name=='src_amiga'
    x='159*zoom_x' if amiga else '159'
    y='170*zoom_y+y_shift' if amiga else '170'
    tail += '''qa_iff_world:
 bsr qa_world
 clr.w id_trigger(a6)
 clr.w check_key(a6)
 clr.w csr_on(a6)
 clr.w display_clock(a6)
 clr.w invisible(a6)
 clr.w view(a6)
 move.w #1,cockpit_on(a6)
 move.l #radar_range,radar_scale(a6)
 clr.l last1_ptr(a6)
 clr.l last2_ptr(a6)
 clr.l last_ptr(a6)
 lea equip(a6),a0
 moveq #equip_len/2-1,d7
.equip:
 clr.w (a0)+
 dbra d7,.equip
 move.w #$8000,equip+pulse_lasers(a6)
 move.w #$8000,equip+beam_lasers(a6)
 move.w #$8000,equip+mining_lasers(a6)
 move.w #$8000,equip+military_lasers(a6)
 lea hold(a6),a0
 moveq #max_products-1,d7
.hold:
 clr.l (a0)+
 dbra d7,.hold
'''+call('ship_apply')+''' rts
qa_old_pixel: dc.w 0
qa_blip_pixel:
'''+f' move.w #{x},d0\n move.w #{y},d1\n bra qa_pixel\n'
    return prefix, ''.join(out), tail, names
