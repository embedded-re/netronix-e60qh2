#!/usr/bin/env python3
"""Decode an i.MX EPDC waveform (.fw = E Ink WBF header + TRT + data)."""
import struct, sys
d = open(sys.argv[1], 'rb').read()
h = d[:48]
chk, fsize, serial = struct.unpack_from('<III', h, 0)
run_type, fpl_platform, fpl_lot = h[12], h[13], struct.unpack_from('<H', h, 14)[0]
mode_version, wf_version, wf_subversion, wf_type = h[16], h[17], h[18], h[19]
fpl_size, mfg_code, wf_tuning, fpl_rate = h[20], h[21], h[22], h[23]
xwia = int.from_bytes(h[28:31], 'little'); cs1 = h[31]
wmta = int.from_bytes(h[32:35], 'little'); fvsn = h[35]
luts, mc, trc = h[36], h[37], h[38]
eb, sb = h[40], h[41]
print(f'file size {len(d)}  hdr.filesize 0x{fsize:x}  serial {serial}')
print(f'run_type 0x{run_type:02x} fpl_platform 0x{fpl_platform:02x} fpl_lot {fpl_lot}')
print(f'mode_version 0x{mode_version:02x}  wf_version {wf_version}.{wf_subversion}  wf_type 0x{wf_type:02x}')
print(f'fpl_size 0x{fpl_size:02x} mfg_code 0x{mfg_code:02x} tuning 0x{wf_tuning:02x} fpl_rate 0x{fpl_rate:02x} ({fpl_rate} Hz?)')
print(f'xwia 0x{xwia:06x} cs1 0x{cs1:02x} wmta 0x{wmta:06x} fvsn {fvsn}')
print(f'luts 0x{luts:02x} ({"5-bit" if luts & 0xc == 4 else "4-bit"})  modes(mc+1) {mc + 1}  temp ranges(trc+1) {trc + 1}  eb {eb} sb {sb}')
trt = d[48:48 + trc + 2]
print('temperature bounds (C):', list(trt))
