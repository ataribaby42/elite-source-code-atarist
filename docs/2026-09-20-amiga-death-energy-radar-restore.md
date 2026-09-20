# Amiga energy-bank corruption during Game Over

## Cause

The main radar saves two adjacent 16-pixel words from each bitplane for every
trace row. Near the right edge of the scanner, these saved words extend into
the left edge of the energy bars, even though the trace itself does not.

`remove_radar` restored a screen's saved-background chain without clearing
`last1_ptr` or `last2_ptr`. Normal flight replaces that pointer at the end of
each frame. The death, hyperspace and docking effect loops do not draw new
radar traces or publish a replacement chain, so they could restore the same
obsolete background repeatedly.

`end_game` resets energy and redraws the instruments once per screen. On the
following visit to that screen, the stale radar background could overwrite
part of an energy bar. Different saved backgrounds in the two alternating
screens make the damage flicker. Whether it happens depends on radar contact
positions and the previous instrument contents.

## Fix

In `src_amiga/asm/radar.m68`, clear the selected screen's saved-chain pointer
immediately after loading it into A0. Restore that chain in the existing reverse
order. The other screen keeps its pending restore. New radar drawing still
builds a fresh chain and normal flight publishes it as before.

This consumes each background exactly once, matching the existing sprite
background lifetime. The change adds two `clr.l` instructions and does not
change radar geometry, energy values or AI logic.

The Atari and preserved original sources contain the same pointer-lifetime
pattern. The Atari version received the same fix in the follow-up below;
the preserved original source remains unchanged.

## Verification

The pre-fix and fixed Amiga executables were exercised in WinUAE with an OCS
68000, Kickstart 1.3, 512 KB Chip RAM and 512 KB slow RAM. Every instance used a
verified private hidden Windows desktop and private executable, configuration
and disk copies under `src_amiga/build/death-energy-qa`.

A native test called the actual game routines with energy 24 and a radar
contact at `(24000, 0, -12288)`. Its trace starts at screen `(219, 178)` and
saves columns 208–239. After the death transition refreshed the instruments,
the original code restored 18 black pixels at x=231–239, y=177–178 on one
screen only: the same position and shape as the reported artifact.

The fixed code passed repeated removal, overlapping trace restoration,
independent screen handling, fresh trace redraw/restoration on both screens,
and three death-style instrument passes without changing any screen pixels
after the initial instrument refresh.

The full `end_game` routine also completed with a pending edge trace. All four
energy banks stayed intact in 38 samples of both screen buffers after their
initial instrument updates. A WinUAE display screenshot was captured during
the animation.

The build completed successfully with `noprotect=yes commander=default
laser=singlebeam aifiresound=no scannerlogo=no altgfx=no outputname=ELITE`.
Native test scripts, dumps and reports remain under the platform build
directory.

## Atari follow-up

The same two pointer clears were added independently to
`src_atari/asm/radar.m68`. Atari's interleaved bitplane storage differs from
Amiga's, but the saved-background lifetime and overlap with the energy bars
are the same.

The original and fixed Atari builds were tested in Hatari, configured as an
ST with TOS 1.04 and 2 MB RAM, on a verified private hidden Windows desktop.
The emulator executable, configuration and disk copies were kept under
`src_atari/build/death-energy-qa`.

The original build reproduced the same 18-pixel overwrite at x=231–239,
y=177–178 on one buffer. The fixed build preserved both buffers across
repeated removal, overlapping trace restoration, fresh radar drawing and
three death-style instrument passes. Both complete `end_game` runs provided
39 samples after the initial updates of both energy displays: the original
showed corruption, while every fixed-build sample kept all four banks intact.

Both Atari graphics variants were rebuilt as `output_atari/ELITE.ST` and
`output_atari/ELITE_ALT.ST`. Native test scripts, RAM dumps, screenshots and
before/after reports remain under `src_atari/build/death-energy-qa`.
