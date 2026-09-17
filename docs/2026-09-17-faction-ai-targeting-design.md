# Faction-based AI targeting

Date: 2026-09-17
Status: implemented, with the amendments recorded in section 12
Trees: `src_atari`, `src_amiga` (applied separately). `src_orig` is not touched.

## 1. Goal

Today every hostile ship attacks the player and nothing else. All object
coordinates are relative to the player, who sits at the world origin, and the
attack logic flies towards `(0,0,0)` and aims at the origin.

This design lets a ship choose the **nearest hostile ship of another faction**,
with the player as one ordinary candidate:

- Pirates attack every non-pirate ship, and the player.
- Traders, shuttles and police attack pirates, and the player once he has shot
  at them.
- Thargoids and Thargons attack everything except Thargoids and Thargons.
- Everyone attacks Thargoids and Thargons.

The rule has no exceptions. Ships spawned as an ambush on the player
("Condition RED!"), vipers launched because of the player's police record and
mission attackers all follow the same nearest-target rule.

## 2. Scope

In scope:

- Target selection and the faction relation.
- Generalising the attack logic, laser aiming and damage so they work against
  any ship instead of only the player.
- Suppressing player score, rating, bounty and police-record bookkeeping for
  kills the player did not make.
- Drawing an AI beam towards its actual target.

Not in scope, explicitly unchanged:

- The player's legal status, police record and the police reaction to it.
- Damage taken by the player, including its dependence on the player's combat
  rating, and the front/aft shield split.
- Spawn rates and spawn locations of traders, pirates, police and Thargoids.
- ECM behaviour when the player fires a missile at a ship.
- The energy bomb, which is player equipment only.
- Ship statistics in `objects.dat`. No data value is edited.

## 3. Design decisions

| Decision | Choice | Reason |
| --- | --- | --- |
| Ambition | Retargeting only; pacing, spawning and rewards unchanged | Lowest risk of unbalancing the game |
| Target storage | Reuse the existing `target` pointer, `0` meaning the player | No growth of the object record |
| Player representation | Special case behind one accessor, not a pseudo object record | A pseudo player object would need an exception in every main-loop service |
| Exceptions to "nearest wins" | None | Uniform rule, no special cases in code |
| AI to AI damage | Fixed mid-table value, independent of the player's rating | The player's rating is meaningless between two NPCs |
| AI to AI weapons | Lasers only | Missiles and the energy bomb stay player-facing |
| Combat range | Only within the player's scanner range | No invisible fights, no ships flying away forever |

## 4. Data model

### 4.1 Combat participants

A ship takes part in the faction system only if its object type is in a
contiguous whitelist, tested with two comparisons:

    type == viper  ||  (cobra <= type <= transporter)

Using the type constants in `common.def:280`: `viper` = 11, traders
`cobra`..`cobra_mk1` = 13..17, pirates `krait`..`wolf` = 18..27 (note that
`thargoid` = 19 sits inside the pirate range, so `random_pirate` can spawn one),
`shuttle` = 28, `transporter` = 29.

The whitelist therefore excludes, with no extra condition:

- the space station, the alien station (`dodec`), missiles, cargo canisters,
  asteroids, escape capsules, explosion platlets, the ELITE title letters and
  the launch-bay panels;
- **`cougar` (30) and `constr` (31)**, the mission ships. Nothing targets them
  and they keep their existing behaviour of attacking only the player.

`thargon` (5) is outside the range and is added explicitly, because Thargons
must be both hunters and victims.

Standing outside the whitelist has a consequence for `do_attack`. `retarget`
only assigns a target to a ship the whitelist admits, so for the Cougar and the
Constrictor `target` stays at the `no_target` that `alloc_object` left, for
ever. `do_attack` therefore asks `is_combat_ship` before it acts on a missing
target: a ship the whitelist admits has genuinely run out of things to fight
and falls back to cruising (§5.1), while anything else takes the player, which
is what `log_attack` meant before this feature existed. Without that question
both mission ships turn away on their first frame and are removed once they
pass scanner range.

The two routines that spawn a ship straight into `log_attack` --
`pirate_attack` and `create_thargoids` -- also write `0` into `target`
themselves, so an ambush never spends a turn of the re-target cursor cruising
away before the cursor reaches it.

### 4.2 Factions

The faction is the existing `ship_type` field, read straight from
`objects.dat`. No per-instance data and no new field are needed.

| `ship_type` | Ships | Hostile to |
| --- | --- | --- |
| `typ_trader` (0) | Cobra Mk III, Cobra Mk I, Python, Fer-de-Lance, Anaconda | pirate, alien |
| `typ_pirate` (1) | Krait, Boa, Gecko, Moray, Adder, Mamba, Asp, Sidewinder, Wolf | trader, shuttle, police, alien |
| `typ_shuttle` (2) | Shuttle, Transporter | pirate, alien |
| `typ_police` (4) | Viper | pirate, alien |
| `typ_alien` (7) | Thargoid, Thargon | trader, pirate, shuttle, police |

