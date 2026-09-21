# Source code and development

See the [main README in the project root](../README.md) for building and running the game. This directory contains the working sources and development tools. `src_orig` now contains an independent build of the preserved original game; enhanced Atari gameplay changes belong only under `src_atari`. The untouched historical source archive is `resources/elite_atarist_source.zip`.

Run all commands below from the project root. Paths in the tables and text are also relative to the root.

## Editable graphics

The build option `altgfx=yes|no` defaults to `no` (`gfx/`). Run
`build_atari.bat altgfx=yes` from the project root to use this tree's `gfx_alt/`
instead. The selected directory must contain all eight PNGs and `layout.json`.
Both choices generate the same asset and distribution paths; use `altgfx=no`
to rebuild with the standard sources.

Edit the eight PNGs in `gfx/`; the build converts them into `assets/` before
assembly. Pillow is required (`python -m pip install Pillow`). Keep canvas sizes
and use each image's exact RGB palette. `cockpit.png` uses the cockpit palette;
all other PNGs use the UI base palette, including in `gfx_alt/`. UI indices 6,
8 and 14 are `#FF0000`, `#6DB600` and `#6D4900`; cockpit indices 6 and 14 are
`#DB0000` and `#FF0000`. Both use cyan `#00FFFF` for transparent index 0 and
black `#000000` for opaque index 13. RGB, RGBA and reordered indexed PNGs are
supported, and game pixel indices and hardware palettes stay unchanged. See the
[PNG editing guide](../docs/2026-09-19-editable-png-graphics.md) for the complete
palette, alpha handling, sheet layouts and verification commands.

## RCS sound

RCS FX also enables a motor tone while the player holds Space (accelerate)
or slash (decelerate). Releasing both keys silences it on the next VBL. Actual
speed changes, including mouse throttle and automatic changes, do not trigger
it. Acceleration is silent at maximum speed, and deceleration is silent at
zero speed; the opposite direction remains audible. Current speed sets the
pitch, using PSG periods from 1920 to 960 for a deeper range close to the
Amiga engine's fundamental. Volume rises to PSG level 12 over four VBLs, matching the continuous
laser's level. The motor has priority below RCS and all ordinary effects. Both RCS FX
OFF and Effects OFF mute it. Docking, either hyperspace jump and death clear
its gameplay request immediately, even if a throttle key remains held.

The Atari build includes a quiet RCS hiss whenever the roll or pitch control
value changes, including automatic damping back to zero. A steady nonzero
value is silent. The request stays continuous between game frames, with a
`RCS FX: ON / OFF` option beneath Effects; it defaults to ON and is saved in
the Commander using bit 7 of the existing user preference byte. Effects OFF
still mutes RCS. The sound has a
short volume ramp. RCS uses only a free sound channel and is the first voice
replaced when another effect needs one. It also yields the shared PSG noise
generator to other noise effects, even when a channel is free. It resumes only
while steering is still changing. Effects OFF, pause, docking, locked controls,
hidden cockpit and game over silence it.
Docking, hyperspace (including galactic jumps), and death animation entry points
also stop RCS immediately and discard pending steering audio before drawing.

## Directory contents

| Path | Purpose |
| --- | --- |
| `src_atari/asm/` | 39 converted game modules, macros, definitions, loader, font, and ship data |
| `src_atari/assets/` | Game bitmaps, loading artwork, images, and trigonometric tables |
| `src_atari/modules.txt` | Game module order from the original `ELITE.LNK` |
| `src_atari/elite.ld` | Reference memory layout and linker symbols for runtime relocation |
| `src_atari/build.py` | Assembly, linking, verification, and floppy image creation |
| `src_atari/build.bat` | Windows build entry point called by the root `build_atari.bat`; forwards all arguments |
| `src_atari/build.ps1` | Python discovery and argument forwarding to `src_atari/build.py` |
| `src_atari/tools/` | Original dialect converter, floppy image builder, original-file verification, and helper scripts |
| `src_atari/tests/` | Regression tests for the conversion, launcher and raster routines |
| `src_atari/vendor/` | Two original vasm/vlink source archives for optional tool rebuilding |
| `src_atari/original-sha256.json` | Baseline SHA-256 hashes of all 307 files in the historical ZIP |
| `src_atari/build/` | Generated objects, logs, maps, and diagnostics |

