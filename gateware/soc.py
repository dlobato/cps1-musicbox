import shutil

from litex.soc.integration.soc_core import SoCCore
from litex.soc.interconnect import wishbone
from litex.soc.interconnect.csr import *

from gateware.jt51.jt51 import JT51
from gateware.jt6295.jt6295 import JT6295RomWishboneDMAReader, JT6295
from gateware.jtframe.sound.mixer import CPS1StereoMixer
from gateware.jtframe.sound.uprate2_fir import Uprate2Fir


class CPS1MusicboxSoC(SoCCore):
    def __init__(self, platform, clk_freq, **kwargs):
        SoCCore.__init__(self, platform, clk_freq, **kwargs)

        # JT51
        self.submodules.jt51 = JT51(platform, clk_freq)

        # JT6295
        self.add_constant("JT6295_ROM_SIZE", 256 * 1024)
        base = self.mem_map.get("jt6295_rom", 0x40c00000)
        bus = wishbone.Interface(data_width=8, adr_width=self.bus.address_width)
        self.add_wb_master(bus)

        self.submodules.jt6295_rom_dma = JT6295RomWishboneDMAReader(
            bus=bus,
            base_address=base,
            with_csr=True
        )
        self.submodules.jt6295 = JT6295(
            platform=platform,
            clk_freq=clk_freq
        )
        self.comb += [
            self.jt6295_rom_dma.i_rom_addr.eq(self.jt6295.o_rom_addr),
            self.jt6295.i_rom_data.eq(self.jt6295_rom_dma.o_rom_data),
            self.jt6295.i_rom_ok.eq(self.jt6295_rom_dma.o_rom_ok),
        ]

        jt6295_sound_upsampled = Signal(16)
        self.submodules.jtframe_uprate2_fir = Uprate2Fir(platform)
        self.comb += [
            self.jtframe_uprate2_fir.i_sample.eq(self.jt6295.sample),
            self.jtframe_uprate2_fir.l_in.eq(Cat(Signal(2), self.jt6295.sound)),
            self.jtframe_uprate2_fir.r_in.eq(0),
            jt6295_sound_upsampled.eq(self.jtframe_uprate2_fir.l_out)
        ]

        self.submodules.mixer = mixer = CPS1StereoMixer(platform)
        self.comb += [
            mixer.i_fm_left.eq(self.jt51.xleft),
            mixer.i_fm_right.eq(self.jt51.xright),
            mixer.i_pcm_left.eq(jt6295_sound_upsampled),
            mixer.i_pcm_right.eq(jt6295_sound_upsampled),
        ]

    def build(self, build_dir, *args, **kwargs):
        init_paths = JT6295.fir_init_paths() + Uprate2Fir.fir_init_paths()
        for f in init_paths:
            shutil.copy(f, build_dir)
        return super().build(build_dir=build_dir, *args, **kwargs)

