# Independent native Amiga version

This source tree started as a copy of the corrected Atari sources before the combined Amiga build was introduced. It retains the game logic and starfield fixes, with Amiga-specific rendering, sound, input, startup and file handling developed here. It builds independently of `src_atari`; neither target uses a platform switch or imports the other target's build script.

## Editable graphics

The build option `altgfx=yes|no` defaults to `no` (`gfx/`). Run
`build_amiga.bat altgfx=yes` from the project root to use this tree's `gfx_alt/`
instead. The selected directory must contain all eight PNGs and `layout.json`.
Both choices generate the same asset and distribution paths; use `altgfx=no`
to rebuild with the standard sources.

Edit the eight PNGs in this tree's `gfx/` folder. The build requires Pillow
(`python -m pip install Pillow`) and generates this tree's `assets/` before
assembly. Keep canvas sizes and use each image's exact RGB palette. `cockpit.png`
uses the cockpit palette; all other PNGs use the UI base palette, including in
`gfx_alt/`. UI indices 6, 8 and 14 are `#FF0000`, `#6DB600` and `#6D4900`;
cockpit indices 6 and 14 are `#DB0000` and `#FF0000`. Both use cyan `#00FFFF`
for transparent index 0 and black `#000000` for opaque index 13. RGB, RGBA and
reordered indexed PNGs are supported, and game pixel indices and hardware
palettes stay unchanged. See the [PNG editing guide](../docs/2026-09-19-editable-png-graphics.md)
for the complete palette, alpha handling, sheet layouts and verification commands.

## RCS sound

RCS FX also enables a synthesized motor hum while Space (accelerate)
or slash (decelerate) is held. It stops at the next VBL after both keys are
released, with a short volume ramp (about 3 ms at full volume) to reduce clicks.
The ramp completes before DMA is stopped, including channel replacement and
cinematic or music transitions; it does not leave a tail for later frames.
Actual speed changes, including mouse throttle and automatic changes,
do not trigger it. Acceleration is silent at maximum speed and deceleration
is silent at zero; the opposite direction remains audible. Current speed
sets the sample period from 428 to 214 without restarting its 1024-byte loop.
At startup, DMA first fetches the new loop at zero volume, then volume rises
in single-level steps to 48/64 over about 3 ms, matching the continuous
laser's level and avoiding abrupt gain changes.
It has priority below RCS and every ordinary effect.
RCS FX OFF and Effects OFF mute it. Docking, either hyperspace jump and death
discard its gameplay request immediately, including when a key remains held.

`RCS FX: ON / OFF` appears below Effects in Game Options. It defaults to ON
and is stored in the Commander's existing user preference byte (bit 7 means
OFF). Effects OFF also mutes RCS.

A quiet filtered-noise sample loops while roll or pitch changes, including
automatic damping to zero. Steady rotation is silent. Paula volume rises to
8/64 and fades briefly when steering settles. RCS takes only a free channel;
ordinary effects use free channels first and replace RCS before another
effect. The continuous beam retains channel 3. Noise effects can coexist
because Paula voices play independent samples. Docking, normal and galactic
hyperspace, and death entry points stop RCS before the first animation frame.

`tools/rcs_audio.py` generates the 4096-byte loop at build time without using
the game's random generator. The loop is placed in Chip RAM with the other
audio.

## Jettison cargo

In flight, double-click an Inventory item and confirm with `Y` or the YES button to eject up to 1 t, or the entire remainder when less is held. `N`, NO or `Esc` cancels. Tonne, kilogram and gram commodities qualify, including Alien Items and Medical Supplies; mission cargo remains excluded. A full object bubble rejects the request without losing cargo. Ejected canisters retain their original commodity and exact mass in grams when scooped. Success and failure use existing sounds. Dumping in the station protection zone adds 15 legal-status points except under Anarchy. See [JETTISON.md](JETTISON.md) for restrictions and validation.

## Build and run

