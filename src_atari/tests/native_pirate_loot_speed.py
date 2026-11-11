"""Native salvage cap, transition and normal-speed restoration scenarios."""
from native_pirate_loot import make_suite as helpers

def make_suite(root,s):
    prefix,_,tail,_=helpers(root,s)
    call=lambda n:f' jsr ${s[n]:x}\n'
    body='';names=[]
    def emit(t):
        nonlocal body
        body+=t
    def case(n):
        names.append(n);emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n')
    def eq(v,f,size='w'):emit(f' cmp.{size} #{v},{f}\n bne fail\n')
    def setup(model='krait',mode='loot_encounter'):
        emit(f' lea objects+3*obj_len(a6),a4\n move.w #{model},d0\n moveq #0,d4\n moveq #0,d5\n move.l #10000,d6\n bsr qa_create\n move.w vel_max(a4),qa_original_max\n move.w vel_max(a4),velocity(a4)\n move.w #{mode},loot_mode(a4)\n move.l #123,loot_origin(a4)\n lea objects+5*obj_len(a6),a4\n move.w #barrel,d0\n moveq #0,d4\n moveq #0,d5\n move.l #12000,d6\n bsr qa_create\n move.l #123,loot_origin(a4)\n lea objects+3*obj_len(a6),a5\n move.w #3,this_obj(a6)\n move.w #3,retarget_slot(a6)\n'+call('retarget'))
    def cap():emit(' bsr qa_check_cap\n')
    def full():
        emit(' move.w #128,qa_speed_steps\nqa_full_'+str(len(names))+':\n move.w #1,on_course(a5)\n move.w #1000,counter(a5)\n'+call('do_run_off')+' subq.w #1,qa_speed_steps\n bne qa_full_'+str(len(names))+'\n move.w qa_original_max,d0\n cmp.w velocity(a5),d0\n bne fail\n cmp.w vel_max(a5),d0\n bne fail\n')
    for model in ('krait','gecko','moray','adder','mamba','asp','sidewinder','boa','wolf'):
        for mode in ('loot_encounter','loot_wreck'):
            case(model+' '+mode+': immediate entry and every approach frame obey the 20 percent cap')
            setup(model,mode);cap()
            emit(' move.w #64,qa_speed_steps\nqa_cap_'+str(len(names))+':\n'+call('do_logic')+' bsr qa_check_cap\n subq.w #1,qa_speed_steps\n bne qa_cap_'+str(len(names))+'\n')
        for phase in ('waiting','lost cargo','pickup','capacity','no cargo','timeout','player hit','Viper hit','cargo theft','cargo destruction'):
            case(model+': '+phase+' preserves the model maximum and applies the correct speed policy')
            setup(model)
            if phase=='waiting':emit(call('loot_release')+call('do_logic'));cap()
            elif phase=='lost cargo':
                emit(' bset #remove,objects+5*obj_len+flags(a6)\n'+call('do_logic'));cap()
            elif phase in ('pickup','capacity'):
                if phase=='capacity':emit(' move.w #3,loot_count(a5)\n')
                emit(' move.l #10080,objects+5*obj_len+zpos(a6)\n'+call('do_logic'))
                eq(4 if phase=='capacity' else 1,'loot_count(a5)')
                if phase=='pickup':cap()
            elif phase=='no cargo':emit(' bset #remove,objects+5*obj_len+flags(a6)\n'+call('do_logic')+call('loot_retarget'))
            elif phase=='timeout':emit(' move.w #loot_approach_steps-1,loot_steps(a5)\n'+call('do_logic'))
            elif phase in ('player hit','Viper hit'):
                emit(' move.l a5,a4\n'+(' suba.l a0,a0\n' if phase=='player hit' else ' lea objects+9*obj_len(a6),a0\n')+call('loot_hit'))
            else:
                emit(' move.l #123,loot_group(a5)\n move.l #123,objects+5*obj_len+loot_group(a6)\n')
                if phase=='cargo theft':emit(' lea objects+5*obj_len(a6),a5\n'+call('loot_provoke_group'))
                else:emit(' lea objects+5*obj_len(a6),a4\n'+call('explode_object'))
                emit(' lea objects+3*obj_len(a6),a5\n')
            if phase in ('capacity','no cargo','timeout'):
                eq('loot_departing','loot_mode(a5)');eq('log_cruise','logic(a5)')
                # Execute the actual departure logic, rather than bypassing it.
                emit(' move.w #128,qa_speed_steps\nqa_depart_'+str(len(names))+':\n'+call('do_logic')+' subq.w #1,qa_speed_steps\n bne qa_depart_'+str(len(names))+'\n move.w qa_original_max,d0\n cmp.w velocity(a5),d0\n bne fail\n')
            elif phase in ('player hit','Viper hit','cargo theft','cargo destruction'):
                eq(0,'loot_mode(a5)');eq('log_attack','logic(a5)');full()
            emit(' move.w qa_original_max,d0\n cmp.w vel_max(a5),d0\n bne fail\n')

    for maximum in (0,1,4,5,9,10,24,25,39,40,255):
        case(f'Integer speed boundary: model maximum {maximum}, including limits below old approach minima')
        setup();emit(f' move.w #{maximum},vel_max(a5)\n move.w #{maximum},qa_original_max\n move.w #255,d0\n'+call('loot_speed'))
        eq(maximum//5,'velocity(a5)');cap()

    case('Pending wreck decision does not slow a pirate before salvage is actually selected')
    emit(' lea objects+3*obj_len(a6),a4\n move.w #krait,d0\n moveq #0,d4\n moveq #0,d5\n move.l #10000,d6\n bsr qa_create\n move.w vel_max(a4),velocity(a4)\n move.l a4,a5\n move.w #loot_pending,loot_mode(a5)\n'+call('loot_retarget')+' move.w vel_max(a5),d0\n cmp.w velocity(a5),d0\n bne fail\n tst.w loot_mode(a5)\n bne fail\n')

    case('A long chase survives the old deadline, then releases the cap at the new bounded deadline')
    setup();emit(' move.w #6,objects+5*obj_len+velocity(a6)\n move.w #6,objects+5*obj_len+vel_max(a6)\n move.w #1024,qa_speed_steps\nqa_escape:\n lea objects+3*obj_len(a6),a5\n'+call('get_range')+call('do_logic')+call('move')+' lea objects+5*obj_len(a6),a5\n'+call('get_range')+call('do_logic')+call('move')+' subq.w #1,qa_speed_steps\n bne qa_escape\n lea objects+3*obj_len(a6),a5\n')
    eq('loot_encounter','loot_mode(a5)');cap()
    emit(' move.w #loot_approach_steps-1,loot_steps(a5)\n'+call('do_logic'))
    eq('loot_departing','loot_mode(a5)');eq(0,'loot_count(a5)');full()

    case('128 real encounters already obey the limit on the creation frame')
    emit(' move.w #128,qa_spawn_checks\nqa_spawn_cap:\n bsr qa_world\n'+call('spawn_loot_encounter')+' lea objects+3*obj_len(a6),a5\n moveq #max_objects-4,d7\nqa_each_spawn:\n cmp.w #loot_encounter,loot_mode(a5)\n bne.s qa_next_spawn\n move.w vel_max(a5),qa_original_max\n bsr qa_check_cap\nqa_next_spawn:\n lea obj_len(a5),a5\n dbra d7,qa_each_spawn\n subq.w #1,qa_spawn_checks\n bne qa_spawn_cap\n')
    tail+='''qa_check_cap:
 movem.l d0-d1,-(sp)
 moveq #0,d0
 move.w qa_original_max,d0
 cmp.w vel_max(a5),d0
 bne fail
 move.w velocity(a5),d1
 bmi fail
 mulu.w #5,d1
 cmp.l d1,d0
 blo fail
 movem.l (sp)+,d0-d1
 rts
qa_original_max: dc.w 0
qa_speed_steps: dc.w 0
qa_spawn_checks: dc.w 0
'''
    return prefix,body,tail,names
