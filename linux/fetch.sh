#!/bin/bash
# Download and prepare everything the build needs that is not in git:
#   src/linux-7.2.11   kernel tree with patches/ applied and the E60QH2 DTS linked in
#   dl/                Alpine armv7 minirootfs and a static apk for the host (x86_64)
# Safe to re-run: finished steps are skipped.
set -euo pipefail
cd "$(dirname "$0")"

KVER=7.2.11
ALPINE=3.24
ALPINE_REL=3.24.2
APK_TOOLS=3.0.8-r0

fetch() {  # url file sha256
	if [ ! -f "$2" ]; then
		curl -fsSL --retry 3 -o "$2.part" "$1"
		mv "$2.part" "$2"
	fi
	echo "$3  $2" | sha256sum -c --quiet
}

mkdir -p src dl

fetch "https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-$KVER.tar.xz" \
	"src/linux-$KVER.tar.xz" fd0fc479f983a8c05313f13e9c36330fe6651cf725396748c40d5cd93fa1e6a4
if [ ! -d "src/linux-$KVER" ]; then
	tar -xJf "src/linux-$KVER.tar.xz" -C src
	for p in patches/*.patch; do
		echo "applying $p"
		patch -d "src/linux-$KVER" -p1 --quiet < "$p"
	done
	ln -sfn ../../../../../../../../dts/imx6sl-netronix-e60qh2.dts \
		"src/linux-$KVER/arch/arm/boot/dts/nxp/imx/imx6sl-netronix-e60qh2.dts"
fi

fetch "https://dl-cdn.alpinelinux.org/alpine/v$ALPINE/releases/armv7/alpine-minirootfs-$ALPINE_REL-armv7.tar.gz" \
	"dl/alpine-minirootfs-$ALPINE_REL-armv7.tar.gz" 5552f1ef2398cee46ef2cf733f8f1258f39a77ad065dfd47282fc0df9fe1976c
fetch "https://dl-cdn.alpinelinux.org/alpine/v$ALPINE/main/x86_64/apk-tools-static-$APK_TOOLS.apk" \
	"dl/apk-tools-static-$APK_TOOLS.apk" c8e2c88c13ba12a12269b79a3543e1190ff8c0ab0beb32b58cadfd5881c619e3
if [ ! -x dl/apkstatic/sbin/apk.static ]; then
	mkdir -p dl/apkstatic
	tar -xzf "dl/apk-tools-static-$APK_TOOLS.apk" -C dl/apkstatic 2>/dev/null || true
	test -x dl/apkstatic/sbin/apk.static
fi

echo "Ready. Next: bash kconfig.sh (see README.md)."
