# Mainline Linux for the E60QH2 (RE build)

Linux 7.2.11 + Alpine 3.24 armv7 on the microSD; the eMMC (stock Android)
is not touched.

## microSD layout (`mmcblk1`)

| Part | Size | FS | Content |
|---|---|---|---|
| p1 | 256 MiB | FAT32 `BOOT` | `uImage` (zImage + appended DTB, legacy U-Boot header) |
| p2 | 4 GiB | ext4 `e60root` | Alpine root |
| p3 | ~10 GiB | FAT32 `DATA` | data, mounted at `/mnt/data` (holds `rootfs.img.gz` backup) |

## Boot (from the stock U-Boot)

Interrupt autoboot on the serial console (bootdelay is 1 s; spam a key), then
type the commands below. `python3 -I tools/boot_sd.py` does all of it: start
it, then reboot the reader (or pass `reboot` to send that first). The serial
tools talk to the UART through a unix socket (`/tmp/kstb.sock`, override with
`E60_SERIAL_SOCK`) so several tools can share one adapter.

```
mmc dev 1
fatload mmc 1:1 0x82000000 uImage
bootm 0x82000000
```

The kernel command line is built in (`CMDLINE_FORCE`):
`console=ttymxc0,115200 root=/dev/mmcblk1p2 rootfstype=ext4 rootwait rw`.
`reset` at the prompt (or just power-cycling) goes back to Android.

## Build

Host: clang/LLVM, make, curl, python3, e2fsprogs, zstd (Arch Linux was used).

```
bash fetch.sh                        # kernel 7.2.11 + patches/, Alpine minirootfs, apk.static
bash kconfig.sh                      # imx_v6_v7_defconfig + E60QH2 options
make -C src/linux-7.2.11 ARCH=arm LLVM=1 O=../build -j8 zImage modules dtbs
python3 -I tools/mkuimage.py src/build/arch/arm/boot/zImage \
    src/build/arch/arm/boot/dts/nxp/imx/imx6sl-netronix-e60qh2.dtb out/uImage
unshare -r bash rootfs.sh            # -> out/rootfs.img (1.5 GB, grows on first boot)
```

`rootfs.sh` also builds the EPDC driver (`drivers/mxc-epdc`, installed under
`/lib/modules/*/updates`). It needs two things that are not in the
repository, by default from `../local/` (override with the variables):

| Variable | Default | Used for |
|---|---|---|
| `STOCK_SYSTEM` | `../local/system` | stock Android `/system`: WC121 `lib/firmware/wc121/nvram.txt` |
| `EMMC_IMG` | `../local/backup/mmcblk0.img` | eMMC dump: EPD waveform at 0x700000 |
| `WIFI_MAC` | empty (keep the nvram template MAC) | this unit's WiFi MAC |

For root SSH, put your public key in `overlay/root/.ssh/authorized_keys`
(git-ignored) before running `rootfs.sh`.

After flashing, copy `desktop/` and `install-desktop.sh` to the reader and
run `sh install-desktop.sh` (installs packages; see [DESKTOP.md](DESKTOP.md)).

Kernel changes are in `patches/` (applied by `fetch.sh`):
`0001-zforce-v2-touch-states.patch` (touch, see below) and
`0002-dts-build-e60qh2.patch`. Device tree: `dts/imx6sl-netronix-e60qh2.dts`
(symlinked into the kernel tree), an overlay on `imx6sl-tolino-shine2hd.dts`.

## Deploy (from stock Android, over WiFi)

Serve `out/` with `python3 -m http.server 8088`, then on Android (root shell):

```
mount -t vfat /dev/block/mmcblk1p1 /data/local/tmp/sdboot
busybox wget -O /data/local/tmp/sdboot/uImage http://<pc>:8088/uImage
# rootfs: download to p3 first, verify, then write (streaming straight into
# dd stalled and corrupted the gzip stream)
busybox gunzip -c rootfs.img.gz | busybox dd of=/dev/block/mmcblk1p2 bs=1048576
```

Android unloads WiFi when the screen turns off: first
`echo x > /sys/power/wake_lock; svc power stayon true; svc wifi enable`.

Once the new system has network, deploy directly: `scp uImage
root@e60qh2:/boot/` (p1 is mounted at `/boot`).

## Status on hardware (first boot, 2026-10-18)

