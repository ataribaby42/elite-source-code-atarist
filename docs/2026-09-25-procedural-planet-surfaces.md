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

The new workspace reserves 3,200 bytes per platform and does not enlarge object
or commander records. Geometry is generated at system creation, not every frame.

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