The Constrictor also carries `typ_alien`, but the whitelist keeps it out, so
inside this system `typ_alien` can only mean a Thargoid or a Thargon.

Implemented as an eight-byte table indexed by `ship_type`, where bit `n` means
"hostile to `ship_type` n":

    faction_mask:
        dc.b $82,$95,$82,$00,$82,$00,$00,$17
        ;    trd  pir  shu  deb  pol  bty  mis  ali

### 4.3 Hunters and victims

The two roles are separate, because three ships can be shot at but never shoot
back. `attack_type` in `objects.dat` already encodes this.

- **Hunter** — whitelisted and `attack_type == act_attack`. Gets a faction
  target and may fire.
- **Victim** — whitelisted, whatever its `attack_type`. May be chosen as a
  target.

| Ship | Hunts | Is hunted |
| --- | --- | --- |
| Krait, Mamba, Sidewinder, Gecko, Asp, Boa, Moray, Wolf, Adder | yes | yes |
| Cobra Mk III, Cobra Mk I, Fer-de-Lance, Anaconda | yes | yes |
| Viper | yes | yes |
| Thargoid, Thargon | yes | yes |
| Python, Shuttle, Transporter (`act_runaway`) | no | yes |

This mirrors what the code already does: `check_hit` (`combat.m68:695`) reads
`attack_type`, and for `act_runaway` sets `next_logic = log_cruise` and peels
off. Such a ship never enters `log_attack`, and since firing lives only inside
`do_attack`, it never fires. Their reaction to the player is unchanged: shoot
them and they flee.

### 4.4 The player as a candidate

The player is a candidate for a hunter when:

- the hunter's `ship_type` is `typ_pirate` or `typ_alien`, or
- the hunter has the `angry` flag set, which the game sets when the player has
  attacked that ship.

`angry` does **not** lock the target. It only puts the player into the
candidate set; the nearest candidate still wins. A trader the player has hit
may well break off to chase a closer pirate.

The player obeys the same scanner-range limit as every other candidate: a
hunter whose own `obj_range` exceeds `radar_range` does not consider him at
all. Without this a lone pirate far out in deep space would still lock onto a
player it cannot see, which is the behaviour this change exists to remove.

### 4.5 Target storage

The existing `target` field (`common.def:501`, `rs.l 1`) holds the target:

- `no_target` (`-1`) — no target selected;
- `0` — the player;
- otherwise a pointer to the target's object record.

The `no_target` sentinel is needed because `0` already means the player and
there would otherwise be no way to express "no target".

Today only missiles use this field. Missiles are excluded by the whitelist, so
there is no conflict, and `check_missile` (`combat.m68:1134`) keeps working
unchanged.

`target` is initialised to `no_target` in `alloc_object` (`main.m68:251`), not
in `create_object`: `fire_missile` (`combat.m68:1260`) writes `target` *before*
calling `create_object`, so initialising there would destroy the player's
missile lock. `copy_object` copies the whole record, so a copied ship inherits
a value that is always valid, never garbage.

New global variables in the workspace block of `common.def`:

- `retarget_slot: rs.w 1` — round-robin cursor over object slots.
- `npc_kill: rs.w 1` — set while an NPC-inflicted kill is being processed.
- `npc_hit: rs.w 1` — set while an NPC-inflicted, non-fatal hit is being
  processed, so `low_energy` holds the missile back (§6.4.1).
- `target_range: rs.l 1` — scratch distance from the current attacker to its
  target, valid only while that object is being processed. It exists because
  `obj_range` must keep meaning "distance from the player": `radar`,
  `collision` and the removal test in `do_cruising` all depend on that.

## 5. Target selection

New routine `pick_target` in `combat.m68`.

**Entry:** `A5` = hunter's record. **Exit:** `target(a5)` updated.

Candidate filter, in the order that rejects most cheaply first:

1. `in_use` set, `remove` clear;
2. not the hunter itself;
3. `logic != log_exploding`;
4. whitelisted type (§4.1);
5. hostile per the faction mask (§4.2);
6. `obj_range <= radar_range` (24576), the distance from the **player**, which
   `get_range` has already computed this frame.

The player is evaluated as an extra candidate per §4.4, at distance
`obj_range(a5)` — the hunter's own range from the origin, also already
computed.

**Distance metric.** Ranking only, so no square root: Chebyshev distance,
`max(|dx|,|dy|,|dz|)` over the 32-bit coordinate differences. Three
subtractions and two comparisons per candidate. The value is never used for
anything but the comparison, so the approximation is invisible. Ship
coordinates stay within a few tens of thousands of units, because ships beyond
scanner range are removed, so the signed subtraction cannot overflow.

**Cadence.**

- Round robin: one ship re-targets per game frame, driven by `retarget_slot`
  in the main object loop (`main.m68:113`). With 30 slots this is about 30
  comparisons per frame instead of 900.
