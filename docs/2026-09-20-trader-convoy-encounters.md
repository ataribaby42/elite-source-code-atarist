# Trader convoy encounters

Date: 2026-09-20
Trees: `src_atari`, `src_amiga`, implemented independently.

## Behaviour

The eighth random encounter template has weight 2, is available under every
government, and creates 1-2 traders from the existing Cobra MkIII, Python,
Anaconda and Cobra MkI table. Each ship is chosen independently.

Two traders start approximately 1000 units apart along the leader's local
x axis, with identical orientation vectors. Both keep the lower of their
model maximum speeds throughout peaceful cruising. A lone trader keeps its
own maximum. The group uses the existing placement in front of the player.

Each ship resumes its ordinary flight behaviour when its logic leaves
`log_cruise`, including entering an attack or evading a hit. It does not
automatically rejoin the convoy afterwards. No ship is forced to attack a
new target: the existing faction rules, nearest-target selection and Python
escape behaviour continue to apply. An unaffected partner can keep cruising.

The 50% encounter substitution, wave timing and mission guards are unchanged.
The new group raises `trader_count`, but has no pirates and does not raise
`pirate_count`; later waves remain governed by the existing timer and gates.

## Weights and government filtering

The original seven rows keep their weights. The totals and shares within
random encounters are now:

| Government | Total weight | Trader convoy | Any Thargoid template |
| --- | ---: | ---: | ---: |
| Anarchy | 12 | 2/12 (16.67%) | 2/12 (16.67%) |
| Feudal | 15 | 2/15 (13.33%) | 2/15 (13.33%) |
| Multi-government and above | 18 | 2/18 (11.11%) | 2/18 (11.11%) |

The selector previously kept the government in D1 across `rand`, although
`rand` destroys D1. Its second pass could therefore admit Viper rows excluded
from its first pass, also distorting the remaining weights. Reloading the
current system's government immediately after the roll fixes both passes.

## Implementation

- `combat.m68`: `role_convoy` uses the normal trader type table. The new row
  has maximum count 2. After creating a member, both it and the leader receive
  their shared initial velocity and `convoy_speed`.
- `common.def`: one additional runtime word, `convoy_speed`, before the model
  header. Zero means ordinary speed control. The object record grows from
  158 to 160 bytes; the model header and commander save format are unchanged.
  Thirty object slots plus the player's record need 62 additional bytes.
- `main.m68`: `create_object` clears the field, including copied records used
  for missiles, cargo and other spawns.
- `logic.m68`: cruising keeps the stored speed while retaining scanner-range
  cleanup. The normal logic dispatcher clears the setting before executing
  any non-cruise logic. Model maximum speed is never modified.

Existing mixed encounter traders have no convoy speed setting. Patrol and
station Vipers, faction relationships, targeting and combat routines are
unchanged apart from the selector's corrected government filter.

## Validation

Native test results and build logs are kept under each source tree's
`build/trader-convoy-qa`. The tests call the actual linked MC68000 game
routines in separate hidden emulator desktops, using private disk copies.

The scenarios cover all 135 weighted outcomes across eight governments,
2048 selections with the real random generator, all 16 trader model pairs
over 128 cruise updates, relative position and speed, single and partial
groups, exhausted and fragmented object pools, combat and Python evasion,
copied-record reset, scanner cleanup and unchanged mixed-group speeds and
Viper patrol flags. A comparison with the previous selector reproduces the
D1 government-filter failure.

Results: all 20 convoy scenarios passed in Hatari and in WinUAE configured as
an A500 with Kickstart 1.3, 512 KB Chip RAM and 512 KB slow RAM. The existing
22 native patrol-police scenarios also passed on both platforms, including
station response, changing legal status and nearest-target AI combat.

The Python suites passed (Atari: 33 tests, one skipped; Amiga: 31 tests, one
skipped). Both `altgfx=no` and `altgfx=yes` distributions were built and
validated as `ELITE` and `ELITE_ALT`; generated working assets were finally
restored to the default `gfx` selection.

The subsequent [existing-spawn regression checks](2026-09-20-convoy-spawn-regression-checks.md)
passed 88 native scenarios per platform, covering mission guards, the original
spawn paths, copied records, missiles, cargo and object-slot reuse.