## Editing and building

`build_atari.bat outputname=ELITE_ALT` creates `output_atari/ELITE_ALT/` and
`output_atari/ELITE_ALT.ST`. The default is `outputname=ELITE`; this option can be
combined with `altgfx=yes` or any other enhanced build option. Pass a filename,
without a path or disk suffix; quote the whole argument if it contains spaces.
Files inside the distribution keep their existing names, including `ELITE.TOS`.
Intermediates, generated assets and the verification report remain shared by
this source tree. The report records the selected name and output paths.

Edit files in `src_atari/asm`. `boot.s` and `workspace.m68` are new sources for the current build. The original novella questions are enabled by default. Build with `noprotect=yes` to skip the question without editing assembly definitions or changing other protection checks.

```powershell
.\build_atari.bat
.\build_atari.bat noprotect=yes
```

`noprotect=no` restores the default behavior. The same options are accepted by `python src_atari/build.py`.

`commander=max` gives the default Jameson commander **1,000,000 Cr** and the **Deadly** rating when starting or resetting a game. His score starts at the Deadly threshold (`$A0000`). `commander=default` keeps the original **100 Cr**, **Harmless** rating and zero score, and is the Python build default. Saved commanders retain their saved balances, scores and ratings.

`laser=dualbeam` is the default player laser style: two filled beams from the bottom left and right converge on the jittering crosshair tip. `laser=singlebeam` selects one narrow filled beam from the bottom centre. Both styles use the existing palette: Pulse is red, Beam orange, Military white, and Mining the same magenta as the instrument bars. They keep the same cosmetic jitter, fixed-axis targeting, damage and timing. These style options do not affect AI beams or their distance-dependent random miss chance.

```powershell
.\build_atari.bat laser=dualbeam
.\build_atari.bat laser=singlebeam
```

`aifiresound=no` is the build default and disables AI laser firing sounds. `aifiresound=yes` enables them, subject to the game's existing Effects setting. This option controls AI laser shot sounds only; hit/impact sounds, player weapons, missile alerts and other effects keep their existing handling.

```powershell
.\build_atari.bat aifiresound=no
.\build_atari.bat aifiresound=yes
```

`scannerlogo=yes` (default) shows the ELITE caption below the scanner. Use `scannerlogo=no` to hide the caption on both cockpit buffers. The scanner, instruments and other game logos are unaffected. This is a build-time setting.

```powershell
.\build_atari.bat scannerlogo=no
```

The root `build_atari.bat` currently supplies `noprotect=yes commander=max laser=singlebeam aifiresound=no scannerlogo=yes`. Arguments passed on the command line override these defaults; the last occurrence of each option wins independently. Use `build_atari.bat commander=default` to build with the original starting balance.

The build uses the bundled `tools/vasmm68k_mot.exe` and `tools/vlink.exe` in the project root. It assembles all game modules from source, without using `src_orig` or old `.LTX` objects. It writes the game files to `output_atari/ELITE` and the floppy image to `output_atari/ELITE.ST`. Both assembler and linker run from `src_atari/build` with explicit output paths to prevent `a.out` from appearing in the root.

The floppy contains `AUTO/ELITE.PRG` for automatic startup when booting from drive A:. This variant of `boot.s` selects the current drive root before opening `LOADER.IMG`; all data and the manual `ELITE.TOS` launcher remain in the root. The directory distribution remains flat for manual startup from a hard-drive folder. The FAT12 verifier checks both the root files and the AUTO directory, including its dot entries and launcher bytes.

