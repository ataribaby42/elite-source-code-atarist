# Missile cleanup beyond scanner range

Date: 2026-09-19
Status: implemented independently in `src_atari` and `src_amiga`

## Behaviour

All guided missiles now leave the world when their distance from the player
exceeds `radar_range` (24,576 world units). They remain active at exactly that
distance. The limit is fixed, independent of scanner zoom and distance to the
missile's target. It applies to the player's `log_locked` missiles, NPC
`log_ai_missile` missiles aimed at ships, and `log_missile` missiles aimed at
the player. `src_orig` retains its original behaviour.

Discarding a distant missile does not explode it, damage its target, award a
kill, release cargo, or refund ammunition. Its target ship and other missiles
pursuing that ship remain active.

## Implementation

Both missile routines in `logic.m68` check `obj_range` before steering, reading
the target record, testing ECM or applying impact damage. Above the limit they
branch to `discard_distant_object`, a label in the existing cruise/abandoned
hull cleanup path introduced by the
[mass-lock fix](2026-09-19-abandoned-hull-mass-lock-fix.md).

The cleanup calls `target_lost` with A4 pointing to the discarded **missile**,
not to the ship it was chasing. This also clears a player lock on that missile
or missiles pursuing it. Unrelated player locks remain intact. The normal
`remove` flag defers freeing the record and decrementing its type counter until
`remove_objects`, after queued rendering. No object layout, logic numbering,
faction rules or ordinary in-range missile combat code changes.

## Verification

Actual MC68000 game routines from each enhanced tree passed 31 scenarios in
isolated WinUAE instances: the 14 abandoned-hull lifecycle regressions plus
17 missile scenarios. The additional scenarios cover:

- All three missile logic values at distances 24,575, 24,576 and 24,577.
- Continued in-range steering and no out-of-range steering or damage.
- Deferred freeing, correct missile counts and no repeated decrement.
- Preservation of the target ship, another missile pursuing that ship, and
  the player's lock on that ship.
- Correct invalidation when the disappearing missile is itself a target.
- Removal before dereferencing an invalid distant target pointer.

A negative-control copy with only the two new range guards removed failed at
the first 24,577-unit missile case. Both patched trees passed. The diagnostic
uses real logic dispatch, missile logic, target invalidation and object
removal. Steering geometry, target-distance calculation, audiovisual services
and damage side effects are instrumented stubs; this is a focused lifecycle
test rather than a full-flight play test. No Unicorn is used.

Temporary generator/runner:
`src_amiga/build/mass-lock-qa/extend_missile_qa.py` and
`src_amiga/build/mass-lock-qa/missile_runtime_check.py`.
Reports and diagnostic ROMs are in each enhanced tree's
`build/missile-range-qa/runtime` directory.

The normal Atari build and its 17 existing tests passed. The eight Amiga
disk/loader/audio tests passed. At the time of this validation, the normal Amiga
build was blocked by the
independently edited palette index 0 in `gfx/panels.png`. An isolated Amiga QA
build using existing generated graphics passed assembly, linking and disk
validation in `src_amiga/build/mass-lock-qa/game/output`; no graphics inputs or
normal build validation were changed by the missile fix. The subsequent
[RGB-based PNG conversion update](2026-09-19-editable-png-graphics.md) resolved
that graphics blocker, and both normal builds passed with the missile fix included.
