# Planet flight colours

The enhanced Atari and Amiga versions now colour the flight planet from its
Planet Data image. Previously, `draw_point` always used `drk_green`.

## Selection

Each source tree stores a precomputed `assets/PLANET_COL.BIN`. Normal builds only
embed that file; they do not run the colour generator. To deliberately refresh
the table after changing the texture or palettes, run that tree's
`tools/planet_colours.py` directly. The maintenance tool decodes
`assets/TEXTURE.PC1`, reads the UI and cockpit palettes, and reads the inhabitant
palette and description grammar from that tree's assembly source.

The generator reproduces the galaxy seed progression, the four name-generation
steps, and the description's random-name side effects before selecting the
texture centre. It counts the exact 5,145 pixels in the radius-40 midpoint circle
used by `pdata.m68`. The original Planet Data renderer and descriptions are
unchanged. Flight colours always use the normal planet description. Mission
`$41` can change the UI texture crop by skipping the usual description RNG work,
but it no longer changes a planet's saved flight colour.

Palette indices 0 and 13 do not vote, excluding transparency and black. Other
RGB-black entries are also ignored. Votes from similar hues are combined; the
most frequent shade within the winning hue is mapped to the closest cockpit RGB
entry. UI brown at index 14 participates in voting and, when selected, maps
directly to steady red at index 6. The pulsing cockpit index 14 cannot be a
destination. Yellow results at index 5 become orange at index 3, reserving
yellow for the sun. Black, dark grey, and an empty vote all produce light grey.
Ties use stable palette-index order.

Both platforms evaluate their actual runtime colour values. In particular,
Amiga imports PC1 palettes into the full OCS range, while the existing inhabitant
routine writes its table words directly into the native runtime palette. This
change does not modify either palette-loading behaviour.

## Runtime

`assets/PLANET_COL.BIN` contains exactly 2,048 one-byte entries: eight galaxies
with 256 systems each. It is included in `special.m68`. There is no second table
for missions or galaxy seeds.

After creating a planet, `create_system` and `launch_system` call
`set_planet_colour` and store the selected index in the existing `obj_colour`
field. The byte offset is `galaxy_no * 256 + current`, using zero-based galaxy
and planet indices. Invalid galaxy or system indices use light grey.

The launch animation also uses this lookup for the planet visible at the tunnel
exit. That rectangle is the separate `panel7` model, created before
`launch_system`; its original material always rendered dark green. After
`create_object` initializes the exit, `launch_tunnel` assigns the current
planet's colour and translates the palette index to the corresponding solid
material in `vector.m68`'s `panel_colours` table. Polygon material numbers are
different from palette indices. Only the exit receives this override, and both
the full hangar sequence and the shortened launch use the same path.

The lookup preserves registers and does not change RNG state or palette entries.
No object or commander record is enlarged. The flight renderer also guards
against indices 0, 2, 13, 14 and invalid values, replacing them with light grey.
The sun and other objects retain their existing rendering paths. `src_orig` and
the historical archive are unchanged.

## Validation

Unit tests cover all 2,048 entries, equality of the saved table to a deliberate
recalculation, Lave's crop and colour, shade grouping, description side effects,
excluded source colours, the grey fallback, yellow-to-orange mapping and
UI-brown-to-steady-red mapping.

The compact implementation passed native checks in Hatari PAL ST / TOS 1.04 and
WinUAE OCS / A500, Kickstart 1.3, with 512 KB Chip RAM plus 512 KB slow RAM. Each
platform checked all 2,048 saved entries twice, under normal mission state and
mission `$41`, and confirmed four invalid galaxy/system index combinations use
light grey. Eighteen Planet Data cases per platform matched all 92,610 sampled
pixels, including description RNG edge cases and all eight galaxies. Both
planet-creation paths and five renderer fallback cases also passed. These native
checks preceded the subsequent yellow and UI-brown remapping in the maintenance
tool and saved tables; the runtime lookup and renderer are unchanged. Emulators
ran only on owned, verified hidden Windows desktops with private test copies.

After adding the yellow and UI-brown remapping rules, the complete unit suites
passed 32 Atari and 30 Amiga tests. One historical bitmap-identity test in each
suite was skipped because the user's PNG sources have been customized. Explicit
regeneration left both existing 2,048-byte tables byte-identical: the new rules
do not change any current planet's saved colour. The default and `altgfx=yes`
disk images already built for the compact implementation therefore retain the
same embedded tables. Final build intermediates and generated assets use default
`gfx`.

The launch-exit correction passed native rendering checks for every colour in
each saved table: ten Atari colours and eight Amiga colours, each compared with
the flight planet (36 render checks in total). The checks also confirmed that
the other eight tunnel objects retained their original materials. Full and
shortened launches completed on both platforms. These checks used Hatari and
WinUAE A500 / OCS / Kickstart 1.3 on verified private hidden desktops. Both
default and alternative graphics distributions were rebuilt.
