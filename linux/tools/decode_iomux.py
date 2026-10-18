#!/usr/bin/env python3
"""Decode an IOMUXC dump (devmem output) against imx6sl-pinfunc.h."""
import re, sys
pinfunc, dump = sys.argv[1], sys.argv[2]
regs = {}
for l in open(dump):
    m = re.match(r'([0-9a-f]{8}): ([0-9a-f]{8})', l)
    if m:
        regs[int(m[1], 16) - 0x020E0000] = int(m[2], 16)
funcs = {}
for l in open(pinfunc):
    m = re.match(r'#define\s+MX6SL_PAD_(\w+?)__(\w+)\s+(0x\w+)\s+(0x\w+)\s+(0x\w+)\s+(0x\w+)\s+(0x\w+)', l)
    if m:
        pad, fn = m[1], m[2]
        mux, conf, inp, mode, val = (int(x, 16) for x in m.group(3, 4, 5, 6, 7))
        funcs.setdefault(mux, []).append((pad, fn, conf, inp, mode, val))
for mux in sorted(funcs):
    if mux not in regs:
        continue
    cur = regs[mux] & 7
    cands = [f for f in funcs[mux] if f[4] == cur]
    pick = None
    for f in cands:
        if f[3] == 0 or regs.get(f[3], -1) == f[5]:
            pick = f
            break
    if not pick and cands:
        pick = cands[0] + ('?',)
    pad = funcs[mux][0][0]
    conf = regs.get(funcs[mux][0][2], 0)
    sion = ' SION' if regs[mux] & 0x10 else ''
    fn = pick[1] if pick else f'ALT{cur}?'
    print(f'MX6SL_PAD_{pad}__{fn:<22s} 0x{conf:05x}{sion}')
