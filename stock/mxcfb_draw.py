import struct, fcntl, os
MXCFB_SEND_UPDATE   = 0x4040462e
MXCFB_WAIT_COMPLETE = 0x4004462d
W, H, S = 1448, 1072, 1472
buf = bytearray(b'\xff' * (S * H * 2))
def px(x, y):
    if 0 <= x < W and 0 <= y < H:
        p = (y * S + x) * 2
        buf[p] = buf[p+1] = 0x00
DOT_POS = [
    (0,0),(0,1),(0,2),
    (1,0),(1,1),(1,2),
    (0,3),(1,3)
]
art = """\
⠀⠀⠀⠀⠀⢀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⡀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠉⠉⠉⠉⢹⣿⣿⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⡏⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⢹⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⡇⠀⣀⣀⣀⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⡇⠀⠉⠉⠉⠉⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⡟⠛⡛⠛⣿⠛⢛⡛⢻⡟⢛⡛⠛⣿⠛⢛⠛⢻⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⡇⠘⠛⠀⣿⠀⠛⠃⢸⡇⠘⠛⠀⣿⠀⠛⠃⢸⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⡟⠛⠛⠛⣿⠛⠛⠛⢻⡟⠛⠛⠛⣿⠛⠛⠛⢻⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⡇⠘⠿⠀⣿⠀⠻⠇⢸⡇⠸⠟⠀⣿⠀⠿⠃⢸⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⡗⠒⠒⠺⣿⠗⠒⠒⢺⡗⠒⠒⠺⣿⠗⠒⠒⢺⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⡇⠠⠶⠀⣿⠀⠴⠆⢸⡇⠰⠦⠀⣿⠀⣶⡄⢸⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⣧⣤⣤⣤⣿⣦⣤⣤⣼⣧⣤⣤⣴⣿⠀⣿⡇⢸⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⡇⢠⣤⠀⣿⠀⣤⡄⢸⡇⢠⣤⠀⣿⠀⣿⡇⢸⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⣧⣤⣤⣤⣿⣤⣤⣤⣼⣧⣤⣤⣤⣿⣤⣤⣤⣼⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠈⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠁⠀⠀⠀⠀⠀
"""
SCALE = 8
lines = art.split('\n')
rows = len(lines)
cols = max(len(l) for l in lines)
cw = cols * 2 * SCALE
ch = rows * 4 * SCALE
ox = (W - cw) // 2
oy = (H - ch) // 2
for row, line in enumerate(lines):
    for col, ch_char in enumerate(line):
        code = ord(ch_char) - 0x2800
        if code <= 0:
            continue
        for bit, (dx, dy) in enumerate(DOT_POS):
            if code & (1 << bit):
                bx = ox + (col * 2 + dx) * SCALE
                by = oy + (row * 4 + dy) * SCALE
                for sy in range(SCALE):
                    for sx in range(SCALE):
                        px(bx+sx, by+sy)
fb = os.open('/dev/graphics/fb0', os.O_RDWR)
# write to both pages so it works regardless of which is active after boot
os.lseek(fb, 0, os.SEEK_SET)
os.write(fb, bytes(buf))
os.lseek(fb, S*H*2, os.SEEK_SET)
os.write(fb, bytes(buf))
upd = struct.pack('16I', 0,0,W,H, 0x0002,0x0001,1,0x1000, 0,0,0,0,0,0,0,0)
fcntl.ioctl(fb, MXCFB_SEND_UPDATE, upd)
fcntl.ioctl(fb, MXCFB_WAIT_COMPLETE, struct.pack('I', 1))
os.close(fb)
print("done")
