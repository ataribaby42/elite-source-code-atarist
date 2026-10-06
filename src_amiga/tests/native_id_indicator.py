"""Native targeting controls and pixel checks for missile/identification sights."""
from native_missile_collision import make_suite as base_suite


def make_suite(root, s):
    prefix, _, tail, _ = base_suite(root, s)
    out, names = [], []
    emit=out.append
    call=lambda name:f' jsr ${s[name]:x}\n'
    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n move.w #1,equip+iff_unit(a6)\n clr.w id_trigger(a6)\n clr.w check_key(a6)\n clr.w csr_on(a6)\n clr.w display_clock(a6)\n')
    def key(char):emit(f" moveq #'{char}',d0\n"+call('check'))
    def eq(value,field):emit(f' cmp.w #{value},{field}\n bne fail\n')
    for state in (0,1,2):
        case(f'I then U: pending identification clears with missile state {state}, inventory is preserved')
        emit(f' move.w #{state},missile_state(a6)\n move.w #4,equip+missiles(a6)\n move.w #$0300,f_missiles(a6)\n')
        key('I');emit(' tst.w id_trigger(a6)\n beq fail\n');eq(state,'missile_state(a6)')
        key('U');eq(0,'id_trigger(a6)');eq(0,'missile_state(a6)');eq(4,'equip+missiles(a6)');eq(0 if state else '$0300','f_missiles(a6)')
    for state in (0,1,2):
        case(f'U with ID already inactive retains the original missile behaviour, state {state}')
        emit(f' move.w #{state},missile_state(a6)\n move.w #4,equip+missiles(a6)\n')
        key('U');eq(0,'id_trigger(a6)');eq(0,'missile_state(a6)');eq(4,'equip+missiles(a6)')
    case('Automatic missile unarming does not cancel the pending I request')
    key('I');emit(' move.w #1,missile_state(a6)\n'+call('unarm_missile'));eq(0,'missile_state(a6)');emit(' tst.w id_trigger(a6)\n beq fail\n')
    for laser in (-1,0):
        case(f'A successful identification consumes the request; laser type {laser}')
        emit(' lea objects+obj_len*3(a6),a4\n move.b #1,flags(a4)\n move.w #cobra,type(a4)\n'+call('create_object'))
        emit(f' move.l a4,a5\n move.l #1000,obj_range(a5)\n clr.l this_xpos(a5)\n clr.l this_ypos(a5)\n move.l #1000,this_zpos(a5)\n move.w #{laser},laser_type(a6)\n')
        key('I');emit(call('check_sights'));eq(0,'id_trigger(a6)')
    for view,func in enumerate(('front_view','rear_view','left_view','right_view')):
        for laser in range(-1,4):
            for screen in (1,2):
                case(f'View {view}, laser {laser}, buffer {screen}: grey pending lock, green ID priority, locked/cleared markers')
                emit(call('ship_apply')+call('prepare_cockpit'))
                for field in ('pulse_lasers','mining_lasers','beam_lasers','military_lasers'):emit(f' clr.w equip+{field}(a6)\n')
                if laser>=0:emit(f' move.w #{1<<view},equip+{("pulse_lasers","mining_lasers","beam_lasers","military_lasers")[laser]}(a6)\n')
                # DRAW_SPACE normally drains the asynchronous viewport clear
                # before DRAW_SIGHT. This focused test skips the space renderer.
                emit(call(func)+f' move.l screen{screen}_ptr(a6),scr_base(a6)\n'+call('clear_image')+call('wait_clear')+call('draw_sight')+' bsr qa_capture_pixels\n')
                def marker(colour):
                    emit(f' move.w #{colour},qa_expect_colour\n'+call('clear_image')+call('wait_clear')+call('draw_sight')+' bsr qa_compare_pixels\n')
                key('I');marker('lgt_green')
                key('U');marker(0)
                emit(' move.w #4,equip+missiles(a6)\n')
                key('T');eq(1,'missile_state(a6)');marker('lgt_grey')
                key('I');marker('lgt_green')
                emit(' clr.w id_trigger(a6)\n');marker('lgt_grey')
                emit(' move.w #2,missile_state(a6)\n');marker(0)
                key('I');marker('lgt_green')
                key('U');marker(0);eq(0,'missile_state(a6)');eq(4,'equip+missiles(a6)')
    # Use only this platform's own geometry and screen layout.
    g=s["_geometry"];zx=g["row_stride"]//160;zy=(g["y_max"]-g["y_min"]+1)//(g["no_rows"]*8);cx=g["x_left"]+(g["x_max"]-g["x_min"]+1)//2;cy=g["y_top"]+(g["y_max"]-g["y_min"]+1)//2-zy
    points=[(cx+lx*zx+dx,cy+ly*zy+dy,int(-2<=lx<=2 and -2<=ly<=2 and (abs(lx)==2 or abs(ly)==2)))
            for ly in range(-4,5) for dy in range(zy) for lx in range(-4,5) for dx in range(zx)]
    tail+='qa_expect_colour: dc.w 0\nqa_baseline: ds.b '+str(len(points))+'\n even\nqa_points:\n'
    tail+=''.join(f' dc.w {x},{y},{edge}\n' for x,y,edge in points)
    tail+='qa_capture_pixels:\n'+call('wait_clear')+' lea qa_points,a2\n lea qa_baseline,a3\n move.w #'+str(len(points)-1)+',d7\n.loop:\n move.w (a2)+,d0\n move.w (a2)+,d1\n addq.l #2,a2\n bsr qa_pixel\n move.b d0,(a3)+\n dbra d7,.loop\n rts\n'
    tail+='qa_compare_pixels:\n'+call('wait_clear')+' lea qa_points,a2\n lea qa_baseline,a3\n move.w #'+str(len(points)-1)+',d7\n.loop:\n move.w (a2)+,d0\n move.w (a2)+,d1\n bsr qa_pixel\n move.w (a2)+,d3\n tst.w qa_expect_colour\n beq.s .baseline\n tst.w d3\n beq.s .baseline\n cmp.w qa_expect_colour,d0\n bne fail\n bra.s .next\n.baseline:\n cmp.b (a3),d0\n bne fail\n.next:\n addq.l #1,a3\n dbra d7,.loop\n rts\n'
    tail+='''qa_pixel:
 moveq #0,d2
 move.w d0,d2
 lsr.w #4,d2
 add.w d2,d2
 mulu #row_stride,d1
 add.l d2,d1
 move.l scr_base(a6),a0
 adda.l d1,a0
 and.w #15,d0
 moveq #15,d1
 sub.w d0,d1
 moveq #0,d0
'''
    for plane,offset in enumerate(('0','plane1','plane2','plane3')):
        tail+=f' move.w {offset}(a0),d2\n btst d1,d2\n beq.s .plane_{plane}\n bset #{plane},d0\n.plane_{plane}:\n'
    tail+=' rts\n'
    return prefix,''.join(out),tail,names
