# Procedural planet surfaces

The independent enhanced Atari and Amiga builds generate markings over the
entire planetary sphere. A complete orbit reveals the other hemisphere and
returns to the same geography. The original version and historical archive
are untouched.

## Appearance

| Planet colour | Markings |
| --- | --- |
| Light grey | Dark grey crater outlines and short rays |
| Light or medium green | Solid blue or light blue seas |
| Light or medium blue | Solid green or light green continents |
| Other valid planet colours | Solid continents in a different seeded colour |

Dark grey planet backgrounds remain excluded by the existing colour lookup.
The system seed chooses one medium or light detail shade for green and blue
worlds. Other valid backgrounds, including dark green and dark blue, choose
from the valid planet palette and skip their own base colour. Transparent,
black, dark grey, yellow and pulsing entries are excluded. Yellow and UI brown
map to steady red for planet backgrounds. These choices do not
advance the geometry generator or change the existing coastline.
Seas and continents have independently oriented, elongated, irregular coasts;
overlapping regions can form larger connected areas. They use a single palette
colour without stippling or alternating rows. The system seed selects 3..6
regions or 3..6 craters over the entire sphere. Each region has eight coastal
vertices; its internal centre is used only for the triangle fan. Regions can
overlap, so their count is not the number of separate visible land masses.
Each crater retains eight rim vertices and four rays.
Ray extensions vary from half to the full rim radius, with independent angular
deflections between -10 and +10 degrees.

Details start at a projected radius of 12 logical pixels, approximately a
24-pixel diameter. The Amiga threshold follows vertical display scaling, and
horizontal projection follows the native circle stretch in HIRES. Below the
threshold the existing circle renderer runs without surface transformations.

## Options and Planet Data

The row above Reset Game / Exit Program in Options contains `Planets: ON / OFF`.
ON enables surface markings in flight and an animated Planet Data portrait.
The preview starts at zero rotation on each visit and then turns in the same
seeded direction as the real planet, at an accelerated speed. The portrait uses the selected system's seed and the existing galaxy/planet colour
table, regardless of the current flight view or hyperspace arrival longitude.
OFF keeps the original plain flight globe and textured bitmap on Planet Data.

With ON, Planet Data reserves the cockpit RGB values only for the colours used
by the rendered portrait. The inhabitants keep all three original private
shades when the globe does not need palette entries 7..9, including grey worlds
such as Learorce. When a green entry is needed, the game tries all six assignments
of the original shades to the remaining free entries. It selects the palette
with the lowest squared RGB error, weighted by the number of character pixels
using each shade. Large body areas therefore take priority over small highlights.
Only the character rectangle is remapped, and transparent/flashing entries are
excluded as destinations. The portrait retains the exact flight colours.
With OFF, the original inhabitant palette changes and bitmap are preserved.

The preference occupies bit 1 of `USER+1`, the previously unused second byte
of the existing saved USER word. A set bit explicitly enables Planets; zero
means OFF for a new game and older saves. It is included in normal and RAM
commander saves without changing the 256-byte format or adding an extension.
Bit 0, used by the earlier experimental OFF flag, is ignored. Thus old saves
from either experimental setting also default to OFF rather than accidentally
enabling the feature. Newly saved commanders retain their selected ON/OFF state.

The portrait uses a private object and backs up the entire live surface
workspace. It renders in a bounded part of the invisible screen already used
by the legacy texture path, then copies the 96-pixel-wide portrait rectangle.
It restores the live map, current system seed, system number and cockpit view.
Amiga portraits synchronize pending clears, temporarily bypass the Fast RAM
shadow and invalidate its screen mirrors after the direct copy.

## Generation and orientation

Each tree owns `asm/planet.m68`. `init_planet_surface` combines the current
system's three seed words into a private xorshift32 state. It generates and
caches the flight system's geometry, independent of the gameplay random state.
The first private random value selects the feature count, rotation direction
and period; subsequent values choose positions and shapes. All these properties
repeat for the same seed. Planet Data keeps a separate selected-system cache.
The map is regenerated after hyperspace and on launch, with no save-file layout changes.

Hyperspace creation and station launch with Planets ON call `turn_planet_surface`. It samples the
existing random state without advancing it and chooses one of 64 longitudes
(5.625-degree steps) around the vertical axis. This simulates rotation while
away or docked; it does not regenerate geography. Continuous local-axis spin
is added to this arrival orientation using the status-screen game clock.
Launch with Planets OFF keeps the original orientation. Player roll and pitch now update
the planet's orientation even though it retains its point-object flag for
gameplay, collisions and draw ordering. Other point objects keep their old path.

## Rendering

The original circular globe silhouette is retained. Markings use Q12 coordinates
on a sphere and the game's Q14 object orientation. The rendering matrix combines
that orientation, the cockpit view, and the actual direction from the player
to the centre. Projection follows the existing orthographic globe appearance;
this is surface decoration, not raised or excavated terrain.

