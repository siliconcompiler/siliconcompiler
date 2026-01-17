
from siliconcompiler import Design, ASIC
from siliconcompiler.schema_support.patch import Patch
from siliconcompiler.targets import asap7_demo


class SPI(Design):
    def __init__(self):
        super().__init__("spi")

        self.set_dataroot("example", __file__)
        with self.active_dataroot("example"), self.active_fileset("rtl"):
            self.add_file("spi.v")
            self.set_topmodule("spi")
            
            patch = Patch("spi_patch")
            patch.create_from_files("spi.v", "spipatch.v")
            self.set("fileset", "rtl", "patch", "spi_patch", "file", "spi.v")
            self.set("fileset", "rtl", "patch", "spi_patch", "dataroot", "example")
            self.set("fileset", "rtl", "patch", "spi_patch", "diff", patch.get("diff"))


def main():
    project = ASIC(SPI())
    project.add_fileset("rtl")

    asap7_demo(project)

    project.option.add_to("synthesis")
    project.option.set_nodashboard(True)

    project.run()
    project.summary()



if __name__ == '__main__':
    main()
