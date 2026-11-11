# Pirate salvage and salvage encounters

Implemented independently in the enhanced Atari ST and Amiga source trees.

## Behaviour

When a regular pirate's current combat target is destroyed, the pirate gets
one opportunity to collect ordinary cargo released by that exact ship. A
despawn or station trader hyperspace departure does not create this opportunity.

- With available cargo and no other hostile target, collection is certain.
- With available cargo and another hostile target, one roll selects collection
  with 50% probability. The player remains a hostile candidate under the usual
  faction and Scramble ID rules.
- Without suitable cargo, normal combat targeting continues without a roll.
- The decision lasts for that wreck's salvage phase; it is not rolled again
  every frame or after rejecting the opportunity.
- An actual laser hit or a successfully launched missile directed at the
  collector interrupts salvage immediately. The victim releases its reservation
  and resumes combat against the attacker. Merely locking a player missile does
  not provoke it.

Collection uses a separate objective from the existing combat target. A pirate
steers toward the drifting container, slows near it, and collects it within the
combined hull/container radius plus 32 units, in its forward hemisphere. Each
pirate can collect at most four ordinary containers during its lifetime. An
individual approach is bounded to 5,120 simulation steps, five times the
original budget to accommodate the slower collection flight.

While collecting, a pirate's speed cannot exceed 20% of its model maximum,
rounded down to an integer. The cap applies immediately when salvage is selected
or a scavenger is spawned, while approaching/turning, after a pickup, and while
waiting for unreserved cargo. Approach minimum speeds never override the cap.
The model's `VEL_MAX` is never changed: departure, ordinary combat, weapon
provocation, theft and cargo destruction resume normal acceleration as soon as
the pirate leaves collection logic. A pending salvage decision does not yet
limit a pirate that has not chosen to collect.

This initial implementation counts collected containers; it does not introduce
a commodity inventory for NPCs. Destroying a collector still uses its model's
existing cargo-drop rules, rather than recreating the exact collected payloads.

## Reservations and hostility

Only one NPC can reserve a container. The reservation stores both object
pointers and lifetime serials, preventing a reused slot from becoming an
accidental cargo or owner reference. Destruction, removal, interruption and
invalid cargo release the reservation. Player scooping ignores reservations.

A second scavenger with no unreserved container continues quiet flight. It can
take over if a reservation is released. Once no suitable containers remain,
scavengers from the dedicated encounter leave peacefully, but still retaliate
if attacked or their encounter cargo is destroyed by the player. Ordinary
pirates resume their existing target selection after finishing salvage.

Pirates retain their original model, faction, vulnerability and radar presence.
Neither `is_combat_ship` nor the faction hostility masks is changed. Police
Vipers and other hostile factions can therefore select and attack collectors,
waiting scavengers and peacefully departing scavengers. Only the attacked
member of a salvage group changes to combat after a weapon attack. Player cargo
theft is a separate group-wide provocation: successfully scooping a container
from the dedicated encounter, or destroying one with a laser, collision or player
missile, immediately makes all surviving pirates from that group attack the
player. This includes waiting, departing and already fighting
members, and revokes their Scramble ID neutrality. Every reservation they held
is released. Other encounter groups and ordinary wreck collectors are unaffected.
Abandoned hulls whose pilots have escaped are excluded from retaliation; their
drift logic and disabled weapons remain intact.

The theft notification runs only after cargo has actually entered the player's
hold, for both ordinary and exact-mass containers. Destruction is notified once
before explosion cleanup, using the existing player/NPC kill attribution. A
failed scoop by itself, a nonlethal hit, NPC pickup or NPC destruction does not
provoke the group. If a failed scoop becomes a destructive collision, that
destruction does provoke it. No legal penalty is added to the existing player
salvage rules.

Mission-only hulls, traders, shuttles, transporters, police and aliens do not
acquire pirate salvage behaviour. Collection excludes escape capsules, mined
fragments and special equipment such as the cloaking-device container.

