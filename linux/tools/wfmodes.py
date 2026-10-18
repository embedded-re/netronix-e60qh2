#!/usr/bin/env python3
"""Fingerprint the modes of an i.MX EPDC waveform (.fw).

Layout after the 48-byte header + TRT (+1 checksum byte), as consumed by the
EPDC hardware: u64 mode_offsets[mc+1]; at each mode: u64 temp_offsets[trc+1];
at each temp: u64 nframes, then nframes frames of 32x32 2-bit entries
(5-bit LUT, 256 B/frame; 4-bit: 16x16 = 64 B). Entry value per frame:
0 = no-op, 1 = drive to black, 2 = drive to white, 3 = end/no-op.
Index order inside a frame is [new][old] or [old][new] - we report both.
"""
import struct, sys
d = open(sys.argv[1], 'rb').read()
luts, mc, trc = d[36], d[37] + 1, d[38] + 1
bits5 = (luts & 0xc) == 4
n = 32 if bits5 else 16
fb = n * n // 4
base = 48 + trc + 1
w = d[base:]
u64 = lambda o: struct.unpack_from('<Q', w, o)[0]
mode_offs = [u64(8 * i) for i in range(mc)]
print('mode offsets:', [hex(x) for x in mode_offs])
tidx = int(sys.argv[2]) if len(sys.argv) > 2 else 7   # 21-24 C range
for m, mo in enumerate(mode_offs):
    toffs = [u64(mo + 8 * t) for t in range(trc)]
    frames = []
    for to in toffs:
        frames.append(u64(to))
    to = toffs[tidx]
    nf = u64(to)
    fr = w[to + 8: to + 8 + nf * fb]
    # decode entries for the chosen temperature
    def ent(f, a, b):
        i = a * n + b
        byte = fr[f * fb + i // 4]
        return (byte >> (2 * (i % 4))) & 3
    # which (a,b) pairs ever get driven
    driven = set()
    targets_b, targets_a = set(), set()
    for f in range(nf):
        for a in range(0, n, 2 if bits5 else 1):
            for b in range(0, n, 2 if bits5 else 1):
                if ent(f, a, b) in (1, 2):
                    driven.add((a, b))
    gl = (lambda v: v // 2) if bits5 else (lambda v: v)
    print(f'mode {m}: frames per temp {frames}')
    a_vals = sorted({gl(a) for a, b in driven}); b_vals = sorted({gl(b) for a, b in driven})
    print(f'   @temp{tidx}: {nf} frames, {len(driven)} driven pairs; idx-A levels {a_vals}; idx-B levels {b_vals}')
