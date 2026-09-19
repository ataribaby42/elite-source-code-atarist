# UI cursor disappearance near the top of the screen

## Finding

The Amiga software cursor can be partially absent because its erase/redraw
sequence overlaps display DMA. The screen buffer contains the correct cursor
after drawing finishes, but some rows have already been fetched for display.
Moving horizontally changes the rendering cost, so the missing portion changes
with position. Variations in interrupt timing can make it flicker.

`draw_sprite` in `src_amiga/asm/sprites.m68` first calls `remove_sprite`, which
restores the complete saved background, and then draws the new cursor from top
to bottom. `drive_cursor` redraws it on every enabled VBL, including when it has
not moved. `amiga_vblank` calls the game VBL work after publishing the display
pointers and colours. The Copper starts the 200-line image at raster line 44.

The inherited algorithm also exists on Atari ST. The tested PAL ST configuration
has sufficient time to draw the corresponding rows before display reaches them.
The Amiga timing failure is therefore not evidence of an incorrect shared clipping
algorithm or damaged cursor artwork.

## Verification

All diagnostics were isolated from the user's emulator sessions. The initial
diagnosis did not change game sources, PNGs, build options or distribution files.

- Executed each platform's current sprite and clipping routines on an emulated
  MC68000 in a private WinUAE diagnostic ROM. Tested 262 positions per platform,
  including all horizontal shifts, top/bottom clipping, left/right clipping and
  corners. Compared every framebuffer byte with an independently generated
  pixel reference after drawing and repeated drawing, then checked complete
  background restoration. Both platforms passed every case.
- Confirmed that the blue cursor's palette indices are identical in `gfx` and
  `gfx_alt` on both platforms.
- Measured the Amiga renderer with cycle-exact PAL OCS emulation, display DMA
  enabled, code and screen in Chip RAM, and the game's display window and modulo.
  Started repeated drawing near raster line 2, earlier than the normal operating
  system callback. At screen y=0, completion ranged from approximately raster
  line 60 to 82 across the 16 horizontal alignments. At x=88, cursor rows 10–17
  completed after the start of their display lines. There is already a timing
  failure before adding input polling or other game VBL work.
- Measured the Atari routines in private Hatari 2.6.1, ST PAL at 8 MHz, with the
  actual TOS 1.04 VBL queue registration method used by the game. After warm-up,
  all 16 horizontal alignments at y=0 completed their rows before display reached
  them. The smallest measured margin was about 13.4 raster lines. This includes
  TOS interrupt activity, but the callback directly invokes `draw_sprite` rather
  than running all game clock/input/sound code.

Row timing instrumentation adds a small amount of work. The Amiga test's late
rows exceed that overhead; the Atari test retains a positive margin despite it.
These are routine-level CPU/display tests, not a recording of a complete game UI
session. Atari NTSC and other machine/OS configurations were not validated.

