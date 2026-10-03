"""Validate per-ship laser selection in the linked 68000 game, not a port of it."""
import importlib.util

ORDINARY = ['cobra','adder','gecko','moray','cobra_mk1','ferdelance','python',
            'boa','anaconda','asp','sidewinder','krait','mamba','worm','viper',
            'wolf','shuttle','transporter']


def make_suite(root, s):
    spec=importlib.util.spec_from_file_location('loadout_world',root/'tests/native_missile_collision.py')
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    prefix,_,tail,_=base.make_suite(root,s)
    parts=[];names=[]
    def emit(t): parts.append(t)
    def call(n): return f' jsr ${s[n]:x}\n'
    def case(n):
        names.append(n);emit(f' move.w #{len(names)},qa_case\n bsr qa_world\n')
    def eq(v,f,size='w'): emit(f' cmp.{size} #{v},{f}\n bne fail\n')
    def patch(n,label):
        a=s[n]
        emit(f' move.l ${a:x},qa_saved_{n}\n move.w ${a+4:x},qa_saved_{n}+4\n move.w #$4ef9,${a:x}\n move.l #{label},${a+2:x}\n')
    def restore(n):
        a=s[n];emit(f' move.l qa_saved_{n},${a:x}\n move.w qa_saved_{n}+4,${a+4:x}\n')
    def spawn(model,slot=3):
        emit(f' lea objects+obj_len*{slot}(a6),a4\n move.b #1,flags(a4)\n move.w #{model},type(a4)\n'+call('create_object'))
    patch('ai_laser_roll','qa_percentile')
    for rating in range(9):
        band=rating//3
        case(f'Rating {rating}: all 100 percentiles for all 18 ordinary hulls; power, colour, persistence and preserved registers')
        emit(f' lea objects+obj_len*3(a6),a4\n move.l a4,a5\n moveq #17,d6\nqa_models_{rating}:\n lea qa_models(pc),a0\n move.w d6,d0\n add.w d0,d0\n move.w (a0,d0.w),type(a4)\n moveq #0,d5\nqa_percent_{rating}:\n move.w #{rating},rating(a6)\n move.w d5,qa_percent\n clr.w qa_draws\n move.w #$dead,ai_laser_loadout(a4)\n move.l #$12345678,d0\n move.l #$34567890,d1\n'+call('init_ship_laser'))
        eq('$12345678','d0','l');eq('$34567890','d1','l');eq(1,'qa_draws')
        emit(f' lea qa_expected_{band}(pc),a0\n move.w d5,d0\n add.w d0,d0\n move.w (a0,d0.w),d4\n cmp.w ai_laser_loadout(a4),d4\n bne fail\n move.w #{8-rating},rating(a6)\n'+call('ai_laser_power')+' cmp.w d4,d0\n bne fail\n'+call('ai_laser_palette'))
        emit(f' lea qa_colours_{band}(pc),a0\n cmp.b (a0,d5.w),d0\n bne fail\n')
        eq(1,'qa_draws')
        emit(f' addq.w #1,d5\n cmp.w #100,d5\n blo qa_percent_{rating}\n dbra d6,qa_models_{rating}\n')
        for model in ('constr','cougar','thargoid','thargon'):
            power=11 if model=='constr' else 9 if model=='cougar' else (5,9,11)[band]
            colour=15 if model=='constr' else 3 if model=='cougar' else 10
            case(f'{model}, rating {rating}: fixed power {power}, colour {colour}, no loadout RNG')
            emit(f' move.w #{rating},rating(a6)\n clr.w qa_draws\n')
            spawn(model)
            eq(power,'ai_laser_loadout(a4)');eq(0,'qa_draws')
            emit(' move.l a4,a5\n'+call('ai_laser_palette'));eq(colour,'d0')
            emit(f' move.w #{8-rating},rating(a6)\n'+call('ai_laser_power'));eq(power,'d0')
    # Check real construction, model-header copying, independent active slots
    # and both extremes of the pool (including the very last object).
    for slot,percent,power in ((3,0,5),(4,70,9),('(max_objects-1)',99,11)):
        case(f'Creation in slot {slot}: stores expected power {power}; other slots remain untouched')
        emit(f' move.w #6,rating(a6)\n move.w #{percent},qa_percent\n move.w #$1234,objects+obj_len*2+ai_laser_loadout(a6)\n')
        for model in ORDINARY:
            spawn(model,slot);eq(power,'ai_laser_loadout(a4)')
            eq('$1234','objects+obj_len*2+ai_laser_loadout(a6)')
    case('Copied wingman rerolls without changing the parent; existing loadouts consume no RNG')
    emit(' move.w #6,rating(a6)\n move.w #99,qa_percent\n');spawn('cobra')
    emit(' move.l a4,a5\n lea objects+obj_len*4(a6),a4\n'+call('copy_object')+' clr.w qa_percent\n'+call('create_object'))
    eq(5,'ai_laser_loadout(a4)');eq(11,'ai_laser_loadout(a5)')
    emit(' clr.w qa_draws\n clr.w rating(a6)\n'+call('ai_laser_power'));eq(11,'d0')
    emit(call('ai_laser_palette'));eq(15,'d0');eq(0,'qa_draws')
    for model in ('missile','barrel','asteroid','platlet','spacestn','dodec','panels','planet','sun','photon'):
        case(f'{model}: converting a ship clears its loadout without a loadout roll')
        spawn('cobra');emit(f' move.w #{model},type(a4)\n clr.w qa_draws\n'+call('create_object'))
        eq(0,'ai_laser_loadout(a4)');eq(0,'qa_draws')
    case('Removal resets only the removed loadout; allocating a dirty slot clears it')
    spawn('cobra');emit(' move.w #11,objects+obj_len*4+ai_laser_loadout(a6)\n move.l a4,a5\n'+call('remove_object'))
    eq(0,'objects+obj_len*3+ai_laser_loadout(a6)');eq(11,'objects+obj_len*4+ai_laser_loadout(a6)')
    emit(' move.w #11,objects+ai_laser_loadout(a6)\n'+call('alloc_object')+' bcc fail\n');eq(0,'ai_laser_loadout(a4)')
    case('Clearing the bubble clears every loadout')
    emit(' lea objects(a6),a4\n moveq #max_objects-1,d7\nqa_dirty:\n move.w #11,ai_laser_loadout(a4)\n lea obj_len(a4),a4\n dbra d7,qa_dirty\n'+call('clear_objects')+' lea objects(a6),a4\n moveq #max_objects-1,d7\nqa_clear:\n tst.w ai_laser_loadout(a4)\n bne fail\n lea obj_len(a4),a4\n dbra d7,qa_clear\n')
    restore('ai_laser_roll')
    patch('random','qa_raw_random')
    case('All 256 raw bytes: 0..199 maps twice to each percentile; 200..255 retries exactly once')
    emit(' moveq #0,d5\nqa_bytes:\n move.w d5,qa_raw\n clr.w qa_draws\n'+call('ai_laser_roll')+''' moveq #1,d1
 move.w d5,d2
 cmp.w #200,d2
 blo.s qa_accepted_byte
 moveq #2,d1
 moveq #42,d2
qa_accepted_byte:
 cmp.w #100,d2
 blo.s qa_byte_check
 sub.w #100,d2
qa_byte_check:
 cmp.w d2,d0
 bne fail
 cmp.w qa_draws,d1
 bne fail
 addq.w #1,d5
 cmp.w #256,d5
 blo qa_bytes
''')
    restore('random')
    # Real game PRNG, three independent nonzero seeds and 20,000 fresh loadouts
    # per band/seed. A one-percentage-point tolerance is deliberately generous;
    # exhaustive boundary checks above verify the exact intended percentages.
    for seed_index,seed in enumerate((0x13579b00,0xabcdef00,0x10203000)):
        for band,probs in enumerate(((90,7,3),(70,21,9),(50,35,15))):
            index=seed_index*3+band
            case(f'Real PRNG seed {seed:08X}, band {band}: 20000 new loadouts within 1 percentage point of {probs}')
            emit(f' move.l #${seed:x},random_seed(a6)\n move.w #{band*3},rating(a6)\n lea objects+obj_len*3(a6),a4\n move.w #cobra,type(a4)\n lea qa_histogram+{index*6},a3\n clr.l (a3)\n clr.w 4(a3)\n move.w #19999,d6\nqa_samples_{index}:\n'+call('init_ship_laser')+f''' moveq #0,d0
 cmp.w #5,ai_laser_loadout(a4)
 beq.s qa_count_{index}
 moveq #2,d0
 cmp.w #9,ai_laser_loadout(a4)
 beq.s qa_count_{index}
 moveq #4,d0
 cmp.w #11,ai_laser_loadout(a4)
 bne fail
qa_count_{index}:
 addq.w #1,(a3,d0.w)
 dbra d6,qa_samples_{index}
''')
            for n,p in enumerate(probs):
                emit(f' cmp.w #{p*200-200},{n*2}(a3)\n blo fail\n cmp.w #{p*200+200},{n*2}(a3)\n bhi fail\n')
    tail+='''
qa_percentile:
 addq.w #1,qa_draws
 move.w qa_percent,d0
 rts
qa_raw_random:
 move.w qa_raw,d0
 tst.w qa_draws
 beq.s qa_first_byte
 moveq #42,d0
qa_first_byte:
 addq.w #1,qa_draws
 rts
qa_saved_ai_laser_roll: ds.b 6
qa_saved_random: ds.b 6
qa_percent: dc.w 0
qa_raw: dc.w 0
qa_draws: dc.w 0
qa_histogram: ds.w 27
qa_models: dc.w '''+','.join(ORDINARY)+'\n'
    for band,probs in enumerate(((90,7,3),(70,21,9),(50,35,15))):
        powers=[5]*probs[0]+[9]*probs[1]+[11]*probs[2]
        tail+=f'qa_expected_{band}: dc.w '+','.join(map(str,powers))+'\n'
        tail+=f'qa_colours_{band}: dc.b '+','.join(str({5:6,9:3,11:15}[p]) for p in powers)+'\n even\n'
    return prefix,''.join(parts),tail,names