Coast triangles and crater segments are clipped against the near hemisphere
before screen projection. Horizon intersections are normalized onto the limb.
The existing viewport clippers protect the cockpit and off-screen memory.
Long screen-coordinate additions saturate before conversion to signed words.
Projection rounds to the nearest pixel, with a three-logical-pixel inset plus
a small size-dependent allowance for accumulated fixed-point rounding. This
also covers the original circle renderer's one-pixel radius decrement.

Entirely hidden features are skipped. Entirely visible, screen-contained coasts
that have only two vertical direction changes use one polygon fill. Other coasts
use a bounded triangle fan. The two alternating polygon colour rows contain
identical masks, avoiding the striped result produced by using line-colour data
as a polygon material.

The renderer first transforms only Z for the nine points of a region
(centre plus eight coast vertices), or all thirteen points of a crater.
If all vertices are behind the horizon, it skips their X/Y transformations.
Otherwise it computes X/Y and projects each near-side vertex once into a
per-feature screen-coordinate cache. Coast polygons, triangle fans and crater
segments reuse those exact rounded and saturated pixel coordinates. Crater
centres participate in the visibility test but need no X/Y transformation or
projection, since only the rim and ray vertices are drawn.

Triangle clipping carries the original vertex IDs alongside its coordinates.
New horizon intersections have a negative ID and retain the original uncached
projection and directed-edge intersection arithmetic. This preserves fixed-point
rounding at the limb. The standalone triangle entry also uses negative IDs,
so callers supplying only coordinates never read the feature cache. Each drawn
feature refreshes all of its near-side cache entries, including after changes
to radius, centre, seed, orientation or cockpit view.

Horizon normalization specializes the known Z=0 plane. It uses the same integer
square root and signed X/Y divisions, omitting the zero Z multiplication,
addition and division. The intersection routine's existing register save also
covers this normalization, avoiding a second save/restore and subroutine call.
The original zero-vector fallback is retained. Bounded six-byte vertex offsets
use additions instead of general multiplications.

The new workspace reserves 3,200 bytes per platform and does not enlarge object
or commander records. The cache and vertex IDs consume 66 bytes, plus 66 bytes
in the existing portrait backup, within this reservation. Geometry is generated
at system creation, not every frame.

## Verification

`tests/native_planet_surface.py` in each tree exercises the actual assembled
game. Tests cover reproducible and different seeds, palette rules, the size
threshold, a complete orbit for seas/continents/craters, viewport bounds from
small to very large off-centre globes, player rotation, arrival longitude,
unchanged gameplay RNG, invisible far-side geometry, and both creation paths.

Generated evidence, private emulator copies, configurations, native payloads,
pixel captures and timing results live under each tree's
`build/planet-surface-qa`. Tests run on verified, separate hidden Windows
desktops, without interacting with the user's emulator session.

The pixel checks compare a complete orbit's first and final frames, distinguish
opposite hemispheres, require only the intended solid colours, and compare all
detail pixels against a plain reference silhouette. Crater-ray geometry is also
checked independently in the local tangent plane.

The original 75-scenario suite was exercised on an
emulated Atari ST with 1 MB RAM, a cycle-exact Amiga 68000 with 512 KB Chip RAM
and 512 KB Slow RAM, and expanded Amiga PAL HIRES and NTSC HIRES-LACED modes.
The expanded display checks use a 68020 emulator running the 68000 binaries;
their accelerated timing is not representative of original hardware.
The palette checks exercise both seeded detail shades for the four green/blue
base colours, the six other valid backgrounds and legacy yellow-to-red conversion. Sixteen seeds per extra
background cover matching-colour rejection, wraparound, deterministic selection
and preservation of the gameplay RNG. Portrait checks verify unchanged flight
state, zero rotation across cockpit views, the bitmap fallback, both saved
option states and the default commander. The Amiga fixture waits
for pending screen clears and presents the Fast RAM shadow before capture,
matching the normal rendering pipeline. The 48 independently measured crater
rays covered 50.35–99.15% of the rim radius with at most 10.35 degrees of
deflection, including integer quantization.

Both Atari graphics variants and all fourteen Amiga graphics/display variants
were rebuilt. The existing Python suites also passed: 35 Atari tests and 34
Amiga tests, with one historical-bitmap configuration skip in each suite.

The palette follow-up expands the suite to 95 scenarios. The additional cases
compare actual runtime RGB values for human worlds, every inhabitant palette
and a red planet with Planets both ON and OFF. They verify exact cockpit RGB
for the portrait's reserved entries and unchanged legacy colours with OFF.
Atari palette reads mask undefined hardware bits; Amiga checks use the relocated
runtime palette, not the code-hunk address. The additional captures are stored
under `build/planet-palette-qa` and also validate the relocated options row.

