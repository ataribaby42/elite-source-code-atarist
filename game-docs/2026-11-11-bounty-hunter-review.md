# Bounty hunter integration review — 2026-11-11

## Scope

Reviewed the independent Atari ST and Amiga implementation of Fer-de-Lance
bounty hunting against the pre-feature source snapshots, the initial hunter
builds and existing faction, police, salvage and station-departure behavior.
The review concentrates on interactions and delayed state transitions, rather
than only re-running the original threshold tests.

Two reproducible edge cases were fixed in both platform copies of
`asm/logic.m68`. The fixes are restricted to bounty hunters. No combat, police,
model, spawn-weight, object-layout or save-format change was needed during this
review.

## Fixed: provocation lost at the end of the station turn

The player could hit a Fer-de-Lance with a laser, or launch a missile at it,
while it was completing its station departure turn. The threat set `angry`,
but the turn correctly remained in progress. On completion, `start_departure`
entered cruise or departure-wait logic. If the round-robin retarget slot had
not arrived yet, cruising cleared `angry`. A Clean attacker was then forgotten.

The initial tests called retarget immediately after the turn and therefore
did not expose the intervening cruise. The review reproduction failed on both
platforms with the hunter's provocation cleared.

`start_departure` now sends an armed, provoked bounty hunter into attack after
the turn completes, before any departure roll or cruise. It preserves the
turn itself and lets ordinary nearest-target selection resume afterward.
Unprovoked hunters and ordinary traders retain their original departure roll.

The new regression suite applies actual laser hits and successful player
missile launches, then runs the normal retarget/logic order through all 30
retarget phases. These 60 cases check that retaliation persists and no jump
is armed.

## Fixed: an escaped pilot could leave a hyperspacing hull

A hunter could have an armed station jump, take damage before acquiring an NPC
target, and launch its escape capsule. Its abandoned hull then had neither a
player provocation nor a target nor a combat logic state. Those were the three
conditions checked by the initial hunter jump-cancellation code. The old timer
could therefore turn the abandoned hull into a hyperspace cloud.

The reproduction uses the real escape-capsule routine and the real logic tick.
It failed on both platforms: the hull left `log_abandoned` and entered the
departure cloud after the pilot had escaped.

`departure_tick` now also cancels a hunter's jump if its attack type is no
longer `act_attack`. The abandoned hull keeps its drift/removal behavior.
Normal traders retain their existing jump policy. Additional tests confirm
that Vipers, Thargoids and Thargons did not gain escape-capsule eligibility.

## Other reviewed boundaries

- **Police:** all five principal station/patrol routines remain unchanged.
  Viper's blueprint and faction remain unchanged. Neutral Vipers next to a
  hunter continue using their own patrol decision at player records 39, 40
  and 50; the hunter threshold does not replace police probabilities.
- **NPC relations:** the full 32-by-32 model relationship comparison matches
  pre-feature behavior. Reclassifying Fer-de-Lance and adding the corresponding
  pirate/alien mask bits preserves all 1,024 relations. Mission exclusions
  and the combat whitelist are unchanged.
- **Salvage:** collectors remain pirates. Hunter/Viper hits release the
  container reservation and restore ordinary acceleration. Group provocation
  cannot reactivate an abandoned pirate hull.
- **Traffic and torus:** hunter creation/removal balances the same civilian
  traffic count as before. A removed hunter slot can become a Viper without
  retaining its role, traffic count, patrol state or hyperspace timer.
- **Departure:** unprovoked hunters still select exactly 50 of 100 departure
  outcomes. Ordinary trader timing, cloud rendering and removal are exercised
  by the existing departure suite.
- **Legal attribution:** hunter protection, player/NPC kill accounting and
  the existing collision exception are unchanged by the review fixes.
- **Player ships:** player ship purchasing/profiles and flight are tested
  separately from NPC roles, including Fer-de-Lance. The player is not placed
  into the NPC hunter faction by buying that hull.
- **Other integration:** regression suites cover ordinary and named-mission
  spawns, missile provocation and target loss, cloaking/comms and station death.

## Evidence and limits

The review adds independent `tests/native_bounty_review.py` copies to both
platform trees. Its 69 scenarios complement the original 72 hunter scenarios.
Pre-fix failures, private images, source snapshots and RAM diagnostics are
retained under `src_*/build/bounty-qa/review-before`. The isolated abandoned-hull
probe is named `qa_abandoned_hunter`; it is a diagnostic helper, not gameplay.

Final builds and test reports are kept under
`src_*/build/bounty-qa/review-final`. Tests use private emulator/configuration/
disk copies on verified separate hidden Windows desktops. They do not operate
the user's emulator session. Standard ELITE and ELITE_ALT are built on each
platform; Amiga testing covers the ordinary PAL/MC68000 configuration.

The Amiga cloak/comms suite initially stopped at the harness size check, before
executing any scenarios: assertion instrumentation produced a 76,012-byte
payload, exceeding the old 62,000-byte payload allowance. The private harness
now obtains 96 KiB through Exec and keeps the payload, diagnostics and completion
markers within that allocation. This changes only the test harness; it does not
increase the game's memory requirement. The initial harness log is retained in
`review-final/ELITE_ALT/native_cloak_comms-harness-limit`.

This is targeted native integration testing and source review, not a complete
mission playthrough or a full Amiga display/CPU matrix test.

## Final results

All final native scenarios passed against the reviewed builds:

| Coverage | Atari ST | Amiga |
| --- | ---: | ---: |
| Hunter and review suites, ELITE | 141 | 141 |
| Hunter and review suites, ELITE_ALT | 141 | 141 |
| Existing integration suites, ELITE_ALT | 624 | 624 |
| **Total scenarios** | **906** | **906** |

The police suite additionally checks 16,384 input combinations against the
original patrol decision oracle within one of its scenarios. Static comparison
preserves all 1,024 model relationship pairs. No other actionable defect was
found in the reviewed paths.

`src_atari/build/bounty-qa/verify_review.py` verified the final source hashes,
distribution artifact hashes, equality of tested and output disk images, and
the unchanged historical source archive. Per-platform results are in
`src_*/build/bounty-qa/review-final/report.json`; the combined report is
`src_atari/build/bounty-qa/review-summary.json`.

Both normal distributions, ELITE and ELITE_ALT, were rebuilt in `output_atari`
and `output_amiga`. No files were updated on G:. The final process check found
no private test emulator still running. `CHANGELOG.md` was not changed.
