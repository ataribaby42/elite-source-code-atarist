# Documentation

Design documents and implementation plans for the enhanced Atari and Amiga
builds. `src_orig` preserves the original game and is never the subject of one.

| Document | Purpose |
| --- | --- |
| [2026-09-17-faction-ai-targeting-design.md](2026-09-17-faction-ai-targeting-design.md) | Design: ships attack the nearest hostile ship of another faction, with the player as one ordinary candidate |
| [2026-09-17-faction-ai-targeting-plan.md](2026-09-17-faction-ai-targeting-plan.md) | The implementation plan for that design, task by task, including the follow-ups |
| [2026-09-17-ecm-wave-timing-design.md](2026-09-17-ecm-wave-timing-design.md) | Design: the ECM wave is timed rather than tied to the ECM sound, which had left it dead on the Amiga |
| [2026-09-17-random-encounter-design.md](2026-09-17-random-encounter-design.md) | Design: deep space also produces small groups that are already fighting each other, beside the existing pirate ambush |
| [2026-09-17-random-encounter-plan.md](2026-09-17-random-encounter-plan.md) | The implementation plan for that design, task by task |
| [2026-09-17-title-screen-draw-order.md](2026-09-17-title-screen-draw-order.md) | Fix: the attract screen drew the rotating ship over its captions instead of behind them |
| [2026-09-17-thargon-dormancy-on-mother-death.md](2026-09-17-thargon-dormancy-on-mother-death.md) | Fix: a Thargoid killed by a missile or by another ship left its Thargons fighting on instead of dormant |

Each tree's own `README.md` describes the shipped behaviour; these documents
record why it is the way it is.
