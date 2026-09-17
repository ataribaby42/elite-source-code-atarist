# Thargon dormancy on the mother's death

Date: 2026-09-17
Status: implemented
Trees: `src_atari`, `src_amiga`. `src_orig` carries the same fault and keeps
it, as it keeps every other 1990 behaviour.

A fix, not a feature. Reported from play: a Thargon whose mother had been
destroyed no longer fired, but kept breaking off and weaving as soon as an AI
trader in a Cobra Mk III started shooting at it.

## 1. Symptom

A Thargon is meant to go dormant the moment its Thargoid mother dies. It
cruises away at full speed and takes no further part in the fight: `hit_reaction`
and `low_energy` both pass over it, so nothing another ship does to it can make
it manoeuvre, and `do_cruising` removes it once it leaves scanner range.

What was observed instead was a Thargon that had stopped shooting yet answered
incoming fire with an evasive break-off — a combination the dormant state
cannot produce, which is what identified this as a live Thargon rather than a
dormant one.

## 2. Root cause

`explode_object` (`combat.m68`) puts the dead mother's brood to sleep:

    lea objects(a6),a0      ; scatter any thargons
    move this_obj(a6),d0
    ...
    cmp mother(a0),d0
    move #log_cruise,logic(a0)
    move #act_nothing,attack_type(a0)

A Thargon's `mother` holds the object slot its mother occupied, written by
`thargons` at release. The loop compares it against `this_obj`, but `this_obj`
is the **main loop's cursor** (`main.m68`) — the slot of the object the loop is
currently servicing — not the slot of the ship that just died. The ship that
died is in **A4**, which is `explode_object`'s documented entry register.

The two agree only when the dying ship is the one being serviced. Across every
call site:

| Path | `this_obj` is | Correct |
| --- | --- | --- |
| `check_hit` — the player's laser | the victim's slot | yes |
| `collision` (`flight.m68`) — ramming | the victim's slot | yes |
| `do_locked` (`logic.m68`) — a missile detonating | the **missile's** slot | **no** |
| `damage_target` (`combat.m68`) — an NPC's laser | the **shooter's** slot | **no** |
| `ecm_check` | only ever destroys missiles | n/a |
| `launch_bomb` | skips the Thargoid outright | n/a |

So a Thargoid killed by a missile, or shot down by another ship, left its
Thargons with their `logic` and `attack_type` untouched. They stayed combat
ships, kept their target and went on fighting.

The failure had a second half. The cursor is always a *valid* slot, so it could
match the `mother` of some **other**, still living Thargoid's brood and put the
wrong Thargons to sleep instead.

### Why it looked like "stopped shooting but evades"

A live Thargon released by `thargons` starts in `log_run_off`, which does not
fire. `hit_reaction` has a branch for exactly that state:

    logic == log_run_off  ->  next_logic = log_avoid  +  start_peel_off

`do_peel_off` then hands over to `do_avoid`, which sets `log_run_off` again for
a few dozen frames. Every further hit restarts the cycle, so while a Cobra keeps
firing the Thargon never reaches `log_attack` — it never shoots and never stops
weaving. That is the reported behaviour, produced by a Thargon that was never
made dormant at all.

## 3. History

The `this_obj` read is original: `src_orig/asm/combat.m68` has the same two
lines, so the missile path has been wrong since 1990 — destroy a Thargoid with
a missile in the original game and its Thargons stay hostile. The faction AI
work (see `2026-09-17-faction-ai-targeting-design.md`) added the second wrong
path by letting NPCs make kills through `damage_target`, and made it far easier
to meet, since a Viper or a trader can now finish a Thargoid off.

Per the project rules `src_orig` is not touched.

## 4. The fix

Derive the slot from A4, the ship that actually died:

    lea objects(a6),a0 ; scatter any thargons
    move.l a4,d0 ; slot of the mother that actually died
    sub.l a0,d0
    divu #obj_len,d0 ; D0.w = its index; MOTHER is compared as a word

Notes on the arithmetic:

- `obj_len` is 156 and `max_objects` is 30, so the offset is at most 4,524 and
  the quotient at most 29. `DIVU.W` cannot overflow here, and A4 always points
  at a record boundary inside `objects`, so the division is exact.
- `DIVU` leaves the remainder in the high word of D0. The loop's `cmp
  mother(a0),d0` is a word compare (`B068`), so only the quotient is read.
- The block runs only after `cmp #thargoid,type(a4)` has passed, so A4 is
  always a live object record when the division executes.
- D0 is dead at this point and `q_loop 1,max_objects` counts in D7, so nothing
  else in the routine is disturbed. `explode_object` saves all registers on
  entry.

## 5. Consequences

- A Thargoid killed by a missile, by another ship's laser, by the player's
  laser or by ramming now leaves the same dormant brood.
- A living Thargoid's Thargons are never put to sleep by another Thargoid's
  death.
- Nothing else reads `mother`, so no other behaviour changes.

## 6. Testing

`tests/test_faction_ai.py` in both trees gains four tests. They assemble the
real `explode_object`, `do_locked` and `damage_target` out of `asm/` and run
them under Unicorn on MC68000 and MC68020, as the rest of that suite does:

| Test | Covers |
| --- | --- |
| `test_a_thargoid_the_player_shot_down_puts_her_brood_to_sleep` | the path that always worked, so the fix does not lose it |
| `test_the_brood_that_sleeps_is_the_one_whose_mother_died` | cursor and dying mother disagree: hers sleeps, another mother's does not |
| `test_a_missile_kill_puts_the_thargoids_brood_to_sleep` | `do_locked`, for both the player's missile and a ship's |
| `test_a_thargoid_another_ship_shot_down_puts_her_brood_to_sleep` | `damage_target` |

The three new ones were confirmed to fail against the unfixed source and pass
against the fixed source; the first passes either way by design. Full suites:
382 tests for `src_amiga` and 377 for `src_atari`, all passing, and both trees
assemble and link.

Not covered: a play test in an emulator or on hardware. The register-level
tests prove the dormant state is now set on every kill path; they do not judge
how the fight reads from the cockpit.