- A target that has died or been removed is caught by a constant-time
  validation at the top of `do_attack`: an NPC target whose `in_use` flag is
  clear, or whose logic is `log_exploding`, is dropped to `no_target`. This is
  preferred over hooking `target_lost`, because ships are also removed silently
  by `do_cruising` and by `remove_object` without any destruction event, and
  validation covers every path at the cost of two tests per frame.

### 5.1 Entering and leaving combat

Selecting a target is not the same as starting a fight. The logic state decides
whether a hunter may be pulled into one, so that launch and docking sequences
are never interrupted:

| Current logic | On finding a target |
| --- | --- |
| `log_cruise`, `log_fly_planet` | switch to `log_attack`, clear `on_course`, store `health` in `pre_attack` |
| `log_attack`, `log_peel_off`, `log_run_off`, `log_avoid` | keep the state, only the target pointer changes |
| everything else (`log_launch`, `log_police`, docking and takeoff sequences, `log_exploding`, `log_locked`, `log_missile`, `log_timer`, `log_twisting`, `log_rotating`) | no target is selected, the state runs to its end |

`log_launch` and `log_police` already transition into `log_cruise` or
`log_attack` by themselves once the ship has cleared the station, at which point
the ship becomes eligible.

A hunter that finds no valid candidate and is currently in `log_attack`,
`log_peel_off`, `log_run_off` or `log_avoid` falls back to `log_cruise` and
flies off, which is the existing behaviour when a fight ends.

## 6. Combat generalisation

### 6.1 `target_coords`

The single place that knows `target == 0` means the player. Returns `(0,0,0)`
for the player, otherwise the target's `xpos/ypos/zpos`. Everything else calls
it.

### 6.2 `do_attack` (`logic.m68:435`)

Three substitutions:

- `auto_pilot` receives the coordinates from `target_coords` instead of a
  hardcoded `(0,0,0)`.
- Every test that today reads `obj_range(a5)` as "range to the enemy" — the
  `fire_range` gate, `ai_laser_aim`, `ai_laser_miss_threshold` and
  `peel_off_check` — reads `target_range` instead. It is computed once per
  frame per attacking ship, at the top of `do_attack`, with the exact
  `calc_distance` path `get_dist` uses, so the value is a true distance and the
  existing miss-threshold anchors keep their meaning. `obj_range` itself is
  never overwritten; it stays the distance from the player for `radar`,
  `collision` and `do_cruising`. When the target is the player, `target_range`
  is simply a copy of `obj_range`.
- `ai_laser_aim` (`logic.m68:380`) currently dots the ship's `z_vector` with
  the negated shooter position, that is, the direction to the origin. It now
  dots with `target - shooter`. The BBC cones 32/36 (fire) and 35/36 (hit) are
  unchanged.

Unchanged: the `mood` roll, the distance-dependent miss table
(`ai_laser_miss_threshold`, `logic.m68:413`), and the attack-run cycle of
peel off, run off and turn back.

### 6.2.1 The player's own state must not reach an NPC fight

`do_attack` and the routines under it read several globals that describe the
**player**, not the world. Each one has to be classified, because a global that
silently governs a fight he is not in is the recurring defect in this feature.

| Global | Meaning | Treatment |
| --- | --- | --- |
| `approach(a6)` | closing speed towards the player | `peel_off_check` uses the shooter's own `velocity(a5)` when the target is a ship. A faster ship peels off earlier, and no new state is needed. |
| `rating(a6)` | the player's combat rating | Read only when `target = 0`. An NPC hit uses `npc_damage` (§6.4) and an NPC Thargon release uses `npc_thargon_prob` (§6.6). |
| `cloaking_on(a6)` | the player's cloaking device is hiding **him** | Tested only when `target = 0`. It cannot hide one ship from another. |
| `controls_locked(a6)` | the player cannot act: docking computer, escape capsule, hyperspace, torus | Tested only when `target = 0`. Two ships do not stop shooting because he is watching an animation. |
| `radar_obj(a6)` | the player is inside space-station space | **Left global on purpose.** Station space is `$22500`, nearly six times the scanner range `$6000`, so whenever it is set every ship he can see is inside it too. It describes the region, not the player, and a pirate breaking off applies equally to a fight between two other ships. |
| `ecm_jammed(a6)` | the player's ECM jammer is running | **Left global on purpose.** It is an emitter, not a state of his: `engage_ecm` refuses him his own ECM while it is on. It silences the use of ECM around him for everyone, so `do_locked` reads it for every missile, not only his. |
| `laser_type(a6)` | the player's laser, read by `release_cargo` | Consulted only for an asteroid, which the whitelist (§4.1) keeps out of the faction system, so no NPC can reach it. |
| `missile_state`, `target_ptr`, `f_missiles` | the player's missile lock, read by `target_lost` | Correct as they are. An NPC kill really can destroy the ship his missile was locked on, and he should be told. |

`explode_object`'s reads of `mission` and `station_destroyed` only fire for the
Constrictor and the alien station, neither of which is targetable.

One exception inside that cycle: `peel_off_check` (`logic.m68:820`) is built on
the global `approach(a6)`, the closing speed **towards the player**, which does
not exist for a pair of NPCs. When the target is an NPC, the shooter's own
`velocity(a5)` is used in its place. A faster ship peels off earlier, and no
new state is needed.