| Item | Status |
|---|---|
| Boot via stock U-Boot `bootm` | works |
| eMMC `mmcblk0`, microSD `mmcblk1`, WiFi SDIO `mmc2` | works |
| ntxec (MSP430 f110), backlight PWM | bound, `backlight` 0–3124 |
| RC5T619: RTC, regulators, battery/charger | works (battery 100 %) |
| zForce touch | works with `patches/0001-zforce-v2-touch-states.patch` (see below); 9-point accuracy 9.7 px mean, 17 px max |
| gpio-keys | input device present (Home press-tested) |
| TPS65185 | bound; regulators `v3p3`, `vposneg` 15 V, `vcom` 2.39 V |
| brcmfmac BCM43362 | works (DHCP 192.168.1.70, SSH as root with key) |
| EPDC (display) | **works**: `mxc_epdc_drm` (Kemnade's DRM driver, branch `kobo/drm-merged-7.1`, ported to 7.2 out-of-tree in `drivers/mxc-epdc/`, TTM→DMA fbdev). `/dev/dri/card1` + `/dev/fb0` (XRGB8888). Test card: `python3 /root/re/fbtest.py` |

Known issues:
* (fixed) zForce never reported finger lift: this firmware ("neonode_v2") sends
  touch states 4/5/6 (down/move/up) and contact IDs from 0, while mainline
  `zforce_ts` expects 0/1/2 and IDs from 1. Without the fix BTN_TOUCH and the MT
  slot stay pressed forever. Fixed by `patches/0001-zforce-v2-touch-states.patch`
  (kernel #3, 2026-10-18). Raw packets were captured with a temporary
  `print_hex_dump` in the IRQ thread.
* (fixed) EPDC pixel clock: was 77.14 MHz from pll3_pfd1; now 80 MHz from PLL5 like stock (assigned-clocks in the DTS).
* fbcon draws on the panel; `e60-inputs` (used by both UI modes) unbinds it.
* (not an issue) `write()` and mmap on `/dev/fb0` both queue exactly one update; checked with the `updates` counter.

## Display control (sysfs)

`D=/sys/devices/platform/soc/2000000.bus/20f4000.epdc`

| File | Use |
|---|---|
| `$D/waveform_mode` | `auto` (default; the EPDC picks DU/GL16/GC16 from the pixel content), or `init`, `du`, `gc16`, `gl16`, `a2`, `du4`, or an index 0–7; used for every following damage update |
| `$D/update_mode` | `partial` (default; only changed pixels are driven) or `full` |
| `$D/refresh` | write a mode name to redraw the whole screen with it, e.g. `echo gc16 > $D/refresh` to clear ghosting |
| `$D/updates` | number of updates queued (debug/verification) |
| `$D/idle` | 1 when initialized and all submitted updates have completed, otherwise 0 |
| `$D/wait_idle` | read to wait for submitted updates to drain; returns 1, or an error after eight seconds/interruption |

Waveform mode map (ED060KG1 `320_R057_AF2701`, from `tools/wfmodes.py`; set in
the DTS as `waveform-mode-*`): 0 INIT, 1 DU, 2 GC16, 3–5 GL16/GLR16/GLD16
(identical data), 6 A2, 7 DU4. Frames at 21–24 °C: INIT 115, GC16 46, GL16 46,
DU4 29, DU 26, A2 12. Demo: `python3 /root/re/modedemo.py [a2|du|gc16|all]`.

Checked on the panel (2026-10-18): A2 moves fast without flashing and leaves
gray ghosting; DU is slower and cleaner; a GC16 full refresh clears the ghosting
to clean white. Frames sent faster than an update completes collide: the EPDC
starts the idle pixels first and finishes the busy ones later (resubmitted in
`auto`), so a moving object briefly shows at two positions. Apps need an
"update done" wait to pace themselves. `wait_idle` now drains submitted
updates; it is not a fence for fbdev deferred damage or future writes and
does not automatically pace Xorg.

## Graphical interface and hardware validation

At boot the reader starts a full-screen e-ink terminal with an on-screen
keyboard, without X (`e60-term`). Typing `gui` starts the Xorg/Openbox
desktop (launcher, book reader, backlight), and leaving it returns to the
terminal. See [DESKTOP.md](DESKTOP.md) for install, service controls,
tested hardware, and remaining validation gaps.

Two RTC deep-suspend tests passed; enabling `wpa_cli` fixes DHCP recovery
after Wi-Fi is recreated on resume. The rootfs uses `mdev-netlink` for
hotplug because this kernel disables the legacy userspace helper.

## EPDC driver build

```
make -C src/build ARCH=arm LLVM=1 M=$PWD/drivers/mxc-epdc modules
scp drivers/mxc-epdc/mxc_epdc_drm.ko root@e60qh2:/lib/modules/7.2.11/updates/ && ssh root@e60qh2 depmod -a
```

Images built by `rootfs.sh` have the module in `updates/`. The first unit was
set up by hand with it in `extra/`; keep only one copy, because `updates/`
takes precedence.

## Files

| Path | What |
|---|---|
| `fetch.sh`, `kconfig.sh`, `rootfs.sh` | download sources, configure the kernel, build the Alpine image |
| `patches/` | kernel patches (applied by `fetch.sh`) |
| `dts/` | E60QH2 device tree |
| `drivers/mxc-epdc/` | EPDC DRM driver, Kemnade's `kobo/drm-merged-7.1` ported to 7.2 (out of tree) |
| `overlay/` | config files copied into the image |
| `desktop/`, `install-desktop.sh` | e-ink terminal, X desktop, launcher, book reader ([DESKTOP.md](DESKTOP.md)) |
| `tools/` | host and device helpers: `boot_sd.py`/`catch_uboot.py` (serial), `mkuimage.py`, `touchcal.py` (touch accuracy), `wfinfo.py`/`wfmodes.py` (waveform), `fbtest.py`/`modedemo.py` (panel tests), `decode_iomux.py`, `devmem.c` |
| `ref/` | upstream reference material: Kemnade's EPDC RFC, 7.1 driver and DT sources, inkwave |
| `logs/` | serial logs of the first mainline boots |