`build_amiga.bat outputname=ELITE_ALT` creates `output_amiga/ELITE_ALT/` and
`output_amiga/ELITE_ALT.ADF`. The default is `outputname=ELITE`; this option can be
combined with `altgfx=yes` or any other enhanced build option. Pass a filename,
without a path or disk suffix; quote the whole argument if it contains spaces.
Files inside the distribution keep their existing names, including `ELITE`,
`ELITE.info` and the disk startup sequence. Intermediates, generated assets and
the verification report remain shared by this source tree. The report records
the selected name and output paths. Paths below show the default output name.

`assets/ELITE.info` is the standard four-colour Workbench tool icon (96 x 24 pixels, normal and selected images). The build copies this asset unchanged beside `ELITE` in both the ADF and `output_amiga/ELITE`. Double-click it to launch the game from Workbench 1.3 or later; keep all game files together. The native executable receives and replies to the Workbench startup message, selects the executable's directory before loading assets, and restores the caller's directory on exit. Ctrl+F10 returns to Workbench. Shell and boot-disk launches remain supported.

Only one instance may run at a time. Repeated icon clicks or another Shell launch return immediately while the existing game continues. Startup atomically claims the public Exec marker `Elite.Native.Amiga` before opening files or taking over hardware; cleanup releases it after restoring the display, input and audio, including startup-failure paths. This prevents two instances from overwriting each other's Workbench display state. The marker uses Kickstart 1.3-compatible port calls and does not allocate a signal.

The icon follows Workbench's screen palette: the default 1.3 colours are blue/white/black/orange; 3.0 uses grey/black/white/blue-grey. `python src_amiga/tools/make_icon.py` rebuilds the checked-in icon from its hand-pixelled winged badge; ordinary builds consume the asset directly.

The loading picture stays visible for at least one second, including asset-loading time. Startup uses the display VBL counter and Exec's PAL/NTSC refresh frequency, with a two-frame allowance for publishing the first Copper frame. Only the remaining time is waited; a missing or unreadable optional picture adds no delay. This applies to Shell, boot-disk and Workbench launches.

Run from the project root:

```powershell
.\build_amiga.bat
.\build_amiga.bat noprotect=yes
.\build_amiga.bat -Python "C:\path\python.exe"
```

`noprotect=yes` skips the novella question at startup. The Python build default, `noprotect=no`, keeps it enabled. Other protection checks are unaffected. `python src_amiga/build.py` accepts the same options.

`commander=max` gives the default Jameson commander **1,000,000 Cr** and the **Deadly** rating when starting or resetting a game. His score starts at the Deadly threshold (`$A0000`). `commander=default` keeps the original **100 Cr**, **Harmless** rating and zero score, and is the Python build default. Saved commanders retain their saved balances, scores and ratings.

`laser=dualbeam` is the default player laser style: two filled beams from the bottom left and right converge on the jittering crosshair tip. `laser=singlebeam` selects one narrow filled beam from the bottom centre. Both styles use the existing palette: Pulse is red, Beam orange, Military white, and Mining the same magenta as the instrument bars. They keep the same cosmetic jitter, fixed-axis targeting, damage and timing. These style options do not affect AI beams or their distance-dependent random miss chance.

```powershell
.\build_amiga.bat laser=dualbeam
.\build_amiga.bat laser=singlebeam
```

`aifiresound=no` is the build default and disables AI laser firing sounds. `aifiresound=yes` enables them, subject to the game's existing Effects setting. This option controls AI laser shot sounds only; hit/impact sounds, player weapons, missile alerts and other effects keep their existing handling.

```powershell
.\build_amiga.bat aifiresound=no
.\build_amiga.bat aifiresound=yes
```

`scannerlogo=yes` (default) shows the ELITE caption below the scanner. Use `scannerlogo=no` to hide the caption on both cockpit buffers. The scanner, instruments and other game logos are unaffected. This is a build-time setting.

```powershell
.\build_amiga.bat scannerlogo=no
```

