#!/usr/bin/env python3

#
# This file is based on https://github.com/enjoy-digital/litex/blob/master/litex/tools/litex_sim.py
#
# Copyright (c) 2015-2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2020 Antmicro <www.antmicro.com>
# Copyright (c) 2017 Pierre-Olivier Vauboin <po@lambdaconcept>
# SPDX-License-Identifier: BSD-2-Clause

from litex.build.generic_platform import *
from litex.build.sim import SimPlatform
from litex.build.sim.config import SimConfig
from litex.build.sim.verilator import verilator_build_args, verilator_build_argdict

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.cores.cpu import CPUS

from litedram import modules as litedram_modules
from litedram.modules import parse_spd_hexdump
from litedram.phy.model import sdram_module_nphases
from litedram.phy.model import SDRAMPHYModel

from litescope import LiteScopeAnalyzer

from gateware.daodump import DaoDump

# IOs ----------------------------------------------------------------------------------------------
from gateware.jt6295.jt6295 import JT6295
from gateware.jtframe.sound.uprate2_fir import Uprate2Fir
from gateware.soc import CPS1MusicboxSoC

_io = [
    # Clk / Rst.
    ("sys_clk", 0, Pins(1)),
    ("sys_rst", 0, Pins(1)),

    # Serial.
    ("serial", 0,
        Subsignal("source_valid", Pins(1)),
        Subsignal("source_ready", Pins(1)),
        Subsignal("source_data",  Pins(8)),

        Subsignal("sink_valid",   Pins(1)),
        Subsignal("sink_ready",   Pins(1)),
        Subsignal("sink_data",    Pins(8)),
    )
]

# Platform -----------------------------------------------------------------------------------------

class Platform(SimPlatform):
    def __init__(self):
        SimPlatform.__init__(self, "SIM", _io)

# Simulation SoC -----------------------------------------------------------------------------------

class SimSoC(CPS1MusicboxSoC):
    mem_map = {**SoCCore.mem_map, **{"spiflash": 0x80000000}}
    def __init__(self,
        with_sdram            = False,
        with_analyzer         = False,
        sdram_module          = "MT48LC16M16",
        sdram_init            = [],
        sdram_data_width      = 32,
        sdram_spd_data        = None,
        sdram_verbosity       = 0,
        with_spi_flash        = False,
        spi_flash_init        = [],
        sim_debug             = False,
        trace_reset_on        = False,
        **kwargs):
        platform     = Platform()
        sys_clk_freq = int(24e6)

        # SoCCore ----------------------------------------------------------------------------------
        CPS1MusicboxSoC.__init__(self, platform, clk_freq=sys_clk_freq,
            ident = "LiteX Simulation",
            **kwargs)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = CRG(platform.request("sys_clk"))

        # SDRAM ------------------------------------------------------------------------------------
        if not self.integrated_main_ram_size and with_sdram:
            sdram_clk_freq = int(100e6) # FIXME: use 100MHz timings
            if sdram_spd_data is None:
                sdram_module_cls = getattr(litedram_modules, sdram_module)
                sdram_rate       = "1:{}".format(sdram_module_nphases[sdram_module_cls.memtype])
                sdram_module     = sdram_module_cls(sdram_clk_freq, sdram_rate)
            else:
                sdram_module = litedram_modules.SDRAMModule.from_spd_data(sdram_spd_data, sdram_clk_freq)
            self.submodules.sdrphy = SDRAMPHYModel(
                module     = sdram_module,
                data_width = sdram_data_width,
                clk_freq   = sdram_clk_freq,
                verbosity  = sdram_verbosity,
                init       = sdram_init)
            self.add_sdram("sdram",
                phy                     = self.sdrphy,
                module                  = sdram_module,
                origin                  = self.mem_map["main_ram"],
                size                    = kwargs.get("max_sdram_size", 0x40000000),
                l2_cache_size           = kwargs.get("l2_size", 8192),
                l2_cache_min_data_width = kwargs.get("min_l2_data_width", 128),
                l2_cache_reverse        = False
            )
            if sdram_init != []:
                # Skip SDRAM test to avoid corrupting pre-initialized contents.
                self.add_constant("SDRAM_TEST_DISABLE")
            else:
                # Reduce memtest size for simulation speedup
                self.add_constant("MEMTEST_DATA_SIZE", 8*1024)
                self.add_constant("MEMTEST_ADDR_SIZE", 8*1024)

        # SPI Flash --------------------------------------------------------------------------------
        if with_spi_flash:
            from litespi.phy.model import LiteSPIPHYModel
            from litespi.modules import S25FL128L
            from litespi.opcodes import SpiNorFlashOpCodes as Codes
            spiflash_module = S25FL128L(Codes.READ_1_1_4)
            if spi_flash_init is None:
                platform.add_sources(os.path.abspath(os.path.dirname(__file__)), "../build/sim/verilog/iddr_verilog.v")
                platform.add_sources(os.path.abspath(os.path.dirname(__file__)), "../build/sim/verilog/oddr_verilog.v")
            self.submodules.spiflash_phy = LiteSPIPHYModel(spiflash_module, init=spi_flash_init)
            self.add_spi_flash(phy=self.spiflash_phy, mode="4x", module=spiflash_module, with_master=True)

        # DAO
        self.submodules.dao_dump = DaoDump(platform, dump_file_name="cps1.raw")
        self.comb += [
            self.dao_dump.sample.eq(self.jt51.sample),
            self.dao_dump.left.eq(self.mixer.o_mixed_left),
            self.dao_dump.right.eq(self.mixer.o_mixed_right)
        ]

        # Simulation debugging ----------------------------------------------------------------------
        if sim_debug:
            platform.add_debug(self, reset=1 if trace_reset_on else 0)
        else:
            self.comb += platform.trace.eq(1)

        # Analyzer ---------------------------------------------------------------------------------
        if with_analyzer:
            analyzer_signals = [
                # IBus (could also just added as self.cpu.ibus)
                self.cpu.ibus.stb,
                self.cpu.ibus.cyc,
                self.cpu.ibus.adr,
                self.cpu.ibus.we,
                self.cpu.ibus.ack,
                self.cpu.ibus.sel,
                self.cpu.ibus.dat_w,
                self.cpu.ibus.dat_r,
                # DBus (could also just added as self.cpu.dbus)
                self.cpu.dbus.stb,
                self.cpu.dbus.cyc,
                self.cpu.dbus.adr,
                self.cpu.dbus.we,
                self.cpu.dbus.ack,
                self.cpu.dbus.sel,
                self.cpu.dbus.dat_w,
                self.cpu.dbus.dat_r,
            ]
            self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals,
                depth        = 512,
                clock_domain = "sys",
                csr_csv      = "analyzer.csv")

