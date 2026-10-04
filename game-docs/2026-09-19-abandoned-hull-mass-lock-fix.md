# Abandoned hulls no longer cause permanent mass-lock

Date: 2026-09-19
Status: implemented in `src_atari` and `src_amiga`

## Cause and scope

The [snapshot diagnosis](2026-09-19-mass-lock-snapshot-analysis.md) found an
abandoned Anaconda at range 81,604 keeping `trader_count` at one. Its pilot's
escape selected `log_none`, which returns without checking range. The hull
therefore remained allocated after leaving the scanner and permanently blocked
the torus drive. The same defect exists in the original gameplay code.

The fix follows the existing [faction combat design](2026-09-17-faction-ai-targeting-design.md),
including its missile amendments, the [random encounter design](2026-09-17-random-encounter-design.md)
and the [Thargon dormancy fix](2026-09-17-thargon-dormancy-on-mother-death.md).
Both enhanced trees receive the change independently. `src_orig` and the
historical archive are unchanged.

## Implementation

`common.def` appends `log_abandoned` after `log_ai_missile`. Existing logic
numbers and object/workspace layouts do not move.

On a successful pilot escape, `launch_escape` selects this new state instead
of `log_none`. Allocation failure still leaves the ship piloted. The existing
`act_nothing` and zero-missile settings remain, and the capsule still receives
`log_cruise`.

In `logic.m68`, `do_abandoned` enters the existing range-cleanup tail of
`do_cruising`, after its acceleration and anger-reset instructions:

- At or inside `radar_range` (24,576), the hull remains in use. Its velocity,
  orientation and faction remain unchanged. A nearby trader/pirate hull still
  causes mass-lock and can still be shot.
- Beyond that range, `target_lost` drops missiles pursuing the hull, including
  AI missiles, and updates the player's missile lock when applicable.
- The hull receives the existing `remove` flag. The normal end-of-frame
  `remove_objects` pass frees its slot and decrements its type/category counters
  once. It is not freed while queued geometry may still refer to it.

The distance is `obj_range`, measured from the player, using the same fixed
threshold as ordinary cruise cleanup. It does not use the AI's `target_range`
or the adjustable scanner scale.

The torus check itself is unchanged, including planet/sun limits. Ordinary
`log_none` objects (planets and animation objects) remain inert. Dormant
Thargons retain their existing cruise acceleration and cleanup. Mission ship
rules, spawn rates, faction masks, damage, rewards and random-number calls
are unchanged. An abandoned hull cannot become a hunter because its attack
response is `act_nothing`; its new logic is also outside the combat-state list.
The existing victim-selection and target-validation rules continue to apply.

This changes future pilot escapes. It does not reinterpret `log_none` in old
emulator snapshots, where that value is also used by unrelated objects.

## Validation

The changed gameplay routines from each tree were assembled for MC68000 and
executed in a separate WinUAE instance using a generated diagnostic ROM.
Each instance used its own copied executable, portable settings and working
directory, with no mounted host drives. The debugger pipe was checked against
the launched process ID. No Unicorn dependency was used.

Both trees passed all 14 runtime scenarios:

1. Successful pilot escape preserves the hull's speed and launches a cruising capsule.
2. A hull exactly at scanner range survives and still blocks torus.
3. The snapshot's 81,604-unit case is marked, removed at the normal pass, and
   releases torus; a repeated removal pass does not underflow counters.
4. A pirate one unit beyond scanner range releases its pirate count.
5. Shuttle removal leaves unrelated category counts unchanged.
6. Player and AI missiles lose the removed hull, unrelated missiles survive,
   and an AI target is rejected while removal is pending.
7. Cleanup of AI missiles alone does not display a player target-loss message.
8. An abandoned hull neither retargets nor evades, remains a nearby victim,
   and is excluded as a distant target.
9. Live opposing factions still select each other and enter attack logic.
10. `log_none` remains inert even far beyond scanner range.
11. Dormant Thargon cruise still accelerates and removes beyond range.
12. Mission ships and docking states remain outside ordinary retargeting.
13. A full object pool prevents escape without abandoning the ship.
14. The sun and planet continue to prevent torus use at their original limits.

As a negative control, the temporary Amiga test copy restored only the original
`log_none` assignment in `launch_escape`. It failed scenario 3, reproducing
the reported fault. The patched copy passed.

Actual game routines handle logic dispatch, pilot escape, record allocation and
copying, range cleanup, targeting, missile invalidation, deferred removal and
torus admission. Randomness is controlled to force escape; rendering, audio,
capsule model-data initialization and control-angle refresh are stubbed. These
are focused lifecycle regressions, not a full flight or hardware play test.

Temporary runner and detailed results are under `src_amiga/build/mass-lock-qa`
and `src_atari/build/mass-lock-qa/runtime`. The Atari normal build and all 17
existing tests passed. The eight Amiga disk/loader/audio tests passed.

At validation time, the independently edited `src_amiga/gfx/panels.png` failed
the existing fixed-palette check at index 0. The ordinary Amiga build and six
graphics tests were blocked by that input; historical PNG identity was skipped
as expected for edited sources. No PNG was changed by this fix. A separate QA
build using the previously generated binary assets assembled, linked and
validated its Hunk and ADF under
`src_amiga/build/mass-lock-qa/game/output`. The normal graphics validation has
not been relaxed or bypassed in the project build scripts.
