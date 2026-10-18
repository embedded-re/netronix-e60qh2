# Netronix E60QH2 — Hardware Map for a New OS

Collected 2026-10-18 from the live device (root shell over UART, `kstb`), the
eMMC dump (`local/backup/mmcblk0.img`, not in the repository), the stock kernel and U-Boot binaries, and
upstream Linux / postmarketOS sources. Raw probe output is in `hwmap_raw/`.

The resulting port is in [`linux/`](../linux/README.md); section 13 below was
the plan before it.

Legend: **[live]** read from the running device · **[dump]** read from the
image · **[upstream]** read from mainline / pmOS source · **[inferred]** not
directly verified.

---

## 0. TL;DR

* **This is the Netronix KB-E60QH2** (FCC ID NOIKB-E60QH2, sold in Slovakia
  as Telekom / Dibuk-type reader). Board ID in hwconfig: **PCB = `E60QH0`**.
* It is a **near-twin of the Tolino Shine 2 HD** (Netronix E60QF2), which has
  a **mainline device tree** (`imx6sl-tolino-shine2hd.dts`) and a
  postmarketOS port by Andreas Kemnade. Same SoC, same three I²C buses with
  the same chips at the same addresses, same MSP430 firmware (`0xF110`), and
  ~all GPIOs match (differences listed in §11).
* Main difference vs. Shine 2 HD: this unit boots from **soldered eMMC**
  (Samsung SEM04G), the Shine 2 HD from an internal microSD.
* Everything except the E-Ink display has a mainline driver. The display
  (i.MX6SL EPDC) needs Kemnade's out-of-tree driver
  (`linux-kobo-clara-mainline`), plus the waveform blob, which is on this eMMC
  at **0x700000** in the same format the pmOS extractor expects.
* Boot experiments can be done **without writing to the eMMC**: stock U-Boot
  has `bootdelay=1` (interrupt on serial), `fatload/ext4load mmc`, `bootm`,
  `loady` and can read the external microSD.
* OTP boot fuses and SRK hash are all zero → HAB (secure boot) not
  provisioned **[inferred]**, so the i.MX USB serial downloader is a viable
  unbrick path.

---

## 1. SoC / memory

| Item | Value | Src |
|---|---|---|
| SoC | Freescale i.MX6 SoloLite, Cortex-A9 r2p10, NEON/VFPv3 | live |
| Machine (stock kernel) | `Freescale i.MX 6SoloLite NTX Board` (board file `mx6sl_ntx`, no DT) | live |
| CPU OPPs | 396 MHz, 996 MHz (governor interactive) | live |
| RAM | 512 MB LPDDR2 @ 0x80000000 (stock passes `mem=499M`) | live/dump |
| GPU | Vivante GC320 2D + GC355 VG (`galcore`), no 3D | live |
| PXP | present (`imx-pxp`, 0x020F0000) – used for EPD rotation/dither | live |
| Unique ID (OCOTP CFG0/1) | `0x2b37b1d4 e31680c5` | live |
| Thermal calib (ANA1) | `0x5845025f` | live |
| OTP BOOT_CFG (CFG4/CFG5) | `0x0 / 0x0` – boot cfg not fused (GPIO/pin boot) | live |
| SRK0 / HAB | `0x0` – no SRK fused → HAB open **[inferred]** | live |
| Watchdog | imx2-wdt, stock sets 60 s, `nowayout=1` | dump |

### Physical memory map (stock kernel `/proc/iomem`)

```
0x02020000 UART1 (ttymxc0, console)      0x020F4000 EPDC
0x020BC000 WDOG1                          0x020F0000 PXP
0x02184000 USB OTG1 (EHCI/UDC)            0x020FC000 DCP (crypto)
0x02194000 uSDHC2  -> mmc1 = external microSD
0x02198000 uSDHC3  -> mmc2 = WiFi SDIO
0x0219C000 uSDHC4  -> mmc0 = eMMC  (boot_port=3)
0x021A0000 I2C1    0x021A4000 I2C2    0x021A8000 I2C3
0x80000000-0x9D2FFFFF System RAM
0x9D300000-0x9F2FFFFF galcore reserved
0x9F95DA00 waveform (6 567 392 B)  -- copied here by U-Boot
0x9FFA1000 boot logo (388 096 B)   -- copied here by U-Boot
0x9FFFFE00 hwconfig (110 B)        -- copied here by U-Boot
```

