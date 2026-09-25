"""Native deterministic map, globe rotation, LOD and viewport regressions."""
import math
from native_viewport_bounds import guard_code

def make_suite(root,s):
    source=(root/'asm/planet.m68').read_text()
    prefix=' include "common.def"\n include "macros.m68"\n'
    prefix+=source[source.index('ps_features:'):source.index('    q_end_vars planet_surface')]+'\n'
    call=lambda name: '' if name == 'wait_clear' and name not in s else f' jsr ${s[name]:x}\n'
    body=' bset #f_planets,user+1(a6)\n clr.w csr_on(a6)\n clr.w display_clock(a6)\n clr.w player_ship(a6)\n'
    body+=call('ship_apply')+call('reset_system')+call('prepare_cockpit')+call('front_view')+call('clear_objects')
    body+=' lea planet_rec(a6),a4\n move.b #$87,flags(a4)\n move.w #planet,type(a4)\n move.w #16384,obj_rad(a4)\n move.l #100000,zpos(a4)\n'
    body+=call('create_object')
    names=[];shots=0
    def case(name):
        nonlocal body
        names.append(name);body+=f' move.w #{len(names)},qa_case\n'
    def init(colour):
        nonlocal body
        body+=f' lea planet_rec(a6),a4\n move.w #{colour},obj_colour(a4)\n'+call('init_planet_surface')+' lea planet_rec(a6),a5\n'
    def snapshot(name,present=True):
        nonlocal body,shots
        shots+=1
        # Present the completed frame, including the Fast RAM shadow viewport.
        body+=' movem.l d0-d7/a0-a5,-(sp)\n move.l scr_base(a6),qa_frame\n'+(call('swap_screen') if present else '')+' movem.l (sp)+,d0-d7/a0-a5\n'
        body+=f' lea ${s["palette"]:x},a0\n lea qa_palette(pc),a1\n moveq #15,d7\nqa_capture_palette_{shots}:\n move.w (a0)+,(a1)+\n dbra d7,qa_capture_palette_{shots}\n'
        body+=f'snap_{name}:\n nop\n'
        if root.name=='src_amiga':
            body+=f' move.w #{shots},qa_snapshot\nqa_wait_{shots}:\n tst.w qa_snapshot\n bne.s qa_wait_{shots}\n'
    def render(radius=48,x=0,y=0):
        nonlocal body
        # Radius and centre are logical pixels, then scaled by the target.
        zx=s['_geometry']['zoom_x']
        zy=s['_geometry']['zoom_y']
        # Match DRAW_SPACE/DRAW_ALL's fence before calling the lower-level draw.
        body+=' bsr qa_fill\n'+call('clear_image')+call('wait_clear')
        body+=f' lea planet_rec(a6),a5\n move.w #{radius*zy},scr_radius(a5)\n move.w #{x*zx},centre_x(a5)\n move.w #{y*zy},centre_y(a5)\n clr.l this_xpos(a5)\n clr.l this_ypos(a5)\n move.l #100000,this_zpos(a5)\n move.w #planet,d0\n'
        body+=call('draw_point')+' bsr qa_guard_check\n'
    case('Same seed regenerates identical complete map without advancing gameplay RNG')
    body+=' move.l #$12345678,random_seed(a6)\n move.l #$5a4a0248,splanet+seed(a6)\n move.w #$b753,splanet+seed+4(a6)\n'
    init(8)
    body+=' cmp.l #$12345678,random_seed(a6)\n bne fail\n lea ps_map(a6),a0\n lea qa_map(pc),a1\n move.w #ps_features*ps_feature_bytes/2-1,d7\nqa_save_map:\n move.w (a0)+,(a1)+\n dbra d7,qa_save_map\n'
    init(8)
    body+=' lea ps_map(a6),a0\n lea qa_map(pc),a1\n move.w #ps_features*ps_feature_bytes/2-1,d7\nqa_compare_map:\n move.w (a0)+,d0\n cmp.w (a1)+,d0\n bne fail\n dbra d7,qa_compare_map\n'
    case('Changing the seed changes the generated geography')
    body+=' addq.w #1,splanet+seed+4(a6)\n'
    init(8)
    body+=' lea ps_map(a6),a0\n lea qa_map(pc),a1\n move.w #ps_features*ps_feature_bytes/2-1,d7\nqa_different_map:\n move.w (a0)+,d0\n cmp.w (a1)+,d0\n bne.s qa_different_ok\n dbra d7,qa_different_map\n bra fail\nqa_different_ok:\n subq.w #1,splanet+seed+4(a6)\n'
    for colour,kind,ink in [(1,1,2),(2,0,0),(3,2,None),(4,2,None),(5,2,None),(6,2,None),(7,2,11),(8,2,11),(9,2,None),(10,2,8),(11,2,8),(12,2,None),(15,2,None)]:
        case(f'Palette {colour}: surface kind {kind}')
        init(colour)
        body+=f' cmp.w #{kind},ps_kind(a6)\n bne fail\n'
        if kind and ink is not None:body+=f' cmp.w #{ink},ps_ink(a6)\n bne fail\n'
        if colour in (7,8,10,11):
            render();snapshot(f'palette_{colour}_medium')
            body+=' eori.w #$100,splanet+seed+4(a6)\n'
            init(colour)
            body+=f' cmp.w #{ink-1},ps_ink(a6)\n bne fail\n'
            render();snapshot(f'palette_{colour}_light')
            body+=' eori.w #$100,splanet+seed+4(a6)\n'
        elif kind==2:
            # New base colours retain exactly the same seeded coastline.
            body+=f' lea ps_map(a6),a0\n lea qa_map(pc),a1\n move.w #ps_features*ps_feature_bytes/2-1,d7\nqa_other_map_{colour}:\n move.w (a0)+,d0\n cmp.w (a1)+,d0\n bne fail\n dbra d7,qa_other_map_{colour}\n'
            render();snapshot(f'other_{colour}')
            body+=' move.w ps_ink(a6),qa_yaw\n'
            init(colour)
            body+=' move.w qa_yaw(pc),d0\n cmp.w ps_ink(a6),d0\n bne fail\n'
            # Sixteen adjacent seeds exercise every palette selection slot,
            # including same-colour rejection and the last-slot wraparound.
            body+=f' move.w #$b700,splanet+seed+4(a6)\n moveq #15,d7\nqa_other_seed_{colour}:\n'
            init(colour)
            body+=' cmp.w #2,ps_kind(a6)\n bne fail\n move.w ps_ink(a6),d0\n cmp.w obj_colour(a5),d0\n beq fail\n tst.w d0\n beq fail\n cmp.w #white,d0\n bhi fail\n cmp.w #drk_grey,d0\n beq fail\n cmp.w #yellow,d0\n beq fail\n cmp.w #black,d0\n beq fail\n cmp.w #pulse,d0\n beq fail\n cmp.l #$12345678,random_seed(a6)\n bne fail\n'
            body+=f' addq.w #1,splanet+seed+4(a6)\n dbra d7,qa_other_seed_{colour}\n move.w #$b753,splanet+seed+4(a6)\n'
    case('Below the size threshold no surface work or pixels change')
    init(8)
    body+=' move.w #$1234,ps_matrix(a6)\n'
    render(11)
    body+=' cmp.w #$1234,ps_matrix(a6)\n bne fail\n'
    snapshot('small')
    case('Reference silhouette for pixel containment')
    init(8)
    body+=' clr.w ps_kind(a6)\n'
    render()
    snapshot('silhouette')
    for colour,label in [(8,'sea'),(11,'land'),(1,'crater')]:
        init(colour)
        for angle in (0,45,90,135,180,225,270,315,360):
            case(f'{label}: full globe orbit at {angle} degrees')
            c=round(math.cos(math.radians(angle))*16384);sn=round(math.sin(math.radians(angle))*16384)
            body+=f' move.w #{c},x_vector+i(a5)\n clr.w x_vector+j(a5)\n move.w #{-sn},x_vector+k(a5)\n move.w #{sn},z_vector+i(a5)\n clr.w z_vector+j(a5)\n move.w #{c},z_vector+k(a5)\n bclr #yvector_ok,flags(a5)\n'
            render()
            snapshot(f'{label}_{angle}')
    # Guard the viewport through near, off-centre and tiny circle renders.
    for radius,x,y in [(12,0,0),(13,0,0),(60,-110,0),(100,100,40),(200,0,0),(500,450,0),(1200,-1100,600),(4000,3900,0)]:
        for colour in (8,1):
            case(f'Bounds: colour {colour}, radius {radius}, centre {(x,y)}')
            init(colour);render(radius,x,y)
    case('Planet orientation follows both player roll and pitch')
    init(8)
    body+=' move.w #20,roll_angle(a6)\n move.w #20,climb_angle(a6)\n'
    body+=call('set_roll_angles')+call('set_climb_angles')+call('world_z_rotate')+call('world_x_rotate')
    body+=' tst.w x_vector+j(a5)\n beq fail\n tst.w z_vector+j(a5)\n beq fail\n'
    case('Arrival longitude changes orientation only and preserves gameplay RNG')
    init(8)
    body+=' lea ps_map(a6),a0\n lea qa_map(pc),a1\n move.w #ps_features*ps_feature_bytes/2-1,d7\nqa_yaw_save:\n move.w (a0)+,(a1)+\n dbra d7,qa_yaw_save\n move.l #$12345678,random_seed(a6)\n'
    body+=call('turn_planet_surface')
    body+=' cmp.l #$12345678,random_seed(a6)\n bne fail\n tst.w z_vector+i(a4)\n beq fail\n move.w z_vector+i(a4),qa_yaw\n move.l #$fedcba98,random_seed(a6)\n'
    body+=call('turn_planet_surface')
    body+=' cmp.l #$fedcba98,random_seed(a6)\n bne fail\n move.w qa_yaw(pc),d0\n cmp.w z_vector+i(a4),d0\n beq fail\n lea ps_map(a6),a0\n lea qa_map(pc),a1\n move.w #ps_features*ps_feature_bytes/2-1,d7\nqa_yaw_compare:\n move.w (a0)+,d0\n cmp.w (a1)+,d0\n bne fail\n dbra d7,qa_yaw_compare\n'
    # Time only the added detail pass, amortized across 32 renders at 50 Hz.
    for colour in (8,1):
        case(f'68000 timing: colour {colour}, 32 surface passes')
        init(colour);render()
        body+=' clr.w frame_count(a6)\n move.w #31,qa_repeat\n'
        body+=f'qa_benchmark_{colour}:\n'+call('draw_planet_surface')+f' subq.w #1,qa_repeat\n bpl qa_benchmark_{colour}\n move.w frame_count(a6),qa_ticks_{colour}\n'
    snapshot('timing')
    case('An exact horizon vertex is emitted once; clipping fits four vertices')
    init(8)
    body+=' lea qa_horizon(pc),a0\n lea ps_triangle(a6),a1\n moveq #8,d7\nqa_horizon_copy:\n move.w (a0)+,(a1)+\n dbra d7,qa_horizon_copy\n'
    body+=call('ps_triangle_draw')+' cmp.w #3,ps_count(a6)\n bne fail\n'
    case('Features on the far hemisphere do not draw through the globe')
    init(8)
    body+=' lea ps_map(a6),a0\n move.w #ps_features*ps_points-1,d7\nqa_back_map:\n clr.l (a0)+\n move.w #4096,(a0)+\n dbra d7,qa_back_map\n'
    render();snapshot('hidden')
    for name in ('create_system','launch_system'):
        case(f'Actual {name} creation path initializes a complete surface')
        body+=call(name)+' lea planet_rec(a6),a5\n cmp.w #unit,y_vector+j(a5)\n bne fail\n cmp.w #planet,type(a5)\n bne fail\n'
        body+=' tst.w ps_kind(a6)\n beq fail\n'
    case('Station launch with Planets ON chooses a vertical longitude')
    body+=' bset #f_planets,user+1(a6)\n move.l #$12345678,random_seed(a6)\n'
    body+=call('launch_system')+' lea planet_rec(a6),a5\n tst.w z_vector+i(a5)\n beq fail\n cmp.w #unit,y_vector+j(a5)\n bne fail\n tst.w x_vector+j(a5)\n bne fail\n tst.w z_vector+j(a5)\n bne fail\n'
    body+=' move.w x_vector+i(a5),qa_launch_basis\n move.w z_vector+i(a5),qa_launch_basis+2\n move.l random_seed(a6),qa_launch_rng\n lea ps_map(a6),a0\n lea qa_map(pc),a1\n move.w #ps_features*ps_feature_bytes/2-1,d7\nqa_launch_map_save:\n move.w (a0)+,(a1)+\n dbra d7,qa_launch_map_save\n'
    case('Planets OFF launch keeps its orientation and identical gameplay RNG')
    body+=' bclr #f_planets,user+1(a6)\n move.l #$12345678,random_seed(a6)\n'
    body+=call('launch_system')+' lea planet_rec(a6),a5\n cmp.w #unit,x_vector+i(a5)\n bne fail\n cmp.w #unit,y_vector+j(a5)\n bne fail\n cmp.w #unit,z_vector+k(a5)\n bne fail\n tst.w z_vector+i(a5)\n bne fail\n tst.w x_vector+k(a5)\n bne fail\n move.l qa_launch_rng(pc),d0\n cmp.l random_seed(a6),d0\n bne fail\n'
    body+=' lea ps_map(a6),a0\n lea qa_map(pc),a1\n move.w #ps_features*ps_feature_bytes/2-1,d7\nqa_launch_off_map:\n move.w (a0)+,d0\n cmp.w (a1)+,d0\n bne fail\n dbra d7,qa_launch_off_map\n'
    case('A later station launch changes longitude but keeps the seeded geography')
    body+=' bset #f_planets,user+1(a6)\n move.l #$fedcba98,random_seed(a6)\n'
    body+=call('launch_system')+' lea planet_rec(a6),a5\n move.w qa_launch_basis(pc),d0\n cmp.w x_vector+i(a5),d0\n bne.s qa_launch_changed\n move.w qa_launch_basis+2(pc),d0\n cmp.w z_vector+i(a5),d0\n beq fail\nqa_launch_changed:\n cmp.w #unit,y_vector+j(a5)\n bne fail\n tst.w x_vector+j(a5)\n bne fail\n tst.w z_vector+j(a5)\n bne fail\n'
    body+=' lea ps_map(a6),a0\n lea qa_map(pc),a1\n move.w #ps_features*ps_feature_bytes/2-1,d7\nqa_launch_on_map:\n move.w (a0)+,d0\n cmp.w (a1)+,d0\n bne fail\n dbra d7,qa_launch_on_map\n'
    case('Planets OFF draws the original plain globe and skips transformations')
    init(8)
    body+=' bclr #f_planets,user+1(a6)\n move.w #$1234,ps_matrix(a6)\n'
    render();snapshot('disabled')
    body+=' cmp.w #$1234,ps_matrix(a6)\n bne fail\n bset #f_planets,user+1(a6)\n'
    # A clean in-game cockpit capture, separate from the guarded frame checks.
    body+=call('prepare_cockpit')+call('front_view')
    for colour,label in ((8,'sea'),(1,'crater')):
        init(colour)
        body+=call('clear_image')+call('wait_clear')+f' lea planet_rec(a6),a5\n move.w #{48*s["_geometry"]["zoom_y"]},scr_radius(a5)\n clr.w centre_x(a5)\n clr.w centre_y(a5)\n clr.l this_xpos(a5)\n clr.l this_ypos(a5)\n move.l #100000,this_zpos(a5)\n move.w #planet,d0\n'+call('draw_point')
        snapshot('preview_'+label)
    case('Planets OFF survives commander save and restore without other flag changes')
    body+=' move.w #$27aa,user(a6)\n'
    body+=call('options')+' moveq #0,d0\n'+call('change_planets')+call('save_state')+' clr.w user(a6)\n'+call('restore_state')+' cmp.w #$27a8,user(a6)\n bne fail\n'
    body+=call('options')+call('hide_cursor')
    snapshot('options_off',False)
    body+=call('restore_cursor')
    case('Planets ON survives commander save and restore')
    body+=' moveq #1,d0\n'+call('change_planets')+call('save_state')+' move.w #$ffff,user(a6)\n'+call('restore_state')+' cmp.w #$27aa,user(a6)\n bne fail\n'
    body+=call('options')+call('hide_cursor')
    snapshot('options_on',False)
    body+=call('restore_cursor')
    case('Planet Data renders the selected seed at zero rotation without changing flight state')
    body+=call('create_system')
    body+=f' move.l #${s["w_swap_rear"]:x},w_view_ptr(a6)\n'
    body+=' lea ps_map(a6),a0\n lea qa_live(pc),a1\n move.w #ps_work_bytes/2-1,d7\nqa_save_live:\n move.w (a0)+,(a1)+\n dbra d7,qa_save_live\n lea planet_rec(a6),a0\n move.w #obj_len/2-1,d7\nqa_save_object:\n move.w (a0)+,(a1)+\n dbra d7,qa_save_object\n'
    body+=' move.l splanet+seed(a6),qa_seed\n move.w splanet+seed+4(a6),qa_seed+4\n move.w current(a6),qa_current\n move.l w_view_ptr(a6),qa_view\n move.w #8,req_planet(a6)\n moveq #8,d0\n'+call('get_planet_info')+call('data')+call('hide_cursor')
    snapshot('data_on',False)
    body+=call('restore_cursor')+' lea ps_map(a6),a0\n lea qa_live(pc),a1\n move.w #ps_work_bytes/2-1,d7\nqa_check_live:\n move.w (a0)+,d0\n cmp.w (a1)+,d0\n bne fail\n dbra d7,qa_check_live\n lea planet_rec(a6),a0\n move.w #obj_len/2-1,d7\nqa_check_object:\n move.w (a0)+,d0\n cmp.w (a1)+,d0\n bne fail\n dbra d7,qa_check_object\n move.l qa_seed(pc),d0\n cmp.l splanet+seed(a6),d0\n bne fail\n move.w qa_seed+4(pc),d0\n cmp.w splanet+seed+4(a6),d0\n bne fail\n move.w qa_current(pc),d0\n cmp.w current(a6),d0\n bne fail\n move.l qa_view(pc),d0\n cmp.l w_view_ptr(a6),d0\n bne fail\n'
    case('Planet Data zero-rotation portrait is independent of the flight view')
    body+=f' move.l #${s["w_swap_front"]:x},w_view_ptr(a6)\n'+call('data')+call('hide_cursor')
    snapshot('data_on_repeat',False)
    body+=call('restore_cursor')
    case('Planets OFF restores the original bitmap on Planet Data')
    body+=' bclr #f_planets,user+1(a6)\n'+call('data')+call('hide_cursor')
    snapshot('data_off',False)
    body+=call('restore_cursor')
    case('A default commander disables enhanced planets')
    body+=call('default_game')+call('restore_state')+' btst #f_planets,user+1(a6)\n bne fail\n'
    for old_flags in (0x2700,0x2701):
        case(f'Legacy commander flags {old_flags:04x} keep Planets OFF')
        body+=f' move.w #${old_flags:x},user(a6)\n'+call('save_state')+' move.w #$ffff,user(a6)\n'+call('restore_state')+f' cmp.w #${old_flags:x},user(a6)\n bne fail\n btst #f_planets,user+1(a6)\n bne fail\n'
    # Actual hardware RGB must agree with flight, including all alien palettes.
    import re,struct
    ui=list(struct.unpack_from('>16H',(root/'assets/TEXTSCR.PC1').read_bytes(),2))
    flight=list(struct.unpack_from('>16H',(root/'assets/COCKPIT.PC1').read_bytes(),2))
    inhabitants=[tuple(int(v,16) for v in row) for row in re.findall(r'dc\s+\$([0-9a-f]+),\$([0-9a-f]+),\$([0-9a-f]+)',(root/'asm/pdata.m68').read_text().split('inhab_palette:',1)[1],re.I)]
    native=lambda value:((value&0x777)*2)|((value>>2)&0x111)
    ui=list(map(native,ui));flight=list(map(native,flight))
    seeds=[];seed=(0x5a4a,0x0248,0xb753)
    for _ in range(256):
        seeds.append(seed)
        for __ in range(4):seed=(seed[1],seed[2],sum(seed)&65535)
    planet_ids=[7,5,12,14,15,22,28,39,50]
    table=(root/'assets/PLANET_COL.BIN').read_bytes()
    red_planet=table.index(6,0,256)
    if red_planet not in planet_ids:planet_ids.append(red_planet)
    body+=' clr.w galaxy_no(a6)\n clr.w mission(a6)\n move.l #$5a4a0248,gal_seed(a6)\n move.w #$b753,gal_seed+4(a6)\n'
    for planet_id in planet_ids:
        for enabled in (False,True):
            state='on' if enabled else 'off'
            case(f'Planet {planet_id}: actual UI RGB with Planets {state}')
            body+=(' bset' if enabled else ' bclr')+' #f_planets,user+1(a6)\n'
            body+=f' move.w #{planet_id},req_planet(a6)\n move.w #{planet_id},d0\n'+call('get_planet_info')+call('data')+call('hide_cursor')
            expected=ui[:]
            if enabled:expected[6:10]=flight[6:10]
            elif seeds[planet_id][2]&128:expected[7:10]=inhabitants[(seeds[planet_id][2]>>13)&7]
            for ink in range(6,10):
                if enabled:
                    body+=f' move.w ps_portrait_colours(a6),d0\n btst #{ink},d0\n beq qa_rgb_skip_{planet_id}_{ink}\n'
                body+=f' cmp.w #${expected[ink]:x},${s["palette"]:x}+{ink*2}\n bne fail\n'
                if enabled:body+=f'qa_rgb_skip_{planet_id}_{ink}:\n'
            snapshot(f'rgb_{planet_id}_{state}',False)
            body+=call('restore_cursor')
    guards=guard_code(s['_geometry'],call)
    if 'forget_mirror' in s:
        # The guard pattern is a direct Chip RAM write, outside normal drawing.
        guards=guards.replace(' movem.l (sp)+,d0/d7/a0\n', ' move.l scr_base(a6),d0\n add.l #y_top*row_stride,d0\n'+call('forget_mirror')+' movem.l (sp)+,d0/d7/a0\n')
    tail=guards+'qa_frame: dc.l 0\nqa_case: dc.w 0\nqa_snapshot: dc.w 0\nqa_yaw: dc.w 0\nqa_repeat: dc.w 0\nqa_ticks_8: dc.w 0\nqa_ticks_1: dc.w 0\nqa_horizon: dc.w 0,4096,0,-2048,0,-3547,2048,0,-3547\nqa_map: ds.b ps_features*ps_feature_bytes\n'
    tail+='qa_live: ds.b ps_work_bytes+obj_len\nqa_seed: ds.b 6\nqa_current: dc.w 0\nqa_view: dc.l 0\n'
    tail+='qa_palette: ds.w 16\nqa_launch_rng: dc.l 0\nqa_launch_basis: ds.w 2\n'
    return prefix,body,tail,names
