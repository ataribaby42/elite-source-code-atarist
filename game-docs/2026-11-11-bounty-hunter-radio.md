# Bounty hunter radio — 2026-11-11

Both platform trees independently add ten Fer-de-Lance combat transmissions.
The sender must have both the Fer-de-Lance hull and `typ_bounty` role. Existing
police, trader, pirate, alien and station routing remains unchanged.

The observer uses the existing target event, scanner limits, 50% transmission
chance, cosmetic random generator and 50-game-frame sender cooldown. It can
address the player or an NPC. All ten texts have equal probability on success.
Keeping a target does not repeat the threat; a silent or cooldown-suppressed
attempt is consumed. Cloaking, docking and game over suppress new messages as
before. A peaceful hunter does not send a greeting.

The new IDs are 130–139; IDs 0–129 retain their text and meaning. No combat,
police, legal-status, spawn, save-format or model-data change is included.

## Texts

1. Your bounty is mine.
2. I've come to collect.
3. The hunt ends here.
4. Consider this contract closed.
5. You can run. I get paid to follow.
6. Target acquired. Weapons ready.
7. You're worth more than your cargo.
8. Nothing personal. Just business.
9. One less name on my list.
10. You won't outrun a bounty hunter.

## Validation

`tests/native_bounty_radio.py` exercises the linked game routines, all ten texts
for player and NPC recipients, exact formatting, actual hunter target selection,
Clean-player retaliation, identity hiding, suppression, cooldown and target
changes. It verifies that the observer preserves non-radio object data, both
gameplay random streams and the station random stream.

The existing rendering suite now checks every hunter text against independently
wrapped reference screen output, including visible/hidden player IDs and UI/3D
display conditions. Regression suites cover the original AI radio, cooldowns,
radio-on/off gameplay parity, station radio and bounty hunter behavior.

Private emulator tests use verified separate hidden desktops and private disk
copies. Evidence is stored in `src_*/build/bounty-qa/radio-final`; source snapshots
from before the addition are in `radio-before` beside it. Only normal ELITE and
ELITE_ALT builds are included; Amiga uses PAL/MC68000.

All final suites passed on both platforms:

| Build / coverage | Atari ST | Amiga |
| --- | ---: | ---: |
| ELITE: hunter radio and full-screen reference rendering | 213 | 213 |
| ELITE_ALT: same checks plus existing integration suites | 572 | 572 |
| **Total native scenarios** | **785** | **785** |

The verifier `src_atari/build/bounty-qa/verify_radio.py` confirms that only
`asm/ai_comm.m68`, `asm/comm.m68` and `asm/common.def` changed among runtime
sources, all 130 prior text entries remain identical, and the disk images in
the output folders match the private images tested. It also verifies the
unchanged historical archive. Reports are in each platform's
`build/bounty-qa/radio-final/report.json` and the combined
`src_atari/build/bounty-qa/radio-summary.json`.

ELITE and ELITE_ALT distributions are updated for both platforms. No G: files
were updated, `CHANGELOG.md` was not modified, and the final process check found
no private emulator left running. The full Amiga display/CPU matrix was not run.
