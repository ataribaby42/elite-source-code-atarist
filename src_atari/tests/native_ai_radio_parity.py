"""Replay actual encounters with radio observers enabled/disabled and compare gameplay."""


def make_suite(root,s):
    combat=(root/'asm/combat.m68').read_text()
    prefix=' include "common.def"\n include "macros.m68"\n'+combat[combat.index('\tq_vars combat'):combat.index('\tq_end_vars combat')]+'\n'
    call=lambda n:f' jsr ${s[n]:x}\n'
    out=[];names=[]
    emit=out.append
    hooks=['ai_comm_observe','ai_comm_hit']
    for n in hooks:
        emit(f' move.w ${s[n]:x},qa_saved_{n}\n')
    n='comm_arrival_sound'
    emit(f' move.w ${s[n]:x},qa_saved_beep\n move.w #$4e75,${s[n]:x}\n')
    # Capture all object gameplay bytes and the relevant global outcomes.
    globals=[('random_seed','l'),('rseed1','l'),('registration_state','w'),('score','l'),('cash','l'),('police_record','w'),('mission','w'),('energy','w'),('front_shield','w'),('aft_shield','w'),('energy_fraction','w'),('front_fraction','w'),('aft_fraction','w'),('pirate_count','w'),('trader_count','w'),('tharg_count','w'),('under_attack','w'),('npc_hit','w'),('npc_kill','w'),('who_ecm','w'),('ecm_on','w'),('no_entry','w'),('comm_seed','w')]
    for route in ('pirate_attack','random_encounter','create_pirates'):
        for mission in ([0] if route=='random_encounter' else [0,0x15,0x21,0x41,0x52]):
            for hidden in (0,255):
                for seed in (0x13579b00,0x69428100):
                    names.append(f'{route}, mission ${mission:02X}, hidden ID {hidden}, seed ${seed:08X}: 90 AI steps identical with radio on/off')
                    emit(f' move.w #{len(names)},qa_case\n')
                    for enabled in (False,True):
                        for n in hooks:
                            emit(f' move.w '+(f'qa_saved_{n}' if enabled else '#$4e75')+f',${s[n]:x}\n')
                        emit(' bsr qa_world\n'+f' move.w #{mission},mission(a6)\n move.w #{hidden},scrambled_id(a6)\n move.l #${seed:x},random_seed(a6)\n'+call(route))
                        emit(' move.w #89,qa_steps\n'+f'qa_run_{len(names)}_{int(enabled)}:\n bsr qa_step\n subq.w #1,qa_steps\n bpl qa_run_{len(names)}_{int(enabled)}\n')
                        emit(' lea '+('qa_second' if enabled else 'qa_first')+',a1\n bsr qa_capture\n')
                    emit(' lea qa_first,a0\n lea qa_second,a1\n move.w #qa_snapshot_size/2-1,d7\n'+f'qa_compare_{len(names)}:\n move.w (a0)+,d0\n cmp.w (a1)+,d0\n bne fail\n dbra d7,qa_compare_{len(names)}\n')
    for n in hooks:emit(f' move.w qa_saved_{n},${s[n]:x}\n')
    emit(f' move.w qa_saved_beep,${s["comm_arrival_sound"]:x}\n')
    tail='''qa_world:
'''+call('clear_objects')+call('comm_reset')+'''
 clr.w docked(a6)
 clr.w game_over(a6)
 clr.w witch_space(a6)
 clr.w radar_obj(a6)
 clr.w mission(a6)
 clr.w police_hunt(a6)
 clr.w launch_count(a6)
 clr.w station_destroyed(a6)
 clr.w cloaking_on(a6)
 clr.w npc_hit(a6)
 clr.w npc_kill(a6)
 clr.w visible(a6)
 clr.w no_entry(a6)
 clr.w ecm_on(a6)
 clr.w who_ecm(a6)
 clr.w ecm_jammed(a6)
 clr.w under_attack(a6)
 clr.w retarget_slot(a6)
 clr.w view(a6)
 clr.w cockpit_on(a6)
 clr.w speed(a6)
 clr.w roll_angle(a6)
 clr.w climb_angle(a6)
 clr.w front_fraction(a6)
 clr.w aft_fraction(a6)
 clr.w energy_fraction(a6)
 clr.l score(a6)
 move.l #10000,cash(a6)
 move.w #96,energy(a6)
 move.w #24,front_shield(a6)
 move.w #24,aft_shield(a6)
 move.w #154,hull_laser_resistance(a6)
 move.w #154,hull_missile_resistance(a6)
 move.w #50,police_record(a6)
 move.w #1,pirate_ctr(a6)
 move.w #1,trader_ctr(a6)
 move.w #1,asteroid_ctr(a6)
 move.w #1,shuttle_ctr(a6)
 move.w #7,splanet+govern(a6)
 move.l #20000,station_range(a6)
 move.w #1,tharg_max(a6)
 clr.w tharg_count(a6)
 move.w #6,rating(a6)
 move.w #37,registration_state(a6)
 move.w #71,comm_seed(a6)
 move.w #31,ai_comm_seed(a6)
 move.l #$12345678,rseed1(a6)
 move.l #$4a532a00,player_registration(a6)
 lea planet_rec(a6),a4
 move.b #$87,flags(a4)
 move.w #planet,type(a4)
 lea sun_rec(a6),a4
 move.b #$87,flags(a4)
 move.w #sun,type(a4)
 lea station_rec(a6),a4
 move.b #1,flags(a4)
 move.w #spacestn,type(a4)
 move.w #unit,x_vector+i(a4)
 move.w #unit,y_vector+j(a4)
 move.w #unit,z_vector+k(a4)
 move.l #15000,zpos(a4)
'''+call('create_object')+''' rts
qa_step:
 lea objects+obj_len*3(a6),a5
 move.w #3,this_obj(a6)
.next:
 btst #in_use,flags(a5)
 beq.s .skip
'''+call('ai_comm_tick')+call('ai_laser_tick')+call('get_range')+call('retarget')+call('do_logic')+call('ai_comm_observe')+call('orthogonal')+call('move')+'''
.skip:
 lea obj_len(a5),a5
 addq.w #1,this_obj(a6)
 cmp.w #max_objects,this_obj(a6)
 blo.s .next
 addq.w #1,retarget_slot(a6)
 cmp.w #max_objects,retarget_slot(a6)
 blo.s .slot
 clr.w retarget_slot(a6)
.slot:
'''+call('remove_objects')+''' rts
qa_capture:
 lea objects(a6),a0
 moveq #max_objects-1,d6
.object:
 move.w #radio_instance/2-1,d7
.before:
 move.w (a0)+,(a1)+
 dbra d7,.before
 lea nodes-radio_instance(a0),a0
 move.w #(obj_len-nodes)/2-1,d7
.after:
 move.w (a0)+,(a1)+
 dbra d7,.after
 dbra d6,.object
'''+''.join(f' move.{size} {name}(a6),(a1)+\n' for name,size in globals)+''' rts
qa_case: dc.w 0
qa_steps: dc.w 0
qa_saved_ai_comm_observe: dc.w 0
qa_saved_ai_comm_hit: dc.w 0
qa_saved_beep: dc.w 0
qa_snapshot_size: equ (obj_len-(nodes-radio_instance))*max_objects+'''+str(sum(4 if size=='l' else 2 for _,size in globals))+'''
qa_first: ds.b qa_snapshot_size
qa_second: ds.b qa_snapshot_size
'''
    return prefix,''.join(out),tail,names
