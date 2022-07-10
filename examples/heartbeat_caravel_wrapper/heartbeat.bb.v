(* blackbox *)
module heartbeat (
//`ifdef USE_POWER_PINS
    inout vpp,	// User area 1 1.8V supply
    inout gnd,	// User area 1 digital ground
//`endif

    input clk,
    input nreset,
    output reg out
);

endmodule