Default-OFF verification expands the suite to 97 scenarios. It checks a new
commander and both legacy USER encodings, while retaining the ON/OFF save and
restore checks. Evidence is stored under `build/planets-default-qa`.

Station-launch verification expands the surface suite to 100 scenarios. It
checks vertical-only longitude selection with ON, identity orientation with
OFF, unchanged geography across repeated launches, and identical gameplay RNG
consumption with either option state. Evidence is under `build/launch-rotation-qa`.

The inhabitant palette fitting regression uses `tests/native_inhabitant_palette.py`
in each independent tree. Its 82 captures cover all eight alien palettes with
every possible reservation of zero, one, or two green entries, plus actual
Planet Data screens and the reported Learorce character. Pixel checks compare
the native result with an exhaustive reference search, require exact flight
RGB for the globe, and require unchanged character colours when no private
entries are reserved. The Atari ST and Amiga framed/NTSC-HIRESLACE checks pass;
evidence and visual comparisons are under `build/inhabitant-palette-qa`.

This first implementation has a measurable cost on a stock 68000. At a logical
radius of 48 pixels, the added detail pass averaged 81.875 ms for seas and
50 ms for craters on the emulated 8 MHz Atari ST. The cycle-exact PAL Amiga
68000 measured 95 ms and 60 ms respectively. These are averages of 32 passes,
excluding the base circle and other game work, not whole-game frame rates.
Distant planets avoid that work through the size threshold. Other radii,
geography and visible regions change the cost.

## Returning from UI screens (2026-10-04)

The visible construction of continents after leaving a chart was a framebuffer
transition defect. UI screens present `scr_base` directly. `prepare_cockpit`
rebuilds both cockpit buffers, but formerly left that visible buffer selected
for the first flight frame. Later frame swaps restored normal double buffering.
The cached globe and its orientation were not regenerated by the transition.

Both enhanced versions now select the other buffer in `select_view` immediately
after preparing the cockpit when returning from UI. The ordinary frame renderer
then presents the completed scene. Switching between existing flight views does
not change the drawing buffer.

Each platform's `tests/native_ui_return.py` provides 56 native scenarios covering
both buffers, all four flight views, and returns from the local chart, galactic
chart, Status, Inventory, Planet Data and Options. They check the actual displayed
buffer, unchanged globe workspace and object state, unchanged visible-screen
checksums while the first planet frame is drawn, and the subsequent presentation.
The related nine communications lifecycle and 49 targeting-indicator checks also
pass on each platform. Isolated emulator evidence is under `build/ui-return-fix-qa`.
The 56 transition scenarios also pass on Amiga PAL with direct drawing, PAL
without the frame, PAL hires, and NTSC hires-laced without the frame, in addition
to the selected PAL framed fastdraw build. This gives 114 native checks on Atari
and 338 across the tested Amiga configurations.

## Projection caching and early visibility (2026-10-28)

Both enhanced renderers now reuse the projection of each original near-side
vertex within a feature and reject wholly hidden features after transforming
Z alone. They retain the original seeded geography, size threshold, matrix
arithmetic, projection rounding and saturation, circle inset, horizon
intersections, polygon fill and line rasterization. The cache fits inside the
existing surface workspace; the reserved surface RAM and object/save layouts
are unchanged. It is included in the Planet Data backup and restoration.

`tests/native_planet_optimization.py` in each tree extends the existing surface
suite with three seeds, eight longitudes, off-axis eye directions, and captured
bounds cases from radius 11 through 4,000 logical pixels. It also records 32
detail passes per benchmark case. The before/after runs use independently
built and copied standard `ELITE` and `ELITE_ALT` distributions, private emulator
executables and disks, and verified hidden Windows desktops.

The following measurements are from the standard `ELITE` distribution at a
logical radius of 48 pixels, averaged over eight longitudes and 256 detail
passes for the same fixed seed. Atari uses an emulated ST with 1 MB RAM. Amiga
uses cycle-exact PAL 68000 emulation, Kickstart 1.3, 512 KB Chip RAM and 512 KB
Slow RAM, with the standard framed `fastdraw=yes` build. Timing uses the
50 Hz vertical-blank counter. These are the added surface pass alone, excluding
the base circle, screen clear, presentation and other game work; they are not
whole-game frame-rate measurements.

| Platform | Surface | Before | After | Less rendering time |
| --- | --- | ---: | ---: | ---: |
| Atari ST | Seas / continents | 101.250 ms | 98.359 ms | 2.85% |
| Atari ST | Craters | 46.250 ms | 40.156 ms | 13.18% |
| Amiga 68000 | Seas / continents | 117.500 ms | 113.984 ms | 2.99% |
| Amiga 68000 | Craters | 55.469 ms | 48.438 ms | 12.68% |

