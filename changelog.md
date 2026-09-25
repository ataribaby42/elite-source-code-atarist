# Changelog

Modified Atari ST/Amiga Elite from Atari ST source code

Release build configuration: `noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no`

## xx.xx.2029 V1.xx

- Amiga: added DblPAL 640 x 512 mode.

## xx.xx.2029 V1.81

- Hyperspace countdown now pulses red in sync with the tunnel text and ship engines.
- Improved inhabitant colour mapping and added random planet rotation on station launch with Planets ON.
- Refresh cockpit instruments on both screen buffers after a system reset, fixing the stale speed gauge after relaunching from a station without touching the throttle.
- Moved Planets above Reset Game / Exit Program. Restricted continents to valid planet colours, mapped yellow and UI brown to steady red, and matched rendered Planet Data colours to flight colours while preserving the original bitmap and inhabitant palette when Planets is OFF.
- Empty Inventory now opens the Cargo Hold Inventory screen with a centred message, both docked and in flight, instead of a cockpit notification or blocking dialog on Atari ST and Amiga.
- Added the saved Planets ON/OFF option. ON also replaces the Planet Data bitmap with the selected planet rendered at zero rotation; OFF retains the original plain globe and bitmap. New games and older commanders default to OFF; newly saved commanders retain their selected setting.
- Added seeded surface details around the entire planet on Atari and Amiga: solid irregular blue/light blue seas on green/light green worlds, green/light green continents on blue/light blue worlds, and dark grey craters on light grey worlds. Each planet's seed selects one detail shade; other planet colours get differently coloured continents. Details appear from a 24-pixel logical diameter. Hyperspace arrivals choose a new longitude while preserving the map; crater rays have varied lengths and directions.

## xx.xx.2029 V1.80
	
- Stopped exporting the unused Cobra from panels.png on Atari ST and Amiga, preserving the PNG artwork and bitmap IDs while saving 3,268 disk bytes and 4,084 bytes of bitmap RAM (8,164 in HIRES, 16,324 in HIRES-LACED).
- Replaced disk-based ship atlases with native model rendering on Atari ST and Amiga: generate all Shipyards tiles at startup and only the current hull's Status and Planet Data views on new game, load or purchase; keep fixed image sizes across display modes and isolated memory buffers. Original PNGs remain archived in resources/gfx_assets; obsolete PNG generation files were removed.
- Fixed polygon and line clipping overflows causing screen corruption and white flashing, protected vertex buffers, and limited flight message width; verified on Atari and Amiga, including WIDE, HIRES, HIRES-LACED and shadowcopy=changes.
- Faster Amiga rendering where Chip RAM is the bottleneck. The flight view sends Chip RAM only what changed, and drawing that goes straight to the screen touches each screen word once.
- New build option shadowcopy=changes (default), counter (frame-time line also shows pieces sent), all (copy everything every frame, for comparison).
- Loading fix. On a 68040 (ACA1240) in pal-hireslace the game could freeze on the loading picture: BITMAPS.IMG read into the second screen sometimes arrived corrupted and the loader looped forever. Files now load through workspace buffers, and a failed or short read exits instead of hanging.
- New Amiga screen ELITE.WIDE.DBLPAL-HIRES (display=dblpal-hires): 640 x 512 like PAL-HIRESLACE, without interlace flicker and slightly faster. Needs AGA and a 27 kHz monitor.

## 23.09.2029 V1.71

- Better cockpit panel bitmap for wide variants.
- Amiga builds with `frame=no` now compile `gfx/cockpit_noframe.png` for `altgfx=no` or `gfx_alt/cockpit_noframe.png` for `altgfx=yes` into `COCKPIT.PC1`, using the cockpit palette in all WIDE, HIRES and HIRES LACED modes. Builds with `frame=yes` use `cockpit.png` from the selected graphics directory.
- Added NES-inspired Energy Bomb electrical arcs on Atari ST and Amiga. Two light-blue zigzags change every rendered flight frame for the sound effect's duration, scale to framed, WIDE, HIRES and interlaced viewports, and leave no trails in either screen buffer.
- Fixed Energy Bomb activation audio on Atari ST and Amiga: successful blasts now play one dedicated effect instead of individual ship explosion sounds. Atari ST uses its original bomb effect; Amiga uses a new sample based on it. Failed activations retain the error beep and do not consume the bomb.

## 22.09.2029 V1.70

- Wide flight view, with six screens to choose from: PAL or NTSC, each in lores, hires and hires interlaced.
- Faster flight view and the view reaching the top of the screen.
- Changed the AI laser damage multiplier from 1–3 to an equally weighted 2 or 3 for both player and AI targets on Atari and Amiga; updated documentation.

