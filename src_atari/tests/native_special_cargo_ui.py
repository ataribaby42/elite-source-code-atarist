"""Exercise real menu click dispatch, contract details, Status and charts."""
from native_special_cargo import make_suite as base_suite, offers, worlds

CAPTURES=10

def make_suite(root,s):
    prefix,_,tail,_=base_suite(root,s)
    bios=(root/'asm/bios.m68').read_text()
    prefix+=bios[bios.index('\tq_vars bios'):bios.index('\tq_end_vars bios')]+'\n'
    out=[];names=[]
    emit=out.append
    call=lambda n:f' jsr ${s[n]:x}\n'
    def case(n):
        names.append(n);emit(f' move.w #{len(names)},qa_case\n')
    def eq(v,f,size='w'):emit(f' cmp.{size} #{v},{f}\n bne fail\n')
    def snapshot(n):
        emit(call('hide_cursor')+(' '+call('wait_clear') if 'wait_clear' in s else '')+f'snap_{n}:\n nop\n')
        if s.get('_capture_wait'):emit(f' move.w #{n+1},qa_capture\nqa_wait_{n}:\n tst.w qa_capture\n bne.s qa_wait_{n}\n')
        emit(call('restore_cursor'))
    def click(x,y,double=False,expected=None):
        zoom='*zoom_x' if root.name=='src_amiga' else ''
        zoomy='*zoom_y' if root.name=='src_amiga' else ''
        emit(call('hide_cursor')+f' move.w #({x}-10){zoom},cursor_spr+sp_xpos(a6)\n move.w #({y}-8){zoomy},cursor_spr+sp_ypos(a6)\n'+call('restore_cursor'))
        emit(' clr.w button_pressed(a6)\n'+call('double_click' if double else 'single_click')+' tst.w button_pressed(a6)\n beq fail\n')
        if expected:emit(f' cmp.l #${s[expected]:x},action_ptr(a6)\n bne fail\n')
        emit(' clr.w button_pressed(a6)\n move.w function(a6),d0\n move.l action_ptr(a6),a0\n jsr (a0)\n')
    market=next(m for m in range(256) if len(offers(0,7,m,0,0,0,(0,0)))==15)
    rows=offers(0,7,market,0,0,0,(0,0));first=rows[0]
    emit(' bsr qa_world\n bsr qa_courier_world\n clr.l score(a6)\n clr.w police_record(a6)\n'+f' move.w #{market},fluctuation(a6)\n')
    case('Buy retains commodity icons and opens Special via the blue title word')
    emit(call('buy_cargo'));eq(0,'courier_mode(a6)');snapshot(0)
    click(128,'title_y+3',expected='courier_open');eq(1,'courier_mode(a6)');eq(len(rows),'courier_count(a6)');eq(0,'courier_reward(a6)');snapshot(1)
    case('Single click accepts exactly the chosen visible row and immediately opens details')
    click(20,29,expected='courier_click');eq(first[4],'courier_reward(a6)');eq(10000000-first[3],'cash(a6)','l');snapshot(2)
    case('Bottom Buy returns to commodities; reopening Special shows the same contract without charging')
    click(68,178,expected='buy_cargo');eq(0,'courier_mode(a6)');click(128,'title_y+3',expected='courier_open')
    eq(first[4],'courier_reward(a6)');eq(10000000-first[3],'cash(a6)','l')
    case('Status displays active destination and value after equipment graphics')
    emit(call('status'));snapshot(3);eq(first[4],'courier_reward(a6)')
    case('No-contract offer screen and empty-row click cannot charge the player')
    none=next(m for m in range(256) if not offers(0,7,m,0,0,0,(0,0)))
    emit(' clr.l courier_reward(a6)\n'+f' move.w #{none},fluctuation(a6)\n'+call('courier_open'));eq(0,'courier_count(a6)');snapshot(4)
    click(20,29,expected='courier_click');eq(0,'courier_reward(a6)');eq(10000000-first[3],'cash(a6)','l')
    case('Maximum value fits on Status and preserves ordinary inventory and navigation')
    seed=worlds(0)[0];xy=((seed[1]>>8)<<8)|(seed[0]>>8)
    emit(f' move.w #65535,courier_reward(a6)\n move.w #{xy},courier_x(a6)\n move.w #45,req_planet(a6)\n move.l #12345,hold(a6)\n'+call('status'));snapshot(5)
    eq(45,'req_planet(a6)');eq(12345,'hold(a6)','l');eq(65535,'courier_reward(a6)')
    case('Real delivery wrapper displays the paid amount then returns for story mission handling')
    emit(f' move.b #{seed[1]>>8},splanet+seed+2(a6)\n move.b #{seed[0]>>8},splanet+seed(a6)\n'+call('courier_dock'))
    eq(0,'courier_reward(a6)');eq(10000000-first[3]+65535,'cash(a6)','l');snapshot(6)
    case('W selects the delivery on the local chart even outside its visible region')
    emit(' move.w #5250,courier_reward(a6)\n'+call('gen_prices')+call('local_chart')+call('courier_chart_key'));eq(0,'req_planet(a6)');snapshot(7)
    case('W selects the delivery on the galactic chart and respects hyperspace countdown')
    emit(call('galactic_chart')+' move.w #45,req_planet(a6)\n move.w #3,count_down(a6)\n'+call('courier_chart_key'));eq(45,'req_planet(a6)')
    emit(' clr.w count_down(a6)\n'+call('courier_chart_key'));eq(0,'req_planet(a6)');snapshot(8)
    case('Special title switches back to Buy, including a double click')
    emit(call('courier_open'));click(128,'title_y+3',True,'buy_cargo');eq(0,'courier_mode(a6)');snapshot(9)
    case('The fifteenth offer is visible, clickable, and charges its own fee')
    emit(' bsr qa_world\n bsr qa_courier_world\n clr.l score(a6)\n clr.w police_record(a6)\n'+f' move.w #{market},fluctuation(a6)\n'+call('courier_open'))
    eq(15,'courier_count(a6)');click(20,141,expected='courier_click')
    eq(rows[14][4],'courier_reward(a6)');eq(10000000-rows[14][3],'cash(a6)','l')
    emit(call('hide_cursor'))
    tail+='qa_capture: dc.w 0\n'
    return prefix,''.join(out),tail,names