The launcher keeps its loader, game and workspace within the TOS process's free ST-RAM block, moving them above resident drivers in 32 KB steps. This preserves the renderer's screen alignment. The build embeds vlink relocation records in each launcher and checks them against an independent link at a higher address. Startup adjusts the expected program checksum only for the address changes. Copy all files from `output_atari/ELITE` together when updating a hard-drive installation; the launcher, loader and game image belong to the same build.

`src_atari/tools/convert_quelo.py` documents the one-time import of the original dialect. It now requires `--source-dir` pointing to a separately extracted copy of `resources/elite_atarist_source.zip`. **The normal build does not run it.** By default, it refuses to overwrite existing files. Its `--overwrite` option discards edits to converted files in `src_atari/asm` and is intended only for deliberately repeating the import.

The loading screen uses [the final Coriolis-and-planet artwork](../resources/loading_screen/elite_loading_screen_new_final.png), converted to `assets/TITLE.PC1` at 320 x 200 pixels with the original 16-colour palette. The PNG is preserved without resampling, colour changes or additional dithering.

The loader keeps the picture visible for at least one second, including time spent reading and relocating `ELITE.IMG`. It starts measuring after the palette reaches the display, using TOS's 200 Hz clock so PAL, NTSC and faster CPUs retain the same minimum. Slow loading adds no further hold.

The build automatically recalculates the new binary's checksum and assembles the checksum module a second time. There is no need to edit the historical `$5123` constant manually.

The link map is in `src_atari/build/elite.map`; verification results and output SHA-256 hashes are in `src_atari/build/verification.json`. See [ANALYSIS.md](ANALYSIS.md) for the memory layout, original architecture, and conversion details.


## Animation timing

The ship parade, animated ELITE lettering, launch, docking, death and both hyperspace animations use the same three-VBL frame limit as the main game (at most 16.67 updates/s at PAL 50 Hz). The wait counts time already spent drawing; a frame that has taken three or more VBLs receives no additional limiter delay. Both hyperspace types use a five-second PAL timer (250 VBLs), followed by the final circle passing through the view. The timer is independent of the Effects setting on both platforms.

## Flight controls

`A`, left `Shift` and right `Shift` fire the player laser on Atari ST, with either mouse or joystick selected. Holding multiple fire keys does not increase the firing rate, and releasing one continues firing while another remains held. The Shift keys provide additional bindings to try with two simultaneous steering keys on the original keyboard.

Alternate retains its original hyperspace shortcut and does not fire the laser.

## Jettison cargo

In flight, double-click an Inventory item and confirm with `Y` or the YES button to eject up to 1 t, or the entire remainder when less is held. `N`, NO or `Esc` cancels. Tonne, kilogram and gram commodities qualify, including Alien Items and Medical Supplies; mission cargo remains excluded. A full object bubble rejects the request without losing cargo. Ejected canisters retain their original commodity and exact mass in grams when scooped. Success and failure use existing sounds. Dumping in the station protection zone adds 15 legal-status points except under Anarchy. See [JETTISON.md](JETTISON.md) for restrictions and validation.

## Missile range

Player and NPC missiles disappear beyond 24,576 world units from the player,
regardless of scanner zoom. At exactly that distance they remain active.
Disappearing missiles cause no explosion or damage and do not remove their
target ship or other missiles pursuing it.

## ECM

ECM destroys every missile in the world for as long as the wave lasts, whether
the player triggered it or a ship defended itself against his missile. The wave
is timed rather than tied to the ECM sound, so it also runs with Effects
switched off, which the original game did not. It lasts 116 VBL ticks, 2.32 seconds at PAL 50 Hz,
the length of the original effect.

## Random encounters

Half of the pirate waves deep space would have thrown at the player become a
small battle between other ships or a peaceful trader convoy. Nothing is
announced; the player can leave the group alone or choose to get involved.
This 50% choice applies both to timed waves during normal flight and to pirate
events that interrupt torus (J). Each event makes the choice once; the original
timers and government-dependent torus attack probability are unchanged.

