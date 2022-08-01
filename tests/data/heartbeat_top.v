module heartbeat_top(
    input clk,
    input nreset,
    output [1:0] out
);

heartbeat hb1 (
    .clk(clk),
    .nreset(nreset),
    .out(out[0])
);

heartbeat hb2 (
    .clk(clk),
    .nreset(nreset),
    .out(out[1])
);

endmodule