The stock kernel gets waveform / logo / hwconfig through RAM handed over by
U-Boot (`waveform_p=`, `logo_p=`, `hwcfg_p=` cmdline). A new kernel should
load the waveform as firmware instead.

---

## 2. Buses and attached chips

| Bus (stock / DT name) | Addr | Chip | Function | IRQ line | Src |
|---|---|---|---|---|---|
| i2c-0 / `&i2c1` | 0x43 | **MSP430** "NTXEC", fw **0xF110** | frontlight PWM, power-off/reset, (battery?) | `MSP_INT` gpio3 27 | live |
| i2c-1 / `&i2c2` | 0x50 | **Neonode zForce** IR touch, fw 0001.0000.0000.0001, v2 cmd set | touch 1448×1072 | gpio5 6 | live |
| i2c-1 / `&i2c2` | 0x68 | **TI TPS65185** rev 0x65 (v1.2) | EPD high-voltage PMIC + temp sensor | gpio2 9 | live |
| i2c-2 / `&i2c3` | 0x32 | **Ricoh RC5T619** | main PMIC, charger, fuel gauge, RTC, ADC | gpio5 11 | live |
| uSDHC4 (mmc0) | — | Samsung **SEM04G** eMMC 3.68 GiB, 8-bit, 52 MHz | system storage | — | live |
| uSDHC2 (mmc1) | — | microSD slot (CD = gpio5 2), 4-bit HS | external SD | gpio5 2 | live |
| uSDHC3 (mmc2) | — | **CyberTAN WC121A2** WiFi (Broadcom, SDIO) | WiFi | WIFI_INT gpio4 31 | live/dump |
| USB OTG1 | — | ChipIdea, gadget + host | adb/MTP, charger detect | — | live |
| UART1 | — | ttymxc0 115200 8N1 | console | — | live |

Absent on this unit: audio codec (`AudioCodec=No`), Bluetooth, light
sensor, G-sensor, pen digitizer (the Waltop driver is in the kernel but no
device answers; `Touch2Ctrl=No`).

---

## 3. NTX hwconfig (sector 1024, `HW CONFIG v2.6`, 62 bytes) [live]

Decoded with the on-device `ntx_hwconfig-static -s /dev/block/mmcblk0`:

| Field | Value | | Field | Value |
|---|---|---|---|---|
| PCB | **E60QH0** | | DisplayCtrl | MX6SL+TPS65185 |
| KeyPad | HOME_Key | | DisplayPanel | 6" Bottom EPD |
| AudioCodec / Amp | No / No | | DisplayResolution | 1448x1072 |
| Wifi | **WC121A2** | | DisplayBusWidth | 8Bits |
| BT / Mobile / GPS / FM | No | | FrontLight | TABLE11+ |
| TouchCtrl | neonode_v2 (IR) | | FrontLight_LEDrv | **SY7201** |
| Touch2Ctrl | No | | FL_PWM | **MSP430** |
| MicroP | MSP430 | | FrontLight_Flags | BootON:OFF, TABLE1X:OFF, EN_INV:ON |
| PMIC / RTC | RC5T619 / RC5T619 | | HallSensor | **TLE4913** |
| Battery | 1500mA | | Led | G (green) |
| RamSize / RAMType | 512MB / LPDDR2 | | PCB_Flags | NO_KeyMatrix, EPD_LV |
| IFlash / ExternalMem | eMMC / Micro SD | | PCB_LVL / REV | A / 0 |
| RootFsType / SysPartType | Ext4 / TYPE12 | | VCOM_10mV | 0 (not stored here) |
| CPU / UIStyle | mx6sl / Android | | **BootOpt** | **ESD:OFF** |