| Group | Weight | Needs a government of |
| --- | ---: | --- |
| 1 Thargoid, 1-2 pirates | 1 | any |
| 1 Thargoid, 1-2 traders | 1 | any |
| 1-2 pirates, 1-2 traders | 4 | any |
| 1-2 pirates, 1-2 Vipers | 3 | Multi-government or better |
| 1-2 pirates, 1 Viper | 3 | Feudal or better |
| 1-2 pirates, 1 bounty hunter | 2 | any |
| 1-2 pirates, 1 bounty hunter, 1 trader | 2 | any |
| 1-2 traders in formation | 2 | any |

Police only turn up where there is law to enforce, so anarchies see neither
Viper group and meet a Thargoid in a sixth of their encounters instead of a
ninth in Multi-government or better systems. The bounty hunter is a
Fer-de-Lance, an ordinary trader by faction, so it hunts the raiders and they
hunt it back without any new rule.

The pirates are rolled from Krait, Gecko, Moray Star Boat, Adder, Mamba, Asp
MkII and Sidewinder, and the traders from Cobra MkIII, Python, Anaconda and
Cobra MK1. Neither table holds the Thargoid, which a group names where it wants
one, and the pirates leave out the Boa and the Wolf: these are the small and
medium raiders. The original "Condition RED!" ambush is untouched and keeps its
own wider table, Thargoid included.

A group's leader uses a nominal radius of 16384 to 22527 units, in the half
of space the player is facing. A 2048-unit reserve below the scanner boundary
keeps all followers inside range despite formation offsets and rounded
trigonometry; members remain a thousand units apart. Mixed groups enter combat
through the existing faction rules. The
trader-only group starts with identical headings and keeps the slower ship's
maximum speed during peaceful flight, even with different ship models. A lone
trader uses its own maximum. Each member leaves the formation speed setting
when it enters combat or evades an attack, then uses its normal flight
behaviour without automatically reforming. At most four ships arrive, fewer
than the ambush already brings at a high combat rating.

Every mission spawn keeps the old path: the Constrictor, the Cougar and both
Thargoid missions are checked before the substitution is even rolled. Witch
space and station launches retain their separate spawn paths. Timed waves keep
their station-zone and pirate-count gates; torus keeps its original eligibility
checks. See [normal-flight and torus routing](../docs/2026-09-21-random-encounter-torus-routing.md).

## Faction AI targeting

Ships no longer attack the player and nothing else. Each combat ship picks the
**nearest hostile ship**, and the player is one ordinary candidate among them.

| Faction (`SHIP_TYPE`) | Ships | Attacks |
| --- | --- | --- |
| Trader | Cobra Mk III, Cobra Mk I, Python, Fer-de-Lance, Anaconda | pirates, Thargoids |
| Pirate | Krait, Boa, Gecko, Moray, Adder, Mamba, Asp, Sidewinder, Wolf | traders, shuttles, police, Thargoids |
| Shuttle | Shuttle, Transporter | pirates, Thargoids |
| Police | Viper | pirates, Thargoids |
| Alien | Thargoid, Thargon | everything except Thargoids and Thargons |

Hunting and being hunted are separate roles. A ship hunts only when its
`ATTACK_TYPE` is `ACT_ATTACK`, so the Python, the Shuttle and the Transporter
are targets but never attackers, exactly as their reaction to the player has
always been: shoot them and they run. The Cougar and the Constrictor stand
outside the system entirely, so nothing targets them and they still pursue only
the player.

The player is always a candidate for pirates and Thargoids, and becomes one for
a trader, shuttle or Viper once he has shot at it, which is the existing `ANGRY`
flag. `ANGRY` only adds him to the candidate set; it never locks the choice, so
a trader the player has hit may still break off for a closer pirate. The rule
has no other exceptions: an ambush spawned on the player, or a Viper launched
because of his police record, also takes the nearest target. Candidates are
limited to the player's scanner range, so fights only happen where he can see
them, and no ship chases another out of the world.

One ship re-targets per game frame, round robin, and candidates are ranked by
the largest axis difference rather than a true distance, so no square root or
division is needed. Nothing else in the flight loop got slower.