The corresponding `ELITE_ALT` reductions at radius 48 are 2.93% / 12.86%
on Atari and 2.86% / 13.22% on Amiga for continents / craters. Its individual
timings are recorded in `comparison-ELITE_ALT.json` under each QA directory.

At radius 12, the measured time reductions are 6.15% / 11.11% on Atari and
5.26% / 11.63% on Amiga for continents / craters. At radius 120 they are
3.95% / 10.67% and 4.37% / 11.24%, respectively. Those supplementary cases
use one longitude and 32 passes each. The timer resolution is one 20 ms tick
per batch, or 0.625 ms per pass for a 32-pass case. Geography and orientation
affect the result; the earlier single-orientation measurements above are not
the baseline for this eight-orientation comparison.

Build logs, baseline source copies, private configurations, native payloads,
raw framebuffers, per-orientation tick counts and comparison reports are under
each tree's `build/planet-opt-qa`. Every comparison report records framebuffer
hashes as well as the before/after timings.

All four optimized distributions passed 186 native scenarios each, for 744
scenarios in total. Each also matched all 141 before/after 32,000-byte
framebuffers exactly: 564 identical comparisons covering the original surface
and portrait cases as well as the extra seeds and bounds captures. Both linked
maps report 3,128 surface-workspace bytes used out of the existing 3,200-byte
reservation. The Python suites passed 35 Atari and 36 Amiga tests, with one
historical-bitmap configuration skip in each. The preserved source archive's
SHA-256 remained unchanged.

## Further horizon arithmetic optimization

This follow-up applies the Z=0 normalization and six-byte index arithmetic
described above independently in both platform trees. It does not change the
general three-dimensional normalizer used by map generation and view matrices.
The surface workspace remains 3,128 bytes within its 3,200-byte reservation.

The baseline already includes projection caching and early visibility from the
preceding section. Fresh builds of both `ELITE` and `ELITE_ALT` reproduced the
previously verified disk images and link maps byte-for-byte, as well as the
Amiga executables. Their existing reference captures and timings were therefore
reused, with that provenance recorded in `baseline-provenance.json`. New builds
were tested in the same verified hidden-desktop emulator configurations.

`tests/native_planet_horizon.py` extends the pixel/timing fixture with 512 endpoint
pairs in both directions. It compares all D0-D7 and A0-A5 register values from
the optimized intersection with a frozen copy of the previous intersection
calling the unchanged general normalizer. The 1,024 comparisons include exact
horizon endpoints, signed rounding, tiny and large coordinates, deterministic
random pairs and the zero-vector fallback. Nonzero upper register words also
check that full result registers and preserved registers remain equivalent.

For the standard `ELITE` distribution, at radius 48 and averaged over the same
eight longitudes and 256 detail passes, the additional improvement is:

| Platform | Surface | With optimizations 1 and 2 | With optimization 3 added | Less rendering time |
| --- | --- | ---: | ---: | ---: |
| Atari ST | Seas / continents | 98.359 ms | 96.406 ms | 1.99% |
| Atari ST | Craters | 40.156 ms | 39.219 ms | 2.33% |
| Amiga 68000 | Seas / continents | 113.984 ms | 112.031 ms | 1.71% |
| Amiga 68000 | Craters | 48.438 ms | 47.422 ms | 2.10% |

These measurements cover only the added surface pass and use the same 50 Hz
batch timing as above. Supplementary radius-12 and radius-120 measurements use
32 passes and are more affected by the 0.625 ms per-pass timer quantization.
Full timings, reference provenance, source copies, build logs, private emulator
configuration, native captures and comparison reports are under each tree's
`build/planet-opt3-qa`.

All four optimized distributions passed 187 native scenarios each (748 in
total), including 1,024 exact directed-intersection comparisons per distribution.
All 564 before/after framebuffers matched byte-for-byte. `ELITE_ALT` also
improved in both surface categories; its per-orientation timings are recorded
in each platform's `comparison-ELITE_ALT.json`. The Python suites again passed
35 Atari and 36 Amiga tests, with one historical-bitmap configuration skip in
each. Only the standard `ELITE` and `ELITE_ALT` distributions were rebuilt.
The preserved source archive's SHA-256 remained unchanged, and all private
test emulator processes were closed after verification.


## Optimization 4: exact continent span batching (2026-10-29)

Both platform renderers now batch the fallback triangle fan for each continent.
The existing single-polygon path for suitable, fully visible regions remains in
place. The fallback still performs the same directed horizon intersections,
viewport clipping and Bresenham edge walks as before. Instead of painting each
triangle immediately, it collects that triangle's inclusive horizontal spans
and paints their union after the continent is complete. Separate intervals on
a row remain separate, so concave coastlines retain their gaps. Adjacent spans
can be merged because there is no missing pixel between their inclusive ends.
Replacing the fan with a newly rasterized coast polygon would not guarantee
this exact edge rounding.

