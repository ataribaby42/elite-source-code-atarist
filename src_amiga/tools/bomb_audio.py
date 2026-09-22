"""Render the ST energy bomb's rising noise and swept decay for Paula."""
import hashlib
import math

PERIOD = 428
PAL_CLOCK = 3546895
NTSC_CLOCK = 3579545
EFFECT_TICKS = 107
OVERSAMPLE = 16


def generate_bomb_audio(target):
    # FX_BANG raises the 4-bit volume every two PAL ticks. After tick 32,
    # DO_BOMB cycles the noise period 5..1 and fades every five ticks.
    # Keep the generator local to this tree and independent of gameplay RNG.
    rate = PAL_CLOCK / PERIOD
    count = math.ceil((EFFECT_TICKS + 4) * rate / 50)
    count += count & 1
    data = bytearray()
    lfsr, phase = 0x1FFFF, 0.0
    for n in range(count):
        tick = int(n * 50 / rate)
        if tick >= EFFECT_TICKS:
            data.append(0)  # silence before VBL stops DMA; never loop the attack
            continue
        if tick <= 32:
            volume = max(0, tick // 2 - 1)
            noise_period = 18
        else:
            volume = 15 - max(0, (tick - 37) // 5)
            noise_period = 5 - (tick - 33) % 5
        gain = 0 if volume == 0 else 2 ** ((volume - 15) / 2)
        step = 2000000 / (16 * noise_period * rate * OVERSAMPLE)
        total = 0
        for _ in range(OVERSAMPLE):
            phase += step
            while phase >= 1:
                lfsr = (lfsr >> 1) | (((lfsr ^ (lfsr >> 3)) & 1) << 16)
                phase -= 1
            total += 1 if lfsr & 1 else -1
        data.append(round(total * 112 * gain / OVERSAMPLE) & 255)
    (target/'bomb-sample.bin').write_bytes(data)
    # PAL/NTSC run the same recorded effect for its full duration. The extra
    # silent PCM tail keeps hardware looping harmless before the stop tick.
    pal_ticks = EFFECT_TICKS + 2
    ntsc_ticks = math.ceil(pal_ticks * 60 / 50 * PAL_CLOCK / NTSC_CLOCK)
    (target/'bomb-sample.inc').write_text(
        f'bomb_audio_period equ {PERIOD}\nbomb_sample_bytes equ {count}\n'
        f'    ifne display_ntsc\nbomb_audio_ticks equ {ntsc_ticks}\n'
        f'    else\nbomb_audio_ticks equ {pal_ticks}\n    endc\n',
        encoding='ascii')
    return {'bytes': count, 'period': PERIOD, 'pal_ticks': pal_ticks,
            'ntsc_ticks': ntsc_ticks,
            'sha256': hashlib.sha256(data).hexdigest()}
