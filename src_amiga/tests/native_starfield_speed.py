"""Run speed-reference checks against the linked MC68000 starfield routines."""
def make_suite(root, s):
    source = (root / 'asm/dust.m68').read_text()
    layout = source[source.index('    rsset 0'):source.index('    q_module dust')]
    prefix = ' include "common.def"\n include "macros.m68"\n' + layout
    parts = []
    names = []
    call = lambda name: f' jsr ${s[name]:x}\n'
    def emit(text):
        parts.append(text)
    def case(name):
        names.append(name)
        emit(f' move.w #{len(names)},qa_case\n')
    def eq(value, field):
        emit(f' cmp.w #{value},{field}\n bne fail\n')
    def setup():
        emit(' movem.l d6-d7,-(sp)\n' + call('setup_dust') + ' movem.l (sp)+,d6-d7\n')
    speeds = [22,19,24,20,20,24,16,19,11,31,29,24,25]
    emit(' clr.w cockpit_on(a6)\n clr.w csr_on(a6)\n clr.w display_clock(a6)\n'
         ' clr.l roll_sin(a6)\n clr.l climb_sin(a6)\n'
         ' move.l #$1000000,roll_cos(a6)\n move.l #$1000000,climb_cos(a6)\n')
    for hull, speed in enumerate(speeds):
        case(f'Hull {hull}: absolute speed, hull limit, retro reversal and jump rates in all four views')
        emit(f' move.w #{hull},player_ship(a6)\n' + call('ship_apply'))
        emit(f' moveq #3,d7\nqa_hull_{hull}:\n move.w d7,view(a6)\n clr.w retro_count(a6)\n clr.w dust_type(a6)\n')
        for actual in (0,10,speed,speed+1):
            emit(f' move.w #{actual},speed(a6)\n')
            setup()
            eq(64+min(actual,speed)*2048//22,'dust_step(a6)')
            emit(' cmp.w dust_motion(a6),d7\n bne fail\n')
        for remaining in (500,250,1):
            emit(f' move.w #{remaining},retro_count(a6)\n')
            setup()
            eq(64+(remaining*speed//500)*2048//22,'dust_step(a6)')
            emit(' move.w d7,d6\n eor.w #1,d6\n cmp.w dust_motion(a6),d6\n bne fail\n')
        for effect in (1,2):
            emit(f' move.w #{effect},dust_type(a6)\n')
            setup()
            eq(128,'dust_step(a6)')
        emit(f' dbra d7,qa_hull_{hull}\n')
    case('Cobra Mk III retains every step of its existing normal-flight speed curve')
    emit(' clr.w player_ship(a6)\n' + call('ship_apply'))
    emit(' clr.w view(a6)\n clr.w dust_type(a6)\n clr.w retro_count(a6)\n')
    for speed in range(23):
        emit(f' move.w #{speed},speed(a6)\n')
        setup()
        eq(64+speed*2048//22,'dust_step(a6)')
    return prefix, ''.join(parts), 'qa_case: dc.w 0\n', names
