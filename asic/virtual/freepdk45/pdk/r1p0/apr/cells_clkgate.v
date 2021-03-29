module OPENROAD_CLKGATE (CK, E, GCK);
  input CK;
  input E;
  output GCK;

`ifdef OPENROAD_CLKGATE

CLKGATE_X1 latch (.CK (CK), .E(E), .GCK(GCK));

`else

assign GCK = CK;

`endif

endmodule