`BootOpt=ESD` most likely gates U-Boot's "Boot from ESD" (external SD)
path. **[inferred]**

---

## 4. eMMC layout [dump]

| Byte offset | Sector | Content |
|---|---|---|
| 0x000000 | 0 | MBR |
| 0x000200 | 1 | Serial `SN-ST001357` (U-Boot reads it for `androidboot.serialno`) |
| 0x000400 | 2 | **U-Boot** (i.MX IVT header `D1 00 20 40`, entry 0x87800660), up to ~0x7FFFF |
| 0x07FFF0 | 1023 end | NTX blob header (magic `fff5afff78563412` + LE length) |
| 0x080000 | 1024 | **hwconfig** `HW CONFIG v2.6` |
| 0x100000 | 2048 | p1 – Android boot.img (kernel 3 655 024 B + ramdisk 177 079 B) – **normal boot** |
| 0x6FFFF0 | 14335 end | NTX blob header, length 0x6435E0 |
| 0x700000 | 14336 | **EPD waveform**, 6 567 392 B, E-Ink WBF, ID `320_R057_AF2701_ED060KG1U1_TC` |
| 0x1100000 | 34816 | Boot logo, 388 096 B |
| 0x1300000 | 38912 | p2 – Android recovery boot.img (7.5 MB ramdisk) |
| — | 104448 | p3 extended |
| — | 106496 | p5 `/system` ext4, 384 MB |
| — | 894960 | p6 `/cache` ext4, 384 MB |
| — | 1683424 | p7 `/data` ext4, 512 MB |
| — | 2734032 | p8 `/device` ext4 "vendor", 8 MB (empty; U-Boot reads its 1st sector as the recovery BCB) |
| — | 2752448 | p9 ext4 named `misc`, damaged superblock, 4 MB |
| — | 2762672 | p10 256 MB, **all zeros** (the old local `waveforms.bin` is this partition, empty) |
| — | 3286967 | p4 vfat user storage 2.1 GB |

Correction to `README.md`: the waveform is **not** in p10. It is in the raw
area at 0x700000.

---

## 5. Boot chain [dump]

**Stock U-Boot 2009.08 (Netronix fork, 2016-05-10).** Default environment:

```
bootdelay=1  baudrate=115200  loadaddr=0x80800000  rd_loadaddr=0x81000000
bootargs_base=setenv bootargs console=ttymxc0,115200 rootwait rw no_console_suspend
bootcmd=run bootcmd_mmc
bootcmd_mmc=run bootargs_base bootargs_mmc;load_ntxkernel; bootm
bootcmd_SD=run bootargs_base bootargs_SD;load_ntxkernel; bootm
bootcmd_recovery=run bootargs_base bootargs_recovery;load_ntxkernel; bootm
KRN_SDNUM_SD=1  KRN_SDNUM_Recovery=0  verify=no
```

The environment CRC is invalid on this unit, so these defaults are what runs.

Useful commands in the stock U-Boot: `mmc`, `mmcinfo`, `fatload/fatls`,
`ext2load/ext4load/ext4ls`, `bootm`, `booti` (Android boot.img), `loady/
loadb/loads` (serial upload), `i2c`, `itest`, `source`/`autoscr`, `saveenv`,
`imxotp`, `download_mode` (enter i.MX USB serial-download ROM mode), NTX
extras (`load_ntxkernel`, `load_ntxbins`, `ntxup`, `ricoh_reg`, `wifi_3v3`,
`hallsensor`, `mf_key`, `get_up_ver`, `get_epdpmic_ver`).

Not present: `bootz`, device-tree support (2009.08 predates it in practice).
To boot a DT kernel, either use a uImage with appended DTB
(`CONFIG_ARM_APPENDED_DTB`), or chain-load a newer U-Boot.

