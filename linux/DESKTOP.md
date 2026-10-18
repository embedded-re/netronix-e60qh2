# E60QH2 graphical interface

The interface uses Xorg's fbdev driver, Openbox, and Python/Tk apps. It runs
in portrait, 1072×1448: Xorg rotates the framebuffer (`Option "Rotate" "CW"`;
measured: root (u,v) lands at native (1447−v, u)) and `e60-session` sets the
touch Coordinate Transformation Matrix `0 1 0 -1 0 1 0 0 1` to match.
The serial root shell and SSH remain available.

## Default: e-ink terminal (no X)

At boot the reader starts `e60-term` (OpenRC service `e60-term`, in the
default runlevel). It is a full-screen root shell with an on-screen keyboard,
drawn straight on `/dev/fb0` in portrait, white on black and not
anti-aliased (fast DU updates). Xorg does not run.

- Keyboard: Shift is one-shot (tap twice for caps lock), Ctrl and Alt are
  one-shot, and ⌫/Del/arrows/Space repeat when held. ⟳ does a full GC16
  refresh. After 3 s idle with 40 or more partial updates, it does a GC16
  cleanup by itself.
- Swipe down/up on the text for scrollback (2000 lines).
- Font size: `E60_TERM_FONT` (px, default 22 → 82×37 cells).
- The terminal emulation is pyte 0.8.2 (LGPL-3), bundled in
  `/usr/local/lib/e60/pyte`.
- Type `gui` to stop the terminal and start the X desktop. The launcher's
  "Back to terminal" (or `pkill xinit`) ends X, and the terminal comes back.
  Log: `/var/log/e60-desktop.log`.
- `e60-inputs` creates the `/dev/input/e60-*` links and unbinds fbcon; both
  modes use it.

## Install on the reader

Copy `desktop/` and `install-desktop.sh` into the same directory on the
reader, then run `sh install-desktop.sh` there. This installs packages and
configuration into the running Alpine root on microSD.

```
rc-service e60-desktop start
rc-service e60-desktop stop
rc-update add e60-term default     # terminal at boot (current setup)
gui                                # X desktop on demand, from the terminal
```

The launcher (fullscreen) has Books, Terminal, Keyboard (toggle), Light −/+
(10 % steps) and Clean screen (GC16 full refresh). The status line shows the
time, battery and light; it updates when you use the launcher or press Home.
Physical Home raises the launcher. A running app is raised with `xdotool`
instead of being started twice. Xorg uses static evdev inputs discovered by
device name at service startup, so mdev does not need to be replaced with
udev. Xorg does not listen on TCP.

### E-ink handling

- UI text is not anti-aliased (`/etc/fonts/local.conf`). Pure black/white
  content lets the EPDC auto mode use DU (~26 frames) instead of GC16
  (~46 frames, grey). Book pages keep their greyscale.
- Tiles (`/usr/local/lib/e60/e60ui.py`) invert on touch, so feedback is
  immediate, and act on release only while the finger is still on the tile
  (24 px slack). The cursor is hidden (`-nocursor`), so finger movement causes
  no screen updates.
- `e60-refreshd` clears ghosting: after 3 s without touch, if 25 or more
  updates were queued since the screen was last clean, it does one GC16 full
  refresh. Tune with `E60_REFRESH_IDLE` / `E60_REFRESH_THRESHOLD` (0 turns it
  off). Apps that refresh themselves touch `/run/e60-clean` to reset it.
- Touch jitter: the DTS sets `touchscreen-fuzz-x/y = <4>` on the zForce, so the
  input core ignores 1–3 unit wobble while a finger rests.

### Book reader

`/usr/local/bin/e60-reader` lists `/mnt/data/books` (PDF, EPUB, MOBI, FB2,
CBZ, XPS; subfolders included) and renders pages with `mutool draw` in a
background thread, keeping the current page −1/+3 in `/tmp/e60-reader`.
Opening a PDF takes about 2 s (about 1 s per page plus startup); then turns are
instant while you read slower than about 1 page/s. EPUB pages render in about
0.4 s.

