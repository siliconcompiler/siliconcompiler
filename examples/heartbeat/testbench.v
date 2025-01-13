`timescale 1ns / 1ns
module heartbeat_tb #(
    parameter N = 8
) ();

    reg  clk;
    reg  n_reset;
    wire beat;

    heartbeat #(
        .N(N)
    ) DUT (
        .clk(clk),
        .nreset(n_reset),
        .out(beat)
    );

    initial begin
        $dumpfile(`SILICONCOMPILER_TRACE_FILE);
        $dumpvars(0, heartbeat_tb);

        clk = 1'b0;
        n_reset = 1'b1;

        $monitor("time=%0t, reset=%0b beat=%0b", $time, DUT.nreset, beat);

        #2 n_reset = 1'b0;

        #10 n_reset = 1'b1;

        #10000 $finish();
    end

    always #5 clk = ~clk;

endmodule