Boot-mode selection strings found: "Detecting Magic keys for recovery /
fastboot", "Boot from ESD", "HW switch boot from ESD", "Boot from SD quick
recovery", "copy soft configs from ESD to ISD". The boot log shows
`ESDin=1, UPGKey=-1, PWRKey=0, USBin=0x0, BootESD=0`. The exact key combo
was not reverse-engineered.

### Verified at the U-Boot prompt (2026-10-18) [live]

Interrupting autoboot on serial gives the prompt `eBR-1A #`.

| Query | Result |
|---|---|
| `bdinfo` | machine id `0x10D4`, boot_params 0x80000100, DRAM 0x80000000 + 512 MB |
| runtime env | same as defaults, except `fastboot_dev=mmc0`, `bootcmd=booti ${fastboot_dev}`, `kernel=uImage` (env size 651/8188) |
| `mmc dev 0` / `mmcinfo 0` | eMMC SEM04G, 3 959 422 976 B, 8-bit DDR, 52 MHz |
| `mmc dev 1` / `mmcinfo 1` | **microSD = U-Boot mmc 1** (SA16G, SD 3.0, 4-bit, 50 MHz) |
| `mmcinfo 2` | no response (uSDHC3 = WiFi SDIO, unpowered) |
| `fatls mmc 1:1` | works (FAT32 partition listed) |
| `ext4ls/ext2ls mmc 1:2` | "Bad partition": the card currently has **only p1** (Linux sees `mmcblk1p1` only), so the Alpine partition that `start_alpine.sh` expects is gone |
| `get_up_ver` | `microp version=0xf110` |
| `get_epdpmic_ver` | fails (TPS65185 not powered at that point) |
| `hallsensor` | 0 (cover open) |
| `mf_rtc` | 2012/01/01 (RTC not set) |
| `mf_adc` | 2450 (battery ADC raw) |

Syntax note: in this U-Boot, `mmc read` works on the *current* device:
`mmc dev 1; mmc read <addr> <blk> <cnt>`.

**Upstream U-Boot used by pmOS for the Shine 2 HD:**
`github.com/akemnade/u-boot-fslc` @ `fcf25705`, `mx6sltolinoshine3_defconfig`
with `DEVICE_TREE=imx6sl-tolino-shine2hd`. pmOS writes `u-boot.imx` at sector
2 and its env at sector 1536, then loads `boot.scr` from partition 1. Note
that this overwrites the area where the stock hwconfig lives; keep the dump.
[upstream]

---

## 6. Display (EPDC) [live/dump]

| Item | Value |
|---|---|
| Panel | E060SCM / **ED060KG1** class (Carta), 6", 1448×1072, 8-bit bus, "bottom" source |
| Stock video mode used | **`PENG060D`**: 85 Hz, pixclk 80 MHz, left 16, right 102, upper 4, lower 4, hsync 28, vsync 2 |
| EPDC timing (stock struct) | vscan_holdoff 4, sdoed_width 10, sdoed_delay 20, sdoez_width 10, sdoez_delay 20, gdclk_hp_offs 562, gdsp_offs 662, gdoe_offs 0, gdclk_offs 225, num_ce 3 |
| Stock fb | `mxc_epdc_fb`, RGB565, virtual 1472×2304, stride 2944 |
| Waveform | eMMC 0x700000, 6 567 392 B, `320_R057_AF2701_ED060KG1U1_TC` |
| EPD PMIC | TPS65185 @ i2c2 0x68 (stock driver `lk_tps65185.c`, not regulator fw) |

EPD GPIOs (mainline notation): VCOM_CTRL gpio2 3, WAKEUP gpio2 7, PWRUP
gpio2 8, INT gpio2 9, PWRGOOD gpio2 13, VIN (PMIC supply) gpio2 14,
EP_3V3_IN gpio4 3. EPDC data D0–D15 = gpio1 7–22, SDCLK/LE/OE/SHR/CE0/CE1 =
gpio1 23–28, GDCLK gpio1 31, GDOE/GDRL/GDSP gpio2 0–2, BDR0 gpio2 5 (pinmux
names from the stock GPIO table).

