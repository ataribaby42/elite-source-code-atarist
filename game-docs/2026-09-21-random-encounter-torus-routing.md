# Random encounters during normal flight and torus

Date: 2026-09-21
Trees: `src_atari`, `src_amiga`. `src_orig` is unchanged.

## Cause

The original 2026-09-17 integration replaced only the final `pirate_attack`
branch in `create_pirates`. That covered timed waves during normal flight.
Torus used `flight.m68`'s `attack` entry, which called `pirate_attack` directly
and bypassed both the substitution and its mission guards.

This explains why flying mainly with J could produce original pirate ambushes
without showing random encounters. The dated design and the existing source
both document that earlier limitation; no Git history was inspected.

Ordinary timed waves also take longer in stable systems. Their countdown is
`(government + 2) * 512` eligible game turns: 2,560 at Lave and 4,608 at Zaonce.
The timer pauses in station space or while at least two pirates are present,
and resets on station departure and hyperspace arrival. It does not accumulate
across repeated jumps. These rules are unchanged by this fix.

## Routing change

Both trees now contain a shared `spawn_pirate_wave` dispatcher in `combat.m68`.

| Entry | Work before dispatch | Result |
| --- | --- | --- |
| `create_pirates` | Original deep-space, pirate-count and countdown checks; timer reload | One ordinary-wave substitution decision |
| `torus_drive` -> `attack` | Original torus event probability; stop torus, restore speed, dust and controls | The same substitution decision |

The dispatcher first checks mission states `$15`, `$21`, `$41` and `$52`.
These go straight to the original `pirate_attack`, without consuming a
substitution random value. All other events call `random` once: an odd result
selects `random_encounter`, an even result selects `pirate_attack`.

`pirate_attack` remains the original squadron builder, so the decision cannot
be repeated inside it. The early Constrictor branch in `create_pirates` remains
ahead of the normal wave gates. Witch-space Thargoids, station police and
shuttles keep their separate triggers. Encounter tables, formation behaviour,
faction targeting and group construction are unchanged.

The 50% chance applies **after an original pirate event becomes eligible**.
It is not a 50% chance every frame or every torus interval, and it creates no
additional wave when the original trigger would have produced none.

## Native validation

The linked MC68000 routines ran in Hatari and WinUAE A500, using private
executable/configuration/disk copies on verified hidden Windows desktops.
WinUAE used Kickstart 1.3, PAL OCS, a real-speed 68000, 512 KB Chip RAM and
512 KB slow RAM. The user's emulator sessions were not accessed.

Both platforms passed **83 native routing and spawn regression scenarios**:

- Timed routing checks all 256 coin values in all eight governments, including
  the original countdown reload and exactly one substitution RNG call.
- The common dispatcher and torus `attack` each check all 256 coin values:
  exactly 128 select encounters and 128 select original ambushes.
- All four mission guards check all 256 values through both entries without
  consuming a substitution roll. Actual mission spawns retain their Constrictor,
  Cougar plus two Asps, and Thargoid compositions and player targets.
- The full `torus_drive` entry checks both outcomes in all eight governments,
  the no-attack case and all four mission states. Speed, controls, dust and
  torus state are checked after an interruption.
- Existing station launches, witch space, ordinary traders, asteroids,
  missiles, Thargons, escape capsules, cargo, object-pool exhaustion and slot
  reuse retain their existing behaviour.

A separate WinUAE run used the **unmodified game RNG and real spawn routines**:

| System | Complete ordinary countdowns | Encounters from those waves | Torus events in 32 intervals | Encounters from torus events |
| --- | ---: | ---: | ---: | ---: |
| Lave | 32 | 13 | 19 | 9 |
| Zaonce | 32 | 18 | 2 | 0 |

These small samples demonstrate execution, not a statistical estimate. The
exhaustive routing checks verify the 50% decision for both entries; the two
Zaonce torus events happened to select original ambushes. Before the fix, the
Lave test produced 19 torus ambushes and zero encounters.

For integration, only the final countdown was accelerated to reach a spawn
quickly. RNG, spawn construction and `game_logic` remained unmodified. A
normal-flight encounter and a torus encounter each completed another 90 real
game turns, retaining two and three non-system objects respectively. Torus
was off, controls were unlocked and the saved speed of 17 was restored after
the torus encounter. The normal pirate timer was not consumed to produce it.

Both default disk images rebuilt successfully. Python build/data checks passed:
Atari 32 passed and 1 skipped; Amiga 30 passed and 1 skipped. The skipped check
is historical graphics identity, which does not apply to customized PNGs.

This is targeted native regression coverage, not a complete mission playthrough.
Generated scripts, payloads and reports are under each tree's
`build/encounter-routing-qa`. The real-RNG before/after evidence, RAM snapshots
and screenshots are under `src_amiga/build/encounter-runtime-qa`.