Random Viper patrols inspect the player's police record on first contact and
when it changes. They use the station's existing arrest probability: a clean
record never triggers pursuit; otherwise a random value from 0 to 255 must be
below `floor(record / 4) + government * 16`. A refused check is not repeated
while the record stays unchanged. A successful check adds the player to the
normal enemy candidates, so a closer pirate or alien still takes priority.
Already angry ships continue their pursuit. Station-launched Vipers keep their
existing arrest or alien-response behaviour and do not run patrol inspections.
See [patrol police-record checks](../docs/2026-09-20-patrol-police-record-checks.md).

A hunter flies the same attack run at a ship as it flies at the player: it
steers at whatever its target is, closes, peels off, runs off and turns back.
Nothing about the player's own situation reaches that fight any more: two ships
keep shooting at each other while he is cloaked, while the docking computer
flies him in, and after he has ejected. Pirates still break off near the space
station, because station space is nearly six times the scanner range, so that
rule is about where everyone is rather than about him.

Taking fire from another ship provokes the same reaction as taking fire from the
player, because both go through the same routine. A ship already on an attack
run or in the middle of a peel off presses on; anything else breaks off, into
`LOG_CRUISE` if it is a runner, into `LOG_AVOID` if it was already running off,
otherwise into a fresh attack run. Lose more than half your energy in one attack
run and the ship may launch an escape capsule and leg it, exactly as it does
under the player's lasers. A hull whose crew has already bailed out still does
nothing.

A ship fires its missile at whatever it is fighting, and the ship it is aimed
at answers with ECM if it carries one, exactly as it would against the player's
missile. Such a missile is silent: "Incoming missile" and the cockpit alert only
ever announce a missile aimed at the player, and a ship that happens to be
fighting him does not fire one at him because a third ship shot it. A missile
destroys the ship it reaches, which is what the player's missiles have always
done, so a well-armed pirate is dangerous to traders that cannot answer.

The energy bomb remains player equipment. Damage between two ships uses a fixed
fixed strength instead of the player's combat rating, which has no meaning in a
fight he is not part of. It is deliberately lighter than his own: a hit lands
somewhere in 2 to 12 and averages six, against the nine an average-rated
commander takes, so two ships take a while over each other and the fight is
worth flying into. Damage taken by the player, his shields and the
rating-dependent damage table are untouched.

A Thargon is a ship rather than a missile, so a Thargoid worn down by a Viper or
a pirate still lets its Thargons go, and they then hunt by the same faction
rules as anything else. Away from the player the release is smaller, two or
three instead of four to seven, so one Thargoid cannot claim the thirty object
slots on its own, and its chance no longer rides on the player's combat rating.
Under his own lasers a Thargoid behaves exactly as it always has. However a
Thargoid dies -- his laser, his missile, another ship's fire or a collision --
its Thargons go dormant, scatter and drift out of range, returning their
slots. See
[../docs/2026-09-17-thargon-dormancy-on-mother-death.md](../docs/2026-09-17-thargon-dormancy-on-mother-death.md).

An NPC kill awards the player no score, rating, bounty or police-record change,
but cargo canisters still drop, so waiting for two ships to fight can pay. It is also silent: the explosion sound
belongs to the ships he destroys himself, with a laser, a missile, by ramming or
with the energy bomb, so a distant fight does not announce itself. An
enemy beam is drawn from its gun to its actual target, with a small random
offset when the shot misses; beams aimed at the player are drawn as before.

## Verification

Tests and original-file verification can be run independently:

```powershell
python -m unittest discover -s src_atari/tests -v
python src_atari/tools/verify_original.py
```

The build checks all external symbols, the embedded checksum, A6 relocation to the variable area, RAM and local-variable bounds, control-key ASCII values, data buffer capacities, the TOS header, and a full readback of the FAT12 floppy image. Tests also cover sensitive Quelo conversion details, including reused labels, the tenth macro argument, and OR conditions, as well as launcher placement under TOS 1.04 and error-message termination.