### 6.3 `angry` and the cockpit warning

`do_attack` currently sets `angry` unconditionally, and `do_logic`
(`logic.m68:66`) raises the player's "under attack" warning from it. `angry` is
now set only when `target == 0`. Without this the cockpit would warn the player
whenever two pirates fight each other near the station.

### 6.4 Damage

The damage path branches on the target:

- **Target is the player** — `reduce_shields` (`combat.m68:505`) unchanged,
  including the rating-dependent damage table, the front/aft shield choice and
  equipment destruction. Combat against the player is bit-for-bit what it is
  today.
- **Target is an NPC** — new routine: `rand(1..npc_damage) * rand(2..4)`
  subtracted from `health(a4)`. The 2..4 multiplier is the one `do_attack`
  already applies and is shared with the player-facing path, so only
  `npc_damage` distinguishes the two. It is **3**, below the `damage` table's
  own range (`logic.m68`, `dc.w 3,3,3,5,5,5,7,7,7`): a hit between two ships
  lands in 2..12 and averages 6, against the 9 an average-rated player takes.
  Their fights are meant to last long enough to be worth flying into, and a
  Mamba survives about seven hits rather than four.

### 6.4.1 The damaged ship's reaction

A ship reacts to another ship's fire exactly as it reacts to the player's, in
the two steps `check_hit` already performs.

**Step one, the break-off.** The block at the top of `check_hit` that chooses a
`next_logic` and starts a peel off moves into its own routine, `hit_reaction`
(entry `A5` = the ship that was hit), and `check_hit` calls it where the block
used to sit. `damage_target` calls the same routine before it subtracts the
damage, so the ordering matches `check_hit`: a ship already in `log_attack` or
`log_peel_off` presses on; an `act_nothing` hull does nothing; an `act_runaway`
ship peels off into `log_cruise`; a ship already in `log_run_off` peels off into
`log_avoid`; anything else peels off into `log_attack` with `pre_attack` reset
to its current health.

**Step two, the retreat.** After the damage is applied and the ship survives,
`damage_target` repeats `check_hit`'s test — more than half the energy gone
since `pre_attack` — and calls `low_energy`, which may launch an escape capsule
and, on a `peel_prob` roll, break off into `log_run_off`.

`npc_hit` is set across that `low_energy` call. `low_energy` already skips the
missile when the shooter's target is not the player; `npc_hit` skips it for an
NPC-inflicted hit as well, so a ship that happens to be fighting the player
never launches a missile at him because a third ship shot it. AI against AI
stays a laser fight (§6.6) and the player is never warned about a missile he did
not provoke.

No other part of `check_hit` is shared. The police record, the `no_entry` flag
for shooting the station and `prepare_vipers` all belong to the player's legal
status, which §2 puts out of scope.

### 6.5 NPC kills

`explode_object` (`combat.m68:206`) unconditionally calls `add_kill` (player
score and rating) and `inc_record` (police record for a destroyed trader or
policeman). Before an NPC-inflicted kill, `npc_kill` is set; `explode_object`
then skips both and sets the existing `no_bounty` flag bit, which already
suppresses both the bounty payout and its message in `do_explosion`.
`release_cargo` is still called, so containers from NPC fights drop and the
player may collect them.

`npc_kill` also silences the explosion. `explode_object` ends every destruction
and plays `sfx_explosion` there, so one test on the flag covers every path at
once: his laser, his missile, ramming and the energy bomb all leave it clear
and are heard, while a kill between two ships is not. The duplicate requests
`damage_target` and `do_locked` used to make afterwards are gone; `check_hit`
and `collision` keep theirs, which the sound driver discards as a repeat within
the same frame exactly as it always has.

No retaliation code is needed. A trader being shot at by a pirate already has
pirates in its hostile set, and the nearest pirate is normally the one shooting
at it.

### 6.6 Missiles, ECM, energy bomb

A ship fires its missile at whatever it is fighting. The energy bomb stays
player equipment, and the cockpit alert stays a statement about the player.

- **A missile aimed at a ship is an ordinary missile.** `do_locked`, the
  player's own missile logic, already flies at `target(a5)` and already lets
  the target defend itself with ECM, so a ship's missile runs the same routine
  under a second logic value, `log_ai_missile`. The separate value is what
  tells the two apart afterwards; nothing else distinguishes the records.
- **The cockpit alert belongs to the player.** `launch_missile` plays
  `sfx_alert` and prints "Incoming missile" (`combat.m68:912`) only on the
  player-facing branch. A missile flying between two ships is silent.
- **No missile reaches the player unless he provoked it.** `low_energy` still
  requires `target = 0` *and* `npc_hit` clear before the player-facing missile,
  so a ship that happens to be fighting him does not fire one because a third
  ship shot it (§6.4.1). Away from him the roll uses `npc_launch_prob`, and it
  needs a real ship to aim at: `target` must be greater than zero, which
  excludes both the player and `no_target`.