The root `build_amiga.bat` currently supplies `noprotect=yes commander=max laser=singlebeam aifiresound=no scannerlogo=yes`. Arguments passed on the command line override these defaults; the last occurrence of each option wins independently. Use `build_amiga.bat commander=default` to build with the original starting balance.

Python 3.10+ and Windows x64 are required. The build uses the root `tools/vasmm68k_mot.exe` (vasm 2.0f, Motorola syntax, MC68000) and `tools/vlink.exe` (vlink 0.18a). No additional Python packages are needed. `-Vasm` and `-Vlink` select alternative tool paths. `python src_amiga/build.py` is also supported. Unknown arguments, including `platform=amiga`, are rejected.

The build reads `resources/amiga/Elite 2.0.adf` without modifying it. Its checksum is validated before extracting the original boot block, 19 effect samples, and the four-channel Blue Danube score with seven music instruments. It produces:

| Path from the project root | Contents |
| --- | --- |
| `output_amiga/ELITE/` | Native Amiga Hunk executable `ELITE`, font, objects and game assets |
| `output_amiga/ELITE.ADF` | Bootable 880 KB OFS disk with all game files |
| `src_amiga/build/` | Objects, generated sound tables, logs, link map and verification report |

Target: **PAL OCS, MC68000, Kickstart 1.3, 512 KB Chip RAM plus 512 KB expansion RAM**. Boot the ADF in DF0:, or copy every file from `output_amiga/ELITE` into one writable directory, change to that directory in AmigaDOS and run `ELITE`. The original novella questions are enabled unless built with `noprotect=yes`. F1 launches, F2-F4 select the other flight views, F5/F6 show the charts, F9 shows status, F10 shows inventory, and minus opens the disk menu while docked. **Ctrl+F10 exits to AmigaDOS.**

When launched from a floppy, commander loading, saving and the catalog use the root of that physical drive (DF0: through DF3:). After the title animation starts, the game disk can be replaced with a commander disk in the same drive, including when answering Y to "Load new commander?". HDD launches keep commander files in the current directory. File errors return to the game instead of opening an AmigaDOS requester behind its custom display; the original requester setting is restored on exit.

## Native implementation

The raster routines write directly to the two screens used by Amiga display DMA. The original Atari word-interleaved framebuffer and the former frame conversion wrapper are absent.

Startup displays [the final Coriolis-and-planet artwork](../resources/loading_screen/elite_loading_screen_new_final.png), converted to `assets/TITLE.PC1` at 320 x 200 pixels with the original 16-colour palette, while loading the game assets. The PNG is preserved without resampling, colour changes or additional dithering. It decodes directly into the primary Amiga screen with a native OCS palette. The secondary screen temporarily holds the compressed picture, then becomes the bitmap loader's disk buffer. Display refresh runs during loading; game clock, cursor and sound updates begin only after initialization. The game continues automatically when loading finishes, without requiring a key press. A missing or unreadable title file is skipped.

Screen swapping waits for the VBL handler to accept the rendered screen before reusing the previous display buffer. It preserves that VBL acknowledgement, so the next viewport clear does not wait for an extra refresh. The existing three-VBL gameplay frame limiter remains in effect.

The ship parade, animated ELITE lettering, launch, docking, death and both hyperspace animations use the same three-VBL frame limit as the main game (at most 16.67 updates/s at PAL 50 Hz). The wait counts time already spent drawing; a frame that has taken three or more VBLs receives no additional limiter delay. Both hyperspace types use a five-second PAL timer (250 VBLs), followed by the final circle passing through the view. The timer is independent of the Effects setting on both platforms.