The ST PAL display deadline uses line 63, matching
[Hatari's video timing implementation](https://raw.githubusercontent.com/hatari/hatari/v2.6.1/src/video.c).
Debugger automation follows the
[Hatari debugger manual](https://hatari.frama.io/hatari/doc/debugger.html).

## Local diagnostic artifacts

- `src_amiga/build/cursor-review/run_review.py`: framebuffer checks for both trees.
- `src_amiga/build/cursor-review/measure_timing.py` and `beam-report.json`: Amiga
  beam measurements.
- `src_atari/build/cursor-review/measure_hatari.py`: standalone ST timing setup.
- `src_atari/build/cursor-review/measure_tos_vbl.py`, `tos-debugger.log` and
  `tos-beam-report.json`: ST measurements through the TOS VBL queue.

The private emulator copies, diagnostic ROMs and generated data remain under the
platform build directories and are not distribution assets.

## Implemented Amiga correction

`src_amiga/asm/cursor.m68` prepares the 16 horizontal shifts of all three UI
cursors after `read_bitmaps`, before the game VBL is enabled. It uses the loaded
bitmaps, so both graphics variants and later PNG edits are included automatically.
The cache occupies 25,934 bytes of ordinary RAM and does not require Chip RAM.

During VBL, `draw_cursor` uses the existing clipping calculations and copies
adjacent words with longword operations. Background rows use the same contiguous
plane layout. The new `cursor_saved` flag directs `remove_sprite` to the matching
restoration routine, so cursor hiding, showing, screen changes and a switch back
to the general sprite renderer preserve the correct background. Other sprites
keep their existing renderer. Unsupported cursor geometry, a changed bitmap
pointer or a nonstandard clipping window safely uses the general path.

The cursor image, position limits, palette, input handling and game timing are
unchanged. The correction is confined to the Amiga tree.

### Fix validation

The initial validation missed a register-width bug in the new cached renderer.
Its pixel tests happened to enter with D4's upper half clear, and the full-game
check stopped after cache initialization. Neither check established that the
cursor worked during normal UI interaction. The reported multicolour rectangle
was a regression in this implementation.

- The private WinUAE framebuffer regression covers 786 cases per graphics
  variant: three cursor images at each of 262 positions. It checks every screen
  byte against independently composed pixels, repeated drawing, movement between
  cases, cursor type changes and complete background restoration. Additional
  checks exercise transitions between cached and general rendering and guard
  both ends of the cache against overwrites.
- Cycle-exact PAL OCS timing uses code, cache and framebuffer in Chip RAM, with
  display DMA active. The corrected renderer passes all 16 horizontal shifts at
  y=0 even when deliberately started at raster line 24. The smallest measured
  row deadline margin is about four raster lines, including instrumentation.
  At x=88, erase/redraw takes approximately 33 lines instead of the original 79.
- Both the normal and alternative graphics builds pass MC68000 assembly, Hunk
  relocation and allocation checks, and ADF filesystem validation.
- The built alternative-graphics ADF loads in a private WinUAE A500 configuration
  with Kickstart 1.3, 512 KB Chip RAM and 512 KB Slow RAM. A live memory check
  confirms that the new cache initializes successfully from the loaded assets.
- The existing Amiga test suite passes 22 tests. Its historical-asset identity
  test is skipped because the source PNGs have already been customized.

Fix diagnostics and reports are under `src_amiga/build/cursor-fix`. The pixel
and timing tests execute the actual production assembly. The timing measurement
is a controlled renderer test rather than a full UI interaction recording.

## Follow-up: corrupted cursor image

The clipped horizontal cache offset is calculated with word operations in D4.
The initial implementation then used `adda.l d4,a3`, incorporating the upper
16 bits inherited from the interrupted game code. With a nonzero upper half,
the renderer reads unrelated memory instead of the cursor's mask and planes.
This explains the multicolour rectangle on the Status screen.

The address addition now uses `adda.w d4,a3`, matching the offset calculation.
Other cache offsets already use `mulu`, which defines the complete longword.
The change is confined to the Amiga cursor renderer.

The regression now seeds D4 with `$00010000` before every cached draw. The
previous instruction fails immediately with that input. The corrected routine
passes all 786 cases for each graphics variant, including clipping, movement,
cursor type changes, renderer transitions and background restoration. Repeated
cycle-exact timing checks retain a minimum row deadline margin of about four
raster lines. Both distribution ADFs have been rebuilt and validated.

The rebuilt alternative-graphics ADF was also exercised as a complete game in
the private cycle-exact PAL OCS WinUAE instance, with Kickstart 1.3, 512 KB Chip
RAM and 512 KB Slow RAM. The diagnostic entered the Status screen through the
game's keyboard queue, switched to Disk Menu and Options, then returned to
Status. All 48 checks passed: each screen used all three cursor types at
`(160,81)` and at `(80,0)`, `(88,0)` and `(95,0)`. The cursor rectangle was
compared pixel by pixel with the PNG source and the game's saved background.

Eight native WinUAE display screenshots were captured in addition to the memory
checks. The Status screenshot shows the correct cursor where the reported
multicolour rectangle appeared; the Disk Menu screenshot shows the complete
cursor across the upper title bar. These are emulator display captures, not
just reconstructed framebuffer images. The live report and screenshots are in
`src_amiga/build/cursor-fix/boot`; the diagnostic only writes to its own emulator
instance and private ADF copy.

## Follow-up: top-edge blinking during clock updates

The preceding spot checks at y=0 did not cover the actual movement limit y=-8
over successive clock ticks. In the complete game, two issues interact:

- The clock's `cmp #100,sp_ypos(a4)` used an unsigned `hi` condition. A negative
  cursor Y was therefore treated as being in the lower part of the screen, and
  the clock erased the cursor before printing its text.
- Clock text was printed before `drive_cursor`. On the tested PAL A500, this
  delayed cursor drawing from approximately raster lines 14-20 to line 110 on
  the once-per-second update. The display begins at line 44, so the top cursor
  was absent in that frame. The cached sprite routine alone cannot compensate
  for that delay.

`src_amiga/asm/except.m68` now separates clock advancement from clock painting.
The time counters retain their original update cadence. A pending flag makes
the clock text paint exactly once per update. After processing movement,
`drive_cursor` paints the clock before a lower cursor, preserving the new digits
in its saved background. For an upper cursor, the VBL paints the clock after
drawing the cursor. The final VBL call also handles a disabled cursor or an
active countdown. Both Y comparisons use signed conditions.

Before the correction, 100 native display captures at `(232,-8)` contained
three frames with the cursor missing. After the correction, 100 captures had
identical, correct cursor pixels. A bounded tracing stub in the private game's
unused screen padding measured clock-update draws starting around line 14 and
finishing around line 34, before line 44. The trace adds overhead; it does not
replace the uninstrumented screenshot sequence.

The complete-game pixel checks additionally pass for all three cursor types at
Y values -8, -1, 0, 80, 100, 101, 140, 151, 160 and 191, including positions
over the clock. All 16 horizontal alignments at the clipped upper edge also
pass, for 46 additional checks in total. Both graphics distributions build and
pass ADF validation. The existing test suite passes 22 tests, with its one
historical-asset identity test skipped for the customized source PNGs.

Diagnostics are in `src_amiga/build/cursor-edge`. Later runs use a separate
Windows desktop created for the diagnostic process, verify that its windows
belong to that desktop, and never switch to it. Private files and minimized
startup alone did not prevent earlier emulator windows from appearing on the
user's desktop. Every diagnostic closes only its own process and desktop.

## Atari ST clock/cursor correction

The Atari implementation had the same unsigned Y comparison and printed the
clock before driving the cursor. `src_atari/asm/except.m68` now independently
implements the pending-clock arrangement described above, including signed Y
comparisons. Clock advancement remains once per 50 VBLs; painting is deferred
until after an upper cursor and performed before a lower cursor saves its
background. The final VBL call also paints when the cursor is disabled or a
countdown suppresses cursor driving. The existing Atari sprite renderer is used.

Validation now includes the built game running through its real TOS VBL queue,
not just a standalone sprite routine. A private Hatari 2.6.1 instance ran ST PAL
at 8 MHz with TOS 1.04 and 2 MB RAM. Its window was verified on a separate hidden
Windows desktop, and only private executable, configuration and disk copies
were used.

- Entered the Status screen through the game's keyboard queue and captured 110
  consecutive native display frames with the blue cursor at `(232,-8)`. The
  cursor pixels were identical throughout, including clock updates.
- Compared the complete cursor rectangle against the PNG source and saved
  background in 46 live-game cases. All three cursor types passed at Y values
  -8, -1, 0, 80, 100, 101, 140, 151, 160 and 191. The tests explicitly trigger
  clock updates after setting each position. All 16 horizontal alignments at
  the clipped top edge also passed.
- Debugger timing traces of the actual game show the top-edge cursor finished
  no later than raster line 48.70, before the PAL ST display starts at line 63.
  These traces include the game's clock and input processing and TOS interrupts.
- Both `ELITE.ST` and `ELITE_ALT.ST` pass assembly, relocation, RAM-layout and
  FAT12 readback validation. The full-game emulator run used `ELITE_ALT.ST`.
- The Atari test suite passes 24 tests. Its historical-asset identity test is
  skipped because the source PNGs have already been customized.

The Atari diagnostic scripts, native screenshots, memory dumps and machine-
readable report are under `src_atari/build/cursor-clock`. Atari NTSC and other
machine/OS configurations were not covered by this run.
