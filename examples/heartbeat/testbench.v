`timescale 1ns / 1ns
module heartbeat_tb #(parameter N = 8) ();

    reg clk;
    reg reset;
    wire beat;

    heartbeat #(.N(N)) DUT(
        .clk(clk),
        .nreset(reset),
        .out(beat)
    );

    initial begin
        clk = 1'b0;
        reset = 1'b1;

        $monitor("time=%0t, reset=%0b beat=%0b", $time, DUT.nreset, beat);

        #2
        reset = 1'b0;

        #10
        reset = 1'b1;

        #10000
        $finish();
    end

    always #5 clk = ~clk;

endmodule