# Build --------------------------------------------------------------------------------------------

def generate_gtkw_savefile(builder, vns, trace_fst):
    from litex.build.sim import gtkwave as gtkw
    dumpfile = os.path.join(builder.gateware_dir, "sim.{}".format("fst" if trace_fst else "vcd"))
    savefile = os.path.join(builder.gateware_dir, "sim.gtkw")
    soc = builder.soc

    with gtkw.GTKWSave(vns, savefile=savefile, dumpfile=dumpfile) as save:
        save.clocks()
        save.fsm_states(soc)
        if "main_ram" in soc.bus.slaves.keys():
            save.add(soc.bus.slaves["main_ram"], mappers=[gtkw.wishbone_sorter(), gtkw.wishbone_colorer()])

        if hasattr(soc, "sdrphy"):
            # all dfi signals
            save.add(soc.sdrphy.dfi, mappers=[gtkw.dfi_sorter(), gtkw.dfi_in_phase_colorer()])

            # each phase in separate group
            with save.gtkw.group("dfi phaseX", closed=True):
                for i, phase in enumerate(soc.sdrphy.dfi.phases):
                    save.add(phase, group_name="dfi p{}".format(i), mappers=[
                        gtkw.dfi_sorter(phases=False),
                        gtkw.dfi_in_phase_colorer(),
                    ])

            # only dfi command/data signals
            def dfi_group(name, suffixes):
                save.add(soc.sdrphy.dfi, group_name=name, mappers=[
                    gtkw.regex_filter(gtkw.suffixes2re(suffixes)),
                    gtkw.dfi_sorter(),
                    gtkw.dfi_per_phase_colorer(),
                ])

            dfi_group("dfi commands", ["cas_n", "ras_n", "we_n"])
            dfi_group("dfi commands", ["wrdata"])
            dfi_group("dfi commands", ["wrdata_mask"])
            dfi_group("dfi commands", ["rddata"])

