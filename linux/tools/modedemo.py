#!/usr/bin/env python3
"""Exercise EPDC waveform modes. Usage: modedemo.py [a2|du|gc16|all]"""
import mmap, os, sys, time
W, H = 1448, 1072
D = '/sys/devices/platform/soc/2000000.bus/20f4000.epdc'
def ctl(name, val):
    open(f'{D}/{name}', 'w').write(val)
fd = os.open('/dev/fb0', os.O_RDWR)
fb = mmap.mmap(fd, W * H * 4)
def rect(x0, y0, x1, y1, v):
    row = bytes([v, v, v, 0]) * (x1 - x0)
    for y in range(y0, y1):
        o = (y * W + x0) * 4
        fb[o:o + len(row)] = row
def run(mode, steps, delay):
    ctl('waveform_mode', mode)
    rect(0, 0, W, H, 255)
    time.sleep(0.6)
    t = time.time()
    for i in range(steps):
        x = 40 + i * (W - 200) // steps
        rect(0, 400, W, 680, 255)
        rect(x, 420, x + 120, 660, 0)
        time.sleep(delay)
    return time.time() - t
stage = sys.argv[1] if len(sys.argv) > 1 else 'all'
if stage in ('a2', 'du', 'all'):
    for mode, delay in (('a2', 0.12), ('du', 0.25)):
        if stage in (mode, 'all'):
            dt = run(mode, 12, delay)
            print(f'{mode}: 12 frames in {dt:.1f}s', flush=True)
            time.sleep(1.5)
if stage in ('gc16', 'all'):
    ctl('waveform_mode', 'auto')
    rect(0, 0, W, H, 255)
    time.sleep(0.6)
    ctl('refresh', 'gc16')
    print('gc16 full refresh sent; updates =', open(f'{D}/updates').read().strip())
ctl('waveform_mode', 'auto')
