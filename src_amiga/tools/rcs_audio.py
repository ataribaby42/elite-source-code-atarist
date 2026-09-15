"""Generate a quiet, periodic filtered-noise RCS loop for Paula."""
import hashlib
import random

PERIOD = 214
SAMPLES = 4096


def generate_rcs_audio(target):
    rng = random.Random(0x524353)
    noise = [rng.uniform(-1, 1) for _ in range(SAMPLES)]
    values = [.65*v + .25*noise[n-1] + .10*noise[n-2]
              for n, v in enumerate(noise)]
    mean = sum(values)/SAMPLES
    peak = max(abs(v-mean) for v in values)
    data = bytes(round((v-mean)*112/peak) & 255 for v in values)
    (target/'rcs-loop.bin').write_bytes(data)
    (target/'rcs-loop.inc').write_text(
        f'rcs_audio_period equ {PERIOD}\nrcs_sample_words equ {SAMPLES//2}\n',
        encoding='ascii')
    return {'bytes': len(data), 'period': PERIOD,
            'sha256': hashlib.sha256(data).hexdigest()}
