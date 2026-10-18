#!/bin/sh
# Run on the reader from a directory containing desktop/.
set -eu
cd "$(dirname "$0")"
apk add xorg-server xf86-video-fbdev xf86-input-evdev xinit openbox \
    xterm font-dejavu matchbox-keyboard xrandr xset xsetroot xinput xdotool \
    python3-tkinter py3-wcwidth mupdf-tools
cp -a desktop/. /
chmod 755 /etc/init.d/e60-desktop /etc/init.d/e60-term /usr/local/bin/e60-session \
    /usr/local/bin/e60-launcher /usr/local/bin/e60-reader /usr/local/bin/e60-refreshd \
    /usr/local/bin/e60-term /usr/local/bin/e60-inputs /usr/local/bin/gui
mkdir -p /mnt/data/books
echo 'Installed. Terminal at boot: rc-update add e60-term default'
echo 'The X desktop starts on demand: type gui in the terminal.'
