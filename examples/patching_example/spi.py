
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

            # Add patch to correct the SPI module
            self.add_patch("spi_patch", "spi.v", """
--- spi.v       2026-02-05 15:04:03
+++ spipatch.v  2026-02-05 15:07:49
@@ -44,7 +44,7 @@
   reg miso_d, miso_q;
  
   assign miso = miso_q;
-  assign done = ~done_q; // This should have been done_q
+  assign done = done_q;
   assign dout = dout_q;
  
   always @(*) begin
@@ -95,8 +95,6 @@
     ss_q <= ss_d;
     data_q <= data_d;
     sck_old_q <= sck_old_d;
-
-    $fatal();
  
   end
""")


def main():
    project = ASIC(SPI())
    project.add_fileset("rtl")

    asap7_demo(project)

    project.run()
    project.summary()


if __name__ == '__main__':
    main()
