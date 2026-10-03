# Scramble ID

Both independent enhanced builds adapt the service from the companion Elite
Unbound C64 source. The preserved original build is unchanged.

## Buying the service

Entering Equip while docked in an **Anarchy** system offers the service if the
current hull does not already have a scrambled ID. The existing Yes/No panel
appears before the normal equipment screen. Its question is:

> You are approached by a shady person. Do you want to scramble your ship ID for 5000.0 CR?

Click Yes/No, press Y/N, or press Escape to decline. Yes costs exactly
**5,000.0 CR**. Insufficient cash changes neither money nor identity. No and
Escape open normal Equip without charging. Declining does not remove the offer
on a later entry. Equipment purchases, resale and the Buy/Equipment heading
continue to use the existing interface.

The Status registration becomes `??-???`; the underlying registration is kept.
Scrambling uses no cargo space and does not immediately change legal status.
It persists through docking, launch, ordinary and galactic hyperspace, and
commander save/restore. A successful ship purchase or escape creates a new,
visible registration. Rejected purchases and failed escapes retain the old ID.

## Stations and police

Inside the existing physical station-space boundary, a scrambled ID raises the
legal record to **at least 100** in government types 2 and 4 through 7:
Multi-Government, Communist, Confederacy, Democracy and Corporate State.
**Anarchy, Feudal and Dictatorship ignore it.**

The check runs before the normal station police response and does not reduce
a record already above 100. A destroyed station does not trigger it. Returning
from an in-flight menu does not produce repeated warnings once the record is
already at least 100. The existing police spawning probabilities still apply.

When the record rises, the station sends one of Unbound's three warnings:
`SCRAM PIRATE!`, `RUN PIRATE!` or `DIE PIRATE!`, prefixed by its registration
and the player's concealed registration. The service remains active afterwards.

## Pirate reactions

At creation, an ordinary human pirate has a **128/256 (50%)** chance to ignore
the player when both conditions hold:

- The player's ship ID is scrambled.
- The legal record is at least **50**, the existing Fugitive threshold.

Each ship rolls independently, including ambush wingmen and pirates in encounter
groups. An entire wing can be neutral, hostile or mixed. Existing ships are not
rerolled when the player's record changes. Neutrality lasts for that ship's
remaining presence in the local object pool, unless the player attacks it.

The ship retains its pirate classification, hidden registration, scanner colour,
statistics, laser loadout and faction enemies. Target selection omits the player
but still permits AI-versus-AI combat. A player laser or surviving player missile
hit permanently ends that ship's neutrality; attacks from another AI do not.
Neutral pirates use Unbound's 16..31 cruising-speed selection, capped by the
port's existing shared hull speed limit.

Thargoids, Thargons/Tharglets, Cougar and Constrictor are excluded. Scripted
mission waves `$15`, `$21`, `$41` and `$52`, including Cougar's Asp escorts,
retain their original hostile targets and do not consume a neutrality roll.
Traders, police, bounty-hunter encounters and non-combat objects are unaffected.

## Implementation and compatibility

Each tree owns its implementation in `asm/registration.m68`. Equip calls the
offer helper only on screen entry. Internal equipment redraws do not repeat the
question. The blocking confirmation is used only while docked; flight jettison
continues using its existing asynchronous dialog.

`create_object` initializes the `pirate_truce` word after installing the actual
model. A nonzero word also stores neutral cruise speed. Allocation, removal and
universe clearing reset it; copied objects receive a fresh decision. Only
ordinary attack/cruise spawns qualify, so launch, preview and escape-capsule
sequences cannot be converted into neutral pirate flights. Targeting
and player-hit paths respect or clear it as appropriate.

Unbound samples the existing random byte. This port takes a fresh byte only for
eligible pirates: the immediately preceding AI laser selection uses rejection
sampling and would bias a reused byte towards neutrality. The decision uses
`byte < 128`; ordinary spawns without the service and mission waves consume no
additional randomness. Warning text uses rejection sampling to choose uniformly
among three messages.

Commander files remain **256 bytes**. Existing fields keep their offsets:

| Decoded file offset | Contents |
| --- | --- |
| 178..185 | Existing RID1 registration |
| 186..191 | Existing SHP1 player hull |
| 192..199 | Existing SCG1 Special Cargo |
| 200..203 | New ASCII `SID1` tag |
| 204..205 | Word: `0` visible, `$00FF` scrambled |
| 206..255 | Unused tail |

Missing tags or other flag values restore a visible registration. An invalid
RID1 identity also clears scrambling. Default commanders start with a visible ID.

## Reference

The primary reference is the local sibling C64 project
`Elite-C64/elite-source-code-commodore-64`, specifically
`1-source-files/main-sources/elite-source.asm`:
`ScrambleRegistrationListEnd`, `ScrambleRegistrationPurchase`,
`ScrambleRegistrationSafeZone`, `MaybeSpawnNeutralPirate`,
`PlayerRegistrationGenerate` and `PlayerRegistrationScrambleValidate`.
The warning text is in `elite-hangar.asm`.

## Validation

Native tests execute the linked game in Hatari and WinUAE on separate hidden
Windows desktops, with private executable, configuration and disk copies.
The new suites cover availability, exact payment, confirmation input, save
migration, registration display, government and station boundaries, every byte
of the neutrality roll, target selection, retaliation, full and mixed wings,
mission exclusions and docking/hyperspace persistence.

`native_scramble_id.py` also creates 4,096 pirates with the real generator in
each of three rating bands. The observed Atari neutral counts are 2,026, 2,024 and
2,024 (49.46%, 49.41%, 49.41%). Exhaustive injected byte tests verify the exact
128-of-256 decision separately from this distribution check.

The final checks cover **1,134 native scenarios per platform** across 16 suites,
including 164 Scramble ID scenarios. They also cover existing mission spawns,
AI combat/loadouts/bursts, player hulls, Special Cargo, missile impacts and
collisions, shield flashes and identification. The affected Scramble ID and
spawn suites were repeated after the final escape-sequence and cruise-speed
checks. Python discovery passes 34 tests per tree; one existing artwork identity
check is skipped for the selected alternate graphics. The build matrix passes
all 20 artwork/display variants and restores the user's selected build options.

The Equip question, mouse and keyboard answers, cursor restoration and hidden
Status registration were also checked visually in both private emulators.
Artifacts and diagnostic logs are under each tree's `build/scramble-id-qa`;
the Amiga visual captures are under `build/scramble-visual`.