- **Ships' missiles must not follow a freed record.** `do_locked` reads
  `target` without checking it, and until now only the player could leave a
  missile in flight. `target_lost` therefore drops **every** missile flying at
  a record that is leaving the world, through the new `drop_missiles`, and
  reports "Target lost" only when one of them was the player's. `do_locked`
  now calls `target_lost` on its own kill as well, which `check_hit` and
  `damage_target` already did.

  Two details make that call safe. `do_locked` flags the killing missile with
  `remove` **before** calling `target_lost`, and `drop_missiles` skips any
  record already flagged. Without both, the missile that just made the kill is
  still in the object list when the sweep runs, and every successful missile
  kill of the player's would answer him with "Target lost".
- **`check_missile` answers only about the player's missiles.** Its other
  caller, `check_sights` (`vector.m68:1000`), refuses him a fresh lock while a
  missile is already on intercept. `fire_missile` gives his missiles
  `log_locked`, so that refusal is unchanged; without the narrowing a ship's
  missile chasing the same ship would have blocked his lock, which is new
  behaviour this change would otherwise have introduced.
- **An NPC missile kill credits him nothing.** `do_locked` sets `npc_kill`
  around `explode_object` when the missile is not his, exactly as
  `damage_target` does (§6.5).
- **Mission objectives are counted where a ship dies, not where it is shot.**
  `explode_object` finishes objective #1 for the Constrictor and objective #5
  for the alien station, each guarded on that objective being the active one
  and on the wreck not already exploding. Laser, missile and ramming all arrive
  there, so all three complete the mission; the energy bomb passes over both
  ships by type and never reaches it. `check_hit` no longer counts the
  Constrictor itself.
- **The player's own state does not reach the fight, but his emitters do.**
  `launch_missile` tests `cloaking_on` and its 2000-unit minimum range against
  `obj_range`, which is the distance from the player; the ship-facing branch
  uses `get_dist` to its own target instead and ignores the cloak. The ECM
  jammer is the other way round and `do_locked` reads it unchanged, for every
  missile (§6.2.1).

  The jammer itself is untouched: `jammer_toggle`, `engage_ecm` and `thanks5`,
  which fits it as the reward for objective #5, are identical to the 1988
  original. It became load-bearing rather than decorative once the ECM wave was
  repaired, because before that a ship's answer destroyed nothing.

  Both ECM and the jammer are area effects and stay that way. `ecm_check`
  clears every missile in the world, so a wave a ship raises in a fight the
  player is not in takes his missiles with it, exactly as his own wave has
  always taken everyone else's; and while his jammer is running, nobody within
  it answers a missile with ECM, himself included.
- **Thargons are not missiles and are still released.** A missile is flown at
  the world origin by `do_missile` and announces itself in the cockpit, so it
  has no meaning between two NPCs. A Thargon is an ordinary ship: `thargons`
  gives it `log_run_off`, it makes no sound and prints no message, and it then
  picks its own faction target as a `typ_alien` hunter. The release therefore
  survives in an NPC fight, with two changes that mirror decisions made
  elsewhere in this design:
  - **Fixed odds.** The player-facing roll is `rating*4 + missile_prob` out of
    256. His combat rating means nothing in a fight he is not in, so the NPC
    path uses `npc_thargon_prob = 4*4 + missile_prob` = 31, the middle rating
    band, exactly as `npc_damage` is the middle of the `damage` table (§6.4).
  - **Smaller release.** `thargons` reads `npc_hit` and releases 2..3 instead
    of 4..7, so one Thargoid cannot empty the thirty object slots in a fight
    the player is not even watching. Both counts come from the same
    `and`/`add` pair over a single random number.

  The release stays one-shot per Thargoid (`clr no_missiles`), `thargons`
  still gives up when `alloc_object` runs dry, and `explode_object`
  (`combat.m68:643`) still scatters a dead Thargoid's Thargons into
  `log_cruise`/`act_nothing`, so `do_cruising` reclaims their slots once they
  leave scanner range.
- `do_missile` (`logic.m68:643`) is **unchanged** and still tracks the origin.
  It remains the logic of a missile aimed at the player.
- ECM is unchanged. A player missile still runs through `do_locked`, which
  tests the target's `ecm_fitted` and triggers ECM exactly as today.
- The energy bomb tests `equip+energy_bomb(a6)`, player equipment, and is not
  reachable by an NPC.
- Thargons released by a damaged Thargoid, and escape capsules, keep their
  current behaviour. Thargons then join the faction system as ordinary
  `typ_alien` hunters.

## 7. Rendering

`draw_ai_laser` (`special.m68:264`) gains a second branch:

- **Target is the player** — current drawing, from the gun node to the opposite
  screen edge, unchanged.
- **Target is an NPC** — a line from the shooter's `gun_node` to the target's
  projected position. On a miss the endpoint is displaced in screen space by
  the same magnitude as the existing player beam tip jitter, x by -4..3 and y
  by -2..1, consuming two random numbers, so misses read as misses.

