(* blackbox *)
module sky130_sram_2kbyte_1rw1r_32x512_8(
`ifdef USE_POWER_PINS
    vccd1,
    vssd1,
`endif
// Port 0: RW
    input clk0,
    input csb0,
    input web0,
    input [3:0] wmask0,
    input [8:0] addr0,
    input [31:0] din0,
    output reg [31:0] dout0,
// Port 1: R
    input clk1,
    input csb1,
    input [8:0] addr1,
    output reg [31:0] dout1
  );
endmodule
