"""Synthesize a seamless deep engine hum for manual throttle input."""
import hashlib
import math


def generate_engine_audio(target):
    values = []
    for n in range(1024):
        t = math.tau*n/1024
        phase = 8*t + .08*math.sin(t)
        values.append((.68*math.sin(phase) + .22*math.sin(2*phase)
                       + .10*math.sin(3*phase))*(.94+.06*math.cos(t)))
    peak = max(map(abs, values))
    data = bytes(round(v*112/peak) & 255 for v in values)
    (target/'engine-loop.bin').write_bytes(data)
    (target/'engine-loop.inc').write_text('engine_sample_words equ 512\n', encoding='ascii')
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