## Ninth custom encounter

The new template has weight 1 and is eligible under every government. Existing
template weights and government restrictions remain intact; their normalized
shares change because the selection now includes a ninth row. The existing
50% ordinary-wave encounter substitution and story-mission routing remain.

The salvage share of custom encounters is approximately 1/13 in Anarchy, 1/16
in Feudal systems and 1/19 under other governments. Including the 50% wave
substitution, that is about 3.85%, 3.13% and 2.63% per eligible ordinary pirate
wave respectively. These are selection probabilities, not fixed time intervals:
station vicinity, existing pirate counts, free object slots and mission routing
still gate actual creation. Torus interruptions use the same wave selector.

The template creates 4–8 ordinary cargo containers followed by 1–2 pirates from
the existing small/medium encounter pirate table. It uses at most ten objects.
Containers form a compact irregular wreck cloud. Seven follower cells have
centres at signed 160-unit offsets on each axis, with independent random jitter
of -64 to +64 units. Thus every container starts within 224 units per axis of
the first one, with enough separation to avoid overlapping hulls. The pirates
start at (+/-900, 0, 1400) relative to that centre, approximately 1,665 units
away and at least 1,176 units from any container along the depth axis. Their
seats are independent of the selected cargo count. All objects still fit inside
the existing 2,048-unit scanner placement margin.

Each container receives its own normalized random flight direction and an
independent speed of 1–2 units per simulation step. Its spin is around that
flight direction; cruise logic retains the selected speed. Containers carry
ordinary commodity IDs 0–15. This lets even the slower capped collectors close
the distance to the new encounter's cargo. Ordinary ship-destruction containers
also use independent speeds of 1–2, following the later adjustment on
2026-11-11. Other encounter formations, drop placement and mined-fragment speeds
retain their previous rules.

The generator counts free slots before creating the group. With fewer than five
free slots it creates nothing. Otherwise it reduces the requested group if
necessary, reducing containers to four before reducing pirates to one. The
partial spawn rules of other encounter templates are unchanged. Each pirate's
existing four-container lifetime capacity is retained, so one pirate may leave
some of the larger cargo group behind.

## Implementation

Each platform owns its own `asm/loot.m68` module. The object record gains 30
transient bytes before the model header, including cargo provenance, reservation
identity, encounter identity, salvage mode, collected count and approach counter.
The 30-object pool and separate player record require 930 additional bytes.
Commander serialization and model-header layout are unchanged.

The encounter identity is the first container's unique lifetime serial, stored
as a value in every member. It survives collection/removal of the original
container and the pirates' transition to combat or departure. Creating a new
object clears it, so slot reuse cannot link unrelated groups. Successful player
theft or cargo destruction scans the fixed 30-object pool once; it adds no
per-frame scans.

Target search runs on the existing rotating retarget schedule: one object slot
per game frame. Candidates are ranked by the existing inexpensive axis-distance
metric within 4,096 units per axis. Newly created cargo receives an initial
range calculation if its regular update has not run yet. Per-frame collection
only validates the selected objective and advances flight; it does not search
the entire object pool or draw new random choices.

Destruction notifications occur before the victim changes to explosion logic;
cargo creation records the victim's lifetime. Selection is deferred until the
hunter's retarget turn. NPC pickup marks a container for normal deferred removal
and releases missile locks without invoking player inventory, equipment,
messages, sounds, bounty or score handling.

A consumed barrel immediately becomes non-colliding and untargetable, with no
visible radius, while retaining its allocated slot until normal removal. This
prevents the player or another NPC from collecting the same cargo later in the
same frame without bypassing the normal object counters or draw-queue lifetime.

## Verification

