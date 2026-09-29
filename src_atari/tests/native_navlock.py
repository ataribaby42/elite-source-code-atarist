"""Exercise the actual compass drawing, N dispatch and lifecycle resets on 68000."""


def make_suite(root, symbols):
    prefix = ' include "common.def"\n include "macros.m68"\n'
    flight = (root / "asm/flight.m68").read_text()
    main = (root / "asm/main.m68").read_text()
    prefix += next(line for line in main.splitlines() if line.startswith("spcstn_space:")) + "\n"
    prefix += flight[flight.index("\tq_vars flight"):flight.index("\tq_end_vars flight")] + "\n"
    parts, names = [], []

    def emit(code):
        parts.append(code)

    def call(name):
        return f" jsr ${symbols[name]:x}\n"

    def case(name):
        names.append(name)
        emit(f" move.w #{len(names)},qa_case\n")

    def eq(value, field):
        emit(f" cmp.w #{value},{field}\n bne fail\n")

    def press_n(message):
        emit(" clr.w check_key(a6)\n moveq #'N',d0\n" + call("check"))
        emit(f" lea {message}(pc),a0\n bsr qa_message\n")

    def compass(index, selected, screen=1):
        emit(f" move.l screen{screen}_ptr(a6),scr_base(a6)\n" + call("remove_radar"))
        emit(f""" move.w #-777,radar{screen}_spr+sp_xpos(a6)
 move.w #{index},this_obj(a6)
 lea objects+obj_len*{index}(a6),a5
 clr.l xpos(a5)
 clr.l ypos(a5)
 move.l #10000,zpos(a5)
""" + call("mini_radar"))
        eq("216" if selected else "-777", f"radar{screen}_spr+sp_xpos(a6)")

    emit(" clr.w csr_on(a6)\n clr.w display_clock(a6)\n")
    case("New game resets Star mode")
    emit(" move.w #1,nav_star(a6)\n" + call("default_game"))
    eq(0, "nav_star(a6)")
    emit(call("restore_state"))

    case("Commander save does not change mode; restoring it resets to Planet/Station")
    emit(" move.w #1,nav_star(a6)\n" + call("save_state"))
    eq(1, "nav_star(a6)")
    emit(call("restore_state"))
    eq(0, "nav_star(a6)")

    case("N while docked leaves the compass mode unchanged")
    emit(" st docked(a6)\n clr.w check_key(a6)\n moveq #'N',d0\n" + call("check"))
    eq(0, "nav_star(a6)")

    for sequence in (False, True):
        case(f"Station launch resets Star mode with launch animation {sequence}")
        emit(" move.w #1,nav_star(a6)\n st docked(a6)\n")
        emit((" bset" if sequence else " bclr") + " #f_sequence,user(a6)\n")
        emit(call("launch"))
        eq(0, "nav_star(a6)")
        eq(0, "docked(a6)")

    case("N dispatch selects Star and writes the exact message")
    emit(" move.w #1,radar_obj(a6)\n")
    press_n("qa_star")
    eq(1, "nav_star(a6)")
    eq(1, "radar_obj(a6)")

    case("N dispatch returns to Planet/Station and writes the exact message")
    press_n("qa_planet")
    eq(0, "nav_star(a6)")
    eq(1, "radar_obj(a6)")

    case("Planet mode draws only the planet on both display buffers")
    emit(" clr.w radar_obj(a6)\n clr.w witch_space(a6)\n")
    for screen in (1, 2):
        compass(1, False, screen)
        compass(2, False, screen)
        compass(0, True, screen)

    case("Station mode draws only the station on both display buffers")
    emit(" move.w #1,radar_obj(a6)\n")
    for screen in (1, 2):
        compass(0, False, screen)
        compass(2, False, screen)
        compass(1, True, screen)

    case("Star mode draws only the star and preserves station-space detection")
    press_n("qa_star")
    for screen in (1, 2):
        compass(0, False, screen)
        compass(1, False, screen)
        compass(2, True, screen)
    eq(1, "radar_obj(a6)")

    case("Station-zone entry and exit update the S state without changing Star mode")
    emit(" clr.w radar_obj(a6)\n clr.w station_destroyed(a6)\n move.w #-1,checkpoint(a6)\n clr.l planet_range(a6)\n")
    emit(call("radar_lock"))
    eq(1, "radar_obj(a6)")
    eq(1, "nav_star(a6)")
    emit(" move.l #spcstn_space+1024,planet_range(a6)\n" + call("radar_lock"))
    eq(0, "radar_obj(a6)")
    eq(1, "nav_star(a6)")

    case("Flight menu and view changes preserve Star mode")
    emit(call("status") + call("front_view") + call("rear_view"))
    eq(1, "nav_star(a6)")
    emit(call("front_view"))
    eq(1, "nav_star(a6)")

    case("Witchspace does not draw a nonexistent star")
    emit(" st witch_space(a6)\n")
    compass(2, False)
    emit(" clr.w witch_space(a6)\n")

    for galactic, witch, name in ((False, False, "Hyperspace"),
                                  (True, False, "Galactic jump"),
                                  (False, True, "Forced witchspace jump")):
        case(name + " resets Star mode")
        emit(""" move.w #1,nav_star(a6)
 clr.w mission(a6)
 move.w #64,jump_count(a6)
 clr.w count_down(a6)
 clr.w fuel_needed(a6)
 move.w #8,req_planet(a6)
 move.w galaxy_no(a6),qa_galaxy
""")
        emit((" st" if witch else " clr.b") + " key_states+$38(a6)\n")
        emit((" st" if galactic else " clr.w") + " jump_type(a6)\n st jump_trigger(a6)\n")
        emit(call("hyperspace"))
        eq(0, "nav_star(a6)")
        emit(" move.w qa_galaxy(pc),d0\n")
        if galactic:
            emit(" addq.w #1,d0\n and.w #7,d0\n")
        emit(" cmp.w galaxy_no(a6),d0\n bne fail\n")
        if witch:
            emit(" tst.w witch_space(a6)\n beq fail\n")
    emit(" clr.b key_states+$38(a6)\n")

    tail = """
qa_message:
 lea text_buffer(a6),a1
.compare:
 move.b (a0)+,d0
 cmp.b (a1)+,d0
 bne fail
 tst.b d0
 bne.s .compare
 rts
qa_star: dc.b 'NavLock Star',0
qa_planet: dc.b 'NavLock Planet/Station',0
 even
qa_case: dc.w 0
qa_galaxy: dc.w 0
"""
    return prefix, "".join(parts), tail, names
