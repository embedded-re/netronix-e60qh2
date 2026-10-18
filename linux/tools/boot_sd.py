#!/usr/bin/env python3
"""Catch the stock U-Boot on the serial console and boot uImage from microSD.

Start it, then reboot or power-cycle the reader (or pass a command to send
first, e.g. `boot_sd.py reboot` from a running Linux/Android console).
The serial port is shared through a unix socket (default /tmp/kstb.sock,
override with E60_SERIAL_SOCK); waits up to 4 minutes for U-Boot.
"""
import os
import socket
import sys
import time

s = socket.socket(socket.AF_UNIX)
s.connect(os.environ.get('E60_SERIAL_SOCK', '/tmp/kstb.sock'))
s.settimeout(0.05)
if len(sys.argv) > 1:
    s.sendall(sys.argv[1].encode() + b'\r')
buf, t0 = b'', time.time()
while time.time() - t0 < 240:
    try:
        buf += s.recv(4096)
    except socket.timeout:
        pass
    if b'U-Boot 2009' in buf:
        s.sendall(b' ')                      # stop autoboot (bootdelay 1 s)
        if b'eBR-1A #' in buf.split(b'U-Boot 2009')[-1]:
            break
else:
    sys.exit('no U-Boot prompt seen')


def cmd(line, wait):
    s.sendall(line.encode() + b'\r')
    out, t = b'', time.time()
    while time.time() - t < wait:
        try:
            out += s.recv(4096)
        except socket.timeout:
            pass
    print(out.decode('latin1').replace('\r', '')[-200:], flush=True)


time.sleep(0.5)
cmd('mmc dev 1', 3)
cmd('fatload mmc 1:1 0x82000000 uImage', 15)
cmd('bootm 0x82000000', 5)
