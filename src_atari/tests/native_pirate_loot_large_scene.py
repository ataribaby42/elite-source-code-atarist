"""Render the real ten-object formation and steal cargo through collision."""
from native_pirate_loot import make_suite as helpers

def make_suite(root,s):
    prefix,_,tail,_=helpers(root,s)
    call=lambda n:f' jsr ${s[n]:x}\n'
    body=call('reset_system')+call('prepare_cockpit')+call('front_view')+call('gen_prices')+' bsr qa_world\n'
    names=[];shots=0
    def emit(t):
        nonlocal body
        body+=t
    def case(n):
        names.append(n);emit(f' move.w #{len(names)},qa_case\n')
    def capture(label):
        nonlocal shots
        shots+=1
        emit(' bsr qa_render_large\n move.l scr_base(a6),qa_frame\n'+f'snap_{label}:\n nop\n')
        if root.name=='src_amiga':emit(f' move.w #{shots},qa_snapshot\nqa_wait_{shots}:\n tst.w qa_snapshot\n bne.s qa_wait_{shots}\n')
    case('Real eight-container/two-pirate formation renders the maximum group through the real drawing routines')
    r=s['rand']
    emit(f' move.l ${r:x},qa_saved_rand\n move.w ${r+4:x},qa_saved_rand+4\n move.w #$4ef9,${r:x}\n move.l #qa_rand,${r+2:x}\n st qa_force_cargo\n move.w #4,qa_cargo_roll\n move.w #1,qa_small_left\n move.w #1,qa_small_second\n'+call('spawn_loot_encounter')+f' move.l qa_saved_rand,${r:x}\n move.w qa_saved_rand+4,${r+4:x}\n')
    emit(' cmp.b #8,obj_ctr+barrel(a6)\n bne fail\n cmp.w #2,pirate_count(a6)\n bne fail\n bsr qa_spawn_positions\n movem.l objects+3*obj_len+xpos(a6),d4-d6\n sub.l #8000,d6\n lea objects+3*obj_len(a6),a4\n moveq #9,d7\nqa_close:\n sub.l d4,xpos(a4)\n sub.l d5,ypos(a4)\n sub.l d6,zpos(a4)\n lea obj_len(a4),a4\n dbra d7,qa_close\n')
    capture('large_initial')
    case('Both pirates collect independently during real movement of the larger group')
    for slot in (11,12):
        emit(f' lea objects+{slot}*obj_len(a6),a5\n move.w #{slot},this_obj(a6)\n move.w #{slot},retarget_slot(a6)\n'+call('retarget')+' tst.l loot_target(a5)\n beq fail\n')
    emit(' move.l objects+11*obj_len+loot_target(a6),d0\n cmp.l objects+12*obj_len+loot_target(a6),d0\n beq fail\n clr.w qa_frames\nqa_large_advance:\n bsr qa_step_large\n addq.w #1,qa_frames\n cmp.w #20,qa_frames\n blo qa_large_advance\n')
    capture('large_collecting')
    case('Player collision scoops a group barrel and immediately redirects both pirates')
    emit(' lea hold(a6),a0\n moveq #max_products-1,d7\nqa_empty_hold:\n clr.l (a0)+\n dbra d7,qa_empty_hold\n move.w #1,equip+fuel_scoop(a6)\n clr.w equip+cargo_bay(a6)\n'+call('ship_equipment_mass')+' add.w #20,d0\n move.w d0,hull_cargo(a6)\n lea objects+3*obj_len(a6),a5\n move.l #0,xpos(a5)\n move.l #-20,ypos(a5)\n move.l #100,zpos(a5)\n move.w #1,cargo_type(a5)\n move.l #123456,cargo_mass(a5)\n clr.w computer_on(a6)\n clr.w controls_locked(a6)\n'+call('get_range')+call('collision')+' cmp.l #123456,hold+4(a6)\n bne fail\n')
    for slot in (11,12):
        emit(f' cmp.w #log_attack,objects+{slot}*obj_len+logic(a6)\n bne fail\n tst.l objects+{slot}*obj_len+target(a6)\n bne fail\n tst.l objects+{slot}*obj_len+loot_target(a6)\n bne fail\n')
    emit(call('remove_objects')+' cmp.b #7,obj_ctr+barrel(a6)\n bne fail\n')
    capture('large_theft')
    tail+='''qa_render_large:
'''+call('clear_image')+''' lea objects+3*obj_len(a6),a5
 move.w #3,this_obj(a6)
.loop:
 btst #in_use,flags(a5)
 beq.s .next
'''+call('get_range')+call('draw_object')+'''.next:
 lea obj_len(a5),a5
 addq.w #1,this_obj(a6)
 cmp.w #13,this_obj(a6)
 blo.s .loop
'''+call('draw_all')+''' rts
qa_step_large:
 lea objects+3*obj_len(a6),a5
 move.w #3,this_obj(a6)
.loop:
 btst #in_use,flags(a5)
 beq.s .next
'''+call('get_range')+call('retarget')+call('do_logic')+call('orthogonal')+call('move')+'''.next:
 lea obj_len(a5),a5
 addq.w #1,this_obj(a6)
 cmp.w #13,this_obj(a6)
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
'''
    return prefix,body,tail,names