Native tests execute the linked MC68000 routines in private Hatari and WinUAE
instances on verified separate hidden Windows desktops. WinUAE uses Kickstart
1.3, a 68000 and 512 KB Chip RAM plus 512 KB slow RAM. Test executables,
configurations and disks live under each source tree's `build/pirate-loot-qa`.
The user's emulator sessions and distribution files on G: are not modified.

The new native suites cover:

- All 100 probability outcomes and absence of repeated rolls.
- Fresh cargo, exact wreck provenance, reservations, ownership transfer and
  container/owner slot reuse.
- Actual Viper/player laser hits and successful AI/player missile launches.
- All four salvage modes remaining valid police targets; unaffected partners
  continuing to collect.
- Player recovery of a reserved exact-quantity container; NPC collection
  leaving player inventory, mission state, cash and score intact.
- Excluded ship/object types, collection capacity, approach timeout and scanner
  cleanup.
- All ten new group compositions, 0–10 free-slot boundaries, and 128 encounters
  generated with the real RNG, checking positions and scanner visibility.
- Actual steering and collection for all nine regular pirate models from
  four approach directions, including moving containers and an initial target
  behind the hull.
- A rendered two-pirate/one-container scene, interleaved AI/movement updates,
  exactly-once collection, peaceful departure and an arriving Viper attack.

Existing regression suites additionally exercise spawn routing, police patrols,
convoys, player salvage, station trader hyperspace, Scramble ID, AI ship systems,
laser bursts, missile handling, death cargo, station destruction, radio,
condition state and cloaked cargo. The older salvage fixture explicitly sets
20 tonnes of net free capacity to account for the current player hull and
equipment-mass rules; the gameplay salvage routine itself is unchanged.

Per-build reports, scene captures, build logs and source review are retained in
the QA directories. Only the standard `ELITE` and `ELITE_ALT` distributions are
built; this verification does not claim a complete mission playthrough or the
full Amiga display/CPU release matrix.

### Initial feature verification

These results record the original 1–2-container implementation, before the
4–8-container expansion and group theft retaliation described above.

| Verification | Atari ST | Amiga |
| --- | ---: | ---: |
| New behaviour, standard artwork | 92 passed | 92 passed |
| Rendered encounter, standard artwork | 4 passed | 4 passed |
| New behaviour, alternate artwork | 92 passed | 92 passed |
| Rendered encounter, alternate artwork | 4 passed | 4 passed |
| Existing gameplay regressions, alternate artwork | 1,018 passed | 1,018 passed |
| Total native scenarios on final binaries | **1,210 passed** | **1,210 passed** |
| Python checks | 34 passed, 1 skipped | 35 passed, 1 skipped |

The Python skip is the existing historical-artwork identity check for customized
graphics. Repeated vectors within individual native scenarios include all 100
salvage rolls, 128 real-RNG salvage groups, 2,048 encounter-selector seeds,
4,608 player cargo collections and the existing exhaustive police-response
comparison; these iterations are not counted as separate scenarios above.

Development tests caught and resolved the mission-only Cougar exclusion and
same-frame double collection by an NPC and the player. The latter has a retained
failing pre-fix run under `verify/ELITE_ALT/pickup-audit`, followed by the passing
final-build regression. The generated test harness also needed larger-fixture
handling and separation of screenshot control words from a test routine with a
similar name; those adjustments affect diagnostics only.

At that verification point, all four distributed images matched their tested
final copies byte for byte.
The historical source archive retains its original SHA-256. Each platform's
`build/pirate-loot-qa/final-report.json` records scenario totals, source hashes
are in `final-sources.json`, and the final rendered comparison is
`src_atari/build/pirate-loot-qa/final-scene-comparison.png`.

### Expanded encounter and theft verification (2026-11-11)

The updated standard `ELITE` and `ELITE_ALT` images passed these checks on each
platform, using the same isolated 1 MB emulator configurations:

