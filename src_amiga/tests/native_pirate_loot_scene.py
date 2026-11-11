"""Render and advance a two-pirate/one-barrel encounter, then a Viper attack."""
from native_pirate_loot import make_suite as helpers

def make_suite(root,s):
    prefix,_,tail,_=helpers(root,s)
    call=lambda n:f' jsr ${s[n]:x}\n'
    body=call('reset_system')+call('prepare_cockpit')+call('front_view')+' bsr qa_world\n'
    names=[];shots=0
    def emit(t):
        nonlocal body
        body+=t
    def case(n):
        names.append(n);emit(f' move.w #{len(names)},qa_case\n')
    def capture(label):
        nonlocal shots
        shots+=1
        emit(' bsr qa_render_scene\n move.l scr_base(a6),qa_frame\n'+f'snap_{label}:\n nop\n')
        if root.name=='src_amiga':emit(f' move.w #{shots},qa_snapshot\nqa_wait_{shots}:\n tst.w qa_snapshot\n bne.s qa_wait_{shots}\n')
    for slot,model,x,y,z in [(3,'krait',-150,0,3600),(4,'gecko',350,100,4000),(5,'barrel',0,-20,2500)]:
        emit(f' lea objects+{slot}*obj_len(a6),a4\n move.w #{model},d0\n move.l #{x},d4\n move.l #{y},d5\n move.l #{z},d6\n bsr qa_create\n')
        if slot<5:emit(' move.w #-unit,x_vector(a4)\n move.w #-unit,z_vector+4(a4)\n move.w #loot_encounter,loot_mode(a4)\n move.w #log_loot,logic(a4)\n')
    emit(' move.w #3,velocity(a4)\n move.w #3,vel_max(a4)\n')
    for slot in (3,4):emit(f' lea objects+{slot}*obj_len(a6),a5\n move.w #{slot},this_obj(a6)\n move.w #{slot},retarget_slot(a6)\n'+call('retarget'))
    case('Rendered initial encounter reserves the only container for one pirate')
    emit(' tst.l objects+3*obj_len+loot_target(a6)\n beq fail\n tst.l objects+4*obj_len+loot_target(a6)\n bne fail\n')
    capture('initial')
    case('Scheduled AI, drift, movement and rendering advance the collector while its partner waits')
    emit(' clr.w qa_frames\nqa_approach_scene:\n bsr qa_step_scene\n addq.w #1,qa_frames\n cmp.w #20,qa_frames\n blo qa_approach_scene\n')
    capture('approaching')
    case('Exactly one pirate scoops the container through interleaved frame updates')
    emit('qa_finish_scene:\n bsr qa_step_scene\n addq.w #1,qa_frames\n cmp.w #1000,qa_frames\n bhs fail\n btst #in_use,objects+5*obj_len+flags(a6)\n bne qa_finish_scene\n cmp.w #1,objects+3*obj_len+loot_count(a6)\n bne fail\n tst.w objects+4*obj_len+loot_count(a6)\n bne fail\n tst.b obj_ctr+barrel(a6)\n bne fail\n')
    for slot in (3,4):emit(f' lea objects+{slot}*obj_len(a6),a5\n move.w #{slot},this_obj(a6)\n move.w #{slot},retarget_slot(a6)\n'+call('retarget')+' cmp.w #loot_departing,loot_mode(a5)\n bne fail\n')
    capture('collected')
    case('An arriving Viper acquires and damages a peaceful scavenger; only the victim retaliates')
    emit(' lea objects+6*obj_len(a6),a4\n move.w #viper,d0\n move.l #600,d4\n moveq #0,d5\n move.l #3500,d6\n bsr qa_create\n move.l a4,a5\n move.w #6,this_obj(a6)\n move.w #6,retarget_slot(a6)\n'+call('retarget')+' cmp.w #log_attack,logic(a5)\n bne fail\n move.l target(a5),a0\n move.l a0,qa_victim\n moveq #1,d0\n'+call('damage_target')+' move.l qa_victim,a0\n tst.w loot_mode(a0)\n bne fail\n cmpa.l target(a0),a5\n bne fail\n')
    capture('police')
    tail+='''qa_render_scene:
'''+call('clear_image')+''' lea objects+3*obj_len(a6),a5
 move.w #3,this_obj(a6)
.loop:
 btst #in_use,flags(a5)
 beq.s .next
'''+call('get_range')+call('draw_object')+'''.next:
 lea obj_len(a5),a5
 addq.w #1,this_obj(a6)
 cmp.w #7,this_obj(a6)
 blo.s .loop
'''+call('draw_all')+''' rts
qa_step_scene:
 lea objects+3*obj_len(a6),a5
 move.w #3,this_obj(a6)
.loop:
 btst #in_use,flags(a5)
 beq.s .next
'''+call('get_range')+call('retarget')+call('do_logic')+call('orthogonal')+call('move')+'''.next:
 lea obj_len(a5),a5
 addq.w #1,this_obj(a6)
 cmp.w #6,this_obj(a6)
 blo.s .loop
 addq.w #1,retarget_slot(a6)
 cmp.w #max_objects,retarget_slot(a6)
 blo.s .slot
 clr.w retarget_slot(a6)
.slot:
'''+call('remove_objects')+''' rts
qa_snapshot: dc.w 0
qa_frame: dc.l 0
qa_ticks_8: dc.w 0
qa_ticks_1: dc.w 0
qa_victim: dc.l 0
'''
    return prefix,body,tail,names
