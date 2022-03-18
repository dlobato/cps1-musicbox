import logging
import os

from migen import *
from litex.soc.interconnect.csr_eventmanager import EventManager, EventSourceLevel
from litex.soc.interconnect.csr import AutoCSR, CSRStorage, CSRField, CSRStatus

class CenJT51(Module):
    def __init__(self, tuning_word):
        self.cen   = Signal()
        self.cen_p1   = Signal()

        phase = Signal(32, reset_less=True)
        self.sync += Cat(phase, self.cen).eq(phase + tuning_word)

        half = Signal(reset=1)
        self.sync += If(self.cen, half.eq(~half))
        self.comb += self.cen_p1.eq(self.cen & half)

YM2151_FREQ = 3570000

class JT51(Module, AutoCSR):
    def __init__(self, platform, clk_freq, with_irq=False):
        assert(clk_freq > YM2151_FREQ)
        self.platform = platform

        self.ct1 = Signal()
        self.ct2 = Signal()
        self.irq_n = Signal()
        self.sample = Signal()
        self.left = Signal(16)
        self.right = Signal(16)
        self.xleft = Signal(16)
        self.xright = Signal(16)
        self.dacleft = Signal(16)
        self.dacright = Signal(16)


        self._control = CSRStorage(description="jt51 control", fields=[
            CSRField('reset', reset=1, size=1, description='Reset'),
            CSRField('cs_n', reset=1, size=1, description='Chip select'),
            CSRField('wr_n', reset=1, size=1, description='Write'),
            CSRField('a0', reset=1, size=1, description='A0'),
        ])
        reset = Signal()
        cs_n = Signal()
        wr_n = Signal()
        a0 = Signal()
        self.comb += [
            reset.eq(self._control.fields.reset),
            cs_n.eq(self._control.fields.cs_n),
            wr_n.eq(self._control.fields.wr_n),
            a0.eq(self._control.fields.a0)
        ]

        self._din = CSRStorage(8, reset_less=True, description="Data in")
        self._dout = CSRStatus(8, description="Data out")
        din = Signal(8)
        dout = Signal(8)
        self.comb += [
            din.eq(self._din.storage),
            self._dout.status.eq(dout)
        ]

        self.logger = logging.getLogger("JT51")
        self.logger.info(f'JT51 clock {YM2151_FREQ}Hz from {clk_freq}Hz')
        cen = Signal()
        cen_p1 = Signal()
        self.submodules.clock_enable = CenJT51(tuning_word=int((YM2151_FREQ / clk_freq) * 2 ** 32))
        self.comb += [
            cen.eq(self.clock_enable.cen),
            cen_p1.eq(self.clock_enable.cen_p1),
        ]

        self.jt51_params = dict(
            i_rst=ResetSignal() | reset,
            i_clk=ClockSignal(),
            i_cen=cen,
            i_cen_p1=cen_p1,
            i_cs_n=cs_n,
            i_wr_n=wr_n,
            i_a0=a0,
            i_din=din,
            o_dout=dout,
            o_ct1=self.ct1,
            o_ct2=self.ct2,
            o_irq_n=self.irq_n,
            o_sample=self.sample,
            o_left=self.left,
            o_right=self.right,
            o_xleft=self.xleft,
            o_xright=self.xright,
            o_dacleft=self.dacleft,
            o_dacright=self.dacright
        )

        self.add_sources(platform)

        if with_irq:
            self.submodules.ev = EventManager()
            self.ev.j51_irq = EventSourceLevel(description="JT51 irq")
            self.ev.finalize()

            self.comb += self.ev.j51_irq.trigger.eq(~self.irq_n)
        

    @staticmethod
    def add_sources(platform):
        vdir = "gateware/rtl/jt51"
        platform.add_source_dir(os.path.join(vdir, "hdl"), recursive=False)
        platform.add_verilog_include_path(os.path.join(vdir, "hdl"))
    
    def do_finalize(self):
        self.specials += Instance("jt51", **self.jt51_params)