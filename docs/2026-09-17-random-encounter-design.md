# Random encounters in deep space

Date: 2026-09-17
Status: implemented
Trees: `src_atari`, `src_amiga` (applied separately). `src_orig` is not touched.

## 1. Goal

Deep space offers one kind of event: `create_pirates` calls `pirate_attack`,
which announces "Condition RED!" and drops a squadron of pirates on the player.
Every ship in it is rolled from one table, so every wave is the same shape.

This design adds a second kind beside it. A **random encounter** places a small
group that is **already at war with itself**: a Thargoid among traders, pirates
among police, a bounty hunter chasing raiders. Nothing announces it and nothing
is aimed at the player. He flies into somebody else's fight and decides whether
to join it, pick off the survivor, or collect what falls out.

The faction rules of `docs/2026-09-17-faction-ai-targeting-design.md` do all the
work: every group listed here is internally hostile under the existing
`faction_mask`, so the members find each other through the ordinary
`retarget`/`pick_target` path. No new hostility rule is added.

## 2. Scope

In scope:

- One new routine, `random_encounter`, and the tables it reads.
- A single substitution point in `create_pirates`.

Not in scope, explicitly unchanged:

- **`pirate_attack` and `random_pirate`.** The existing ambush keeps its
  composition, its "Condition RED!", its rating-based squadron size and its
  Thargoid inside the pirate type range.
- **Every mission spawn.** See section 7, which is the constraint this design
  is most careful about.
- Ship statistics in `objects.dat`. No data value is edited.
- The faction relation, `faction_mask`, and every routine in the faction
  targeting design.
- Spawn rates: the encounter replaces a wave that was going to happen anyway
  and never adds one.

## 3. Design decisions

| Decision | Choice | Reason |
| --- | --- | --- |
| Relationship to the old system | Substitution, never an addition | The wave budget, its counters and its pacing stay exactly as they are |
| Substitution rate | 50% of ordinary deep-space waves | Both kinds stay common |
| Group members | Fixed templates, 4 members at most | Fewer objects than `pirate_attack` already creates at a high rating |
| Ship choice | Two new tables, narrower than `random_pirate` | The encounter is about the *shape* of the group, so its ships are chosen deliberately |
| Bounty hunter | An ordinary `typ_trader` Fer-de-Lance | It already hunts pirates and is hunted by them; no change to the faction table |
| Starting logic | `log_cruise` | They are not attacking the player. `retarget` draws them into fighting each other, which is what the player should see |
| Announcement | None | "Condition RED!" is a statement about an ambush on the player |
| Mission states | Always take the old path | Section 7 |

## 4. Data model

### 4.1 Ship tables

Two tables, both narrower than `random_pirate`'s type range:

    encounter_pirates: dc.w krait,gecko,moray,adder,mamba,asp,sidewinder
    encounter_traders: dc.w cobra,python,anaconda,cobra_mk1

`thargoid` is **not** in the pirate table: where a Thargoid appears it is a
fixed member of the template, not a roll. `boa` and `wolf` are left out
deliberately — the encounter's raiders are the small and medium ships.
`ferdelance` is left out of the trader table because it is the bounty hunter's
fixed type.

`viper`, `thargoid` and `ferdelance` are never rolled; the template names them.

### 4.2 Roles

A member is one of five roles, resolved when the group is built:

| Role | Type |
| --- | --- |
| `role_pirate` | rolled from `encounter_pirates` |
| `role_trader` | rolled from `encounter_traders` |
| `role_thargoid` | `thargoid` |
| `role_viper` | `viper` |
| `role_bounty` | `ferdelance` |

Each member's `ship_type` is whatever `objects.dat` gives it, so the bounty
hunter is a `typ_trader` and hunts pirates exactly as a Cobra would. Nothing
writes `ship_type` per instance.

### 4.3 Templates

One table, each row carrying a weight, the lowest government it may appear
under, and its member roles with the **maximum** count of each. The actual
count is `rand(max) + 1`, which gives 1 for a maximum of 1 and 1..2 for a
maximum of 2, so fixed and variable members follow one rule.

