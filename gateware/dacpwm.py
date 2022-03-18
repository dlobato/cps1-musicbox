import os

from litex.soc.interconnect.csr import *

class DacPWM(Module):
    def __init__(self, platform, pcm_bits = 12, dac_bits=4):
        self.platform = platform

        self.pcm = Signal(pcm_bits)
        self.dac = Signal(dac_bits)

        self.dacpwm_params = dict(
            p_C_pcm_bits=pcm_bits,
            p_C_dac_bits=dac_bits,
            i_clk=ClockSignal(),
            i_pcm=self.pcm,
            o_dac=self.dac
        )

        self.add_sources(platform)
        

    @staticmethod
    def add_sources(platform):
        vdir = "gateware/rtl/ulx3s-misc/examples/audio/hdl"
        platform.add_source(os.path.join(vdir, "dacpwm.v"))
    
    def do_finalize(self):
        self.specials += Instance("dacpwm", **self.dacpwm_params)