The target's view coordinates `this_xpos/this_ypos/this_zpos` are set by
`draw_object` before `move`, so by the time the draw list is rendered every
in-use object carries current-frame view coordinates. A target behind the
camera (`this_zpos <= 0`) is not drawn.

To distinguish a hit from a miss at draw time, `ai_laser(a5)` stores the aim
result, 1 for a miss and 2 for a hit, instead of `$FF`. Every existing reader
only tests the field for non-zero (`main.m68:122`, `main.m68:288`,
`vector.m68:205`, `special.m68:266`), so the change is safe.

Beam colours are unchanged: Thargoid and Thargon light blue, Constrictor white,
everyone else in the player-rating bands.

## 8. Performance

The target platform is an 8 MHz 68000 with up to 30 object slots. Three
measures keep the cost flat:

- one ship re-targets per game frame, not all of them;
- Chebyshev ranking, no square root and no division;
- the candidate set is limited to scanner range using `obj_range`, which is
  already computed by `get_range`.

The only permanent extra work in the flight loop is one distance computation
per attacking ship per frame in `do_attack`.

## 9. Files touched

Applied separately and identically to `src_atari/asm` and `src_amiga/asm`.
`src_orig` is left alone, per `AGENTS.md`.

| File | Change |
| --- | --- |
| `common.def` | Whitelist constants, `no_target`, `log_ai_missile`, `retarget_slot`, `npc_kill`, `npc_hit`, `target_range` |
| `combat.m68` | Faction mask table, `is_combat_ship`, `is_hostile`, `chebyshev_range`, `pick_target`, `hit_reaction` split out of `check_hit`, NPC damage and reaction routine, `explode_object` bookkeeping guard, `low_energy` release gate, ship-facing `launch_missile`, `drop_missiles`, narrowed `check_missile` |
| `logic.m68` | `target_coords`, target validation, generalised `do_attack` and `ai_laser_aim`, attack-run steering from `target_coords`, `angry` gate, `peel_off_check` substitution, `log_ai_missile` in `logic_vectors`, `do_locked` kill bookkeeping and jammer gate |
| `special.m68` | Ship-to-ship beam drawing |
| `main.m68` | Round-robin re-target cursor, `target` initialisation in `alloc_object` |

`tests/test_lasers.py`, `tests/test_enemy_escape.py` and `tests/test_missions.py`
each assemble `check_hit` out of the real source, so all three list
`hit_reaction` among the routines they pull in.

## 10. Testing

A new `tests/test_faction_ai.py` follows the existing Unicorn harness used by
`tests/test_lasers.py`:

- the faction matrix, every hunter class against every victim class;
- the whitelist rejects the station, canisters, title letters, panels, and
  **Cougar and Constrictor**;
- both mission ships keep attacking the player when `retarget` skips them, a
  whitelisted ship with nothing left still disengages, and a Thargoid created
  in witch space is born with the player in `target`;
- the nearest candidate wins, with the player competing under the same rule;
- `angry` adds the player to a trader's candidate set without locking it;
- a hunter requires `act_attack`: Python, Shuttle and Transporter never hunt;
- an NPC kill moves neither score, rating, bounty nor police record, cargo
  still drops, and it makes no explosion sound, while a kill the player made
  with a laser or a missile still does;
- no target is selected beyond scanner range;
- the state table of §5.1: a cruising ship enters `log_attack`, a launching or
  docking ship is never interrupted, and a ship left without a candidate falls
  back to `log_cruise`;
- `obj_range` still holds the distance from the player after `do_attack` has
  run against an NPC target, so radar, collision and out-of-range removal are
  unaffected;
- hits needed to destroy a Thargoid and a Thargon under AI-to-AI fire,
  compared against the player's figures, to confirm their relative toughness
  is preserved;
- one whole fight end to end through the real `retarget` and `do_attack`: a
  cruising pirate finds a trader closer than the player, enters `log_attack`
  with its health banked, the trader answers on its own turn and picks the
  pirate back, three attack frames aim, fire, damage and destroy it, cargo
  drops, and none of the player's score, rating, record, shields, messages or
  `angry` flag moves while `obj_range` still holds his own distance;
- `peel_off_check` takes `approach` for the player and for `no_target`, and
  the shooter's `velocity` only for a real ship, so the `target_range` scratch
  of another ship can never reach `do_police`, `do_launch` or `do_fly_planet`;
- `do_attack` steers at the target's coordinates and, when the target is the
  player, still steers at the origin (§6.2);
- the reaction table of §6.4.1 under NPC fire: the break-off for each starting
  logic and each `attack_type`, the `low_energy` retreat on a heavy hit, no
  retreat on a light one, and no missile even from a ship whose own target is
  the player;
- a hunter lined up on its target fires with the player's cloaking device on
  and with his controls locked, while the same hunter aimed at the player holds
  its fire in both cases (§6.2.1);
- `hit_reaction` on its own against the ten outcomes of the 1988 table, which
  pins the routine for the player's fire and another ship's at once, because
  after the split there is only one copy of it;
