from migen import *

class Uprate2Fir(Module):
    """Wraps jtframe_uprate2_fir module:
    module jtframe_uprate2_fir(
        input         rst,
        input         clk,
        input         sample,
        output reg    upsample,
        input  signed [15:0] l_in,
        input  signed [15:0] r_in,
        output signed [15:0] l_out,
        output signed [15:0] r_out
    );

    """
    def __init__(self, platform):
        self.platform = platform

        self.i_sample = Signal()
        self.o_upsample = Signal()

        self.l_in = Signal(16)
        self.r_in = Signal(16)

        self.l_out = Signal(16)
        self.r_out = Signal(16)

        self.jtframe_uprate2_fir_params = dict(
            i_rst=ResetSignal(),
            i_clk=ClockSignal(),
            i_sample=self.i_sample,
            o_upsample=self.o_upsample,
            i_l_in=self.l_in,
            i_r_in=self.r_in,
            o_l_out=self.l_out,
            o_r_out=self.r_out
        )

        self.add_sources(platform)
        

    @staticmethod
    def add_sources(platform):
        platform.add_source("gateware/rtl/jtframe/hdl/sound/jtframe_uprate2_fir.v")
        platform.add_source("gateware/rtl/jtframe_fir.v")

    @staticmethod
    def fir_init_paths():
        return [
            "gateware/rtl/jtframe/hdl/sound/uprate2.hex"
        ]
    
    def do_finalize(self):
        self.specials += Instance("jtframe_uprate2_fir", **self.jtframe_uprate2_fir_params)