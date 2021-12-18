import chisel3.stage.ChiselStage

import chisel3._

object SCDriver extends App {
  (new ChiselStage).execute(
    Array("-E", "verilog", "--target-dir", "chisel_work") ++ args,
    Seq()
  )
}
