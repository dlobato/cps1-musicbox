#!/usr/bin/env python3

#
# This file is based on https://github.com/litex-hub/litex-boards/blob/master/litex_boards/targets/radiona_ulx3s.py
#
# Copyright (c) 2018-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2018 David Shah <dave@ds0.me>
# SPDX-License-Identifier: BSD-2-Clause

from litex.build.generic_platform import *
from litex.soc.interconnect import wishbone
from migen import *

from litex.build.io import DDROutput

from litex_boards.platforms import radiona_ulx3s

from litex.build.lattice.trellis import trellis_args, trellis_argdict

from litex.soc.cores.clock import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.cores.video import VideoHDMIPHY
from litex.soc.cores.led import LedChaser

from litedram import modules as litedram_modules
from litedram.phy import GENSDRPHY, HalfRateGENSDRPHY

from gateware.soc import CPS1MusicboxSoC
from gateware.dacpwm import DacPWM

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq, sdram_rate="1:1"):
        self.rst = Signal()
        self.clock_domains.cd_sys    = ClockDomain()
        if sdram_rate == "1:2":
            self.clock_domains.cd_sys2x    = ClockDomain()
            self.clock_domains.cd_sys2x_ps = ClockDomain(reset_less=True)
        else:
            self.clock_domains.cd_sys_ps = ClockDomain(reset_less=True)

        # # #

        # Clk / Rst
        clk25 = platform.request("clk25")
        rst   = platform.request("rst")

        # PLL
        self.submodules.pll = pll = ECP5PLL()
        self.comb += pll.reset.eq(rst | self.rst)
        pll.register_clkin(clk25, 25e6)
        pll.create_clkout(self.cd_sys,    sys_clk_freq)
        if sdram_rate == "1:2":
            pll.create_clkout(self.cd_sys2x,    2*sys_clk_freq)
            pll.create_clkout(self.cd_sys2x_ps, 2*sys_clk_freq, phase=180) # Idealy 90° but needs to be increased.
        else:
           pll.create_clkout(self.cd_sys_ps, sys_clk_freq, phase=90)

        # SDRAM clock
        sdram_clk = ClockSignal("sys2x_ps" if sdram_rate == "1:2" else "sys_ps")
        self.specials += DDROutput(1, 0, platform.request("sdram_clock"), sdram_clk)

        # Prevent ESP32 from resetting FPGA
        self.comb += platform.request("wifi_gpio0").eq(1)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(CPS1MusicboxSoC):
    def __init__(self, device="LFE5U-45F", revision="2.0", toolchain="trellis",
        sys_clk_freq=int(50e6), sdram_module_cls="MT48LC16M16", sdram_rate="1:1",
        with_led_chaser=True, with_video_terminal=False,
        with_spi_flash=False, **kwargs):
        platform = radiona_ulx3s.Platform(device=device, revision=revision, toolchain=toolchain)
        platform.add_extension([
            ("audio_out", 0,
             Subsignal("left", Pins("E4 D3 C3 B3"), IOStandard("LVCMOS33"), Misc("DRIVE=16"), Misc("PULLMODE=NONE")),
             Subsignal("right", Pins("A3 B5 D5 C5"), IOStandard("LVCMOS33"), Misc("DRIVE=16"), Misc("PULLMODE=NONE")),
            ),
        ])

        # SoCCore ----------------------------------------------------------------------------------
        CPS1MusicboxSoC.__init__(self, platform, sys_clk_freq,
            ident = "LiteX SoC on ULX3S",
            **kwargs)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq, sdram_rate=sdram_rate)

        # SDR SDRAM --------------------------------------------------------------------------------
        if not self.integrated_main_ram_size:
            sdrphy_cls = HalfRateGENSDRPHY if sdram_rate == "1:2" else GENSDRPHY
            self.submodules.sdrphy = sdrphy_cls(platform.request("sdram"), sys_clk_freq)
            self.add_sdram("sdram",
                phy           = self.sdrphy,
                module        = getattr(litedram_modules, sdram_module_cls)(sys_clk_freq, sdram_rate),
                size          = 0x40000000,
                l2_cache_size = kwargs.get("l2_size", 8192)
            )

        # SPI Flash --------------------------------------------------------------------------------
        if with_spi_flash:
            from litespi.modules import IS25LP128
            from litespi.opcodes import SpiNorFlashOpCodes as Codes
            self.add_spi_flash(mode="4x", module=IS25LP128(Codes.READ_1_1_4))

        # Leds -------------------------------------------------------------------------------------
        if with_led_chaser:
            self.submodules.leds = LedChaser(
                pads         = platform.request_all("user_led"),
                sys_clk_freq = sys_clk_freq)

        # DAC left & right
        self.submodules.dac_left = DacPWM(platform)
        self.submodules.dac_right = DacPWM(platform)
        audio_out_pads = platform.request('audio_out')
        self.comb += [
            self.dac_left.pcm.eq(self.mixer.o_mixed_left[4:16]),
            self.dac_right.pcm.eq(self.mixer.o_mixed_right[4:16]),
            audio_out_pads.left.eq(self.dac_left.dac),
            audio_out_pads.right.eq(self.dac_right.dac)
        ]

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on ULX3S")
    parser.add_argument("--build",           action="store_true",   help="Build bitstream.")
    parser.add_argument("--load",            action="store_true",   help="Load bitstream.")
    parser.add_argument("--toolchain",       default="trellis",     help="FPGA toolchain (trellis or diamond).")
    parser.add_argument("--device",          default="LFE5U-45F",   help="FPGA device (LFE5U-12F, LFE5U-25F, LFE5U-45F or LFE5U-85F).")
    parser.add_argument("--revision",        default="2.0",         help="Board revision (2.0 or 1.7).")
    parser.add_argument("--sys-clk-freq",    default=25e6,          help="System clock frequency.")
    parser.add_argument("--sdram-module",    default="MT48LC16M16", help="SDRAM module (MT48LC16M16, AS4C32M16 or AS4C16M16).")
    parser.add_argument("--with-spi-flash",  action="store_true",   help="Enable SPI Flash (MMAPed).")
    sdopts = parser.add_mutually_exclusive_group()
    sdopts.add_argument("--with-spi-sdcard", action="store_true",   help="Enable SPI-mode SDCard support.")
    sdopts.add_argument("--with-sdcard",     action="store_true",   help="Enable SDCard support.")
    parser.add_argument("--with-oled",       action="store_true",   help="Enable SDD1331 OLED support.")
    parser.add_argument("--sdram-rate",      default="1:1",         help="SDRAM Rate (1:1 Full Rate or 1:2 Half Rate).")
    builder_args(parser)
    soc_core_args(parser)
    trellis_args(parser)
    args = parser.parse_args()

    soc = BaseSoC(
        device                 = args.device,
        revision               = args.revision,
        toolchain              = args.toolchain,
        sys_clk_freq           = int(float(args.sys_clk_freq)),
        sdram_module_cls       = args.sdram_module,
        sdram_rate             = args.sdram_rate,
        with_spi_flash         = args.with_spi_flash,
        **soc_core_argdict(args))
    if args.with_spi_sdcard:
        soc.add_spi_sdcard()
    if args.with_sdcard:
        soc.add_sdcard()
    if args.with_oled:
        soc.add_oled()

    builder = Builder(soc, **builder_argdict(args))
    builder_kargs = trellis_argdict(args) if args.toolchain == "trellis" else {}
    builder.build(**builder_kargs, run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".svf"))

if __name__ == "__main__":
    main()