## 21.09.2029 V1.68

- Reduced the AI laser damage multiplier from 2–4 to 1–3 for both player and AI targets on Atari and Amiga; updated documentation.

## 21.09.2029 V1.67

- Fixed encounter ships spawning beyond scanner range by reducing the leader’s maximum spawn radius on Atari and Amiga.

## 21.09.2029 V1.66

- Fixed random encounters to replace 50% of pirate spawns during both normal flight and torus travel on Atari and Amiga, preserving mission spawns.

## 20.09.2029 V1.65

- Fixed intermittent energy-bank flickering during Game Over on Atari ST and Amiga caused by repeatedly restoring stale radar backgrounds.
- Added trader convoy encounters (1–2 ships, weight 2) on Atari ST and Amiga, maintaining formation and a shared cruising speed until combat.
- Fixed government filtering in random encounter selection.

## 20.09.2026 V1.64

- Fixed Amiga memory corruption during commander loading by increasing the stack to 4 KB, preventing missing stars, false drive malfunctions, and unexpected scanner contacts after launch.
- Added legal-status checks for random Viper patrols on Atari ST and Amiga, using the existing police-response probability and reacting to record changes during flight. Preserved nearest-enemy targeting, AI-vs-AI combat, and station-launched Viper behaviour.
- Cached AI laser colours on station launch and after normal or galactic hyperspace jumps, keeping them unchanged during flight on Atari ST and Amiga.
- Set cargo canisters dropped by destroyed AI ships to a random speed of 3–6, capped at their initial speed, on Atari ST and Amiga.
- Adjusted salvaged cargo quantities to 1 t, 1–10 kg, or 1–10 g per container on Atari ST and Amiga. Player-jettisoned cargo retains its exact original quantity.
- Fixed the planet colour at the launch tunnel exit to match its in-flight colour on Atari ST and Amiga.
- Reversed default mouse pitch controls on Atari ST and Amiga. The “Reverse dive/climb” option restores the previous direction.
- Added dominant planet colours in flight for Atari ST and Amiga using a saved 2,048-byte table, without recalculation during builds.
- Mapped yellow to orange (#3) and UI brown (#14) to steady red (#6).
- Excluded transparent and pulsing flight colours; black and dark grey fall back to light grey.

## 19.09.2026 V1.63

- Fixed Amiga UI cursor flickering and disappearing near the top of the screen by optimizing cursor drawing and background restoration.
- Fixed Atari ST cursor flickering at the top of UI screens by correcting negative Y coordinate checks and clock redraw ordering.
- Amiga: Import the asset palette over the full colour range.

## 19.09.2026 V1.62

- Added outputname=NAME for Atari and Amiga builds, naming the output folder and .ST/.ADF image. Defaults to ELITE.
- Added filename validation and updated build documentation.
- Verified custom and default names produce byte-identical game files.
- Fixed permanent mass-lock caused by distant abandoned ships on Atari and Amiga.
- Added missile cleanup beyond 24,576 units from the player.
- Enabled RGB-based PNG conversion with cyan transparency and unrestricted palette ordering.
- Migrated source PNGs while preserving edits and original binary output for default artwork.
- Documented PNG editing, palette mapping and Pillow installation.

## 18.09.2026 V1.61

- Atari ST & Amiga: Thargons now go dormant however their Thargoid mother dies, not only under the player's laser (EXPLODE_OBJECT read THIS_OBJ instead of A4)

## 17.09.2026 V1.60

- Atari ST & Amiga: Player is not center of universe anymore. AI-vs-AI ship combat is introduced. Pirates attack traders. Traders fight back. Police attack pirates. Everyone attack Thargoids
  - Atari ST & Amiga: AI ships now fly their attack run at the ship they are fighting instead of always at the player
  - Atari ST & Amiga: Ships hit by another ship break off, and below half energy run or launch an escape capsule, as they already did under player fire
  - Atari ST & Amiga: Ships fire missiles at each other; the cockpit alert and "Incoming missile" stay reserved for missiles aimed at the player
  - Atari ST & Amiga: Thargoids release 2-3 Thargons in ship-to-ship fights, at odds independent of the player's combat rating
  - Atari ST & Amiga: Player's cloaking device and locked controls (docking computer, escape capsule) no longer stop ships firing at each other
  - Atari ST & Amiga: Fix Cougar and Constrictor breaking off instead of attacking, which left missions 3 and 4 unwinnable
  - Atari ST & Amiga: Fix Constrictor mission completing only on a laser kill, not on a missile or ramming kill
  - Atari ST & Amiga: Fix "Target lost" being reported after a successful player missile kill
  - Atari ST & Amiga: Deep space now also produces small groups that are already fighting each other - pirates against traders, vipers hunting pirates, sometimes a Thargoid among them. They replace half the ordinary pirate ambushes, are placed ahead of the player at ambush range, and are not aimed at him - no Condition RED, he has flown into somebody else's fight.
  - Atari ST & Amiga: Mission spawns keep the old path - the Thargoid waves, the Cougar and the Constrictor are never replaced by an encounter
  - Atari ST & Amiga: Explosion sound is heard again only for ships the player destroys himself, by laser, missile, ramming or energy bomb; ship-to-ship kills are silent. ECM stays audible, as it was in 1988
  - Atari ST & Amiga: Fix police vipers launched from the space station peeling off and flying out of scanner range instead of attacking the player. The cockpit attack indicator and the flashing scanner blips now start when the vipers launch rather than when they turn to attack
- Atari ST & Amiga: Lower AI to AI laser damage so ship-to-ship fights last long enough to be worth diverting to - a hit now lands in 2-12 and averages 6 instead of 2-20 averaging 10. Damage to and from the player is unchanged
- Amiga: Fix ECM doing nothing at all - ECM_ON was never set, so no missile was ever destroyed and the cockpit indicator never lit
- Atari ST: Fix ECM not working with Effects switched off
- Atari ST: Fix title screen rotating ship being drawn over the ship name and "Load new commander ?" instead of behind them
- Amiga: Fix title screen rotating ship being drawn over the ship name and "Load new commander ?" instead of behind them

## 16.09.2026 V1.56

- Atari ST & Amiga: Fix zero divide in docking computer and object auto-pilot (Amiga Guru #00000005)

## 16.09.2026 V1.55

- Fixed abandoned ships firing missiles after crew escape on Atari ST and Amiga; verified normal missile launches remain unaffected.
- Atari ST & Amiga: Set AI laser range to half the ×1 scanner range (12,288 units); accuracy unchanged, distant beam visibility and depth ordering verified. The combat experience is very close to that of the original BBC Elite.

## 15.09.2026 V1.54

- Atari ST: Increased engine volume and lowered its pitch to better match Amiga.
- Amiga: Increased engine volume and added short fade-in/out ramps to reduce clicks when the sound starts or stops.

## 15.09.2026 V1.53

- RCS: Quiet thruster sound during roll/pitch changes, including automatic centering.
- Engine: Speed-dependent pitch while accelerating or braking; silent on key release or at the corresponding speed limit.
- Settings: Shared RCS FX toggle for RCS and Engine sound, ON by default, saved with the Commander.
- Priority: Effects → RCS → engine; both stop immediately during docking, hyperspace jumps and death.

## 14.09.2026 V1.52

- Added Amiga single-instance protection to prevent repeated Workbench launches from corrupting the display and ensure clean exit and restart.

## 14.09.2026 V1.51

- Added a minimum one-second loading screen display on Atari ST and Amiga, counting loading time and supporting PAL/NTSC and faster CPUs.
- Added a standard four-colour Amiga Workbench icon and direct launch support from Workbench 1.3 and later; ensured the loading screen remains visible for at least one second on Atari ST and Amiga, including loading time, with PAL/NTSC support.
- Replaced immediate penalties for scooping illegal cargo with S-zone entry inspections on Atari ST and Amiga; traders can now jettison contraband before entering the station’s protection zone.

## 13.09.2026 V1.50

- Applied the main game’s FPS limit to ship previews, launch, docking, death and both hyperspace animations, with 5-second hyperspace timers independent of sound settings on Atari ST and Amiga.
- Fixed AI laser visibility from ships outside the viewport in all four views on Atari ST and Amiga, preserving depth ordering, damage and hit probability.
- Made Jettison confirmation non-blocking on Atari ST and Amiga, with exclusive Y/N input, cargo and slot revalidation with error feedback, and automatic closure during docking, death and both hyperspace jump types.

## 13.09.2026 V1.47

- Added distance-based AI laser accuracy on Atari ST and Amiga, with smoothly interpolated miss chances of 10% at 1000 units, 20% at 3000, 30% at 5000 and 50% at 7000, preserving firing cadence and damage per hit.
- Added Inventory cargo jettison on Atari ST and Amiga with confirmation, up to 1 t per canister including kg/g goods, exact cargo recovery, random rearward drift and orientation, audio feedback and station-zone legal penalties. Double-click on cargo in the Inventory screen to jettison after confirm.

## 13.09.2026 V1.46

- Added commander persistence for Stars ON/OFF in Atari ST and Amiga. Stars remain ON at startup, for default Jameson and when loading older saves. The 256-byte save format and cross-platform compatibility are preserved.
- Replaced the loading screen in both versions with the final supplied artwork, preserving its pixels and colours without additional dithering.

## 13.09.2026 V1.45

- Created new loading screen. No, this one isn’t AI-generated. It was painted by… me https://www.deviantart.com/ataribaby42/art/Leaving-Lave-971816512 ;)
- Added sparse white background stars (Idea by hitchhikr from lemonamiga.com forum) to Atari ST and Amiga, following ship rotation across all four views and drawn behind all objects and UI.
- Added Stars: ON/OFF to Game Options, enabled by default. Disabling stars skips their drawing and rotation calculations. Re-enabling them resets the sky orientation.
- The moving starfield is dark grey with Stars ON and yellow with Stars OFF. Coloured warp trails remain unchanged.
- Both star layers remain hidden after a failed hyperspace jump.
- Amiga: Fixed commander loading after swapping floppies, including loading directly from the title screen. Loading, saving and the catalog now use the disk inserted in the startup drive.
- Amiga: Prevented freezes caused by hidden AmigaDOS disk requesters. Errors are handled in-game, while HDD saves continue to use the current directory.

## 12.09.2026 V1.44

- Added pulsing red single-pixel anti-collision lights to the four corners of the Coriolis station’s docking face on Atari ST and Amiga, using the existing ship engine palette animation. Lights are hidden when viewed from behind.
- Fixed the scanner zoom indicator remaining at 2x after launch when the actual zoom had reset to 1x, on Atari ST and Amiga.
- Increased the AI laser random miss chance from 10% to 20% on both platforms.

## 12.09.2026 V1.43

- Added an Amiga-inspired hangar launch sound on Atari ST, using a rising PSG engine tone with noise, gradual onset and fade-out. The effect respects the Effects setting and is skipped when the launch animation is disabled.
- Fixed Atari ST hard disk startup with resident HDD drivers by relocating the game into available ST RAM. Verified on a real 1 MB Atari ST with PP HDD Driver. Floppy startup on 512 KB systems remains supported and was tested in Hatari.
- Added left and right Shift as alternative laser fire keys on Atari ST, allowing simultaneous steering in both axes and firing. The original A key remains supported.

## 12.09.2026 V1.42

- Fixed Mission 5 completion on Atari ST and Amiga when the Alien Space Station is destroyed by a missile or collision. Normal hyperspace now unlocks correctly, and docking awards the ECM Jammer once.
- Concealed Dodecahedron station registrations, displaying Alien Space Station ??-???.

## 11.09.2026 V1.41

- Fixed unwanted starfield rotation when engaging warp with the J key while pitching or rolling. Rotation now resets correctly during warp and after returning to normal flight, in all four views on both Atari ST and Amiga.
- Added ship and station registration IDs to IFF identification with the I key, including views without a fitted laser.
- Added the player's registration to the Status screen and commander saves, while retaining compatibility with existing save files.
- New and legacy commanders start with registration JS-042. A successful escape capsule launch assigns a new registration to the replacement ship.
- Pirates, Thargoids and Tharglets conceal their registration as ??-???. The Constrictor retains a visible registration, matching the C64 version.
- Station registrations identify the station model, galaxy and system. AI ships retain their assigned ID throughout their lifetime.
- Removed stray yellow pixels from the Beam and Military laser equipment labels in both Atari ST and Amiga versions.

## 11.09.2026 V1.4

- Amiga / Atari ST: Thargoid and Tharglet lasers now always use light blue from the existing palette, regardless of commander rating.
- Amiga / Atari ST: commander=max now starts Jameson with the Deadly rating and matching score, alongside 1,000,000 Cr. Saved commanders remain unchanged.
- Added distinct continuous Beam and Military laser sounds on Amiga and Atari ST, with short fade-in and fade-out. Target impact sounds remain audible; Pulse and Mining retain their original firing sounds.
- Added scannerlogo=yes|no to Atari ST and Amiga builds to show or hide the ELITE caption below the scanner. Enabled by default.
- Amiga: Added the original ADF sound effect when the hangar launch animation begins. Respects the Effects setting and is skipped when the launch animation is disabled.
- Atari ST and Amiga: Replaced travelling laser effects and AI photon projectiles with BBC-style beams and immediate hit detection.
- Player targeting remains fixed at the crosshair centre; beam jitter is purely cosmetic.
- Preserved original player damage, firing intervals and overheating behaviour. Pulse and Mining fire in pulses; Beam and Military display continuous beams between damage ticks.
- Added laser=dualbeam (default) and laser=singlebeam build options for two converging beams or one central beam.
- Added player laser colours from the existing palette: Pulse red, Beam orange, Military white and Mining instrument-bar magenta.
- AI lasers originate from each model’s gun_node and use the firing ship’s depth for occlusion. Corrected centred muzzle positions for Sidewinder, Gecko, Adder and Moray.
- Successful AI hits apply a random 2×, 3× or 4× multiplier to the original base damage, approximating repeated damage from the former projectiles.
- Added a 10% random miss chance for correctly aimed AI shots, alongside existing aiming checks. Misses still display a beam but cause no damage or impact sound.
- AI beam colours follow player rating: Harmless–Poor red, Average–Competent orange and Dangerous–Elite white. Constrictor beams are always white.
- Added aifiresound=no|yes, defaulting to no, to control AI firing sounds independently of impact and player weapon sounds.
- Fixed “Entering Hyperspace” text being covered by tunnel circles. The message remains visible throughout normal and galactic hyperspace.
- Amiga: Repositioned the intro credit to fit entirely inside the viewport without overlapping the cockpit.
- Atari ST and Amiga: Restored slow starfield drift at zero throttle in all four views. Increased maximum starfield speed by 50%, with smooth linear scaling across the entire throttle range.
- Atari ST and Amiga: Fixed stars accumulating in columns along the rear-view edges during climbing and diving. Vertical departures now re-enter through the opposite edge with randomized horizontal positions and preserved fractional overshoot, preventing synchronized rows.
- Amiga: Replaced ST-derived music with the original four-channel Blue Danube arrangement from the Amiga ADF, including seven sampled instruments. Used for the title, docking computer and Elite congratulations screen, with click-free shutdown and cache-safe playback.
- Atari ST and Amiga: Added commander=max, giving the default commander 1,000,000 Cr when starting or resetting a game. Use commander=default to restore the original 100 Cr. Existing saved commanders retain their balances.
- Halved manual acceleration and deceleration in the Atari ST and Amiga versions, reducing the speed change from 2 to 1 unit per game frame for finer throttle control.
- Fixed starfield clustering in side views immediately after launch by correctly initializing rotation values.
- Fixed horizontal rows of stars forming during sustained roll by preserving each star’s movement past the viewport edge when respawning.
- Reduced control damping from 8 to 2 units per game frame in the Atari ST and Amiga versions. With Damping ON, roll and pitch now return to neutral more gradually, taking 20 frames from full deflection.
- Updated rendering order on Amiga and Atari ST: stars now appear over the planet and sun, while ships, stations and other 3D objects obscure them.
- Kept lasers, the targeting sight and viewport text above the starfield, preserving depth order within each object layer.
- Replaced the Amiga and Atari ST starfield with a native adaptation of the BBC/C64 Elite model.
- Added depth-dependent movement and view-specific star recycling, including incoming-edge spawning in side views.
- Improved steering motion while keeping every star exactly one pixel.
- Preserved retro rocket support and coloured warp trails.
- Removed obsolete starfield lookup files, freeing approximately 29 KB of RAM.
- Fixed viewport clipping on Amiga and Atari ST: hangar scenes, 3D objects, planets and the sun now fill the complete 256 × 112 viewport without missing edge columns.
- Applied sun-flare clipping after expansion to prevent drawing over the cockpit border.
- Updated starfield bounds and movement tables to support the full viewport width and prevent out-of-bounds lookups.
- Fixed corrupted missile indicators and options icons on CPUs with instruction caches in both the Amiga and Atari ST versions. Replaced self-modifying sprite code with fixed rotation routines, preserving fast rendering on the 68000.
- Added the original Atari title image to Amiga startup, displayed with native Amiga graphics and colours while game assets load. The game continues automatically when loading finishes.
- Optimized viewport clearing on Amiga and Atari ST using larger MOVEM.L transfers.
- Accelerated Amiga vertical lines, horizontal spans and block fills by caching plane colours.
- Optimized diagonal line drawing on both platforms by caching colour masks and reducing memory accesses.
- Added MC68000 regression tests covering rendering accuracy, viewport boundaries, register preservation and VBL synchronization.
- Amiga port and noprotect=yes build option for disabling novella check at start.
- Fixed slow vertical starfield movement in all cockpit views to match object movement during turns, preserving fractional pixels for smoother motion.
- Fixed reversed vertical starfield movement when rolling in the left and right cockpit views.
