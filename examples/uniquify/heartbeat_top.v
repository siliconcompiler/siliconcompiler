// Parent design. It depends on the parameterized `heartbeat` and `prescaler`
// modules (each defined in its own file / SiliconCompiler Design) and
// instantiates them with several distinct parameter values.
module heartbeat_top (
    input        clk,
    input        nreset,
    output       out_fast,
    output       out_slow,
    output       out_slow2,
    output       out_slowest,
    output [3:0] cnt_a,
    output [7:0] cnt_b
);
    // Four heartbeat instances, three distinct parameterizations (N=24 merges).
    heartbeat #(.N(8))  u_fast    (.clk(clk), .nreset(nreset), .out(out_fast));
    heartbeat #(.N(24)) u_slow    (.clk(clk), .nreset(nreset), .out(out_slow));
    heartbeat #(.N(24)) u_slow2   (.clk(clk), .nreset(nreset), .out(out_slow2));
    heartbeat #(.N(48)) u_slowest (.clk(clk), .nreset(nreset), .out(out_slowest));

    // Two prescaler parameterizations.
    prescaler #(.W(4)) u_ps4 (.clk(clk), .nreset(nreset), .count(cnt_a));
    prescaler #(.W(8)) u_ps8 (.clk(clk), .nreset(nreset), .count(cnt_b));
endmodule