| # | Group | Weight | Min. government |
| --- | --- | ---: | --- |
| 1 | 1 Thargoid, 1-2 pirates | 1 | — |
| 2 | 1 Thargoid, 1-2 traders | 1 | — |
| 3 | 1-2 pirates, 1-2 traders | 4 | — |
| 4 | 1-2 pirates, 1-2 Vipers | 3 | 2 (not Anarchy, not Feudal) |
| 5 | 1-2 pirates, 1 Viper | 3 | 1 (not Anarchy) |
| 6 | 1-2 pirates, 1 bounty hunter | 2 | — |
| 7 | 1-2 pirates, 1 bounty hunter, 1 trader | 2 | — |

Encoded as bytes: weight, minimum government, then role and maximum count pairs
terminated by zero. The roles are numbered from one, because a zero byte is
what ends a row.

Government is `splanet+govern(a6)`, the system the player is in: 0 Anarchy,
1 Feudal, 2 Multi-government, through 7 Corporate state. `gen_prices` copies
`cplanet` into `splanet` on arrival, so it is the current system.

**Largest group: four objects** (templates 3, 4 and 7). `pirate_attack` already
creates up to six at an Elite rating, so the object pool sees no new pressure.

### 4.4 Thargoid frequency

Weights, not equal chances, because two of the seven templates carry a Thargoid
and one encounter in three would be too many for normal space. The share
depends on which templates the government allows:

| Government | Weight available | Thargoid share |
| --- | ---: | ---: |
| Anarchy | 10 | 20% |
| Feudal | 13 | 15% |
| Multi-government and above | 16 | 12.5% |

Thargoids are commonest where there is no police to meet instead, which is the
right shape for it.

## 5. Selecting a template

One routine, two passes over the template table:

1. Sum the weights of every row whose minimum government is at most the
   system's.
2. Roll `rand(total)` and walk again, subtracting weights until the roll is
   used up. That row is the template.

The government filter and the weighting fall out of the same walk, so a
template a government forbids can never be selected and the remaining weights
keep their proportions. The sum is never zero: templates 1, 2, 3, 6 and 7 carry
no government condition.

## 6. Building the group

1. **Place the first member.** `orbit` with radius `rand(rand_range) +
   rand_limit`, the same 16384..24576 the ambush uses.
2. **Force the front hemisphere.** `orbit` computes `z = r*sin(a)*cos(b)`, so
   the sign of `zpos` is the only thing to correct: negate it when it is
   negative. The radius is unchanged and the distribution stays even over the
   half sphere the player is facing.
3. **Point it at the player** with `vector_pos`. This is not decoration. The
   spawn radius reaches `radar_range` exactly, and `do_cruising` removes an
   object once `obj_range` passes that, so a group in `log_cruise` facing away
   would delete itself within a frame or two.
4. **Copy the rest** from the first member with `copy_object`, offset by
   `spacing2` (1000) along its own x and y vectors, in the manner of
   `squadron_positions`.
5. Each member takes its type from its role (§4.2), `log_cruise`, and full
   velocity, then `create_object`.
6. When `alloc_object` runs dry the group is finished short, exactly as
   `pirate_attack` already does.

No message is printed and no sound is played.

`retarget` then finds each member its nearest hostile candidate. Members are
1000 units apart and the player is at least 16384 away, so they choose each
other, and the round-robin cursor reaches every one of them within
`max_objects` frames.

## 7. Mission spawns must not change

This is the constraint the design is built around. Every spawn that a mission
depends on is enumerated here with the reason it is unaffected.

### 7.1 The substitution point

`random_encounter` replaces exactly one instruction: the final
`bra pirate_attack` at the end of `create_pirates`, reached only after the
routine has already established that

- the mission is **not** `$15`, because the Constrictor branch above it either
  jumps to `pirate_attack` or returns;
- the player is in deep space (`radar_obj` clear);
- fewer than two pirates are present;
- the `pirate_ctr` countdown has expired.

At that point three mission states can still arrive, and each is sent down the
old path before the 50% roll is taken:

| State | Mission | What `pirate_attack` does |
| --- | --- | --- |
| `$21` | 2, state 1 | Thargoid leader **and** Thargoid wingmen |
| `$41` | 4, state 1 | Cougar leader and two Asps |
| `$52` | 5, state 2 | Thargoid leader **and** Thargoid wingmen |

`$15` is listed in the test suite as well, even though `create_pirates` cannot
deliver it here, so the guard survives any future edit to the routine above.

### 7.2 Spawns the substitution cannot reach

