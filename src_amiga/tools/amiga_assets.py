"""Read the supplied Amiga disk; recover original effects and music assets."""
import hashlib
from pathlib import Path
import struct

ADF_HASH = '3ef395dc1d73c86f7a8486329a24d2ced29b5c6b108df3da6cae1380b5666ee3'


def be32(data, offset=0):
    return struct.unpack_from('>I', data, offset)[0]


def ofs_file(image, header):
    def block(number):
        if not 0 <= number < len(image) // 512:
            raise ValueError('OFS block outside disk')
        return image[number * 512:(number + 1) * 512]
    head = block(header)
    number, chunks, seen = be32(head, 16), [], set()
    while number:
        if number in seen:
            raise ValueError('Cyclic OFS file')
        seen.add(number)
        data = block(number)
        if (be32(data) != 8 or be32(data, 4) != header or
                be32(data, 8) != len(chunks) + 1 or be32(data, 12) > 488 or
                sum(struct.unpack('>128I', data)) & 0xffffffff):
            raise ValueError('Invalid OFS data block')
        chunks.append(data[24:24 + be32(data, 12)])
        number = be32(data, 16)
    result = b''.join(chunks)
    if len(result) != be32(head, 324):
        raise ValueError('Truncated OFS file')
    return result


def extract_assets(adf: Path, target: Path):
    image = adf.read_bytes()
    if hashlib.sha256(image).hexdigest() != ADF_HASH:
        raise ValueError('Expected the supplied resources/amiga/Elite 2.0.adf; its checksum differs')
    game = ofs_file(image, 887)
    lengths = struct.unpack_from('>19H', game, 0x60d0)
    if sum(lengths) != 53908:
        raise ValueError('Unexpected Amiga sample bank')
    samples = game[0x5b1cc:0x5b1cc + sum(lengths)]
    # The original player uses eight-byte descriptors and a 16-note period table.
    descriptors = game[0x5fe4:0x5fe4+19*8]
    periods = struct.unpack_from('>16H', game, 0x5f5a)
    if any(descriptors[n*8] != n for n in range(19)):
        raise ValueError('Unexpected Amiga effect descriptors')
    (target / 'amiga-samples.bin').write_bytes(samples)
    offsets, position = [], 0
    for length in lengths:
        offsets.append(position)
        position += length
    (target / 'amiga-samples.inc').write_text(
        '; Original Amiga PCM samples: Wally Beben. Offsets and byte lengths.\n'
        'amiga_sample_offsets:\n    dc.l ' + ','.join(map(str, offsets)) + '\n'
        'amiga_sample_lengths:\n    dc.w ' + ','.join(map(str, lengths)) + '\n'
        'amiga_effect_descriptors:\n    dc.b ' + ','.join(map(str, descriptors)) + '\n'
        'amiga_effect_periods:\n    dc.w ' + ','.join(map(str, periods)) + '\n', encoding='ascii')
    music = extract_music(game, target)
    return image[:1024], {'adf_sha256': ADF_HASH, 'sample_count': len(lengths),
                          'sample_bytes': len(samples), 'sample_sha256': hashlib.sha256(samples).hexdigest(),
                          'music': music}


def extract_music(game, target):
    """Recover Wally Beben's four-channel Blue Danube score and seven instruments.

    The disk loader copies game[0x5cc:] to $400. Music PCM is a separate
    length-prefixed disk asset, loaded at $5a066 in the original game.
    Only data is extracted; the relocatable replay source lives in music.m68.
    """
    bias = 0x1cc
    def region(start, end):
        return game[start+bias:end+bias]

    pcm_size = be32(game, 0x68dc8)
    if pcm_size != 60350:
        raise ValueError('Unexpected Amiga music sample bank')
    pcm = game[0x68dcc:0x68dcc+pcm_size]
    pointers = struct.unpack('>15I', region(0x6ae0, 0x6b1c))
    lengths = [struct.unpack_from('>H', region(0x6b1c, 0x6b54), i*8+2)[0]
               for i in range(7)]
    offsets = [p-0x5a066 for p in pointers[:7]]
    if (offsets != [0, 8900, 18600, 27100, 36800, 46700, 56100] or
            sum(lengths) != pcm_size or any(p != 0x68c24 for p in pointers[7:])):
        raise ValueError('Unexpected Amiga music instruments')
    for i, offset in enumerate(offsets):
        desc = region(0x6b1c+i*8, 0x6b24+i*8)
        sample, looping, length, loop_start, loop_length = struct.unpack('>BBHHH', desc)
        if (sample != i or looping not in (0, 1) or
                offset+length > pcm_size or loop_start+loop_length > length):
            raise ValueError('Amiga music loop exceeds its instrument')
    orders = struct.unpack('>4I', region(0x6bd4, 0x6be4))
    patterns = struct.unpack('>40I', region(0x6be4, 0x6c84))
    if orders != (0x6c84, 0x6c95, 0x6ca6, 0x6cb7):
        raise ValueError('Unexpected Amiga music orders')
    if any(not 0x6cc8 <= p < 0x74f1 for p in patterns):
        raise ValueError('Amiga music pattern outside score')
    score = region(0x6c84, 0x74f2)
    (target/'amiga-music-samples.bin').write_bytes(pcm)
    (target/'amiga-music-score.bin').write_bytes(score)
    lines = ['; Original Amiga music data: Wally Beben. Extracted from Elite 2.0.']
    def bytes_table(label, data):
        lines.append(label+':')
        for i in range(0, len(data), 16):
            lines.append('    dc.b '+','.join(f'${v:02x}' for v in data[i:i+16]))
        lines.append('    even')
    bytes_table('wb_period_table', region(0x6954, 0x69b6))
    bytes_table('wb_initial_state', region(0x69b6, 0x6ae0))
    lines += ['wb_sample_pointers:', '    dc.l '+','.join(
        ['wb_samples+'+str(o) for o in offsets]+['wb_silence']*8)]
    bytes_table('wb_sample_defs', region(0x6b1c, 0x6b54))
    bytes_table('wb_envelopes', region(0x6b54, 0x6bc4))
    bytes_table('wb_chord_notes', region(0x6bc4, 0x6bd4))
    for label, values in [('wb_orders', orders), ('wb_patterns', patterns)]:
        lines += [label+':', '    dc.l '+','.join('wb_score+'+str(v-0x6c84) for v in values)]
    lines += ['wb_score:', '    incbin "amiga-music-score.bin"', '    even']
    (target/'amiga-music.inc').write_text('\n'.join(lines)+'\n', encoding='ascii')
    return {'track_count': 1, 'channels': 4, 'instrument_count': 7,
            'pattern_count': len(patterns), 'sample_bytes': len(pcm),
            'sample_sha256': hashlib.sha256(pcm).hexdigest(),
            'score_bytes': len(score), 'score_sha256': hashlib.sha256(score).hexdigest()}
