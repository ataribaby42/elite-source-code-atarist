# Stable AI laser colours during flight

Both enhanced versions cache the normal AI laser colour when leaving a station
or completing a hyperspace jump. Normal and galactic hyperspace share the same
completion path, including witch-space arrivals.

Previously, `draw_ai_laser` chose a colour from the player's current rating on
every draw. Crossing a rating threshold during combat could therefore change
the colour of existing ships' beams. The renderer now reads `ai_laser_colour`
from the reserved local variable area in `special.m68`. Newly spawned ships use
the same cached colour as ships already present.

`init_ai_laser_colour` records the existing rating bands: red for Harmless
through Poor, orange for Average through Competent, and white for Dangerous
through Elite. The initializer preserves general registers and does not use the
random-number generator. `launch` calls it after resetting flight state;
`hyperspace` calls it after the common arrival reset. Switching views, opening
menus, drawing beams, and the reset at the start of the hyperspace animation do
not refresh the colour.

Constrictor beams remain white, and Thargoid/Thargon beams remain light blue.
Damage calculations, targeting, firing cadence, player lasers, commander saves,
object records, and the preserved original version are unchanged.

Native regression diagnostics are under each enhanced tree's
`build/ai-laser-colour-qa` directory. They exercise all nine initial ratings
against all nine live ratings and five ship types, plus actual station launch,
normal hyperspace, galactic hyperspace, and forced witch-space arrival. Tests
run only on verified private hidden Windows desktops.

Both Hatari and WinUAE A500 / OCS / Kickstart 1.3 passed all 14 scenarios,
including 405 beam-colour selections per platform and complete launch/jump
sequences. Initializing the cache also preserved D0 and the RNG seed. Both
default and alternative graphics distributions were rebuilt successfully.
