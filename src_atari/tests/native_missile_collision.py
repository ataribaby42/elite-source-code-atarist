"""Native 68000 regressions for missile strength and Cougar mission rewards."""


def make_suite(root, symbols):
    combat = (root / "asm/combat.m68").read_text()
    local_vars = combat[combat.index("\tq_vars combat"):combat.index("\tq_end_vars combat")]
    prefix = ' include "common.def"\n include "macros.m68"\n' + local_vars + "\n"
    parts, names = [], []

    def emit(code):
        parts.append(code)

    def call(name):
        return f" jsr ${symbols[name]:x}\n"

    def case(name):
        names.append(name)
        emit(f"qa_scenario_{len(names)}:\n move.w #{len(names)},qa_case\n bsr qa_world\n")

    def eq(value, field, size="w"):
        emit(f" cmp.{size} #{value},{field}\n bne fail\n")

    def reward():
        eq(1, "obj_ctr+barrel(a6)", "b")
        emit(""" lea objects(a6),a0
 moveq #max_objects-1,d7
.find_reward:
 btst #in_use,flags(a0)
 beq.s .next_reward
 cmp.w #barrel,type(a0)
 beq.s .reward_found
.next_reward:
 lea obj_len(a0),a0
 dbra d7,.find_reward
 bra fail
.reward_found:
""")
        eq(-1, "cargo_type(a0)")
        eq(0, "equip+cloaking_device(a6)")

    case("Unshielded Cobra: 61 energy survives with 1, exactly 60 dies")
    emit(" lea objects(a6),a4\n move.w #cobra,type(a4)\n" + call("create_object"))
    emit(" move.l a4,a5\n clr.w ai_front(a4)\n clr.w ai_aft(a4)\n move.w #61,health(a4)\n" + call("ship_missile_damage"))
    eq(0, "d0")
    eq(1, "health(a4)")
    emit(" move.w #60,health(a4)\n" + call("ship_missile_damage"))
    eq(1, "d0")
    eq(0, "health(a4)")

    case("Cobra AI requires two missiles; station and invincible targets remain immune")
    emit(" lea objects(a6),a4\n move.w #cobra,type(a4)\n" + call("create_object"))
    emit(" move.l a4,a5\n" + call("ship_missile_damage"))
    eq(0, "d0")
    eq(60, "health(a4)")
    eq(0, "ai_front(a4)")
    eq(24, "ai_aft(a4)")
    emit(call("ship_missile_damage"))
    eq(1, "d0")
    for ship in ("spacestn", "dodec"):
        emit(f" move.w #{ship},type(a4)\n move.w #72,health(a4)\n" + call("ship_missile_damage"))
        eq(0, "d0")
        eq(72, "health(a4)")
    emit(" move.w #cobra,type(a4)\n bset #invincible,flags(a4)\n" + call("ship_missile_damage"))
    eq(0, "d0")
    eq(72, "health(a4)")

    case("Full-health Cougar rammed in Cobra: 40 damage, mission ends without reward or bounty")
    emit(" bsr qa_cougar\n" + call("collision"))
    eq(0, "game_over(a6)")
    eq(0, "front_shield(a6)")
    eq(24, "aft_shield(a6)")
    eq(80, "energy(a6)")
    eq("log_exploding", "logic(a5)")
    emit(" btst #no_bounty,flags(a5)\n beq fail\n")
    eq(1000, "score(a6)", "l")
    eq(0, "obj_ctr+barrel(a6)", "b")
    # Finish the actual explosion; it marks the wreck for removal and pays bounty.
    emit(" move.w #1,exp_timer(a5)\n" + call("do_explosion") + call("remove_objects"))
    eq(0, "mission(a6)")
    eq(0, "obj_ctr+cougar(a6)", "b")
    eq(0, "obj_ctr+barrel(a6)", "b")
    eq(0, "equip+cloaking_device(a6)")
    eq(100000, "cash(a6)", "l")

    case("Laser finishing hit on Cougar still releases the cloaking-device canister")
    emit(""" bsr qa_cougar
 move.w #1,health(a5)
 move.w #$ffff,ai_energy_fraction(a5)
 clr.w ai_front(a5)
 clr.w ai_aft(a5)
 move.w #2,laser_power(a6)
 move.w #1,hit_check(a6)
 move.w #1,in_sights(a6)
 move.l #1,this_zpos(a5)
""" + call("check_hit"))
    eq("log_exploding", "objects+obj_len*3+logic(a6)")
    reward()

    case("Successful missile finishing hit on Cougar still releases the reward")
    emit(""" bsr qa_cougar
 move.w #1,health(a5)
 move.w #$ffff,ai_energy_fraction(a5)
 clr.w ai_front(a5)
 clr.w ai_aft(a5)
 clr.w ecm_fitted(a5)
 bsr qa_missile
 lea objects+obj_len*3(a6),a4
 move.l a4,target(a5)
 move.w #log_locked,logic(a5)
""" + call("do_locked"))
    eq("log_exploding", "objects+obj_len*3+logic(a6)")
    reward()

    case("Cougar ECM still prevents an unprotected missile impact")
    emit(""" bsr qa_cougar
 bsr qa_missile
 lea objects+obj_len*3(a6),a4
 move.l a4,target(a5)
 move.w #log_locked,logic(a5)
""" + call("do_locked"))
    eq(96, "objects+obj_len*3+health(a6)")
    eq(24, "objects+obj_len*3+ai_front(a6)")
    eq(0, "obj_ctr+barrel(a6)", "b")
    emit(" btst #remove,flags(a5)\n bne fail\n")

    case("Incoming AI missile deals the same 60 base damage as the player's missile")
    emit(" bsr qa_missile\n" + call("do_missile"))
    eq(0, "front_shield(a6)")
    eq(24, "aft_shield(a6)")
    eq(60, "energy(a6)")

    case("Constrictor retains its fatal collision protection")
    emit(" bsr qa_cougar\n move.w #constr,type(a5)\n" + call("collision"))
    emit(" tst.w game_over(a6)\n beq fail\n")
    eq("no_energy", "reason(a6)")

    tail = """
qa_world:
 lea objects(a6),a0
 move.w #obj_size/2-1,d7
.objects:
 clr.w (a0)+
 dbra d7,.objects
 lea obj_ctr(a6),a0
 move.w #max_obj_num-1,d7
.counters:
 clr.b (a0)+
 dbra d7,.counters
 clr.w player_ship(a6)
 move.w #7,hull_strength(a6)
 move.w #weapon_resistance_base,hull_laser_resistance(a6)
 move.w #weapon_resistance_base,hull_missile_resistance(a6)
 clr.w energy_fraction(a6)
 clr.w front_fraction(a6)
 clr.w aft_fraction(a6)
 move.w #3,hull_class(a6)
 move.w #24,front_shield(a6)
 move.w #24,aft_shield(a6)
 move.w #96,energy(a6)
 move.w #max_rating,rating(a6)
 move.w #$41,mission(a6)
 move.l #100000,cash(a6)
 clr.l score(a6)
 clr.w kill_count(a6)
 clr.w game_over(a6)
 clr.w reason(a6)
 clr.w docked(a6)
 clr.w collided(a6)
 clr.w npc_kill(a6)
 clr.w obj_hit(a6)
 clr.w hit_check(a6)
 clr.w controls_locked(a6)
 clr.w computer_on(a6)
 clr.w witch_space(a6)
 clr.w radar_obj(a6)
 clr.w ecm_on(a6)
 clr.w ecm_jammed(a6)
 clr.w missile_state(a6)
 clr.l target_ptr(a6)
 clr.w equip+cloaking_device(a6)
 clr.w launch_count(a6)
 clr.w trader_count(a6)
 clr.w pirate_count(a6)
 rts
qa_cougar:
 lea objects+obj_len*3(a6),a4
 move.b #1,flags(a4)
 move.w #cougar,type(a4)
""" + call("create_object") + """
 clr.l obj_range(a4)
 move.l #$10000,zpos(a4)
 move.l #-1,target(a4)
 move.l a4,a5
 move.w #3,this_obj(a6)
 rts
qa_missile:
 lea objects+obj_len*4(a6),a4
 move.b #1,flags(a4)
 move.w #missile,type(a4)
""" + call("create_object") + """
 clr.l obj_range(a4)
 move.l #$10000,zpos(a4)
 move.w #2,on_course(a4)
 move.l a4,a5
 move.w #4,this_obj(a6)
 rts
qa_case: dc.w 0
"""
    return prefix, "".join(parts), tail, names
