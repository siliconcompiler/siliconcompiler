module heartbeat (
    //inputs
    input      clk,     // clock
    input      nreset,  //async active low reset
    //outputs
    output reg out      //heartbeat
);

    always @(posedge clk) begin
        assert (0);
    end

endmodule
