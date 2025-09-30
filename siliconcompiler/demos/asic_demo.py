from siliconcompiler import ASIC, Design
from siliconcompiler.targets import skywater130_demo


class ASICDemo(ASIC):
    '''
    "Self-test" target which builds a small 8-bit counter design as an ASIC,
    targeting the Skywater130 PDK.

    This target is intended for testing purposes only,
    to verify that SiliconCompiler is installed and configured correctly.
    '''

    def __init__(self):
        super().__init__()

        design = Design("heartbeat")
        design.set_dataroot("heartbeat", "python://siliconcompiler")
        with design.active_dataroot("heartbeat"), design.active_fileset("rtl"):
            design.set_topmodule("heartbeat")
            design.add_file("data/heartbeat.v")
            design.set_param("N", "8")
        with design.active_dataroot("heartbeat"), design.active_fileset("sdc"):
            design.add_file("data/heartbeat.sdc")

        # Set design
        self.set_design(design)
        self.add_fileset("rtl")
        self.add_fileset("sdc")

        # Load the Sky130 PDK/standard cell library target.
        skywater130_demo(self)


if __name__ == "__main__":
    proj = ASICDemo.create_cmdline(
        "asic_demo",
        description="\"Self-test\" target which builds a small 8-bit counter design as an ASIC, "
                    "targeting the Skywater130 PDK.",
        switchlist=["-remote"])
    proj.run()
    proj.summary()
    proj.snapshot()