- **Display:** 320 x 200, four planes, 16 colours. Each row contains four consecutive 40-byte plane rows. Pixel word addresses are `screen + y*160 + (x>>4)*2`, with plane offsets 0, 40, 80 and 120. Copper uses a bitplane modulo of 120. Two 32 KB Chip RAM buffers provide double buffering; a VERTB handler publishes the completed screen.
- **Drawing:** lines, polygons, text, sprites and their saved backgrounds, radar, scrolling text, chart circles and planet shading use the native plane addresses. DEGAS RLE artwork decodes directly into this row-interleaved layout. The asset palette is imported once into native 12-bit OCS colours. Game artwork and compact sprite assets remain derived from the Atari release.
- **Input:** an `input.device` handler supplies native Amiga raw keys and mouse movement. The keyboard tables and steering bindings use Amiga key codes directly. The vertical blank handler reads the joystick port and fire button. There is no ST scancode translation or IKBD packet emulation.
- **Sound:** `sounds.m68` drives Paula DMA using the 19 original Amiga effect samples. The hangar launch animation triggers the original Amiga launch effect; it follows the Effects setting and is skipped when the launch animation is disabled. Music uses the original four-channel Amiga Blue Danube score and seven sampled instruments, with a relocatable adaptation of Wally Beben's replay in `music.m68`. The title, docking computer and Elite congratulations screen use this arrangement. Audio samples and Copper data are allocated in Chip RAM. Timing and envelopes for the original effects remain simplified. Two new synthesized PCM loops provide continuous player Beam and Military sounds, adding 8 KB of Chip RAM. See [MUSIC.md](MUSIC.md) for extraction, playback and validation details.
- **Files:** `fileio.m68` calls AmigaDOS Open, Read, Write and Close with full 32-bit BPTR handles. Directory enumeration uses Lock, Examine and ExNext and returns commander filenames directly. Startup resolves the current filesystem with DeviceProc so commander operations follow a replacement floppy without retaining a path to the ejected volume. Asset paths remain relative. It does not simulate GEMDOS traps, handle numbers or a DTA. The existing 256-byte commander format is retained.
- **Lifecycle:** Exec remains running for input and disk I/O. Startup saves the OS View and installs the handlers; exit removes them, closes open files, releases the directory lock and restores the OS display and Copper list. Relocatable Hunk sections replace the fixed Atari memory map. Each BSS Hunk stays below the Kickstart 1.x clearing limit.

Viewport clearing writes each 32-byte plane span with one MC68000 `MOVEM.L`. Vertical lines cache their masked plane colours; horizontal spans and block fills cache all four plane words. Diagonal lines cache both colour pairs and preserve the caller's D7 counter. These CPU optimizations retain patterned colours, inclusive line endpoints, viewport borders and the existing frame limiter.

Sprite and bitmap drawing uses fixed left/right rotation loops from `asm/sprite_rows.inc`, including clipped sprites. It never patches executable instructions, avoiding stale rotation opcodes in the instruction cache of 68020 and later CPUs. Each rotation still uses at most eight steps on the 68000. This addresses the CPU-side corruption of missile indicators and options icons; it does not establish full A1200/AGA hardware compatibility.

The viewport uses inclusive logical coordinates `x=-128..127`, `y=-56..55`, matching the full cleared screen area `x=32..287`, `y=8..119` (256 x 112 pixels). Clipped lines and filled polygons reach both edge columns. Planets and other solid circles use the same bounds; sun flares are added before final clipping, so they cannot overwrite the cockpit border.

The starfield uses a native adaptation of the BBC/C64 Elite depth and recycling model. Each star is always one pixel, with nearby particles moving faster than distant ones. Front, rear and side views have their original distinct replacement rules; steering follows this game's 512-pixel object projection. The old direction lookup files are no longer loaded or distributed. See [STARFIELD.md](STARFIELD.md) for the original source references, scaling and validation.