Mainline status [upstream]:
* `regulator: tps65185` driver merged in 2026-01 (regulator tree), and DT
  wiring for Shine 2 HD / Shine 3 / Clara HD applied the same month.
* The EPDC DRM driver (Kemnade RFC, 2022) is **not merged**; the 2026 cover
  letter says it "still needs polishing". It lives in his near-mainline
  kernel used by pmOS (`linux-kobo-clara-mainline`, 6.8.x).
* pmOS extracts the waveform with `extract-waveform.pl /dev/mmcblk0
  epdc_PENG060D.fw` (checks the `fff5afff78563412` header at 0x700000-16).
  **This unit's dump matches that format exactly.**
* `drivers/video/fbdev` route: the old NXP `mxc_epdc_fb` could also be
  forward-ported, but the DRM driver is the realistic path.

---

## 7. Power

### Ricoh RC5T619 rails (stock values) [live]

| Rail | mV | State | Rail | mV | State |
|---|---|---|---|---|---|
| DC1 | 1400 | on | LDO4 | 1200 | off |
| DC2 | 3300 | on | LDO5 | 3300 | on |
| DC3 | 1425 (950 in suspend) | on | LDO6 | 600 | on |
| DC4 | 1200 | on | LDO7 | 3300 | off |
| DC5 | 1800 | on | LDO8 | 1800 | on |
| LDO1 | 3300 | on | LDO9 | 1200 | off |
| LDO2 | 3300 | on | LDO10 | 1400 | off |
| LDO3 | 1200 | on | LDORTC1/2 | 3300 / 3300 | on / off |

SoC internal (anatop): vddcore 1250, vddsoc 1150, vdd2p5 2400, vdd1p1 1100,
vdd3p0 3200, vddpu off.

* Battery: Li-ion 1500 mAh. Stock exposes it as `mc13892_bat` (name only;
  the data comes from the Ricoh fuel gauge). Mainline: `rn5t618` MFD +
  `rn5t618_power` charger/gauge driver (supports RC5T619).
* RTC: Ricoh RC5T619 (mainline `rtc-rc5t619`).
* Charger detect: Ricoh ADP/USB IRQs, `MX6SL_NTX_ACIN_PG` gpio5 14,
  `MX6SL_NTX_CHG` gpio5 15, `MX6SL_BAT_LOW` gpio3 28.
* Power-off/reset goes through the MSP430 (mainline `ntxec` registers
  pm_power_off + restart handler).

---

## 8. Input [live]

| Source | Event codes | GPIO (mainline) |
|---|---|---|
| Power button | KEY_POWER | gpio5 8 (active low) |
| Home button | KEY_HOME | **gpio3 24** (Shine2HD DT says gpio3 25 – verify) |
| Hall sensor TLE4913 (cover) | SW_LID | gpio5 12 |
| gpio-keys also advertises | KEY_H (0x23), KEY_F1 (0x3b) | not mapped to a claimed GPIO **[unclear]** |
| zForce touch | ABS_X/Y 0–1448/0–1072, MT slots, BTN_TOUCH | INT gpio5 6, RST gpio5 9 |

Mainline: `zforce_ts` driver (`neonode,zforce`).

---

## 9. Frontlight and LEDs [live]

* Frontlight PWM from the MSP430 (stock `mxc_msp430_fl.0`, brightness 0–100),
  LED driver SY7201, enable `MX6SL_FL_EN` gpio2 10, boost/R_EN `FL_R_EN`
  gpio1 29. Mainline: `ntxec` PWM → `pwm-backlight`, as in the Shine 2 HD
  DT.
* LEDs: `MX6SL_ON_LED` gpio5 7 (output), `MX6SL_CHG_LED` gpio5 10 (input
  in stock = maybe hardware-driven charge LED). The Shine 2 HD DT puts the
  "on" LED at gpio5 13 – **differs, verify**.

---

## 10. WiFi [dump/live]

