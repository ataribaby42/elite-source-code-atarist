"""Synthesize original seamless Paula loops for the two continuous lasers.

Only Python's standard library is required. These are new sounds, not samples
from Frontier or either original Elite release. Integer spectral bins keep the
waveform and its modulation periodic at the DMA loop boundary.
"""
import hashlib
import math
import random

PERIOD = 214
SAMPLES = 4096
PAL_CLOCK = 3546895


def waveform(military=False):
    rng = random.Random(0x68020 if military else 0x68000)
    noise = [(rng.randrange(110, 920), rng.random()*math.tau, rng.uniform(.002, .008))
             for _ in range(128)]
    carrier = 97 if military else 53
    values = []
    for n in range(SAMPLES):
        t = math.tau*n/SAMPLES
        phase = carrier*t + (.24 if military else .14)*math.sin(3*t)
        body = (.48*math.sin(phase) + .23*math.sin(2*phase + .4)
                + .14*math.sin(3*phase) + .08*math.sin(5*phase))
        body += .18*math.sin((carrier+1)*t + .35*math.sin(2*t))
        if military:
            body += .12*math.sin(7*phase) + .08*math.sin(11*phase)
        air = sum(gain*math.sin(freq*t+phase) for freq, phase, gain in noise)
        values.append(body*(.92+.08*math.cos(t)) + air*(1.3 if military else .75))
    mean = sum(values)/SAMPLES
    peak = max(abs(v-mean) for v in values)
    return bytes(round((v-mean)*112/peak) & 255 for v in values)


def generate_beam_audio(target):
    loops = [waveform(False), waveform(True)]
    data = b''.join(loops)
    (target/'beam-loops.bin').write_bytes(data)
    (target/'beam-loops.inc').write_text(
        '; Original synthesized continuous laser loops.\n'
        f'beam_audio_period equ {PERIOD}\n'
        f'beam_sample_bytes equ {SAMPLES}\n'
        f'beam_sample_words equ {SAMPLES//2}\n', encoding='ascii')
    return {'count': 2, 'bytes': len(data), 'period': PERIOD,
            'sample_rate': PAL_CLOCK/PERIOD,
            'sha256': hashlib.sha256(data).hexdigest()}