Each row has a count and room for twelve pairs of word-sized endpoints: one
possible interval per input triangle. Intersections, overlaps and bridge spans
merge into that bounded list. Counts are initialized once and cleared as the
batch is painted, avoiding a full viewport clear for every continent. The paint
step uses the existing platform horizontal-line routine, including its colour
masks, physical-row dither phase and Amiga shadow-buffer addressing. Craters
continue to use their existing line renderer.

The standard 112-row viewport needs 5,600 bytes of span storage. Atari places
it in the existing gap before the aligned second screen; both standard builds
retain the same `ram_end` address. Amiga reserves 5,600 additional workspace
bytes. The buffer scales with `y_size` in other Amiga configurations, which
were not part of this verification. Ten control bytes fit in the existing
600-byte graphics variable reservation (578 bytes used on Atari, 572 on Amiga).
The surface workspace remains 3,128 of its reserved 3,200 bytes.

Fresh baseline builds reproduced optimization 3's verified disks and link maps
byte-for-byte, and also reproduced both Amiga executables. The previous native
captures and timing records were reused with that provenance recorded. The new
builds use the same isolated, verified hidden-desktop emulator configurations:
8 MHz Atari ST and cycle-exact PAL Amiga 68000, each with 1 MB RAM. Only the
standard `ELITE` and `ELITE_ALT` distributions are involved.

At radius 48, averaged over eight longitudes and 256 detail passes, the standard
`ELITE` results are:

| Platform | Surface | With optimization 3 | With optimization 4 | Less rendering time |
| --- | --- | ---: | ---: | ---: |
| Atari ST | Seas / continents | 96.406 ms | 86.875 ms | 9.89% |
| Atari ST | Craters | 39.219 ms | 39.141 ms | 0.20% |
| Amiga 68000 | Seas / continents | 112.031 ms | 102.969 ms | 8.09% |
| Amiga 68000 | Craters | 47.422 ms | 47.422 ms | 0.00% |

These are surface-detail times, excluding the base circle, clear, presentation
and other game work. They are not whole-game frame rates. The small Atari crater
difference is one VBL tick over all 256 passes, not an optimization of the crater
renderer. At radius 120, the measured continent time falls by 12.43% on Atari
and 9.69% on Amiga. At radius 12, it is unchanged on Atari and falls by 1.43% on
Amiga. Those supplementary measurements use one longitude and 32 passes each;
the 20 ms timer tick corresponds to 0.625 ms per pass in such a batch.

`tests/native_planet_spans.py` adds 24 native interval-union cases to the existing
pixel, timing and exact horizon-arithmetic suite. They include twelve disjoint
intervals, touching intervals, reversed endpoints and insertion order, duplicate
coverage, a span bridging many gaps, deterministic random inputs, the first and
last viewport rows, count recycling and empty batches. The native results are
checked against independently computed expected unions, including the number
of intervals and each pair of endpoints.


All four distributions passed 188 native scenarios each (752 in total), with
all 564 before/after framebuffers identical byte-for-byte. Each distribution
also passed the 24 span-union cases and the existing 1,024 directed horizon
intersection comparisons. `ELITE_ALT` continent time at radius 48 fell from
96.484 to 86.875 ms on Atari (9.96%) and from 112.109 to 103.125 ms on Amiga
(8.01%). Crater timing differences across the variants are within the VBL timer
quantization; no crater speedup is claimed for this change.

The Python suites completed 35 Atari and 36 Amiga tests with one expected
historical-bitmap configuration skip in each and no failures. Final source
cleanup reproduced the tested binaries byte-for-byte. The original source
archive retained SHA-256
`19496256fb315c5db71c92385783acf4590a682ee3aaE0c6a3435d0ea5faa1e2`.
All owned emulator processes exited after their isolated tests.

The reproducible native fixtures live in each platform's `tests` directory.
Build logs, exact baseline provenance, before-source copies, final source
hashes, private emulator configurations, captures, cleanup verification and
`comparison-ELITE.json` / `comparison-ELITE_ALT.json` reports are under each
platform's `build/planet-opt4-qa` directory. The Atari directory also contains
`comparison-summary.json`, covering both platforms and all measured radii.


## Seeded feature counts and six-point coasts (2026-10-29)

Both enhanced builds now use six coastal vertices per filled region, plus the
internal fan centre. The region has six fan triangles when clipping requires
the fallback path. Craters retain eight rim vertices and four ray endpoints.
The first value from the private seeded generator selects 1..6 filled regions
or 3..6 craters. The count covers the complete sphere; overlap and the hidden
hemisphere can reduce the number of separate markings visible in one view.

Counts are chosen once during map generation and repeat for the same system
seed. Surface colour selection does not consume this generator, so filled
worlds with different base colours still share the same count and geography
for the same seed. Gameplay randomness remains unchanged. Planet Data saves
and restores the count and point limit together with the live surface state.

