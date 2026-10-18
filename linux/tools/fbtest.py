#!/usr/bin/env python3
"""Draw a test card on /dev/fb0 (XRGB8888, 1448x1072) for the E60QH2 panel."""
from PIL import Image, ImageDraw, ImageFont
W, H = 1448, 1072
img = Image.new('L', (W, H), 255)
d = ImageDraw.Draw(img)
# 16-level grayscale ramp (tests the GC16 waveform)
for i in range(16):
    d.rectangle([i * W // 16, 0, (i + 1) * W // 16 - 1, 180], fill=i * 17)
# checkerboard
for y in range(200, 560, 40):
    for x in range(0, W, 40):
        if ((x + y) // 40) % 2:
            d.rectangle([x, y, x + 39, y + 39], fill=0)
try:
    f = ImageFont.truetype('/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf', 96)
except OSError:
    f = ImageFont.load_default(size=96)
d.text((60, 620), 'E60QH2', font=f, fill=0)
d.text((60, 760), 'mainline Linux 7.2', font=f, fill=0)
d.rectangle([4, 4, W - 5, H - 5], outline=0, width=6)
rgb = img.convert('RGB').tobytes()
# RGB -> XRGB8888 little endian (B, G, R, X)
out = bytearray(W * H * 4)
out[0::4] = rgb[2::3]; out[1::4] = rgb[1::3]; out[2::4] = rgb[0::3]
with open('/dev/fb0', 'wb') as fb:
    fb.write(out)
print('drawn')
