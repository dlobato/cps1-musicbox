# CPS1 Musicbox
RISC-V softcore driving CPS1 sound chips YM2151 and MSM6295

## Build & run simulation
Build SoC:
```
$> ./sim.py --with-sdram --no-compile-gateware
```

Build software:
```
$> cd software/vgmplay
$> BUILD_DIR=../../build/sim make
```

Run simulation:
```
$> ./sim.py --with-sdram --sdram-init software/vgmplay/vgmplay.bin
....
....
        __   _ __      _  __
       / /  (_) /____ | |/_/
      / /__/ / __/ -_)>  <
     /____/_/\__/\__/_/|_|
   Build your hardware, easily!

 (c) Copyright 2012-2022 Enjoy-Digital
 (c) Copyright 2007-2015 M-Labs

 BIOS built on Mar 21 2022 19:41:09
 BIOS CRC passed (7415c0be)

 Migen git sha1: ac70301
 LiteX git sha1: 7f49c523

--=============== SoC ==================--
CPU:		VexRiscv @ 24MHz
BUS:		WISHBONE 32-bit @ 4GiB
CSR:		32-bit data
ROM:		128KiB
SRAM:		8KiB
L2:		8KiB
SDRAM:		65536KiB 32-bit @ 24MT/s (CL-2 CWL-2)

--========== Initialization ============--
Initializing SDRAM @0x40000000...
Switching SDRAM to software control.
Switching SDRAM to hardware control.

--============== Boot ==================--
Booting from serial...
Press Q or ESC to abort boot completely.
sL5DdSMmkekro
Timeout
Executing booted program at 0x40000000

--============= Liftoff! ===============--

LiteX vgmplay Mar 21 2022 19:38:40

Enter to play/stop
```

Raw audio samples are written to build/sim/gateware/cps1.raw
To play the raw audio samples use:
```
$> play -r 55000 -b 16 -c 2 -e signed-integer cps1.raw
```

## Radiona ULX3S
Build bitstream:
```
$> ./radiona_ulx3s.py --device LFE5U-85F --build
```

Build software:
```
$> cd software/vgmplay
$> BUILD_DIR=../../build/radiona_ulx3s make
```

Load the bitstream with [openFPGALoader](https://github.com/trabucayre/openFPGALoader):
```
$> openFPGALoader build/radiona_ulx3s/gateware/radiona_ulx3s.bit -b ulx3s
```

Load software:
```
$> litex_term /dev/ttyUSB0 --kernel software/vgmplay/vgmplay.bin
(click reset)
        __   _ __      _  __
       / /  (_) /____ | |/_/
      / /__/ / __/ -_)>  <
     /____/_/\__/\__/_/|_|
   Build your hardware, easily!

 (c) Copyright 2012-2022 Enjoy-Digital
 (c) Copyright 2007-2015 M-Labs

 BIOS built on Mar 24 2022 17:40:23
 BIOS CRC passed (a99a8b5e)

 Migen git sha1: ac70301
 LiteX git sha1: dd7a04a5

--=============== SoC ==================--
CPU:		VexRiscv @ 25MHz
BUS:		WISHBONE 32-bit @ 4GiB
CSR:		32-bit data
ROM:		128KiB
SRAM:		8KiB
L2:		8KiB
SDRAM:		32768KiB 16-bit @ 25MT/s (CL-2 CWL-2)

--========== Initialization ============--
Initializing SDRAM @0x40000000...
Switching SDRAM to software control.
Switching SDRAM to hardware control.
Memtest at 0x40000000 (2.0MiB)...
  Write: 0x40000000-0x40200000 2.0MiB     
   Read: 0x40000000-0x40200000 2.0MiB     
Memtest OK
Memspeed at 0x40000000 (Sequential, 2.0MiB)...
  Write speed: 7.7MiB/s
   Read speed: 10.9MiB/s

--============== Boot ==================--
Booting from serial...
Press Q or ESC to abort boot completely.
sL5DdSMmkekro
[LITEX-TERM] Received firmware download request from the device.
[LITEX-TERM] Uploading software/vgmplay/vgmplay.bin to 0x40000000 (332288 bytes)...
[LITEX-TERM] Upload calibration... (inter-frame: 10.00us, length: 64)
[LITEX-TERM] Upload complete (9.9KB/s).
[LITEX-TERM] Booting the device.
[LITEX-TERM] Done.
Executing booted program at 0x40000000

--============= Liftoff! ===============--

LiteX vgmplay Mar 24 2022 17:47:31

Enter to play/stop
```