* Module CyberTAN **WC121A2**, Broadcom SDIO chip from the BCM4336 family
  (nvram: "Copied from bcm94336sdg.txt", `manfid=0x2d0`, `boardtype=0x0598`,
  26 MHz crystal). Stock driver `bcmdhd` 5.90.125, firmware
  `/system/lib/firmware/wc121/rtecdc.bin` (5.90.195.89.23) + `nvram.txt`.
* Bus: uSDHC3. Power: `MX6SL_WIFI_3V3` gpio4 29, reset `MX6SL_WIFI_RST`
  gpio5 0, host-wake `MX6SL_WIFI_INT` gpio4 31. These match the Shine 2 HD
  DT (`reg_wifi` gpio4 29 active-low, pwrseq reset gpio5 0).
* Mainline: `brcmfmac`. The exact SDIO chip ID was **not read** (WiFi was
  powered off). Likely `brcmfmac43362-sdio.bin`; confirm by powering WiFi in
  Android and reading `/sys/bus/sdio/devices/*/device`.
* The nvram from `/system` must be renamed to
  `brcmfmac<chip>-sdio.kobo,tolino-shine2hd.txt` (or your new compatible).

---

## 11. Full GPIO table (stock names → mainline `gpioN M`) [live]

Stock numbers are global (0-based); mainline bank = n/32+1, line = n%32.

| Stock # | Mainline | Name | Dir/level | Matches Shine2HD DT? |
|---|---|---|---|---|
| 29 | gpio1 29 | MX6SL_FL_R_EN | in lo | yes (backlightboost LED) |
| 35 | gpio2 3 | tps65185_VCOMCTRL | out lo | yes |
| 39 | gpio2 7 | tps65185_WAKEUP | out hi | yes |
| 40 | gpio2 8 | tps65185_PWRUP | out lo | yes |
| 41 | gpio2 9 | tps65185_INT | in hi | yes |
| 42 | gpio2 10 | MX6SL_FL_EN | out lo | yes (backlight regulator) |
| 45 | gpio2 13 | tps65185_PWRGOOD | in lo | yes |
| 46 | gpio2 14 | tps65185_VIN | out hi | yes (epd_pmic_supply) |
| 88 | gpio3 24 | btn home | in hi | **DT uses gpio3 25** |
| 91 | gpio3 27 | msp430_int (IRQ) | — | — |
| 92 | gpio3 28 | MX6SL_BAT_LOW | in hi | — |
| 98,100–103 | gpio4 2,4–7 | MX6SL_HW_ID0..4 | in (=0b00001) | — |
| 99 | gpio4 3 | tps65185_EP_3V3_IN | out hi | — |
| 125 | gpio4 29 | MX6SL_WIFI_3V3 | in hi | yes |
| 127 | gpio4 31 | MX6SL_WIFI_INT | in lo | — |
| 128 | gpio5 0 | MX6SL_WIFI_RST | out lo | yes |
| 130 | gpio5 2 | ESDHC_CD (microSD detect) | in lo | — |
| 134 | gpio5 6 | MX6SL_IR_TOUCH_INT | in hi | yes |
| 135 | gpio5 7 | MX6SL_ON_LED | out lo | **DT uses gpio5 13** |
| 136 | gpio5 8 | btn power | in hi | yes |
| 137 | gpio5 9 | MX6SL_IR_TOUCH_RST | in hi | yes |
| 138 | gpio5 10 | MX6SL_CHG_LED | in hi | — |
| 139 | gpio5 11 | MX6SL_MSP_INT (used as Ricoh IRQ) | in hi | yes (rc5t619 irq) |
| 140 | gpio5 12 | TLE4913 hall | in hi | yes (SW_LID) |
| 142 | gpio5 14 | MX6SL_NTX_ACIN_PG | in lo | — |
| 143 | gpio5 15 | MX6SL_NTX_CHG | in lo | — |
| 144–149 | gpio5 16–21 | SD3 DAT0-3/CLK/CMD (parked as GPIO while WiFi off) | out lo | — |
| 224–228 | — | Ricoh RC5T619 GPIO expander (5 lines) | — | — |

---

## 12. Stock kernel facts [live/dump]