- Tap the right two thirds or swipe left: next page. Tap the left third or
  swipe right: previous page. Tap the top strip: menu (Library, −10/+10
  pages, A−/A+ font size for reflowable books, Clean).
- A GC16 full refresh after opening and every 8 page turns; turns in between
  are partial.
- Progress and font size: `/root/.config/e60-reader.json`.

The desktop currently runs as root, matching this device's development
environment. Logs: `/var/log/e60-desktop.log` and `/var/log/Xorg.0.log`.
The launcher is `/usr/local/bin/e60-launcher`; the service is
`/etc/init.d/e60-desktop`; X configuration is `/etc/X11/e60qh2.conf`.

## Validation on 2026-10-18

- Started Xorg, Openbox and launcher successfully; inspected framebuffer
  screenshot and confirmed X input devices are attached. Verified desktop
  autostart through a controlled Linux reboot. Terminal and keyboard each
  ran in a four-second smoke test without reporting errors.
- Captured real zForce touch movement and six Home press/release pairs.
- Touch lift was never reported before the `patches/0001-zforce-v2-touch-states.patch` kernel
  fix (see README). After it, `tools/touchcal.py` (9 crosshairs, 60 px from
  the edges, desktop stopped) measured 9.7 px mean / 17.3 px max error
  (about 1.4 mm). The fitted affine is near identity, so Xorg uses no
  Coordinate Transformation Matrix. Portrait rotation is not yet validated.
- Battery reported 100%, 4.19 V, temperature 27.5°C; backlight readback 1562/3124.
- Wi-Fi and SSH working; RTC date correct; no deferred driver probes listed.
- USB `g_ether` loaded and UDC progressed to `configured` (host enumerated).
  USB network traffic and host mode are not yet tested. Module loading was
  temporary; USB networking is not configured persistently.
- `iw reg reload` succeeded after root mount. An OpenRC local startup hook
  in `overlay/etc/local.d/regulatory.start` is installed on the reader and
  repeats this on future builds.
- Two 15-second RTC-triggered deep suspend/resume cycles completed. The
  first exposed IPv4 loss after brcmfmac recreated wlan0. Enabling Alpine's
  existing `wpa_cli` OpenRC service renewed DHCP on reconnection; the second
  cycle recovered SSH automatically. Launcher survived both cycles. The
  rootfs build now enables `wpa_cli` as well.
- Replaced legacy mdev hotplug-helper startup with `mdev-netlink`, using
  BusyBox `mdev -df -S`. This kernel has CONFIG_UEVENT_HELPER disabled.
  The daemon started successfully; the rootfs build uses it too.

Not yet established: repeated/long suspend reliability, power-button and lid wake,
charging/discharging transitions, USB networking, portrait touch rotation,
and long-running GUI refresh behavior. Hardware map confirms that audio,
Bluetooth and a pen digitizer are absent on this unit.

## Display completion API

The local EPDC driver now provides `idle` and `wait_idle` under
`/sys/devices/platform/soc/2000000.bus/20f4000.epdc/`.
`idle` returns 1 only when initialized and queued/in-flight updates have
drained; reading `wait_idle` waits up to eight seconds, returning 1 or an
error (timeout/interruption). Concurrent writers are not blocked.

This is a drain of work already submitted to the driver, **not** a fence
for fbdev's deferred dirty-page work or future writes. It does not yet
pace Xorg rendering automatically. Apps must ensure their damage has been
submitted before waiting. A continuously updating producer can time out.

The module compiled against the repository's 7.2.11 tree (existing warnings
remain) and was deployed through a controlled reboot. Three explicit full
refreshes (GC16, DU, GC16) each changed idle from 1 to 0, then released two
simultaneous waiters with result 1 after 0.665–0.845 seconds, with one update
count increment per refresh. No timeout occurred. Timeout and interruption
paths have not been exercised on hardware.

Previous module backup on the reader: `/root/re/mxc_epdc_drm.before-idle.ko`.
Restore it to `/lib/modules/7.2.11/extra/mxc_epdc_drm.ko`, run `depmod -a`,
and reboot into the SD Linux to roll back. Avoid hot-unloading this driver:
the inherited remove path lacks explicit workqueue teardown.