- a ship drives a missile at the ship it is fighting, as `log_ai_missile` with
  that ship in `target`, and prints nothing; the player is warned only by a
  missile his own attacker fired; a ship holds its missile when it has no
  target at all, when its target is too close, and when it has none left;
- a ship's missile kills without moving the player's score, rating, bounty or
  record, while his own missile still credits him;
- neither kind of missile kill reports "Target lost" for the missile that made
  it, while a second missile of his on the same ship is removed and reported;
- an ECM wave destroys every missile in flight whatever its logic, leaves ships
  alone, does nothing while no wave is running, and costs the player energy
  only when `who_ecm` says the wave is his;
- the ECM jammer lets a missile through a ship that carries ECM and would
  otherwise answer it, whoever fired that missile, and does not invent an
  answer from a ship that carries none; with the jammer off the same ship
  answers either kind of missile;
- his ECM jammer does not suppress a ship's ECM against another ship's missile;
- `target_lost` removes every missile chasing the dying ship, whoever fired it,
  and reports only when one of them was his;
- `check_missile` ignores a ship's missile, so it cannot block his own lock;
- through the real `check_sights` in `tests/test_registration.py`: a missile of
  his already flying at a ship still refuses him a second lock on it, a ship's
  missile flying at that same ship does not, and a missile of his aimed
  somewhere else does not either;
- the four Thargon counts, 4 and 7 under the player's fire against 2 and 3
  under another ship's, counted from `create_object`; that only a Thargoid
  releases anything on the NPC path; and that the NPC roll takes
  `npc_thargon_prob` rather than the player's rating, checked at both sides of
  the threshold with the rating set to Harmless and to Elite.

## 11. Risks and follow-ups

- **Missiles between ships are lethal.** `do_locked` destroys its target
  outright rather than taking energy off it, which is what the player's missile
  has always done. Against ships that is severe and uneven: a Wolf carries
  three certain kills, thirteen of the nineteen targetable types have no ECM at
  all, and the Viper has neither missiles nor ECM. Accepted deliberately in
  favour of a missile meaning the same thing whoever fires it; the alternative,
  `missile_damage` applied to `health`, is the change to make if play testing
  says the fights are too short.
- **Object slot pressure from missiles.** Every missile in flight is one of the
  thirty object slots, on top of the cargo and escape capsules NPC fights
  already produce.
- **Slow NPC fights.** `mood` in `objects.dat` ranges from 5 to 25 out of 255,
  so ships fire rarely. Two NPCs may take a long time to resolve a fight. If
  play testing confirms this, a separate `mood` multiplier for AI-to-AI fire is
  the remedy. Deliberately not part of this design.
- **"Condition RED!" can now lie.** An ambush spawned on the player may pick a
  closer trader instead. Accepted: the uniform rule was chosen over the
  message's accuracy.
- **Object slot pressure.** Containers dropped by NPC kills consume slots out
  of the 30 available, which can starve `alloc_object` for new spawns. Worth
  watching during play testing.
- **Vipers may ignore the player.** A viper launched because of the player's
  police record will chase a nearer pirate first. Accepted deliberately.

## 12. Amendments

Every amendment below was made after the first build was play tested. The
symptom that started them was that a trader picked a pirate but flew straight
past it, firing only when the pirate happened to cross its sights; the rest
came out of auditing the feature around that fix. They are listed in the order
they were made.

**2026-09-17, attack-run steering.** §6.2 has always required `do_attack` to
pass `target_coords` to `auto_pilot`, but the implementation plan's Task 6 left
that one substitution out, so the tail of `do_attack` still read:

    moveq #0,d0 ; auto-pilot towards player
    moveq #0,d1
    moveq #0,d2
    bsr auto_pilot

`(0,0,0)` is the player, who is the origin of every object coordinate, so every
ship in `log_attack` flew at the player whatever its `target` said. Aiming,
`target_range`, the miss threshold and `peel_off_check` had all been generalised
around it, which is why the ship still fired the occasional shot. Fixed by
replacing the three `moveq`s with `bsr target_coords`. No change to the design;
the design was simply not fully applied.

**2026-09-17, damage reaction.** The design covered how a ship *delivers*
damage to another ship but not how it *reacts* to taking it, so `low_energy`
and the break-off stayed on the player's path in `check_hit` only. A ship shot
by another ship kept flying straight where the player's fire would have made it
break off or run. §6.4.1 adds the reaction and is implemented; §4.5 and §6.6
carry the `npc_hit` gate it needs.

**2026-09-17, the Constrictor objective only counted a laser kill.** The
increment sat in `check_hit`, so destroying it with a missile or by ramming
left mission #1 unfinished, and shooting a Constrictor outside that objective
advanced the state anyway. Moved beside the alien station's in
`explode_object`, which every destruction path reaches, and guarded the same
way. The energy bomb is unchanged: `launch_bomb` skips the Constrictor along
with the Thargoid, the Cougar and platlets, so there is no bomb kill to count.

