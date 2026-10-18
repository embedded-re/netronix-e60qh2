import socket, time, sys
s = socket.socket(socket.AF_UNIX); s.connect('/tmp/kstb.sock'); s.settimeout(0.05)
if len(sys.argv) > 1: s.sendall(sys.argv[1].encode() + b'\r')
buf = b''; t0 = time.time()
while time.time() - t0 < 90:
    try:
        d = s.recv(4096)
        buf += d
    except socket.timeout:
        pass
    if b'U-Boot 2009' in buf: s.sendall(b' ')
    if b'eBR-1A #' in buf.split(b'U-Boot 2009')[-1] and b'U-Boot 2009' in buf:
        s.sendall(b'\r'); time.sleep(0.5); print('GOT PROMPT'); break
print(buf.decode('latin1').replace('\r', '')[-600:])
