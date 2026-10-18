#!/usr/bin/env python3
"""Build a legacy U-Boot uImage (kernel, uncompressed payload) from
zImage + appended DTB, for the stock Netronix U-Boot 2009.08 `bootm`.

  mkuimage.py zImage board.dtb out.uImage [load_addr]
"""
import struct, sys, time, zlib

zimg, dtb, out = sys.argv[1:4]
load = int(sys.argv[4], 0) if len(sys.argv) > 4 else 0x80808000

data = open(zimg, 'rb').read()
data += b'\0' * (-len(data) % 4)
data += open(dtb, 'rb').read()

name = b'Linux E60QH2'.ljust(32, b'\0')
dcrc = zlib.crc32(data) & 0xffffffff
# magic, hcrc, time, size, load, ep, dcrc, os=linux, arch=arm, type=kernel, comp=none
hdr = struct.pack('>7I4B32s', 0x27051956, 0, int(time.time()), len(data),
                  load, load, dcrc, 5, 2, 2, 0, name)
hcrc = zlib.crc32(hdr) & 0xffffffff
hdr = hdr[:4] + struct.pack('>I', hcrc) + hdr[8:]
open(out, 'wb').write(hdr + data)
print(f'{out}: {len(data)} bytes payload, load/entry 0x{load:08x}')