Hatari 2.6.1 with TOS 1.04 DE also reached the title animation from a 512 KB floppy and the commander prompt from C: on a 1 MB ST with a 128 KB resident allocation. These checks do not emulate PP HDD Driver itself.

Hangar launch now plays a native PSG engine effect inspired by the Amiga launch sound: a rising tone with slight pitch modulation, noise, a short attack and a final fade to silence. It uses one ordinary effect channel for 234 VBL ticks (about 4.7 seconds at 50 Hz), without sample playback, additional interrupts or extra workspace. It follows Effects and is skipped when the launch animation is disabled.

Viewport clearing uses three `MOVEM.L` stores per row (11 + 11 + 10 longwords), saving and restoring A2-A4 once per call. It clears the same 256 x 112 viewport and keeps the original VBL wait. Diagonal lines cache their two colour pairs in registers and preserve the caller's D7 counter. The original pixel selection, patterned colours and frame synchronization are retained.

The viewport uses inclusive logical coordinates `x=-128..127`, `y=-56..55`, matching the full cleared screen area `x=32..287`, `y=8..119` (256 x 112 pixels). Clipped lines and filled polygons reach both edge columns. Planets and other solid circles use the same bounds; sun flares are added before final clipping, so they cannot overwrite the cockpit border.

The starfield uses a native adaptation of the BBC/C64 Elite depth and recycling model. Each star is always one pixel, with nearby particles moving faster than distant ones. Front, rear and side views have their original distinct replacement rules; steering follows this game's 512-pixel object projection. The old direction lookup files are no longer loaded or distributed. See [STARFIELD.md](STARFIELD.md) for the original source references, scaling and validation.

