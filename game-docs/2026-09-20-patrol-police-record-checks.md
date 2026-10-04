# Random patrol police-record checks

## Behaviour

Random-encounter Vipers now inspect the player's police record during their
first eligible targeting turn within scanner range. A patrol that declined
to pursue the player checks again when the numeric record changes. This
includes Clean becoming Offender or Fugitive, and an increase within Offender.

Both patrols and the existing station response use `police_response`:

- Record zero never triggers an arrest and consumes no random number.
- For a nonzero record, draw the original random value from 0 through 255.
- Pursue when the value is less than `floor(record / 4) + government * 16`.

Each patrol remembers its last inspected record. An unchanged record does not
receive another roll every targeting turn: repeated rolls would turn the
original probability into an almost certain arrest. Different patrols make
independent decisions. Checks use the existing round-robin targeting cadence,
so an eligible ship observes a change within at most 30 game frames.

A successful decision sets the existing `angry` flag. The player joins the
normal candidate set; a nearer pirate or alien still wins. This is the same
targeting rule used by station arrest ships and by a ship the player shoots.
Once angry, a patrol continues its existing pursuit without further legal
rolls. A later record reduction does not cancel an ongoing pursuit, just as it
does not cancel a station arrest or direct provocation.

## Isolation from existing behaviour

Only a Viper created by `encounter_member` opts into this check. The new
`patrol_record` word is initialized by `create_object` for every spawn, including
copied and reused slots:

| Value | Meaning |
| --- | --- |
| -1 | Not an encounter patrol; never inspect the record through this path |
| -2 | Encounter patrol awaiting its first eligible check |
| 0..255 | Last inspected police record |

The object record grows by two bytes, adding 60 bytes across the 30 slots.
The model data header and saved commander format are unchanged.

Station launches retain `police_hunt`: arrest launches are angry, alien-response
launches are not. Patrol checks do not modify `police_hunt`, `launch_count`,
`launch_rate`, or the station checkpoint. Station checks remain once per system;
their trigger and number-of-Vipers calculation are unchanged.

The faction table, nearest-target selection, launch-state exclusions, attack
routines, direct-hit retaliation and AI-versus-AI damage are unchanged. The
new check runs only after the existing hunter and combat-state eligibility
tests, before `pick_target`. Distant patrols wait until inside scanner range.

The implementation is maintained independently in `src_atari` and `src_amiga`.
The historical archive and `src_orig` are untouched.

## Validation

Native MC68000 regression suites passed on Atari ST in Hatari and on an Amiga
A500 configuration in WinUAE (68000, OCS, Kickstart 1.3, 512 KB chip and 512 KB
slow RAM). Both ran on verified private hidden Windows desktops, using private
test configurations and disk copies under each tree's `build/patrol-police-qa`.

Each platform passed 22 scenarios, including:

- 16,384 comparisons against the pre-change station routine: eight records,
  all eight governments and every one of the 256 random outcomes. Pending
  launch count, launch timing, launch reason and final random state match.
- Native verification that the test seeds cover all 256 random outcomes.
- Actual random encounters, first contact as Clean/Offender/Fugitive, cached
  refusals and detection of a later crime or an increased Offender record.
- Nearest pirate/alien selection ahead of the player, continued NPC combat
  after a declined arrest, and disengagement after NPC enemies disappear.
- Scanner-range and round-robin gates, independent patrol decisions, copied
  records, slot reuse, and retaliation after a player's laser hit.
- Both kinds of station launch and their nearest-NPC targeting and recovery,
  plus the original launch reasons after player
  hits on a trader, police ship or alien inside station space.

Default and alternate-graphics distributions are built for both platforms.
The existing Python suites also passed: 33 Atari tests and 31 Amiga tests,
with one expected skip per platform because customized PNGs are no longer
required to reproduce the historical asset hashes.