def sim_args(parser):

    builder_args(parser)
    soc_core_args(parser)
    verilator_build_args(parser)
    parser.add_argument("--rom-init",             default=None,            help="ROM init file (.bin or .json).")
    parser.add_argument("--ram-init",             default=None,            help="RAM init file (.bin or .json).")
    parser.add_argument("--with-sdram",           action="store_true",     help="Enable SDRAM support.")
    parser.add_argument("--sdram-module",         default="MT48LC16M16",   help="Select SDRAM chip.")
    parser.add_argument("--sdram-data-width",     default=32,              help="Set SDRAM chip data width.")
    parser.add_argument("--sdram-init",           default=None,            help="SDRAM init file (.bin or .json).")
    parser.add_argument("--sdram-from-spd-dump",  default=None,            help="Generate SDRAM module based on data from SPD EEPROM dump.")
    parser.add_argument("--sdram-verbosity",      default=0,               help="Set SDRAM checker verbosity.")
    parser.add_argument("--with-analyzer",        action="store_true",     help="Enable Analyzer support.")
    parser.add_argument("--with-i2c",             action="store_true",     help="Enable I2C support.")
    parser.add_argument("--with-sdcard",          action="store_true",     help="Enable SDCard support.")
    parser.add_argument("--with-spi-flash",       action="store_true",     help="Enable SPI Flash (MMAPed).")
    parser.add_argument("--spi_flash-init",       default=None,            help="SPI Flash init file.")
    parser.add_argument("--with-gpio",            action="store_true",     help="Enable Tristate GPIO (32 pins).")
    parser.add_argument("--sim-debug",            action="store_true",     help="Add simulation debugging modules.")
    parser.add_argument("--gtkwave-savefile",     action="store_true",     help="Generate GTKWave savefile.")
    parser.add_argument("--non-interactive",      action="store_true",     help="Run simulation without user input.")

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC Simulation utility")
    sim_args(parser)
    args = parser.parse_args()

    soc_kwargs             = soc_core_argdict(args)
    builder_kwargs         = builder_argdict(args)
    verilator_build_kwargs = verilator_build_argdict(args)

    sys_clk_freq = int(1e6)
    sim_config   = SimConfig()
    sim_config.add_clocker("sys_clk", freq_hz=sys_clk_freq)

    # Configuration --------------------------------------------------------------------------------

    cpu = CPUS.get(soc_kwargs.get("cpu_type", "vexriscv"))

    # UART.
    if soc_kwargs["uart_name"] == "serial":
        soc_kwargs["uart_name"] = "sim"
        sim_config.add_module("serial2console", "serial")

    # ROM.
    if args.rom_init:
        soc_kwargs["integrated_rom_init"] = get_mem_data(args.rom_init, endianness=cpu.endianness)

    # RAM / SDRAM.
    soc_kwargs["integrated_main_ram_size"] = args.integrated_main_ram_size
    if args.integrated_main_ram_size:
        if args.ram_init is not None:
            soc_kwargs["integrated_main_ram_init"] = get_mem_data(args.ram_init, endianness=cpu.endianness)
    elif args.with_sdram:
        assert args.ram_init is None
        soc_kwargs["sdram_module"]     = args.sdram_module
        soc_kwargs["sdram_data_width"] = int(args.sdram_data_width)
        soc_kwargs["sdram_verbosity"]  = int(args.sdram_verbosity)
        if args.sdram_from_spd_dump:
            soc_kwargs["sdram_spd_data"] = parse_spd_hexdump(args.sdram_from_spd_dump)

    # SoC ------------------------------------------------------------------------------------------
    soc = SimSoC(
        with_sdram         = args.with_sdram,
        with_analyzer      = args.with_analyzer,
        with_i2c           = args.with_i2c,
        with_sdcard        = args.with_sdcard,
        with_spi_flash     = args.with_spi_flash,
        with_gpio          = args.with_gpio,
        sim_debug          = args.sim_debug,
        trace_reset_on     = int(float(args.trace_start)) > 0 or int(float(args.trace_end)) > 0,
        sdram_init         = []   if args.sdram_init     is None else get_mem_data(args.sdram_init,     endianness=cpu.endianness),
        spi_flash_init     = None if args.spi_flash_init is None else get_mem_data(args.spi_flash_init, endianness="big"),
        **soc_kwargs)
    if args.ram_init is not None or args.sdram_init is not None:
        soc.add_constant("ROM_BOOT_ADDRESS", soc.mem_map["main_ram"])

    # Build/Run ------------------------------------------------------------------------------------
    def pre_run_callback(vns):
        if args.trace:
            generate_gtkw_savefile(builder, vns, args.trace_fst)

    builder_kwargs["csr_csv"] = "csr.csv"
    builder = Builder(soc, **builder_kwargs)
    init_paths = JT6295.fir_init_paths() + Uprate2Fir.fir_init_paths()
    for f in init_paths:
        shutil.copy(f, builder.gateware_dir)
    builder.build(
        sim_config       = sim_config,
        interactive      = not args.non_interactive,
        pre_run_callback = pre_run_callback,
        **verilator_build_kwargs,
    )

if __name__ == "__main__":
    main()
