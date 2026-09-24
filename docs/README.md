# Documentation

Design documents and implementation plans for the enhanced Atari and Amiga
builds. `src_orig` preserves the original game and is never the subject of one.

| Document | Purpose |
| --- | --- |
| [2026-09-24-unused-cobra-bitmap.md](2026-09-24-unused-cobra-bitmap.md) | Remove the unused panel Cobra from the generated bitmap bank and RAM while preserving its PNG artwork and all other bitmap IDs |
| [2026-09-24-runtime-ship-images.md](2026-09-24-runtime-ship-images.md) | Current ship graphics: runtime rendering, fixed image sizes, isolated memory buffers, archived PNGs and measured savings on both platforms |
| [2026-09-24-player-shipyards.md](2026-09-24-player-shipyards.md) | Ship purchasing, equipment resale, hull statistics, combat balance and saved commanders |
| [2026-09-24-shipyards-regression-check.md](2026-09-24-shipyards-regression-check.md) | Historical validation of the initial Shipyards integration and menu controls before runtime ship rendering |
| [2026-09-24-death-and-ship-screen-fixes.md](2026-09-24-death-and-ship-screen-fixes.md) | Station clipping overflow, death flashing, purchase confirmation and ship image placement fixes |
| [2026-09-24-viewport-rendering-bounds.md](2026-09-24-viewport-rendering-bounds.md) | General polygon, line and flight-text bounds checks across Atari and Amiga display modes |
| [2026-09-23-amiga-ship-atlases.md](2026-09-23-amiga-ship-atlases.md) | Archived PNG atlas reference: original dimensions, camera views, palette and tile order; superseded by runtime rendering |
| [2026-09-21-random-encounter-spawn-range-audit.md](2026-09-21-random-encounter-spawn-range-audit.md) | Fix: reserve space for encounter formations so all eight templates start inside scanner range |
| [2026-09-21-random-encounter-torus-routing.md](2026-09-21-random-encounter-torus-routing.md) | Fix: apply the 50% encounter substitution to both timed waves and torus interruptions, preserving mission spawns |
| [2026-09-20-convoy-spawn-regression-checks.md](2026-09-20-convoy-spawn-regression-checks.md) | Validation: existing spawn paths, missions, missiles, cargo and object-slot reuse after adding trader convoys |
| [2026-09-20-trader-convoy-encounters.md](2026-09-20-trader-convoy-encounters.md) | Change: weight-2 trader convoys keep a shared cruise speed until combat; fix government filtering after the random roll |
| [2026-09-20-patrol-police-record-checks.md](2026-09-20-patrol-police-record-checks.md) | Change: random Viper patrols inspect changing legal status using the existing police-response probability |
| [2026-09-17-faction-ai-targeting-design.md](2026-09-17-faction-ai-targeting-design.md) | Design: ships attack the nearest hostile ship of another faction, with the player as one ordinary candidate |
| [2026-09-17-faction-ai-targeting-plan.md](2026-09-17-faction-ai-targeting-plan.md) | The implementation plan for that design, task by task, including the follow-ups |
| [2026-09-17-ecm-wave-timing-design.md](2026-09-17-ecm-wave-timing-design.md) | Design: the ECM wave is timed rather than tied to the ECM sound, which had left it dead on the Amiga |
| [2026-09-17-random-encounter-design.md](2026-09-17-random-encounter-design.md) | Design: deep space also produces small groups that are already fighting each other, beside the existing pirate ambush |
| [2026-09-17-random-encounter-plan.md](2026-09-17-random-encounter-plan.md) | The implementation plan for that design, task by task |
| [2026-09-17-title-screen-draw-order.md](2026-09-17-title-screen-draw-order.md) | Fix: the attract screen drew the rotating ship over its captions instead of behind them |
| [2026-09-17-thargon-dormancy-on-mother-death.md](2026-09-17-thargon-dormancy-on-mother-death.md) | Fix: a Thargoid killed by a missile or by another ship left its Thargons fighting on instead of dormant |
| [2026-09-19-mass-lock-snapshot-analysis.md](2026-09-19-mass-lock-snapshot-analysis.md) | Diagnosis: an abandoned Anaconda outside scanner range permanently blocked torus |
| [2026-09-19-abandoned-hull-mass-lock-fix.md](2026-09-19-abandoned-hull-mass-lock-fix.md) | Fix: remove distant abandoned hulls through the existing missile and object cleanup paths |
| [2026-09-19-missile-scanner-range-cleanup.md](2026-09-19-missile-scanner-range-cleanup.md) | Change: discard player and NPC missiles beyond the fixed scanner range |
| [2026-09-19-editable-png-graphics.md](2026-09-19-editable-png-graphics.md) | Editable graphics, exact RGB-to-index palette mapping, source sheets and build conversion |
| [2026-09-20-amiga-wide-and-multi-mode-support.md](2026-09-20-amiga-wide-and-multi-mode-support.md) | Six Amiga screens from one source tree, the frameless flight view and the framed option |
| [2026-09-21-amiga-fastdraw.md](2026-09-21-amiga-fastdraw.md) | Taking the flight view off the chip bus: the blitter on a 68000, a Fast RAM shadow above it |
| [2026-09-23-amiga-shadow-transfer.md](2026-09-23-amiga-shadow-transfer.md) | The Fast RAM shadow carries only the pieces that changed, and what `shadowcopy` shows on the frame time line |

Each tree's own `README.md` describes the shipped behaviour; these documents
record why it is the way it is.