* Linux 3.0.35 (NXP L3.0.35 BSP + Netronix), gcc 4.4.3, no device tree.
  Full config in `hwmap_raw/config.txt` (from `/proc/config.gz`).
* Custom char devices: `/dev/ntx_io` (misc minor 190, Netronix ioctl
  interface used by the Android apps), `/dev/pxp_device`.
* WiFi module loaded by `libhardware_legacy` from `/system/wifi/bcmdhd.ko`.
* No sound card, no Bluetooth.

---

## 13. Paths to a new OS (recommendation)

1. **Kernel:** start from Kemnade's near-mainline tree (pmOS
   `linux-kobo-clara-mainline`), which has EPDC + TPS65185 + ntxec +
   rn5t618. Copy `imx6sl-tolino-shine2hd.dts` to e.g.
   `imx6sl-netronix-e60qh2.dts` and fix the deltas: eMMC on uSDHC4 (8-bit,
   non-removable) instead of the internal microSD, home key gpio3 24,
   "on" LED gpio5 7, and check KEY_F1 / KEY_H sources.
2. **First boot without touching eMMC:** interrupt stock U-Boot on serial
   (bootdelay 1), then either:
   * `fatload mmc 1 0x80800000 uImage` (kernel built with appended DTB) and
     `bootm`, or
   * load a newer U-Boot (akemnade u-boot-fslc) into RAM from the microSD
     and jump to it, which gives `bootz` + DT + distro boot.

   The external SD is **mmc 1** (verified). Use the FAT partition
   (`fatload mmc 1:1 ...`) or recreate an ext4 p2; this U-Boot has
   `ext4load`.
3. **Waveform:** read 6 567 392 B from eMMC 0x700000 into
   `/lib/firmware/imx/epdc/epdc_PENG060D.fw` (pmOS script works as-is).
4. **Userspace:** no audio or GPU 3D, so a framebuffer/DRM-direct UI fits:
   KOReader (has generic Linux/EPDC support), Plato, InkBox, or a custom
   app on top of the DRM EPDC driver.
5. **Permanent install (later):** replace U-Boot at sector 2 and keep
   p1/hwconfig/waveform areas intact, or repartition. Recovery: the full
   eMMC dump, plus `download_mode` / i.MX USB serial downloader (`uuu`,
   `imx_usb_loader`), since HAB appears unfused.

### Still to verify on hardware

* Exact SDIO chip ID of the WC121 (power WiFi on once in Android).
* Home button and LED GPIOs vs. the Shine 2 HD DT (press-test with
  `cat /sys/kernel/debug/gpio`).
* What produces KEY_F1 / KEY_H.
* U-Boot "Boot from ESD" trigger.
* Pinmux pad settings (only derivable from the stock board file; the
  Shine 2 HD DT pinctrl is the best starting point).
* UART headers 2–4.

---

## Sources

* Mainline DTS: https://github.com/torvalds/linux/blob/master/arch/arm/boot/dts/nxp/imx/imx6sl-tolino-shine2hd.dts
* ntxec versions (`0xf110` = Tolino Shine 2 HD): https://github.com/torvalds/linux/blob/master/include/linux/mfd/ntxec.h
* Shine 2 HD DTS series: https://lkml.iu.edu/hypermail/linux/kernel/2008.3/04801.html
* TPS65185 DT wiring (2026-01): https://lkml.iu.edu/2601.1/13569.html
* TPS65185 regulator driver: https://lkml.iu.edu/2601.0/00481.html
* EPDC DRM RFC: https://patchew.org/linux/20220206080016.796556-1-andreas@kemnade.info/
* pmOS Shine 2 HD port: https://gitlab.postmarketos.org/postmarketOS/pmaports/-/commit/24b152725f1feae6f8ed3c19b7d23a5951d1e232
* pmOS kernel pkg: https://pkgs.postmarketos.org/package/master/postmarketos/armv7/linux-kobo-clara-mainline
* FCC ID: https://fccid.io/NOIKB-E60QH2
