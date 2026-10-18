#!/bin/bash
# Build the Alpine armv7 rootfs image for the E60QH2. Run as:
#   unshare -r bash rootfs.sh   (user namespace: files end up root-owned in the image)
set -euo pipefail
cd "$(dirname "$0")"
TOP=$PWD
R=$TOP/out/rootfs
APK=$TOP/dl/apkstatic/sbin/apk.static
MIRROR=https://dl-cdn.alpinelinux.org/alpine/v3.24
KBUILD=$TOP/src/build
# Data that is not in the repository (proprietary / unit-specific):
#   STOCK_SYSTEM  stock Android /system (for the WC121 WiFi nvram.txt)
#   EMMC_IMG      full eMMC dump (for the EPD waveform)
#   WIFI_MAC      this unit's WiFi MAC; empty keeps the nvram template MAC
LOCAL=${E60_LOCAL:-$TOP/../local}
STOCK_SYSTEM=${STOCK_SYSTEM:-$LOCAL/system}
EMMC_IMG=${EMMC_IMG:-$LOCAL/backup/mmcblk0.img}
WIFI_MAC=${WIFI_MAC:-}
IMG_MB=1536

PKGS="alpine-base openrc busybox-openrc busybox-mdev-openrc
 openssh wpa_supplicant wpa_supplicant-openrc iw wireless-regdb linux-firmware-brcm
 i2c-tools evtest libgpiod mmc-utils usbutils util-linux e2fsprogs e2fsprogs-extra dosfstools
 kmod python3 py3-pip py3-numpy py3-pillow
 gcc musl-dev make binutils gdb strace file git vim htop tmux less dtc rsync"

rm -rf "$R"; mkdir -p "$R"
tar --no-same-owner -xzf dl/alpine-minirootfs-3.24.2-armv7.tar.gz -C "$R"
printf '%s/main\n%s/community\n' "$MIRROR" "$MIRROR" > "$R/etc/apk/repositories"
mkdir -p "$R/etc/apk/cache"

# Package install scripts are armv7 and can't run here; they are re-run on the
# device at first boot from the cache (see /etc/local.d/firstboot.start).
"$APK" --root "$R" --arch armv7 --keys-dir "$R/etc/apk/keys" \
	--repositories-file "$R/etc/apk/repositories" --cache-dir "$R/etc/apk/cache" \
	--no-interactive update
"$APK" --root "$R" --arch armv7 --keys-dir "$R/etc/apk/keys" \
	--repositories-file "$R/etc/apk/repositories" --cache-dir "$R/etc/apk/cache" \
	--no-interactive add $PKGS || echo "apk: script errors ignored (re-run at first boot)"

# Kernel modules
make -C src/linux-7.2.11 ARCH=arm LLVM=1 O="$KBUILD" INSTALL_MOD_PATH="$R" \
	INSTALL_MOD_STRIP=1 modules_install >/dev/null
# Out-of-tree EPDC display driver (drivers/mxc-epdc) -> /lib/modules/*/updates
make -C "$KBUILD" ARCH=arm LLVM=1 M="$TOP/drivers/mxc-epdc" modules >/dev/null
make -C "$KBUILD" ARCH=arm LLVM=1 M="$TOP/drivers/mxc-epdc" INSTALL_MOD_PATH="$R" \
	INSTALL_MOD_STRIP=1 modules_install >/dev/null
rm -f "$R"/lib/modules/*/build "$R"/lib/modules/*/source

# WiFi nvram (stock WC121 file; template MAC replaced with WIFI_MAC if set)
FW=$R/lib/firmware/brcm
if [ -n "$WIFI_MAC" ]; then
	sed "s/^macaddr=.*/macaddr=$WIFI_MAC/" "$STOCK_SYSTEM/lib/firmware/wc121/nvram.txt"
else
	cat "$STOCK_SYSTEM/lib/firmware/wc121/nvram.txt"
fi > "$FW/brcmfmac43362-sdio.netronix,e60qh2.txt"
cp "$FW/brcmfmac43362-sdio.netronix,e60qh2.txt" "$FW/brcmfmac43362-sdio.txt"
zstd -q -d -f "$FW/brcmfmac43362-sdio.bin.zst" -o "$FW/brcmfmac43362-sdio.bin"

# EPD waveform from the eMMC dump (same layout pmOS extract-waveform.pl reads)
mkdir -p "$R/lib/firmware/imx/epdc"
python3 -I - "$EMMC_IMG" "$R/lib/firmware/imx/epdc/epdc_PENG060D.fw" <<'EOF'
import sys, struct
f = open(sys.argv[1], 'rb'); f.seek(0x700000 - 16)
hdr = f.read(16)
assert hdr[:8] == bytes.fromhex('fff5afff78563412'), hdr.hex()
n = struct.unpack('<I', hdr[8:12])[0]
open(sys.argv[2], 'wb').write(f.read(n))
print('waveform', n, 'bytes')
EOF
ln -sf epdc_PENG060D.fw "$R/lib/firmware/imx/epdc/epdc.fw"

# Overlay (config files) and RE material
cp -a overlay/. "$R"/
mkdir -p "$R/root/re"
cp "$TOP/../docs/hwmap_raw/"*.txt "$R/root/re/"
cp "$TOP/../docs/hardware-map.md" "$TOP/tools/devmem.c" "$R/root/re/"

# Services
add() { mkdir -p "$R/etc/runlevels/$2"; ln -sf "/etc/init.d/$1" "$R/etc/runlevels/$2/$1"; }
for s in devfs dmesg mdev-netlink hwdrivers; do add $s sysinit; done
for s in modules sysctl hostname bootmisc syslog hwclock networking; do add $s boot; done
for s in local wpa_supplicant wpa_cli sshd crond; do add $s default; done
for s in mount-ro killprocs savecache; do add $s shutdown; done

chown -R 0:0 "$R"
chmod 700 "$R/root"

find "$R" ! -perm -u+r -exec chmod u+r {} +
find "$R" -type d ! -perm -u+x -exec chmod u+x {} +
mkdir -p out
rm -f out/rootfs.img
mkfs.ext4 -q -F -L e60root -O ^metadata_csum_seed -d "$R" out/rootfs.img ${IMG_MB}M
du -sh "$R"

# Ownerships a single-uid user namespace can't express: fix them in the image
/sbin/debugfs -w -R "set_inode_field /etc/shadow gid 42" out/rootfs.img >/dev/null