A separate sparse white sky sits behind every flight object and the existing dark grey starfield. Its fixed one-pixel stars remain consistent across all views and move only with rotation. **Game Options / Stars: ON/OFF** controls this white sky (default ON). OFF skips its rendering and rotation updates and restores the moving starfield to yellow. Switching back ON restarts the sky orientation and returns the moving starfield to dark grey. The preference is saved with the commander. Startup and default Jameson use ON; older commanders also load with ON. The 256-byte save format remains compatible between Atari and Amiga. A spatial tree skips unseen regions, and straight flight reuses cached screen positions; see [STARFIELD.md](STARFIELD.md#distant-white-sky) for implementation and validation details.

Player and AI lasers use instant-hit beams. Player Beam and Military lasers now have distinct continuous firing sounds with short attack and release ramps; Pulse and Mining retain their original firing effects. Player colours depend on the weapon: Pulse red, Beam orange, Military white, and Mining instrument-bar magenta. AI beam colours follow player rating: Harmless through Poor is red, Average through Competent orange, and Dangerous through Elite white; Constrictor beams are always white; Thargoid and Thargon (Tharglet) beams are always light blue. Player damage per hit is unchanged; successful AI hits multiply the original base damage by a random 2, 3 or 4 to approximate repeated projectile damage. Player beam jitter is cosmetic: targeting stays at the crosshair centre. AI beams originate at each model's `gun_node`, with centred bow muzzles for Sidewinder, Gecko, Adder and Moray; even correctly aimed shots can miss, with a linearly interpolated chance of 10% at 1,000 units or less, 20% at 3,000, 30% at 5,000 and 50% at 7,000, preserving the beam and optional firing sound without causing damage. See [LASERS.md](LASERS.md) for weapon timing, targeting and runtime validation.

Sprite and bitmap drawing uses fixed left/right rotation loops from `asm/sprite_rows.inc`, including clipped sprites. It never patches executable instructions, avoiding stale rotation opcodes in the instruction cache of 68020 and later CPUs. Each rotation still uses at most eight steps on the 68000. This change concerns sprite rendering; compatibility with other Atari display hardware and operating systems requires separate testing.

Use `src_atari/tools/run_hatari.py` to repeat the startup diagnostic. It requires a separately installed Windows [Hatari 2.6.1](https://www.hatari-emu.org/download.html) and your own TOS ROM. Supply their paths as arguments; the emulator is not copied into the repository:

```powershell
python src_atari/tools/run_hatari.py --hatari 'C:\Hatari\hatari.exe' --rom 'C:\path\tos104.img'
python src_atari/tools/run_hatari.py --hatari 'C:\Hatari\hatari.exe' --rom 'C:\path\tos104.img' --floppy
```

The script uses the game from the root `output_atari` directory and stores screenshots and diagnostics separately in `src_atari/build/hatari-test/harddrive` and `src_atari/build/hatari-test/floppy`. The floppy diagnostic uses the real TOS AUTO scan; only the hard-drive diagnostic uses desktop autorun. It runs without a window, write-protects the game disks, and does not save settings to the user profile. Assess the result using the screenshots and logs; the emulator's exit code alone does not confirm that the game works. The normal build does not run the emulator (`runtime_tested: false` in its report).

## Optional assembler and linker rebuild

The normal build uses the bundled executables and does not need this step. Rebuilding the assembler and linker themselves requires Visual Studio 2022 or Build Tools with the C++ tools and Windows SDK:

```powershell
.\src_atari\tools\setup-toolchain.ps1
```

The script verifies the SHA-256 hashes of the archives in `src_atari/vendor`, extracts them to `src_atari/build/toolchain`, builds the tools with MSVC and a statically linked C runtime (`/MT`), and copies the resulting executables to the root `tools` directory. If archives are missing, it downloads them from the official site. Versions and hashes are recorded in `src_atari/tools/toolchain.json`; the script rejects changed upstream content until it has been reviewed. Extracted sources and objects therefore remain among the ignored build files.

The upstream license terms are included beside the executables: [vasm](../tools/vasm-LICENSE.txt), [vlink](../tools/vlink-LICENSE.txt). The original archives remain in `src_atari/vendor`. See [tools/README.md](../tools/README.md) for the bundled binaries, and the [vasm](https://sun.hasenbraten.de/vasm/) and [vlink](https://sun.hasenbraten.de/vlink/) sites for official documentation.

## Docking computer

`auto_rotate` steers the Cobra by dividing each reduced axis distance by the
length of the target vector, and the `dot` macro divides the object auto-pilot's
dot products by the same kind of length. That length is zero whenever the target
sits on the axis being measured, and both auto-pilots reached such a division.
Launching places the space station at (0,0,-2500) with an identity orientation,
so the docking computer's first turning point is exactly axial: engaging the
computer without touching the controls reached the division every time, and an
approach that lines the ship up on the station axis reached it as well. The
object auto-pilot reaches it when an object arrives at its target point, which
the missile and attack logics in `logic.m68` can do because they aim at the
player at the origin.

The ST did not stop there. The game installs handlers for the bus and address
error vectors only (`traps` in `debug.m68`, patched in `init.m68`), so the zero
divide was left to TOS, which resumes execution and leaves the quotient register
alone. That register already held zero, which is the answer a target on the axis
should give, so the auto-pilots worked while relying on an ignored exception.
Every one of these dot products now treats a zero-length target vector as no
angle to correct, producing the same result without the exception. The same
code is fatal on hosts that abort on a zero divide.

## Cargo inspections

Fuel Scoop collection no longer adds an immediate legal penalty. Each entry into the station protection zone (S) checks all cargo: Firearms add 2 points per complete tonne; Slaves and Narcotics add 4. Inspections apply under all governments, saturate at 255, and repeat only after travelling at least 512 world units beyond the S boundary and re-entering the zone. Launching and switching flight screens do not trigger another inspection. Purchase penalties and the existing once-per-system police response remain unchanged.


## Automated checks

Run `python -B -m unittest discover -s src_atari/tests -v` from the project root.
The retained tests cover binary formats, asset conversion and build tooling;
they do not emulate the game CPU. Gameplay and audio checks require Hatari
or original hardware. Enhanced builds and PNG tests require Pillow.
