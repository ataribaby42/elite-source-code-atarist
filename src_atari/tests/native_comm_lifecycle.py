"""Real transition entry points; skip only animations and unrelated dialogs."""
def make_suite(root,s):
    call=lambda n:f' jsr ${s[n]:x}\n'
    prefix=' include "common.def"\n include "macros.m68"\n'
    body=call('hide_cursor')+' clr.w display_clock(a6)\n clr.w mission(a6)\n clr.w player_ship(a6)\n'+call('ship_apply')+call('prepare_cockpit')+call('front_view')
    names=[];tail='qa_case: dc.w 0\n'
    # Preserve the real reset calls before the long death/hyperspace loops.
    hooks=[('q_effects_m68_1','qa_return'),('q_effects_m68_39','qa_return'),
           ('docking_sequence','qa_return'),('start_fade','qa_return'),
           ('courier_dock','qa_return'),('dock_check','qa_return'),('courier_continue','qa_return')]
    for name,label in hooks:
        a=s[name];body+=f' move.l ${a:x},qa_saved_{name}\n move.w ${a+4:x},qa_saved_{name}+4\n move.w #$4ef9,${a:x}\n move.l #{label},${a+2:x}\n'
        tail+=f'qa_saved_{name}: ds.b 6\n'
    for routine,mode,label in [('end_game',0,'Death'),('hyperspace',0,'Hyperspace jump'),('hyperspace',1,'Galactic jump'),('docking',0,'Station docking')]:
        for sent in (1, 2):
            names.append(label+f' clears all pending messages and sent state {sent}')
            if routine != 'docking': body+=' st no_entry(a6)\n'
            body+=f' move.w #{len(names)},qa_case\n clr.w mission(a6)\n clr.w docked(a6)\n clr.w view(a6)\n clr.w rating(a6)\n move.w #{mode},jump_type(a6)\n move.w #1,jump_trigger(a6)\n move.w #7,req_planet(a6)\n move.w #1,galaxy_no(a6)\n move.w #20,jump_count(a6)\n move.w #3,comm_count(a6)\n move.w #1,comm_seed(a6)\n move.w #{sent},comm_arrival_sent(a6)\n'+call(routine)+' tst.w comm_count(a6)\n bne fail\n tst.w comm_seed(a6)\n bne fail\n tst.w comm_arrival_sent(a6)\n bne fail\n'
            if routine != 'docking': body+=' tst.w no_entry(a6)\n bne fail\n'
    # A countdown which has not triggered must leave communications alone.
    names.append('Untriggered hyperspace preserves live messages')
    body+=f' move.w #{len(names)},qa_case\n clr.w jump_trigger(a6)\n move.w #1,comm_arrival_sent(a6)\n move.w #3,comm_count(a6)\n'+call('hyperspace')+' cmp.w #3,comm_count(a6)\n bne fail\n cmp.w #1,comm_arrival_sent(a6)\n bne fail\n'
    for name,_ in hooks:
        a=s[name];body+=f' move.l qa_saved_{name},${a:x}\n move.w qa_saved_{name}+4,${a+4:x}\n'
    tail+='qa_return:\n rts\n'
    return prefix,body,tail,names
