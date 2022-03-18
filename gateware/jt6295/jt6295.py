import logging

from migen import *
from litex.soc.cores.dma import WishboneDMAReader
from litex.soc.interconnect import wishbone
from litex.soc.interconnect.csr import AutoCSR, CSRStorage, CSRField, CSRStatus

from gateware.jtframe.sound.pole import Pole


class CenJT6295(Module):
    def __init__(self, tuning_word):
        self.cen   = Signal()

        phase = Signal(32, reset_less=True)
        self.sync += Cat(phase, self.cen).eq(phase + tuning_word)

MSM6295_FREQ = 1e6

class JT6295RomWishboneDMAReader(Module, AutoCSR):
    """ROM DMA

    """
    def __init__(self, bus, base_address=0, with_csr=False):
        assert isinstance(bus, wishbone.Interface)
        assert bus.data_width == 8
        self.bus = bus

        self.i_rom_addr = Signal(18)
        self.o_rom_data = Signal(8)
        self.o_rom_ok = Signal()

        self.base_address = Signal(bus.adr_width, reset=base_address)

        # Submodules
        self.submodules.dma = WishboneDMAReader(bus)

        data_valid = Signal()
        new_address = Signal()
        current_address = Signal(bus.adr_width)
        prev_address = Signal(bus.adr_width)

        self.sync += [
            prev_address.eq(current_address),
            If(self.dma.source.valid, data_valid.eq(1))
        ]
        self.comb += [
            new_address.eq(current_address != prev_address),
            current_address.eq(self.i_rom_addr + self.base_address),
            self.dma.sink.address.eq(current_address)
        ]

        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        fsm.act("IDLE",
                self.o_rom_ok.eq(data_valid),
                If(new_address, self.o_rom_ok.eq(0), NextState("CMD"))
        )
        fsm.act("CMD",
                self.dma.source.ready.eq(1),
                self.dma.sink.valid.eq(1),
                self.dma.sink.last.eq(1),
                If(self.dma.sink.valid & self.dma.sink.ready, NextState("IDLE"))
        )

        self.sync += If(self.dma.source.valid & self.dma.source.ready, self.o_rom_data.eq(self.dma.source.data))

        if with_csr:
            self.add_csr(default_base=base_address)

    def add_csr(self, default_base=0):
        self._base = CSRStorage(self.bus.adr_width, reset=default_base)

        self.comb += self.base_address.eq(self._base.storage)


class JT6295(Module, AutoCSR):
    """JT6295 4 channel ADPCM decoder compatible with OKI 6295, by Jose Tejada (aka jotego)

    Parameters:
    interpol : 0 = no interpolator, 1 = 4x upsampling, LPF at 0.25*pi, 2 = 4x upsampling, LPF at 0.5*pi

    """
    def __init__(self, platform, clk_freq, interpol=1):
        self.platform = platform

        self.o_rom_addr = Signal(18)
        self.i_rom_data = Signal(8)
        self.i_rom_ok = Signal()

        self.ss = Signal()
        self.sample = Signal()
        self.sound = Signal(14)

        self._control = CSRStorage(description="jt6295 control", fields=[
            CSRField('reset', reset=1, size=1, description='Reset'),
            CSRField('ss', reset=0, size=1, description='Sample rate select'),
            CSRField('wr_n', reset=1, size=1, description='Write enable'),
            CSRField('enable_filter', size=1, description="Enable LPF")
        ])
        reset = Signal()
        wr_n = Signal()
        enable_filter = Signal()
        self.comb += [
            reset.eq(self._control.fields.reset),
            self.ss.eq(self._control.fields.ss),
            wr_n.eq(self._control.fields.wr_n),
            enable_filter.eq(self._control.fields.enable_filter)
        ]

        self._din = CSRStorage(8, reset_less=True, description="Data in")
        self._dout = CSRStatus(8, description="Data out")
        din = Signal(8)
        dout = Signal(8)
        self.comb += [
            din.eq(self._din.storage),
            self._dout.status.eq(dout)
        ]

        self.logger = logging.getLogger("JT6295")
        self.logger.info(f'JT6295 clock {MSM6295_FREQ}Hz from {clk_freq}Hz')
        cen = Signal()
        self.submodules.clock_enable = CenJT6295(tuning_word=int((MSM6295_FREQ / clk_freq) * 2 ** 32))
        self.comb += cen.eq(self.clock_enable.cen)

        sound_raw = Signal(len(self.sound))
        self.jt6295_params = dict(
            p_INTERPOL=interpol,
            i_rst=ResetSignal() | reset,
            i_clk=ClockSignal(),
            i_cen=cen,
            i_ss=self.ss,
            i_wrn=wr_n,
            i_din=din,
            o_dout=dout,
            o_rom_addr=self.o_rom_addr,
            i_rom_data=self.i_rom_data,
            i_rom_ok=self.i_rom_ok,
            o_sample=self.sample,
            o_sound=sound_raw
        )

        sound_filtered = Signal(len(self.sound))
        self.submodules.low_pass_filter = low_pass_filter = Pole(platform, ws=len(self.sound))
        self.comb += [
            low_pass_filter.i_sample.eq(self.sample),
            low_pass_filter.sin.eq(sound_raw),
            low_pass_filter.a.eq(Mux(self.ss, 108, 104)),
            sound_filtered.eq(low_pass_filter.sout)
        ]
        self.sync += [
            self.sound.eq(Mux(enable_filter, sound_filtered, sound_raw))
        ]

        self.add_sources(platform)
        

    @staticmethod
    def add_sources(platform):
        platform.add_source_dir("gateware/rtl/jt6295/hdl", recursive=False)
        platform.add_verilog_include_path("gateware/rtl/jt6295/hdl")
        platform.add_source("gateware/rtl/jtframe/hdl/sound/jtframe_fir_mono.v")
        platform.add_source("gateware/rtl/jtframe/hdl/ram/jtframe_dual_ram.v")

    @staticmethod
    def fir_init_paths():
        return [
            "gateware/rtl/jt6295/hdl/jt6295_up4.hex",
            "gateware/rtl/jt6295/hdl/jt6295_up4_soft.hex"
        ]
    
    def do_finalize(self):
        self.specials += Instance("jt6295", **self.jt6295_params)