| Verification | Atari ST | Amiga |
| --- | ---: | ---: |
| Salvage, counts, placement and slot boundaries, both artwork variants | 208 passed | 208 passed |
| Successful/failed scoops and group retaliation, both artwork variants | 74 passed | 74 passed |
| Rendered maximum group, movement and actual player collision, both variants | 6 passed | 6 passed |
| Spawn, police, convoy, cargo, death, trader departure, Scramble ID and missile regressions | 483 passed | 483 passed |
| Total native scenarios | **771 passed** | **771 passed** |
| Python checks | 34 passed, 1 skipped | 35 passed, 1 skipped |

The theft checks include all 16 generated commodities, exact payloads, failed
scoops, unrelated groups, ordinary wreck cargo, removed/destroyed/reused slots,
departing members, members already fighting police, NPC pickup and continued
Viper hostility. Maximum-group scenes execute real drawing, AI and movement
routines; theft is also exercised through the player's collision routine.

Reports and source/image hashes are under each platform's
`build/pirate-loot-qa/cargo-4-8/report.json`. The distributed images match their
tested copies, and the historical archive hash remains unchanged. The rendered
comparison is `src_atari/build/pirate-loot-qa/cargo-4-8/large-scene-comparison.png`.

### Compact debris and destruction retaliation verification (2026-11-11)

The later debris-layout revision passed 592 native scenarios on each platform:
314 salvage, theft, debris and rendered-scene cases across standard and alternate
artwork, plus 278 spawn, patrol, convoy, player cargo, missile impact/collision,
death-cargo and cloaked-cargo regressions. The 13 new debris cases per build
execute real player laser, collision and missile destruction paths, verify NPC
laser/missile kills do not provoke the player, and cover missed/nonlethal hits,
unrelated cargo, departing/dead pirates and repeated destruction notification.
They also inspect 128 real-RNG groups for cluster bounds, separate pirate seats,
normalized headings and all three speeds, then advance actual drift and cruise.

A separate audit uses the game's exact orbit trig table for all 129,600 angle
pairs at the greatest spawn radius. The farthest pirate is approximately 24,255
units from the player, below the 24,576-unit scanner boundary. The conservative
cargo bound is approximately 23,011 units. Native placement tests also verify
the game's own range results and unique object positions.

Both Python suites pass with the same existing artwork skip. Updated standard
`ELITE` and `ELITE_ALT` distribution images match their runtime-tested copies.
Reports, source/image hashes, placement bounds and visual comparisons are in
each platform's `build/pirate-loot-qa/debris` directory. The historical archive
hash is unchanged.

### Collection speed limit verification (2026-11-11)

The 20% cap and agreed encounter-container speed of 1–2 passed 683 native
scenarios per platform: 279 feature cases in each artwork variant, plus 125
spawn, patrol and convoy regressions. Each variant includes 122 dedicated speed
cases covering all nine regular pirate models, both collection modes, entry,
waiting, lost cargo, pickup, capacity, timeout, departure, player/Viper hits and
group provocation. They verify the original model maximum remains intact and
normal departure/combat acceleration can reach it again. Integer limits below
the old approach minima and 128 real spawn groups are also checked.

Real steering-and-movement pickup tests retain their four original approach
directions and distances, now using the agreed cargo speeds. They exposed the
old deadline as too short for slow collectors; extending the bounded attempt
from 1,024 to 5,120 steps allows these longer pursuits without raising the speed
cap. The timeout boundary still releases the reservation and cancels the cap.
Examples of integer limits are Krait 24 -> 4 and Adder 19 -> 3; both can close
on the new encounter's 1–2-speed cargo.

Both Python suites pass with their existing artwork skip. Current
standard distributions match their tested copies and the historical archive
hash is preserved. Per-platform reports, hashes, source review and scene captures
are under `build/pirate-loot-qa/speed-limit`.

The temporary forced-encounter Amiga disk was retired on 2026-11-11. Normal
distributions retain random encounter selection. Reusable regression tests run
against the ordinary Atari and Amiga images.
