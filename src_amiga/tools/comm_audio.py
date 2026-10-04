"""Create a single short Paula notification in the identification tone's range."""
import hashlib
import math

PERIOD = 404
PAL_CLOCK = 3546895
NTSC_CLOCK = 3579545
FREQUENCY = 740
TONE_SECONDS = .100
SAMPLE_SECONDS = .180
PAL_TICKS = 6
NTSC_TICKS = 8


def generate_comm_audio(target):
    rate = PAL_CLOCK / PERIOD
    count = math.ceil(SAMPLE_SECONDS * rate)
    count += count & 1
    data = bytearray(count)
    for n in range(math.ceil(TONE_SECONDS * rate)):
        t = n / rate
        gain = min(1.0, t / .004, (TONE_SECONDS - t) / .012)
        phase = math.tau * FREQUENCY * t
        tone = math.sin(phase) + .12 * math.sin(2 * phase) + .06 * math.sin(3 * phase)
        data[n] = round(90 * gain * tone) & 255
    # The silent tail lasts beyond the VBL stop on PAL and NTSC, so DMA never
    # repeats the audible part. The short attack/release avoids boundary clicks.
    (target/'comm-sample.bin').write_bytes(data)
    (target/'comm-sample.inc').write_text(
        f'comm_audio_period equ {PERIOD}\ncomm_sample_bytes equ {count}\n'
        f'    ifne display_ntsc\ncomm_audio_ticks equ {NTSC_TICKS}\n'
        f'    else\ncomm_audio_ticks equ {PAL_TICKS}\n    endc\n', encoding='ascii')
    return {'bytes': count, 'period': PERIOD, 'frequency': FREQUENCY,
            'tone_seconds': TONE_SECONDS, 'pal_ticks': PAL_TICKS,
            'ntsc_ticks': NTSC_TICKS, 'sha256': hashlib.sha256(data).hexdigest()}