**2026-09-17, the mission ships stopped attacking.** `validate_target` treats
`no_target` as "nothing to fight" and `do_attack` answered that by cruising
away. That is right for a ship `retarget` looks after, and wrong for the Cougar
and the Constrictor, which the whitelist excludes on purpose and which are
spawned into `log_attack` with no target at all: both turned away on their
first frame instead of hunting the player, taking missions 3 and 4 with them.
§4.1 carries the fix. `explode_object`'s alien-station objective was never
affected -- the `dodec` is outside the whitelist too, so only the player can
ever destroy it.

**2026-09-17, the player's cloak and locked controls.** A sweep of every
`(a6)` global reachable from `do_attack` found two more of the same kind as the
Thargon gate: `do_attack` refused to fire while the player's cloaking device
was on or his controls were locked, whoever the target was. Neither state hides
one ship from another, so all AI-against-AI fire stopped during a docking
computer sequence, after an escape capsule launch, and for as long as the
player stayed cloaked. Both are now tested only when `target = 0`. The same
sweep cleared `radar_obj`, `laser_type` and `target_lost`; §6.2.1 records the
whole classification so the next reader does not have to repeat it.

**2026-09-17, missiles between ships.** §6.6 originally read "AI versus AI
combat uses lasers only", on the grounds that `do_missile` flies at the world
origin and that a launch announces itself in the cockpit. The first is a
property of `do_missile` alone -- `do_locked`, the player's missile logic, has
always flown at a target pointer and always let that target answer with ECM --
and the second is a property of `launch_missile`, not of missiles. Both are now
addressed directly: a ship's missile is a `log_ai_missile` running `do_locked`,
and the alert stays on the player-facing branch. §6.6 carries the whole change
and §11 the balance risk it brings.

**2026-09-17, Thargons kept out of that gate.** The first cut of `npc_hit`
suppressed the whole missile branch of `low_energy`, which took the Thargon
release with it — further than §6.6 ever asked, since §6.6 said Thargons keep
their current behaviour. The two reasons to ban an NPC missile, that
`do_missile` flies at the origin and that the launch announces itself, are both
untrue of a Thargon, which is an ordinary faction ship that makes no sound. The
gate now lets a Thargoid release, at fixed odds and in a smaller group; §6.6
carries the reasoning and the numbers.

**2026-09-17, the explosion is the player's sound again.** Once ships fought
each other, deep space answered with a constant rumble: every wreck anywhere in
the object list played `sfx_explosion`, and the player heard fights he could
not see. The sound is now his own again -- `explode_object` plays it only with
`npc_kill` clear, which is every path he can cause and no other: his laser, his
missile, ramming and the energy bomb. The ECM is deliberately left alone. It is
an area emitter rather than a kill, the 1988 game let him hear another ship's
ECM, and hearing one is how he learns his missile has been jammed. §6.5 carries
the change.

**2026-09-17, `npc_damage` lowered from 5 to 3.** Play testing found the ships
killed each other too quickly to be worth diverting to: a group was usually
down to one survivor by the time the player closed. Halving the damage roughly
doubles the length of a fight -- a hit now lands in 2..12 and averages 6 rather
than 2..20 averaging 10, and a Mamba survives about seven hits rather than
four. Nothing else moved: the 2..4 multiplier is still the one `do_attack`
applies on both paths, and the player-facing `damage` table is untouched, so
what he deals and takes is unchanged. §6.4 carries the number.

**2026-09-17, launched police flew away instead of arresting him.** Reported
from play: shoot the station, fly a little way off, and the vipers it launches
peel off and disappear past the edge of the scanner without ever attacking.
`pick_target` (§4.4) offers the player only to a ship with `angry` set, to a
`typ_pirate` or to a `typ_alien`; a policeman is none of the three, so a
launched viper had no candidate at all. `combat_state` counts `log_peel_off`
and `log_run_off` as "already in a fight", and `retarget` answers a fighting
ship with nothing to fight by sending it to `log_cruise` -- so the viper was
binned during its peel-off, before it ever reached `do_attack`. In 1988 this
could not happen: `log_attack` meant the player, and no ship needed a
candidate.

`launch_vipers` now sets `angry` on the ship it launches. `prepare_vipers`
sizes the wave from the player's combat rating, so a launch is always about
him, and `angry` is the flag §4.4 already defines for "this ship is after the
player". It is set after `launch_ship`, which writes `flags` outright. The
station's mission-5 Thargoids go out of the same door and are marked the same
way, which changes nothing for them -- `typ_alien` hunts him regardless.

Two consequences are deliberate. The cockpit attack indicator and the flashing
scanner blip, both driven by `angry`, now start when the vipers launch rather
than when they turn to attack about a hundred frames later; police coming for
the player is exactly what they are meant to report. And a viper placed by a
random encounter (§4.3 of the encounter design) is *not* marked, so it keeps
fighting pirates and leaves a clean player alone. The station's S zone plays no
part in any of this: `do_attack`'s station-space break-off has always applied
to `typ_pirate` only, and a viper is `typ_police`.
