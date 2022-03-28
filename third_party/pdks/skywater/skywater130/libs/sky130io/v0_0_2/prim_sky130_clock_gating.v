module prim_sky130_clock_gating #(
  parameter bit NoFpgaGate = 1'b0
) (
  input        clk_i,
  input        en_i,
  input        test_en_i,
  output logic clk_o
);

// sky130_fd_sc_hd__dlclkp_1 latch (.CLK (clk_i), .GATE(en_i | test_en_i), .GCLK(clk_o));

// We've noticed issues with OpenROAD CTS's handling of clock gates, so hardcode
// a passthru for now.
assign clk_o = clk_i;

endmodule
