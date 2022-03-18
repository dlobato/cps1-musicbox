import os

from litex.soc.interconnect.csr import *

class DaoDump(Module, AutoCSR):
    def __init__(self, platform, dump_file_name="dao.raw"):
        self.platform = platform

        self.sample = Signal()
        self.left = Signal(16)
        self.right = Signal(16)

        self._control = CSRStorage(description="dao dump control", fields=[
            CSRField('en', reset=0, size=1, description='enable dump')
        ])

        en = Signal()
        self.comb += en.eq(self._control.fields.en)

        self.dao_dump_params = dict(
            p_DUMPFILE=dump_file_name,
            i_sample=self.sample,
            i_en=en,
            i_left=self.left,
            i_right=self.right
        )

        self.add_sources(platform)

    @staticmethod
    def add_sources(platform):
        vdir = "gateware/rtl"
        platform.add_source(os.path.join(vdir, "dao_dump.v"))

    def do_finalize(self):
        self.specials += Instance("dao_dump", **self.dao_dump_params)