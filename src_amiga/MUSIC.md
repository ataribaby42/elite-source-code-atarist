# Original Amiga music

The Amiga build plays Wally Beben's four-channel arrangement of Johann Strauss II's Blue Danube from the supplied `resources/amiga/Elite 2.0.adf`. The same arrangement is used for the title animation, docking computer and Elite congratulations screen. It replaces the Atari note sequence and generated sine waveform. The arrangement loops after 9,480 PAL vertical blanks, approximately 189.6 seconds at 50 Hz.

## Extraction

`tools/amiga_assets.py` verifies the entire supplied ADF checksum before reading the original executable from its OFS file. It extracts data only; no original game executable or opaque replay binary is included in the new executable.

| Original location | Extracted data |
| --- | --- |
| Executable offset `0x68dcc` | Seven PCM instruments, 60,350 bytes; the preceding longword contains the byte length |
| Original address `$6954..$69b5` | Note period table |
| Original address `$69b6..$6adf` | Initial replay state |
| Original address `$6ae0..$6b1b` | Sample pointer table, rebuilt as relocatable references |
| Original address `$6b1c..$6bd3` | Instrument descriptors, envelopes and chord intervals |
| Original address `$6bd4..$6c83` | Four channel order lists and 40 pattern pointers, rebuilt as relocatable references |
| Original address `$6c84..$74f1` | Order and pattern bytes, 2,158 bytes |

Within the executable's game-code block, the file offset equals the original address plus `0x1cc`. PCM is a separate disk asset loaded at `$5a066` by the original game. The extractor validates instrument lengths, loop bounds and score references. Generated files stay under `build`; the original disk is never modified.

## Native replay and Paula output

`asm/music.m68` contains a relocatable assembly adaptation of the original replay routines at `$5f36..$6952`. It retains the original event timing, four independent channel streams, envelopes, sample attacks and loops, pitch slides, chords and vibrato. Three original writes into instruction immediates are replaced with ordinary variables. Executable code is never patched and can run with a 68020 instruction cache enabled.

The replay prepares channel state once per PAL VBL. `asm/sounds.m68` commits that state to Paula. Sample data is allocated in the existing `amiga_audio` Chip RAM section; score data and replay variables do not require Chip RAM. The seven music instruments add 60,350 bytes of sample storage. The existing 19 effect samples remain separate.

When stopping or restarting an active channel, playback sets volume to zero and waits for the sample clock to latch it before disabling DMA. Fresh attacks are programmed before DMA starts. Loop addresses and lengths are installed only after at least two scanlines have elapsed, allowing Paula to fetch the attack first. The conservative shutdown delay covers the score's maximum period of 1,712. Fade-out lasts 32 VBLs and scales each channel's current envelope, preserving silent rests. Full shutdown clears all four volumes and disables audio DMA; effects become available again afterward.

## Validation

The former CPU-emulation test suite has been removed. Build and file-format
checks remain available through the normal build and `tests/` discovery.
Gameplay validation requires WinUAE or original hardware.

Listen through a complete arrangement and restart, exercise docking music and sound effects, and verify fades and silence after stopping. Asset extraction and bounds are covered by `tests/test_amiga.py`; earlier recordings in `build/audio-qa` predate the current replay and do not validate its audible quality.

