# Fer-de-Lance bounty hunters — 2026-11-11

## Behaviour

NPC Fer-de-Lance ships now use `typ_bounty` on both Atari ST and Amiga. The
installed model header supplies the role for ordinary deep-space traffic,
station launches and custom encounters. Other hulls retain their roles. Buying
a Fer-de-Lance as the player does not assign the player an NPC faction.

- Hunters select pirates and aliens as enemies. Both factions can fight back.
  This preserves the Fer-de-Lance's previous trader-faction relationships.
- The player becomes an eligible target at legal record **40**, matching the
  C64/BBC hunter threshold. This includes serious Offenders at 40–49, as well
  as Fugitives at 50 or above. Below 40 the player must provoke the hunter.
- Scrambled ID does not exempt the player from a hunter's legal-record check.
  The decision consumes no random draw. Existing pirate truce rules are intact.
- The ordinary nearest-target selection ranks the wanted player alongside
  hostile NPCs. Scanner limits, mission exclusions, object removal checks and
  the existing round-robin retarget schedule remain in force.
- Hunters leave police, lawful traders, shuttles and other hunters alone. With
  IFF fitted, their existing radar colour is orange. Without IFF the ordinary
  unidentified-contact colour remains in use.
- Hunters do not collect cargo. A pirate remains a valid victim while
  collecting; actual damage interrupts its collection, releases its reservation
  and restores normal combat acceleration through the existing salvage hooks.
- After its final target disappears, a hunter resumes cruising. No new spawn
  template, population roll or encounter weight is added.

The player still receives the ordinary attack warning once a hunter attacks.
Existing `angry` state can retain a pursuit after the initial warrant check;
lowering the record does not introduce a new mid-fight amnesty mechanic.

Hunters also have [ten dedicated radio threats](2026-11-11-bounty-hunter-radio.md)
for acquired combat targets. These use the existing radio chance and cooldown;
they do not change target selection or police behavior.

## Station departures and police

A station-launched hunter completes its original launch and model-dependent
turn before normal target selection can begin. Station space does not grant
immunity from bounty hunting: at record 40 or above the hunter may select the
player after the turn, unless another eligible target is nearer.

Without a target, Fer-de-Lance retains the existing one-time 50% departure roll
and 5–10-second delay. Acquiring a target cancels an armed jump. The departure
tick also catches direct player or NPC provocation before the hunter's next
retarget slot, so an expired timer cannot replace a fighting hunter with a
hyperspace cloud. A cancelled jump is not automatically re-armed after combat. Player provocation
received during the station turn is retained when that turn completes, and an
abandoned hunter hull cannot execute an armed jump.
Ordinary traders retain their previous departure behaviour, including jumping
while under attack. Police, shuttles and transporters remain excluded.

Viper faction relations, legal-record probabilities, patrol caching, station
launch rules and equipment are unchanged. The player shooting a hunter near
the station still triggers the same police response as shooting the former
trader Fer-de-Lance. Player destruction of a hunter retains the existing
civilian legal penalty; NPC kills do not affect the player's record or score.
The existing collision exception and model bounty value are unchanged.

## Implementation boundaries

The two platform trees contain independent edits to `objects.dat`,
`common.def`, `combat.m68`, `main.m68` and `logic.m68`.

- `objects.dat` changes only the Fer-de-Lance faction word from 0 to 5. Its
  geometry and other model data are unchanged.
- `bounty_record_min` names the threshold. `pick_target` checks it only for
  `typ_bounty`; it does not route Vipers through hunter logic.
- The hostility table becomes `$82,$B5,$82,$00,$82,$82,$00,$37`. The police row
  remains `$82`. Added pirate/alien bits represent their existing hostility to
  Fer-de-Lance before it changed from trader to hunter.
- `trader_count` continues to count Fer-de-Lance as civilian traffic. Creation
  and removal both include `typ_bounty`. This preserves its existing mass lock
  and ordinary-traffic spawn gate without adding fields or changing save data.
- Explicit civilian checks retain Fer-de-Lance's legal protection and escape
  capsule eligibility. An abandoned hull cannot resume hunting.
- The existing retarget pass performs the new check. No additional object
  scan, per-frame random decision or new movement system is introduced.

The historical archive and `src_orig` are untouched. `CHANGELOG.md` is not
modified. Normal `ELITE` and `ELITE_ALT` distributions are the build targets;
the full Amiga mode/CPU matrix is outside this change.

## Verification scope

`src_atari/tests/native_bounty_hunter.py` and the independent Amiga copy run
against linked game routines and installed object headers. The 72 scenarios
cover the complete 64-pair faction matrix, legal boundaries with and without
Scrambled ID, nearest targets, all spawn paths, S-zone launch/turn completion,
deadline races, actual laser/missile provocation, police neutrality, salvage
interruption, civilian counters, actual torus locking, legal attribution and
escape capsules.

Existing suites exercise police patrols, ordinary/mission spawning, trader
departures, salvage, missiles, AI weapons, radio, IFF and Scrambled ID. The
police suite also compares the original station decision against 16,384
combinations of record, government and random outcome.

Each emulator uses a private executable, configuration and disk under `build`
on a verified separate hidden Windows desktop. Atari runs in a 1 MB Hatari ST;
Amiga runs MC68000/KS1.3 with 512 KB Chip RAM and 512 KB slow RAM. Reports and
tested image copies are retained in each tree's `build/bounty-qa/final`.
This is targeted native integration testing, not a complete mission playthrough.

## Initial verification results

A subsequent [integration review](2026-11-11-bounty-hunter-review.md) fixed two
station-departure edge cases and records the current builds and verification.
The table below describes the first implementation before those corrections.

| Check | Atari ST | Amiga |
| --- | ---: | ---: |
| Hunter scenarios, standard artwork | 72 passed | 72 passed |
| Hunter scenarios, alternate artwork | 72 passed | 72 passed |
| Existing integration scenarios, alternate artwork | 1,352 passed | 1,352 passed |
| Native scenario total | **1,496 passed** | **1,496 passed** |
| Python checks | 34 passed, 1 skipped | 35 passed, 1 skipped |

The existing historical-artwork identity check is skipped for customized
artwork. The 16,384 police-oracle vectors are exercised inside one native
scenario per platform, rather than added to the scenario totals.

Source comparison confirms that `prepare_vipers`, `launch_vipers`,
`check_police`, `police_response` and `check_patrol_record` are unchanged.
All four distributed object tables assign faction 5 only to Fer-de-Lance and
retain faction 4 for Viper. Distributed image and artifact hashes match the
tested copies. The aggregate verifier is
`src_atari/build/bounty-qa/verify_final.py`; per-platform results are in
`src_*/build/bounty-qa/final/report.json`.

One Amiga diagnostic attempt timed out during emulator boot, before injecting
the test scenarios. Its transcript is retained as
`src_amiga/build/bounty-qa/final/ELITE/boot-timeout.log`. The repeated run passed
all 72 scenarios. All owned emulator processes were closed after testing.
Nothing was copied to G: and the historical archive retains SHA-256
`19496256fb315c5db71c92385783acf4590a682ee3aae0c6a3435d0ea5faa1e2`.
