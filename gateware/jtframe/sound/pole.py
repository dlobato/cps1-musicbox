from migen import *

class Pole(Module):
    """Wraps jtframe_uprate2_fir module:
    module jtframe_pole #(parameter
        WS=16,      // Assuming that the signal is fixed point
        WA=WS/2     // WA is only the decimal part
    )(
        input                      rst,
        input                      clk,
        input                      sample,
        input      signed [WS-1:0] sin,
        input             [WA-1:0] a,    // coefficient, unsigned
        output reg signed [WS-1:0] sout
    );

    """
    def __init__(self, platform,ws=16):
        wa = ws//2
        self.platform = platform

        self.i_sample = Signal()

        self.sin = Signal(ws)
        self.a = Signal(wa)
        self.sout = Signal(ws)

        self.jtframe_pole_params = dict(
            p_WS=ws,
            p_WA=wa,
            i_rst=ResetSignal(),
            i_clk=ClockSignal(),
            i_sample=self.i_sample,
            i_sin=self.sin,
            i_a=self.a,
            o_sout=self.sout
        )

        self.add_sources(platform)
        

    @staticmethod
    def add_sources(platform):
        platform.add_source("gateware/rtl/jtframe/hdl/sound/jtframe_pole.v")
    
    def do_finalize(self):
        self.specials += Instance("jtframe_pole", **self.jtframe_pole_params)