import chisel3._
import chisel3.stage.ChiselStage

object SCDriver extends App {
  (new ChiselStage).execute(
    Array("-E", "verilog", "--target-dir", "chisel_work") ++ args,
    Seq()
  )
}