A separate sparse white sky sits behind every flight object and the existing dark grey starfield. Its fixed one-pixel stars remain consistent across all views and move only with rotation. **Game Options / Stars: ON/OFF** controls this white sky (default ON). OFF skips its rendering and rotation updates and restores the moving starfield to yellow. Switching back ON restarts the sky orientation and returns the moving starfield to dark grey. The preference is saved with the commander. Startup and default Jameson use ON; older commanders also load with ON. The 256-byte save format remains compatible between Atari and Amiga. A spatial tree skips unseen regions, and straight flight reuses cached screen positions; see [STARFIELD.md](STARFIELD.md#distant-white-sky) for implementation and validation details.

Player and AI lasers use instant-hit beams. Player Beam and Military lasers now have distinct continuous firing sounds with short attack and release ramps; Pulse and Mining retain their original firing effects. Player colours depend on the weapon: Pulse red, Beam orange, Military white, and Mining instrument-bar magenta. AI beam colours follow player rating: Harmless through Poor is red, Average through Competent orange, and Dangerous through Elite white; Constrictor beams are always white; Thargoid and Thargon (Tharglet) beams are always light blue. Player damage per hit is unchanged; successful AI hits multiply the original base damage by a random 2, 3 or 4 to approximate repeated projectile damage. Player beam jitter is cosmetic: targeting stays at the crosshair centre. AI beams originate at each model's `gun_node`, with centred bow muzzles for Sidewinder, Gecko, Adder and Moray; even correctly aimed shots can miss, with a linearly interpolated chance of 10% at 1,000 units or less, 20% at 3,000, 30% at 5,000 and 50% at 7,000, preserving the beam and optional firing sound without causing damage. See [LASERS.md](LASERS.md) for weapon timing, targeting and runtime validation.

## Source layout

| Path within this directory | Purpose |
| --- | --- |
| `asm/system.m68` | Amiga startup, shutdown, Copper, frame presentation and input |
| `asm/fileio.m68` | Native AmigaDOS file and directory operations |
| `asm/raster.inc` | Native bitplane drawing and background save/restore primitives |
| `asm/graphics.m68`, `asm/bios.m68`, `asm/sprites.m68` | Raster geometry, text, sprites and cursor |
| `asm/sounds.m68`, `asm/music.m68`, `asm/workspace.m68` | Paula effects, original Amiga music replay and relocatable storage |
| `asm/` | Independent game modules, definitions, font and ship data |
| `assets/` | Game artwork and lookup tables |
| `build.py`, `build.ps1`, `build.bat` | Build owned by this target |
| `tools/` | Original sound extraction, Hunk validation and OFS disk creation |
| `tests/` | Asset, Hunk and OFS regression tests |

The root `build_amiga.bat` forwards arguments here. Atari development and optional assembler/linker rebuilding remain under `src_atari`; normal Amiga builds only use the bundled executables in the root `tools` directory.

## Missile range

Player and NPC missiles disappear beyond 24,576 world units from the player,
regardless of scanner zoom. At exactly that distance they remain active.
Disappearing missiles cause no explosion or damage and do not remove their
target ship or other missiles pursuing it.

## ECM

ECM destroys every missile in the world for as long as the wave lasts, whether
the player triggered it or a ship defended itself against his missile. The wave
is timed rather than tied to the ECM sound, so it also runs with Effects
switched off and while the music is playing. It lasts 116 VBL ticks, 2.32 seconds at PAL 50 Hz,
the length of the original effect.

## Random encounters

Half of the pirate waves deep space would have thrown at the player become a
small group that is **already fighting itself**. Nothing is announced, nothing
is aimed at him, and he decides whether to join in, pick off the survivor or
wait for the cargo.

| Group | Weight | Needs a government of |
| --- | ---: | --- |
| 1 Thargoid, 1-2 pirates | 1 | any |
| 1 Thargoid, 1-2 traders | 1 | any |
| 1-2 pirates, 1-2 traders | 4 | any |
| 1-2 pirates, 1-2 Vipers | 3 | Multi-government or better |
| 1-2 pirates, 1 Viper | 3 | Feudal or better |
| 1-2 pirates, 1 bounty hunter | 2 | any |
| 1-2 pirates, 1 bounty hunter, 1 trader | 2 | any |

Police only turn up where there is law to enforce, so anarchies see neither
Viper group and meet a Thargoid in a fifth of their encounters instead of an
eighth. The bounty hunter is a Fer-de-Lance, an ordinary trader by faction, so
it hunts the raiders and they hunt it back without any new rule.

The pirates are rolled from Krait, Gecko, Moray Star Boat, Adder, Mamba, Asp
MkII and Sidewinder, and the traders from Cobra MkIII, Python, Anaconda and
Cobra MK1. Neither table holds the Thargoid, which a group names where it wants
one, and the pirates leave out the Boa and the Wolf: these are the small and
medium raiders. The original "Condition RED!" ambush is untouched and keeps its
own wider table, Thargoid included.

A group appears at the ambush's range, 16384 to 24576 units away, but always in
the half of space the player is facing, with its members a thousand units
apart. They are created cruising rather than attacking, and the faction rules
turn them on each other within a second. At most four ships arrive, fewer than
the ambush already brings at a high combat rating.

Every mission spawn keeps the old path: the Constrictor, the Cougar and both
Thargoid missions are checked before the substitution is even rolled, and
encounters never happen in witch space or inside station space.

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

## Validation

The build checks assembly/link diagnostics, relocations, required Chip RAM allocations, BSS sizes, module variable capacities, asset buffer capacities, the two-screen layout, original effect/music assets and sample loop bounds, and OFS disk contents read back byte for byte. Run the automated tests after building:

```powershell
python -B -m unittest discover -s src_amiga/tests -v
```

Runtime checks use an isolated WinUAE 6.0.3 instance with Kickstart 1.3, PAL OCS, a real-speed MC68000, 512 KB Chip RAM and 512 KB slow RAM. Evidence and the exact executable hash are recorded locally in `build/qa/runtime-verification.json`; screenshots are in the same generated directory. `build/verification.json` reports structural checks only and does not claim emulator coverage automatically.

The new native renderer has been exercised through the novella screen, title animation, commander status, launch, all four flight views, cockpit/radar, both charts and planet data. Native keyboard pitch controls and firing were exercised, and Paula sample addresses, lengths, periods and volumes were inspected. An existing commander loaded successfully; a new commander was saved, read back from the ADF as a valid 256-byte OFS file, listed in the catalog and reloaded. Ctrl+F10 restored the AmigaDOS screen and keyboard, with the game no longer present in the CLI task. Further runtime results are listed in the local verification record.

The audio shutdown fix was separately checked with WinUAE PCM recording at 48 kHz, stereo, 16-bit. Keyclick, laser, error and alert effects returned every channel to zero volume with audio DMA disabled; the following 14.69 seconds of recorded output contained only zero samples. Music fade and exit also produced a silent recorded tail. Evidence and the tested executable hash are in `build/audio-qa/audio-verification.json`. Playback mutes a channel and allows its sample clock to latch the change before disabling DMA. The delay observes the vertical byte of VHPOSR; comparing the complete register would count horizontal positions and end the wait too soon. Music rests remain muted during a fade.

Real hardware, extended gameplay and audible quality of the new music replay remain unvalidated. Mouse/joystick bindings need a physical-device play test.

Original game and asset credits and bundled tool licences are documented in the [main README](../README.md#legal-information-and-credits).

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

On the Amiga the zero divide is fatal: the CPU exception becomes a dead-end
alert, `Guru Meditation #00000005`, and the game stops. Every one of these dot
products now treats a zero-length target vector as no angle to correct.

## Cargo inspections

Fuel Scoop collection no longer adds an immediate legal penalty. Each entry into the station protection zone (S) checks all cargo: Firearms add 2 points per complete tonne; Slaves and Narcotics add 4. Inspections apply under all governments, saturate at 255, and repeat only after travelling at least 512 world units beyond the S boundary and re-entering the zone. Launching and switching flight screens do not trigger another inspection. Purchase penalties and the existing once-per-system police response remain unchanged.


## Automated checks

Run `python -B -m unittest discover -s src_amiga/tests -v` from the project root.
The retained tests cover binary formats, asset conversion and build tooling;
they do not emulate the game CPU. Gameplay and audio checks require WinUAE
or original hardware. Enhanced builds and PNG tests require Pillow.
