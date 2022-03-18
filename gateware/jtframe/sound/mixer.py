
from migen import *
from litex.soc.interconnect.csr import AutoCSR, CSRStorage, CSRField


class Mixer(Module):
    """Generic mixer by Jose Tejada (aka jotego)

    """
    def __init__(self, platform, w=(16, 16, 16, 16), wout=16):
        self.platform = platform

        self.i_cen = Signal()
        self.i_ch0 = Signal(w[0])
        self.i_ch1 = Signal(w[1])
        self.i_ch2 = Signal(w[2])
        self.i_ch3 = Signal(w[3])
        self.i_gain0 = Signal(8)
        self.i_gain1 = Signal(8)
        self.i_gain2 = Signal(8)
        self.i_gain3 = Signal(8)
        self.o_mixed = Signal(wout)
        self.o_peak = Signal()

        self.jtframe_mixer_params = dict(
            p_W0=w[0],
            p_W1=w[1],
            p_W2=w[2],
            p_W3=w[3],
            p_WOUT=wout,
            i_rst=ResetSignal(),
            i_clk=ClockSignal(),
            i_cen=self.i_cen,
            i_ch0=self.i_ch0,
            i_ch1=self.i_ch1,
            i_ch2=self.i_ch2,
            i_ch3=self.i_ch3,
            i_gain0=self.i_gain0,
            i_gain1=self.i_gain1,
            i_gain2=self.i_gain2,
            i_gain3=self.i_gain3,
            o_mixed=self.o_mixed,
            o_peak=self.o_peak
        )

        self.add_sources(platform)
        

    @staticmethod
    def add_sources(platform):
        platform.add_source("gateware/rtl/jtframe/hdl/sound/jtframe_mixer.v")
    
    def do_finalize(self):
        self.specials += Instance("jtframe_mixer", **self.jtframe_mixer_params)

class CPS1StereoMixer(Module, AutoCSR):
    """"
    """
    def __init__(self, platform, win=16, wout=16, fmgain_value=6):
        self.i_fm_left = Signal(win)
        self.i_fm_right = Signal(win)
        self.i_pcm_left = Signal(win)
        self.i_pcm_right = Signal(win)

        self.o_mixed_left = Signal(wout)
        self.o_mixed_right = Signal(wout)
        self.o_peak = Signal()

        self._control = CSRStorage(description="jt51 control", fields=[
            CSRField('enable_pcm', reset=0, size=1, description='Enable pcm channel'),
            CSRField('enable_fm', reset=0, size=1, description='Enable fm channel'),
            CSRField('pcm_level', reset=0, size=2, description='Controls pcm channel level'),
        ])
        peak_left = Signal()
        peak_right = Signal()
        enable_pcm = Signal()
        enable_fm = Signal()
        fx_level = Signal(2)
        fm_gain = Signal(8)
        pcm_gain = Signal(8)
        self.comb += [
            enable_pcm.eq(self._control.fields.enable_pcm),
            enable_fm.eq(self._control.fields.enable_fm),
            fx_level.eq(self._control.fields.pcm_level),
            fm_gain.eq(Mux(enable_fm, fmgain_value, 0)),
        ]
        self.sync += [
            self.o_peak.eq(peak_left | peak_right),
            If(enable_pcm,
               Case(fx_level, {
                   0: pcm_gain.eq(0x04),
                   1: pcm_gain.eq(0x08),
                   2: pcm_gain.eq(0x0c),
                   3: pcm_gain.eq(0x10),
               })
            ).Else(
                pcm_gain.eq(0)
            )
        ]

        self.submodules.mixer_left = mixer_left = Mixer(platform, (win,) * 4, wout)
        self.comb += [
            mixer_left.i_cen.eq(1),
            mixer_left.i_ch0.eq(self.i_fm_left),
            mixer_left.i_ch1.eq(self.i_pcm_left),
            mixer_left.i_ch2.eq(0),
            mixer_left.i_ch3.eq(0),
            mixer_left.i_gain0.eq(fm_gain),
            mixer_left.i_gain1.eq(pcm_gain),
            mixer_left.i_gain2.eq(0),
            mixer_left.i_gain3.eq(0),
            self.o_mixed_left.eq(mixer_left.o_mixed),
            peak_left.eq(mixer_left.o_peak)
        ]

        self.submodules.mixer_right = mixer_right = Mixer(platform, (win,) * 4, wout)
        self.comb += [
            mixer_right.i_cen.eq(1),
            mixer_right.i_ch0.eq(self.i_fm_right),
            mixer_right.i_ch1.eq(self.i_pcm_right),
            mixer_right.i_ch2.eq(0),
            mixer_right.i_ch3.eq(0),
            mixer_right.i_gain0.eq(fm_gain),
            mixer_right.i_gain1.eq(pcm_gain),
            mixer_right.i_gain2.eq(0),
            mixer_right.i_gain3.eq(0),
            self.o_mixed_right.eq(mixer_right.o_mixed),
            peak_right.eq(mixer_right.o_peak)
        ]