A map now reserves six feature records. Each record retains space for thirteen
points so crater indexing stays unchanged; the six unused coastal slots are
cleared and skipped. Visibility, transformation and projection visit seven
points for a filled region and thirteen for a crater. Fast polygon filling and
the clipped fan both use six coastal vertices. The surface workspace uses
2,196 bytes inside its unchanged 3,200-byte reservation, including the portrait
backup; the existing span-batch capacity is unchanged.

### Performance sample

The same radius-48 fixture measures eight longitudes and 256 detail passes on
an emulated 8 MHz Atari ST and a cycle-exact PAL Amiga 68000, each with 1 MB RAM.
The seed `5a4a 0248 b753` now generates three regions or four craters. The prior
measurements below come from the retained optimization-4 build, whose source
hash matches the source saved before this change. That version generated eight
regions with twelve coastal vertices, or twelve craters.

| Platform, standard ELITE | Detail | Previous time | Current time | Time reduction |
| --- | --- | ---: | ---: | ---: |
| Atari ST | Regions | 86.875 ms | 21.797 ms | 74.91% |
| Atari ST | Craters | 39.141 ms | 13.750 ms | 64.87% |
| Amiga 68000 | Regions | 102.969 ms | 25.781 ms | 74.96% |
| Amiga 68000 | Craters | 47.422 ms | 16.719 ms | 64.74% |

These are detail-pass times, excluding the base circle and other frame work.
They reflect the requested changes to both geometry and population, and are
not a comparison of identical images. Other seeds have different counts and
costs. Timing uses the same 50 Hz VBL counter as the earlier measurements.

### Validation

The standard `ELITE` and `ELITE_ALT` distributions were built and tested on
both platforms. Each passed 201 native scenarios (804 total), including
64 seeds per surface type, both range endpoints and every intermediate count,
repeat generation, gameplay RNG preservation, normalized vertices, cleared
unused records and coastal padding. Ten new captures exercise every allowed
population. Existing tests cover viewport guards, orbit rotation, hidden
features, palette selection, Planets OFF, saves and Planet Data state restore.

Per distribution, 37 decoded frames remain inside the plain globe silhouette,
and six framebuffer comparisons verify full-orbit repetition, hidden and
disabled markings, and repeatable portraits. The exact horizon arithmetic and
span-union regressions also pass. Emulator instances used verified private
hidden Windows desktops, with no interaction with the user's emulator.

The Python suites passed 35 Atari and 36 Amiga tests, with one pre-existing
skip per platform. QA reports, snapshots and timing data are under each tree's
`build/planet-counts-qa`. All four distribution images match the tested copies.
The preserved source archive, original game tree and changelog were not changed.


## Eight-point coasts and animated planets (2026-10-29)

This revision supersedes the six-point coast and 1..6 region settings above.
Both platforms now generate 3..6 filled regions with eight coastal vertices
plus an internal fan centre, or 3..6 craters with their existing eight rim
vertices and four rays. The same seed also determines a local rotation
direction and an integer period from 30 through 120 game minutes, following
the period-range update below.

Flight rotation reads the seconds, minutes, hours and days displayed on the
status screen. Its phase is derived from that clock, not accumulated once per
frame, so lower frame rates do not change the period. The calculation follows
the saved clock, including its existing 24-day reset. It adds local-axis spin
to the temporary rendering matrix and leaves the object's stored orientation
and position unchanged. The existing random longitude on hyperspace arrival
and station launch is retained, as are the player's roll and pitch transforms.
The 64-entry trigonometric table is interpolated to a 16-bit full-turn phase.

F7 uses a deliberately accelerated preview with the selected planet's real
rotation direction. It advances 1/256 turn (1.40625 degrees) per rendered
main-loop frame. The docked menu has the same minimum three-flyback spacing as
the flight loop, so it cannot spin faster merely because that menu otherwise
polls input without a frame limit. At 12 rendered frames per second a preview
turn takes about 21.3 seconds; the PAL minimum interval permits at most about
16.7 frames per second. A late frame produces one step, without a catch-up
burst. Leaving F7, turning Planets OFF, entering the cockpit or pausing stops
the preview updates.

Opening F7 regenerates its selected map once. Subsequent frames use the private
cache and preserve the entire flight surface workspace, live planet object,
view and gameplay RNG. Each frame is drawn into the invisible scratch screen;
only pixels belonging to the globe are copied back. This keeps the distance
arrow, captions, inhabitants and other page contents intact. The cursor handling
was subsequently corrected as described below. The combined surface state,
flight backup and preview cache originally used 2,708 of the existing 3,200
reserved bytes on each platform.

### Original rotation validation (2..24-hour revision)