| Spawn | Why it is safe |
| --- | --- |
| Constrictor, mission `$15` | Handled by `create_pirates` **before** the deep-space and `pirate_count` gates, so neither an encounter nor a crowd of pirates can delay or block it |
| Thargoids in witch space | `object_logic` calls `create_thargoids` and **returns**; `create_pirates` never runs in witch space, so encounters cannot happen there |
| Thargoids from the station, mission `$52` | `launch_vipers`, a different routine on a different trigger |
| Alien space station, mission 5 | `audit_station`; the `dodec` is outside the faction whitelist and cannot be targeted by any ship |
| Post-hyperspace ambush | `attack` in `flight.m68` jumps straight to `pirate_attack`, not through `create_pirates` |
| Police from the station | `check_police` and `prepare_vipers`, a different trigger entirely |
| Shuttles | `launch_shuttle`, which already refuses on mission `$52` |

### 7.3 Counter side effects

`create_object` maintains `pirate_count`, `trader_count` and `obj_ctr` from
each new ship's `ship_type` and type. An encounter therefore behaves like the
ambush it replaced:

- its 1-2 pirates raise `pirate_count`, which suppresses the next
  `create_pirates` until they die — the same self-limiting the ambush has;
- its traders raise `trader_count`, suppressing `create_trader` meanwhile;
- its Vipers raise `obj_ctr+viper`, which is read by `check_hit`'s "fewer than
  two Vipers" test before `prepare_vipers`. Shooting a trader inside station
  space may therefore summon fewer station police while encounter Vipers are
  alive. Accepted: it is the same counter the station's own launches use, and
  encounters only exist in deep space, so the two rarely overlap.

None of these counters gates a mission spawn except through `create_pirates`
itself, and there the Constrictor is checked first (§7.2).

## 8. Performance

The work happens once per replaced wave, not per frame: two walks over a seven
row table, one `rand` per member for its type, and up to four `create_object`
calls. `pirate_attack` already does more.

## 9. Files touched

Applied separately and identically to `src_atari/asm` and `src_amiga/asm`.

`common.def` is **not** touched. The roles and the spacing are private to
`combat.m68` and belong beside `spacing1`; the group's working state fits in
that module's own variable block, which uses 12 of its 32 bytes.

| File | Change |
| --- | --- |
| `combat.m68` | Role constants and `spacing2` beside `spacing1`; four module variables in its own `q_vars` block; `random_encounter` with its five helpers; `encounter_pirates`, `encounter_traders`, `encounter_groups`, `encounter_positions`; the substitution in `create_pirates` |
| `tests/test_faction_ai.py` | The suite below |
| `src_atari/README.md`, `src_amiga/README.md` | A section describing the feature |

## 10. Testing

Added to the existing Unicorn harness:

- every template is selected under a government that allows it and never under
  one that does not, checked for all eight governments;
- the weights hold: over a swept roll, templates 1 and 2 together take the
  expected share, and the share changes with the government as §4.4 says;
- a member's type only ever comes from `encounter_pirates` or
  `encounter_traders` — never `thargoid`, `boa` or `wolf` from a pirate roll —
  and the fixed roles always give `thargoid`, `viper` and `ferdelance`;
- no group exceeds four members, and a group finishes short rather than
  failing when `alloc_object` runs dry;
- every member is created in `log_cruise`, with `zpos` positive, at the ambush
  radius, and 1000 units apart;
- nothing is printed and no sound is requested;
- **mission states `$15`, `$21`, `$41` and `$52` always reach `pirate_attack`**,
  whatever the 50% roll would have said;
- the substitution happens on roughly half of ordinary waves and never outside
  deep space.

## 11. Risks and follow-ups

- **Encounters crowd out ambushes.** Half the deep-space waves stop being
  aimed at the player. If play testing says the game got quiet, the
  substitution rate is one constant.
- **A group can die before the player reaches it.** Spawned at the edge of
  scanner range and fighting from the first seconds, a two-ship encounter may
  be over by the time he closes. That is the intended texture, but it means
  some encounters are only ever seen as wreckage and cargo.
- **Vipers in deep space** have no precedent in the original game, where police
  only ever launch from a station. Deliberate, and gated on government so the
  lawless systems where it would look strangest never produce them.
- **Object slot pressure** from cargo dropped by a fight the player did not
  join, on top of the faction feature's existing sources.
