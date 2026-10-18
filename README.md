# Netronix E60QH2 — reverse engineering and mainline Linux

The Netronix E60QH2 is a 6″ e-ink reader that Slovak Telekom sold under its
own brand. It has an i.MX6 SoloLite, a 1448×1072 E Ink panel, a zForce IR
touchscreen, BCM43362 WiFi and Android 4 on a 4 GB eMMC. This repository
documents the hardware and the stock firmware, and ports mainline Linux to it.
The port uses Linux 7.2 and Alpine 3.24 from the microSD, and leaves the eMMC
with stock Android untouched.

## Status

Working on the hardware (2026-10-18): boot from the stock U-Boot, eMMC and
microSD, WiFi, battery and charger, RTC, backlight, buttons, suspend and
resume. Also working:

- **Display:** the out-of-tree EPDC DRM driver, with waveform modes and
  ghosting control.
- **Touch:** a kernel patch fixes the zForce touch release, and the measured
  accuracy is 9.7 px mean.

There is no audio or Bluetooth hardware. Details are in
[linux/README.md](linux/README.md).

At boot the reader opens a full-screen e-ink terminal with an on-screen
keyboard, without X. `gui` starts an Xorg desktop with a touch launcher and a
PDF/EPUB book reader. See [linux/DESKTOP.md](linux/DESKTOP.md).

## Security as shipped

This reader reached customers with every layer of protection open. You need
physical access and a USB-UART adapter, and nothing else: no exploit and no
password.

| Layer | As shipped | Effect |
|---|---|---|
| Debug UART | Four UART headers, **clearly labeled on the silkscreen at the top of the PCB**. The console header runs at 115200 8N1 | Easy to find and connect |
| Bootloader | U-Boot 2009 with `bootdelay=1` and no password. **Ctrl+C** (or any key) at boot stops it at the `eBR-1A #` prompt, which has `fatload`, `bootm`, `loady` and `saveenv` | Boot any kernel from microSD or serial, and change the boot environment |
| Android build | **Engineering build** (`ro.build.type=eng`, fingerprint `…/eng.hudy.20161221…:eng/V2.1.2.ST.rev.`) with debug tools, `gdbserver` and `strace` | Debug build shipped to customers |
| Shell | The UART console opens a **root shell** (`root@android:/ #`) at boot, with no login | Full root over serial |
| ADB | Enabled, with `adbd` **running as root** | Root over USB as well; `adb pull /dev/block/mmcblk0` copies the whole eMMC |
| Secure boot | OTP boot fuses and SRK hash read as zero, so HAB is not provisioned **[inferred]** | Unsigned images run; the i.MX USB serial downloader works for recovery |

This made the port possible without opening any exploit path. It also means
that anyone who held the device for a few minutes could read or replace
everything on it. Details: [docs/stock-android.md](docs/stock-android.md)
(UART, root, ADB, eMMC dump) and [docs/hardware-map.md](docs/hardware-map.md)
(U-Boot, fuses).

## Layout

| Path | Contents |
|---|---|
| [`docs/hardware-map.md`](docs/hardware-map.md) | SoC, buses, GPIOs, PMICs, panel, partitions, U-Boot; how they map to mainline |
| [`docs/stock-android.md`](docs/stock-android.md) | stock firmware: UART root shell, eMMC backup, drawing on the panel from Android |
| `docs/stock-boot.log`, `docs/hwmap_raw/` | stock boot log and raw probe output from the live device |
| [`linux/`](linux/README.md) | the Linux port: kernel patches, device tree, EPDC driver, rootfs build, desktop and terminal, tools |
| `stock/` | scripts for the stock Android system |

## Not in this repository

Some files stay in a git-ignored `local/` folder, because they are
proprietary, specific to one unit, or too large:

- the full eMMC dump
- the stock `/system`
- APKs and books

The build reads the WiFi `nvram.txt` from the stock `/system` and the EPD
waveform from the eMMC dump. Both come from your own device; see
[linux/README.md](linux/README.md#build). `linux/fetch.sh` downloads the kernel
and Alpine sources, verifies their checksums, and applies the patches.

## License

Open source. This guide and its code are under the [MIT License](LICENSE),
except for these parts, which keep their upstream licenses:

- Kernel patches, the device tree and `linux/drivers/mxc-epdc` are GPL-2.0,
  as derived from Linux and Andreas Kemnade's EPDC driver.
- `linux/desktop/usr/local/lib/e60/pyte` is pyte 0.8.2 (LGPL-3.0, license
  included).
- `linux/ref/` holds upstream reference material under its original licenses.