Standard `ELITE` and `ELITE_ALT` builds passed 218 native scenarios each on
Atari ST and Amiga 68000, for 872 scenarios in total. The new
`tests/native_planet_rotation.py` fixture checks 368 exact clock-phase vectors
per distribution, covering every period from 2 through 24 hours, both signs,
quarter/full turns, second/minute/day boundaries and the clock's final day.
It verifies unchanged arrival basis vectors and geography during flight spin,
preview rate limiting, the selected system's direction, cache reuse, preservation
of input events and flight state, and stopping on pause, Planets OFF, cockpit
entry and another UI page.

Per distribution, eleven pairs of framebuffer captures match exactly, including
full periods and opposite-direction quarter turns. A separate status-page check
allows only its normal ticking/flashing game-clock row to change after leaving
F7. Forty-five flight frames remain inside the globe silhouette. Eight successive
F7 updates change globe pixels while preserving all pixels outside its circle.
The Python suites also passed (35 Atari and 36 Amiga tests, with one existing
skip each). All emulator runs used verified private hidden desktops and private
disks. Release disk hashes match the tested copies; QA evidence is in each tree's
`build/planet-rotation-qa`. The original source archive remains unchanged.

## F7 cursor visibility correction (2026-10-29)

The animated portrait previously erased the software cursor before rendering
each frame and disabled its VBL updates until the whole operation finished.
The next VBL redrew it, but another preview frame soon erased it again. This
made the cursor visibly blink even when it did not overlap the globe.

Both platforms now keep a separate visible UI screen pointer while rendering
the portrait offscreen. The VBL temporarily uses that pointer, so the normal
cursor renderer and mouse/joystick handling continue during the expensive draw.
It restores the main loop's drawing target before returning.

Only the final portrait copy briefly holds cursor movement. It leaves the
visible cursor rectangle intact and merges covered globe words into the
cursor's saved background instead. The next normal VBL redraw applies that
background, including when the mouse moves away. There is no extra cursor
erase/redraw outside the VBL and no clearing of queued movement or clicks.
Amiga handles both its cached cursor background layout and the general sprite
fallback. Atari uses its own interleaved sprite layout.

The fix adds four bytes within the reserved planet workspace (2,712 bytes used)
and a four-byte visible UI pointer. Planet geometry, colours, rotation direction,
phase calculation and preview step size are unchanged.

### Validation of cursor visibility

Both standard distributions passed 184 native cursor checks per platform.
These cover all three cursor types, all 16 horizontal shifts, globe overlap,
clipping at screen edges, queued clicks, movement and exact full-screen
background restoration. Amiga `ELITE_ALT` additionally passed 48 cases with
the cached cursor path disabled, exercising the general sprite fallback.
Across the 784 cases, VBL probes observed 2,802 rendering-time flybacks without
a missing cursor or an incorrect sampled opaque pixel. The original Atari
binary failed the same regression on its first case, with the cursor absent
during the three observed flybacks.

An uninstrumented Amiga main-loop run then captured 150 native display frames:
50 each with the cursor over the globe, clipped at the top edge and overlapping
the globe's lower-right edge. Every visible opaque cursor pixel matched the
reference in every capture while the planet animation continued.

All four standard builds also passed the existing 218 native planet scenarios
and their framebuffer validation. For each distribution, 46 flight and F7
frames match the pre-fix binary byte for byte. The Python suites passed 35 Atari
and 36 Amiga tests, with one existing skip each. Tests used private disks and
verified hidden desktops; release disks match those tested. Diagnostics are
under each source tree's `build/planet-cursor-qa` directory.

## F7 presentation and live Atari rotation corrections (2026-10-29)

### Atari destination address

The F7 entry points accept word-sized coordinates. The portrait copy converted
X to a byte offset with word operations, then added it to the screen address as
a longword. An unrelated upper half left in D0 by the normal game loop therefore
became part of the destination address. Rotation phase advanced, but the visible
globe stayed unchanged. The controlled native fixture had previously supplied
zero upper halves and did not expose this live-loop failure.

The Atari renderer now clears the unused upper half before adding the offset.
The rotation fixture deliberately supplies nonzero upper halves and checks the
destination on every subsequent F7 step. The previous binary fails this check;
both corrected Atari distributions pass all 218 native planet scenarios.

A separate cold boot in a private Steem SSE 4.1.2 instance, using TOS 1.04 UK,
1 MB RAM and Lave with Planets ON, reproduced the user's symptom: all 15 globe
captures were identical despite an advancing phase. The corrected program
produced 15 different globe captures; the first and last differed at 1,128
interior pixels. The tested image was copied to the user's specified emulator
disk path, with its previous contents retained under `build/planet-present-qa`.
The emulator must boot the updated program to replace its old RAM contents.

### Amiga display transfer

The original masked copy modified the visible bitplanes through intermediate
AND/OR states. Display DMA could read those states or a mixture of old and new
planes, producing short horizontal strips in colours absent from the planet.
An ordinary Orerve F7 session reproduced this in three of 200 native WinUAE
display captures; completed framebuffer comparisons alone could not detect it.

