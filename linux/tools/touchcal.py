#!/usr/bin/env python3
"""Touch accuracy check for the E60QH2: draws crosshair targets on /dev/fb0
one at a time, records where the zForce reports each tap, and fits an affine
correction. Stop the desktop first (rc-service e60-desktop stop).

Usage: touchcal.py [margin_px]   (default 60)
"""
import mmap, os, select, struct, sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1448, 1072
EPDC = '/sys/devices/platform/soc/2000000.bus/20f4000.epdc'
EV_KEY, EV_ABS, BTN_TOUCH, ABS_X, ABS_Y = 1, 3, 0x14a, 0, 1
EVFMT = 'llHHi'
EVSZ = struct.calcsize(EVFMT)
DEBUG = os.environ.get('TOUCHCAL_DEBUG') == '1'

m = int(sys.argv[1]) if len(sys.argv) > 1 else 60
targets = [(x, y) for y in (m, H // 2, H - 1 - m) for x in (m, W // 2, W - 1 - m)]
try:
    font = ImageFont.truetype('/usr/share/fonts/dejavu/DejaVuSans.ttf', 36)
except OSError:
    font = ImageFont.load_default()


def show(i, done):
    img = Image.new('L', (W, H), 255)
    d = ImageDraw.Draw(img)
    for (x, y), (rx, ry) in done:
        d.line([x - 8, y, x + 8, y], fill=128, width=2)
        d.line([x, y - 8, x, y + 8], fill=128, width=2)
        d.ellipse([rx - 5, ry - 5, rx + 5, ry + 5], fill=0)
    if i < len(targets):
        x, y = targets[i]
        d.line([x - 40, y, x + 40, y], fill=0, width=3)
        d.line([x, y - 40, x, y + 40], fill=0, width=3)
        d.ellipse([x - 12, y - 12, x + 12, y + 12], outline=0, width=3)
        d.text((W // 2 - 300, H // 2 + 80), f'Tap the cross center ({i + 1}/{len(targets)})',
               font=font, fill=0)
    else:
        d.text((W // 2 - 200, H // 2 + 80), 'Done (dot = reported)', font=font, fill=0)
    rgb = img.convert('RGB').tobytes()
    out = bytearray(W * H * 4)
    out[0::4] = rgb[2::3]; out[1::4] = rgb[1::3]; out[2::4] = rgb[0::3]
    fd = os.open('/dev/fb0', os.O_RDWR)
    mm = mmap.mmap(fd, len(out))
    mm[:] = bytes(out)
    mm.flush(); mm.close(); os.close(fd)


def read_tap(f):
    """Return the median position of one touch (down..up)."""
    xs, ys, x, y, down = [], [], None, None, False
    while True:
        select.select([f], [], [])
        data = os.read(f, EVSZ * 64)
        for off in range(0, len(data) - EVSZ + 1, EVSZ):
            _, _, typ, code, val = struct.unpack_from(EVFMT, data, off)
            if DEBUG:
                print(f'  ev {typ} {code:#x} {val}', file=sys.stderr, flush=True)
            if typ == EV_ABS and code == ABS_X:
                x = val
            elif typ == EV_ABS and code == ABS_Y:
                y = val
            elif typ == EV_KEY and code == BTN_TOUCH:
                if val:
                    down, xs, ys = True, [], []
                elif down and xs:
                    xs.sort(); ys.sort()
                    return xs[len(xs) // 2], ys[len(ys) // 2], len(xs)
            elif typ == 0 and down and x is not None and y is not None:
                xs.append(x); ys.append(y)


def fit(pairs):
    """Least-squares affine screen = A * raw + b, per axis."""
    def solve(rows, rhs):
        # normal equations for 3 unknowns
        n = [[sum(r[i] * r[j] for r in rows) for j in range(3)] for i in range(3)]
        v = [sum(r[i] * t for r, t in zip(rows, rhs)) for i in range(3)]
        for c in range(3):
            p = max(range(c, 3), key=lambda k: abs(n[k][c]))
            n[c], n[p], v[c], v[p] = n[p], n[c], v[p], v[c]
            for k in range(3):
                if k != c:
                    q = n[k][c] / n[c][c]
                    n[k] = [a - q * b for a, b in zip(n[k], n[c])]
                    v[k] -= q * v[c]
        return [v[i] / n[i][i] for i in range(3)]
    rows = [(rx, ry, 1.0) for _, (rx, ry) in pairs]
    return solve(rows, [t[0] for t, _ in pairs]), solve(rows, [t[1] for t, _ in pairs])


def main():
    f = os.open('/dev/input/e60-touch', os.O_RDONLY)
    with open(f'{EPDC}/waveform_mode', 'w') as w:
        w.write('du')
    done = []
    try:
        for i, t in enumerate(targets):
            show(i, done)
            rx, ry, n = read_tap(f)
            done.append((t, (rx, ry)))
            print(f'target {t[0]:5d},{t[1]:5d}  got {rx:5d},{ry:5d}  '
                  f'err {rx - t[0]:+4d},{ry - t[1]:+4d}  ({n} samples)', flush=True)
        show(len(targets), done)
    finally:
        with open(f'{EPDC}/waveform_mode', 'w') as w:
            w.write('auto')
    errs = [((rx - tx) ** 2 + (ry - ty) ** 2) ** 0.5 for (tx, ty), (rx, ry) in done]
    print(f'mean error {sum(errs) / len(errs):.1f} px, max {max(errs):.1f} px')
    cx, cy = fit(done)
    print('affine x = %.4f*rx %+.4f*ry %+.1f' % tuple(cx))
    print('affine y = %.4f*rx %+.4f*ry %+.1f' % tuple(cy))
    # X "Coordinate Transformation Matrix" works in normalized units
    print('xinput CTM: %.5f %.5f %.5f %.5f %.5f %.5f 0 0 1' % (
        cx[0], cx[1] * (H - 1) / (W - 1), cx[2] / (W - 1),
        cy[0] * (W - 1) / (H - 1), cy[1], cy[2] / (H - 1)))


main()
