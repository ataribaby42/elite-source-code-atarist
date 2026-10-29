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
colour without stippling or alternating rows. Eight regions or twelve craters
are spread around the sphere. Each crater has eight rim vertices and four rays.
Ray extensions vary from half to the full rim radius, with independent angular
deflections between -10 and +10 degrees.

Details start at a projected radius of 12 logical pixels, approximately a
24-pixel diameter. The Amiga threshold follows vertical display scaling, and
horizontal projection follows the native circle stretch in HIRES. Below the
threshold the existing circle renderer runs without surface transformations.

## Options and Planet Data

The row above Reset Game / Exit Program in Options contains `Planets: ON / OFF`.
ON enables surface markings in flight and a rendered Planet Data portrait at zero rotation. The
portrait uses the selected system's seed and the existing galaxy/planet colour
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
caches only that system's geometry, independent of the gameplay random state.
The map is regenerated after hyperspace and on launch, with no save-file layout changes.

Hyperspace creation and station launch with Planets ON call `turn_planet_surface`. It samples the
existing random state without advancing it and chooses one of 64 longitudes
(5.625-degree steps) around the vertical axis. This simulates rotation while
away or docked; it does not regenerate geography or animate rotation during the visit.
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

The renderer first transforms only Z for all thirteen vertices of a feature.
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