The Amiga renderer now completes the masked composition on the invisible
screen, records the changed 16-pixel groups, and transfers those groups through
direct stores after the beam has passed the portrait. Unchanged groups are not
transferred. Each changed row also checks the beam before writing: if a slow
transfer crosses into the next field, it waits until that row has been scanned
instead of exposing partially updated bitplanes. This is confined to F7
presentation; flight geometry and the four existing rendering optimizations
are unchanged.

The visible cursor remains drawn throughout. Its saved background receives
covered planet words. Cursor redraw is held during the final composition,
raster wait and transfer, while interrupts, sound and queued input continue.
This also prevents the slower general HiRes cursor path on a 68000 from
repeatedly consuming the transfer window. Cursor updates continue normally
through the longer offscreen planet rendering work.

The planet workspace uses 2,884 bytes in single-height modes and 3,044 bytes in
double-height modes, within the existing 3,200-byte reservation. Surface shapes,
colours, seeded direction, 2–24 STATUS-hour flight periods, arrival orientation
and the accelerated F7 phase step are unchanged.

### Atari scanout transfer

Following the additional report of vertical F7 artifacts on Atari, its own
renderer received the same offscreen-composition and changed-group transfer
approach. It uses the ST video address counter, rather than Amiga registers,
to start below the globe and protect each destination row from Shifter reads.
All four interleaved plane words are transferred directly. The address fix
above remains in place, and the cursor's saved background is preserved.
The Atari planet workspace now uses 2,884 of its reserved 3,200 bytes.

Synchronization adds some F7 overhead. A short Steem sample of Lave measured
about 9.5 preview updates per second at 8 MHz, compared with about 12.4 using
the address-corrected but unsynchronized copy. This affects the F7 presentation
path; the flight renderer and STATUS-clock rotation calculation are unchanged.

### Final verification

All 18 Amiga release distributions were rebuilt and booted on private hidden
desktops: standard PAL, WIDE PAL/NTSC, PAL/NTSC HiRes, PAL/NTSC HiRes interlace,
and DblPAL/DblNTSC, each with both graphics sets. Non-doubled modes were also
stressed on a 68000; doubled modes used AGA and a 68020. Each distribution
passed 120 native display captures, with advancing rotation in the correct
direction and working F7 exit/re-entry. None of the 2,160 frames contained an
unexpected globe colour, including a second check covering 95% of its radius.

Both Atari distributions passed 200 native Hatari display captures each without
unexpected globe colours. The preceding unsynchronized Atari captures did not
reproduce the user's transient artifact in Hatari, so those captures alone do
not establish the original symptom's cause. The transfer now explicitly avoids
partially updated plane words during scanout. A separate private Steem session
confirmed that all 15 successive Lave globe captures still differ after this
presentation change.

All four standard distributions passed 218 native planet scenarios each.
Atari passed 184 cursor scenarios per distribution; Amiga passed 232, including
its general sprite fallback. Amiga additionally passed 150 native opaque-cursor
captures per graphics set. For every standard distribution, 46 flight and F7
framebuffers match the previous intended appearance byte for byte, and the
existing clock, silhouette and preview-boundary validations pass. Python tests
passed 35 Atari and 36 Amiga cases, with one existing skip per tree.

Final binaries, private test copies, native captures and verification reports
are under each tree's `build/planet-present-qa/release`. Release outputs and the
user's specified Atari disk are byte-identical to their tested copies. The
historical source archive and original-game tree were not changed.


## Shorter flight rotation periods (2026-10-29)

Both independent platform trees now select an integer rotation period from
30 through 120 STATUS-clock minutes, inclusive, replacing the previous
2..24-hour range. The same seeded value selects the period without consuming
another random number. Seeded direction, continent/crater geometry and initial
arrival orientation are unchanged. Flight phase still follows the saved STATUS
clock, and the accelerated F7 preview keeps its existing speed and direction.
The cached period is stored in minutes, so phase calculation no longer needs
an hours-to-minutes multiplication.

The standard `ELITE` and `ELITE_ALT` distributions were rebuilt for both
platforms. Each passed 218 native scenarios, including 1,456 exact phase checks
covering all 91 periods in both directions, full and quarter turns, sub-minute
positions and day boundaries. Per distribution, 168 framebuffer captures match
the preceding release byte for byte at equivalent rotation angles; the existing
F7 circle bounds, full-turn and opposite-direction comparisons also pass.
Python tests passed 35 Atari and 36 Amiga cases, with one existing skip each.
Emulator tests ran on verified private hidden desktops. Evidence is under each
tree's `build/planet-present-qa/period-minutes`. The four output disk images match
the tested copies, and the user's specified Atari `ELITE_ALT.ST` was updated
with a preserved backup under the Atari build directory.
