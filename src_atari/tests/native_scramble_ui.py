"""Real Equip entry and Yes/No panel, with deterministic injected input."""
from native_scramble_id import make_suite as base_suite

CAPTURES = 3


def make_suite(root,s):
    prefix, _, tail, _ = base_suite(root,s)
    bios=(root/'asm/bios.m68').read_text()
    prefix+=bios[bios.index('\tq_vars bios'):bios.index('\tq_end_vars bios')]+'\n'
    out,names=[],[]
    emit=out.append
    call=lambda n:f' jsr ${s[n]:x}\n'
    def case(n):
        names.append(n);emit(f' move.w #{len(names)},qa_case\n bsr qa_player_world\n'
            ' clr.w mission(a6)\n clr.w scrambled_id(a6)\n clr.w splanet+govern(a6)\n'
            ' clr.w qa_keys\n clr.w qa_ui_capture\n clr.w qa_capture\n')
    def eq(v,f,size='w'):emit(f' cmp.{size} #{v},{f}\n bne fail\n')
    def snapshot(i):
        emit(call('hide_cursor')+(call('wait_clear') if 'wait_clear' in s else '')+f'snap_{i}:\n nop\n')
        if s.get('_capture_wait'):emit(f' move.w #{i+1},qa_capture\nqa_wait_{i}:\n tst.w qa_capture\n bne.s qa_wait_{i}\n')
        emit(call('restore_cursor'))
    key=s['read_key']
    emit(f' move.l ${key:x},qa_key_original\n move.w ${key+4:x},qa_key_original+4\n'
         f' move.w #$4ef9,${key:x}\n move.l #qa_input,${key+2:x}\n')
    for index,(answer,label) in enumerate(((ord('N'),'N'),(27,'Escape'),(ord('Y'),'Y'),(0,'mouse No'),(1,'mouse Yes'))):
        case(f'Equip: {label} answers the real confirmation and opens normal equipment')
        emit(f' move.w #{answer},qa_answer\n move.w save_idx(a6),qa_stack\n')
        if index==0:emit(' move.w #1,qa_ui_capture\n')
        emit(call('equip_ship'))
        eq(1,'qa_keys');eq(255 if answer in (ord('Y'),1) else 0,'scrambled_id(a6)')
        eq(9950000 if answer in (ord('Y'),1) else 10000000,'cash(a6)','l')
        eq(f'${s["equip_ship_action"]:x}','action_table(a6)','l')
        eq(0,'equip_sell_mode(a6)');eq(0,'button_pressed(a6)')
        emit(' move.w save_idx(a6),d0\n cmp.w qa_stack,d0\n bne fail\n')
        if index==0:snapshot(1)
    case('Active ID: reopening Equip does not offer or charge twice')
    emit(' move.w #255,scrambled_id(a6)\n'+call('equip_ship'));eq(0,'qa_keys');eq(10000000,'cash(a6)','l')
    case('Ordinary government: Equip is immediate with its normal action table')
    emit(' move.w #7,splanet+govern(a6)\n'+call('equip_ship'));eq(0,'qa_keys')
    eq(f'${s["equip_ship_action"]:x}','action_table(a6)','l')
    case('Status displays concealed player registration after successful service')
    emit(' move.l #$4a532a00,player_registration(a6)\n move.w #255,scrambled_id(a6)\n'
         ' clr.w courier_reward(a6)\n clr.w police_record(a6)\n'+call('status'));snapshot(2)
    eq('$3f3f2d3f','registration_buffer(a6)','l');eq('$3f3f','registration_buffer+4(a6)')
    emit(f' move.l qa_key_original,${key:x}\n move.w qa_key_original+4,${key+4:x}\n')
    # Snapshot on the first native keyboard poll: the real panel is on screen.
    helper=f'qa_input:\n cmp.l #${s["confirm_table"]:x},action_table(a6)\n beq.s qa_input_panel\n moveq #0,d0\n rts\nqa_input_panel:\n addq.w #1,qa_keys\n tst.w qa_ui_capture\n beq.s qa_input_answer\n clr.w qa_ui_capture\n'
    helper+=call('hide_cursor')+(call('wait_clear') if 'wait_clear' in s else '')+'snap_0:\n nop\n'
    if s.get('_capture_wait'):helper+=' move.w #1,qa_capture\nqa_wait_0:\n tst.w qa_capture\n bne.s qa_wait_0\n'
    helper+=call('restore_cursor')+'qa_input_answer:\n move.w qa_answer,d0\n cmp.w #1,d0\n bhi.s qa_input_done\n'
    # Click through the real cursor hit-testing rather than writing its result.
    zx='*zoom_x' if root.name=='src_amiga' else ''
    zy='*zoom_y' if root.name=='src_amiga' else ''
    helper+=call('hide_cursor')+f' move.w #(190-10){zx},cursor_spr+sp_xpos(a6)\n tst.w qa_answer\n beq.s qa_mouse_y\n'
    helper+=f' move.w #(126-10){zx},cursor_spr+sp_xpos(a6)\nqa_mouse_y:\n move.w #(103-8){zy},cursor_spr+sp_ypos(a6)\n'
    helper+=call('restore_cursor')+call('single_click')+' moveq #0,d0\nqa_input_done:\n rts\n'
    tail+=helper+'qa_answer: dc.w 0\nqa_keys: dc.w 0\nqa_ui_capture: dc.w 0\nqa_capture: dc.w 0\nqa_stack: dc.w 0\nqa_key_original: ds.b 6\n'
    return prefix,''.join(out),tail,names
