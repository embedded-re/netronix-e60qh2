# Reverse Engineering Report: Netronix E60QH2 E-Book Reader
### Slovak Telekom OEM Device

---

## 1. Device Overview

| Field | Value |
|---|---|
| Manufacturer | Netronix |
| Model | E60QH2 |
| Brand | Netronix (OEM'd for Slovak Telekom) |
| PCB Marking | 37NB-E60QH0+4A1 |
| Serial (board label) | ST001357 |

---

## 2. Hardware

| Component | Details |
|---|---|
| SoC | Freescale i.MX6SoloLite, ARMv7 Cortex-A9 @ 792MHz |
| RAM | 512MB DDR @ 396MHz |
| Storage | Samsung SEM04G eMMC 3.68GiB |
| Display | E-ink E060SCM, 1448×1072, 6" |
| WiFi | CyberTAN WC121 |
| Touch | zForce IR (1448×1072 resolution) |
| Stylus | Waltop I2C pen |
| PMIC | RICOH619 |
| EPD Controller | TPS65185 |
| Battery | 3.7V, 1500mAh (SP 285083) |
| Debug Interface | 4× UART headers, labeled pins |

---

## 3. Firmware

| Field | Value |
|---|---|
| Bootloader | U-Boot 2009.08, built 2016-05-10 |
| Kernel | Linux 3.0.35, built 2016-05-10 |
| OS | Android 4.0.4 (Ice Cream Sandwich), SDK 15 |
| Build ID | V2.1.2.ST.rev. |
| Build date | 2016-12-21 |
| Build user | hudy @ hudy-VirtualBox |
| Fingerprint | `Netronix/E60QH2/E60QH2:4.0.4/UNKNOWN/eng.hudy.20161221.104654:eng/V2.1.2.ST.rev.` |
| Locale | `sk_SK` (Slovak) |

---

## 4. Partition Map

| Partition | Size | Mount Point | Filesystem | Notes |
|---|---|---|---|---|
| mmcblk0p1 | 6MB | — | raw | U-Boot + environment |
| mmcblk0p2 | 32MB | — | raw | Kernel + ramdisk |
| mmcblk0p3 | 1 block | — | — | Extended container |
| mmcblk0p4 | 2.1GB | /mnt/sdcard | vfat | User storage |
| mmcblk0p5 | 384MB | /system | ext4 ro | Android system |
| mmcblk0p6 | 384MB | /cache | ext4 | Cache |
| mmcblk0p7 | 512MB | /data | ext4 | App data |
| mmcblk0p8 | 8MB | /device | ext4 ro | Board hwcfg (Netronix NTX) |
| mmcblk0p9 | 4MB | — | raw | Unknown |
| mmcblk0p10 | 256MB | — | raw | E-ink waveform data |

---

## 5. Notable Software

### System Binaries (`/system/bin`)
- `busybox` v1.15.3 — full applet set available
- `epd_ctrl` — e-ink display control
- `ntx_hwconfig-static` — Netronix hardware config utility
- `strace`, `gdbserver` — debug tools left in production build
- `dd`, `fdisk` (via busybox) — raw storage access

### Extended Binaries (`/system/xbin`)
- `ssh`, `scp`, `nc`, `tcpdump` — network tools
- `sqlite3` — database access
- `strace`, `su` — privilege and debug tools

### Notable APKs (`/system/app`)
- `DLReader.apk`, `DanteReader.apk`, `HomerReader.apk` — multiple e-reader frontends
- `MsgE6.apk`, `st_system.apk` — Slovak Telekom customization layer
- `EPDRefresh.apk`, `FastPageTurn.apk` — e-ink display management
- `HandWriting.apk`, `HandWriting2.apk` — Waltop stylus input
- `vending.apk` — Google Play (present but not configured)

---

## 6. UART Access

### UART 0 — Primary Console (confirmed)

The device exposes clearly labeled UART headers on the PCB. Connecting to the first header immediately yields a root Android shell — no exploit, no authentication, no interaction required.

**Connection parameters:** `115200 8N1`  
**Console device:** `ttymxc0`

**Boot sequence summary:**
1. U-Boot initializes hardware, loads kernel from mmcblk0p2
2. Kernel boots with `init=/init`, mounts partitions
3. Android init starts, adbd and zygote launch
4. Root shell prompt appears: `root@android:/ #`

**Note:** Post-prompt kernel log noise is present (PMU charging status updates). This is normal — the shell is fully interactive despite the interleaved output.

### Access method

```
UART header → USB-UART adapter → minicom/screen @ 115200 8N1
```

No bootloader interruption needed. Shell is spawned automatically.

### Privilege level

Full root, no restrictions. Verified:
- Read/write access to all block devices
- Access to `/data`, `/system`, `/device`
- `adb` running as root (`adbd`)

---

## 7. Full eMMC Backup

ADB was available immediately after UART root access. Full image acquired via:

```sh
adb pull /dev/block/mmcblk0 mmcblk0.img
# 3,959,422,976 bytes @ ~3.7 MB/s
```

Image verified with `file`:
```
mmcblk0.img: DOS/MBR boot sector; partition 1: ID=0x83 ... partition 4: ID=0xb
```

SHA256 hash stored alongside image for integrity verification.

---

## 8. UART Sections 2–4

> **TODO** — Three additional labeled UART headers identified on PCB. To be investigated.

Possible assignments based on hardware present:
- CyberTAN WC121 WiFi module debug console
- Waltop stylus MCU
- MSP430 (identified in boot log as `msp430_i2c_probe, firmware version F110`) — likely a secondary microcontroller for power/input management

---

## 9. Drawing to the Display

### Background

The E060SCM e-ink display does not refresh automatically when you write pixel data to the framebuffer. A refresh must be explicitly triggered via ioctl. While the device has a dedicated tool (`epd_ctrl`) and standard EPDC ioctls, these are stubbed out in the kernel via a `fake_s1d13522` shim and do not work.

The working refresh path was identified by attaching `strace` to the running `surfaceflinger` process and capturing the ioctl calls it made on the framebuffer file descriptors during normal display updates. The exact ioctl sequence was then replicated directly.

### Discovery Method

```sh
# Find surfaceflinger PID
busybox ps | busybox grep surfaceflinger

# Attach strace and capture ioctl calls
/system/xbin/strace -p <PID> -e trace=ioctl > /data/local/trace.txt 2>&1 &

# Interact with screen to trigger a refresh, then stop strace
# Filter for fb0 file descriptors (12, 13, 15, 16)
grep -E "ioctl\((12|13|15|16)" /data/local/trace.txt
```

This revealed the following sequence issued every frame:
```
ioctl(13, 0x4606,      ...) = 0   # FBIOPAN_DISPLAY
ioctl(13, 0x4004462d,  ...) = 0   # MXCFB_WAIT_FOR_UPDATE_COMPLETE
ioctl(13, 0x4040462e,  ...) = 0   # MXCFB_SEND_UPDATE
```

### Framebuffer Layout

| Parameter | Value |
|---|---|
| Resolution | 1448 × 1072 |
| Stride | 1472 px (24px padding) |
| Bit depth | 16bpp RGB565 |
| Virtual size | 1472 × 2304 (two pages) |
| Active page offset | `1472 * 1072 * 2` bytes (page 1) |
| Panel seam | Horizontal line at y=536 — dual-scan panel, normal |

### Prerequisites

- Alpine Linux chroot on SD card (provides Python 3)
- `setprop ctl.stop surfaceflinger` — stops surfaceflinger without init restarting it
- `/dev/graphics/fb0` — world-writable, no special permissions needed

### Drawing Template

```python
import struct, fcntl, os

MXCFB_SEND_UPDATE   = 0x4040462e
MXCFB_WAIT_COMPLETE = 0x4004462d

W, H, S = 1448, 1072, 1472  # width, height, stride

# Create white canvas
buf = bytearray(b'\xff' * (S * H * 2))

# Draw a black pixel (RGB565: 0x0000 = black, 0xffff = white)
def px(buf, x, y):
    if 0 <= x < W and 0 <= y < H:
        p = (y * S + x) * 2
        buf[p] = 0x00
        buf[p+1] = 0x00

# --- Draw your shapes here ---

# Write to active page and trigger refresh
fb = os.open('/dev/graphics/fb0', os.O_RDWR)
os.lseek(fb, S * H * 2, os.SEEK_SET)   # seek to page 1
os.write(fb, bytes(buf))

upd = struct.pack('16I',
    0, 0, W, H,      # update region: full screen
    0x0002,          # waveform mode: GC16 (full quality)
    0x0001,          # update mode: full
    1, 0x1000,       # marker, temperature (ambient)
    0, 0, 0, 0, 0, 0, 0, 0
)
fcntl.ioctl(fb, MXCFB_SEND_UPDATE, upd)
fcntl.ioctl(fb, MXCFB_WAIT_COMPLETE, struct.pack('I', 1))
os.close(fb)
```

A full example (Braille-art demo) is [`stock/mxcfb_draw.py`](../stock/mxcfb_draw.py).

### Step-by-step Usage

```sh
# 1. Stop surfaceflinger (stays stopped, init won't restart it)
setprop ctl.stop surfaceflinger

# 2. Enter Alpine chroot
/data/local/start_alpine.sh

# 3. Write and run your drawing script
python3 /tmp/draw.py

# 4. Restore Android UI when done
exit
setprop ctl.start surfaceflinger
```

---

## 10. Summary

The device presents essentially no security barrier on its debug interface. The primary UART header provides an unauthenticated root shell on first connection. Combined with ADB being enabled and running as root, full firmware extraction requires no exploitation — only physical access to the PCB headers.

The firmware itself is a 2016 engineering build (`ro.build.type=eng`) with debug tools, gdbserver, and strace left on the system partition, suggesting this was never hardened for consumer deployment.
