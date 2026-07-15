module heartbeat8 (
    //inputs
    input      clk,     // clock
    input      nreset,  //async active low reset
    //outputs
    output reg out      //heartbeat
);

    reg [7:0] counter_reg;

    always @(posedge clk or negedge nreset) begin
        if (!nreset) begin
            counter_reg <= 8'b0;
            out <= 1'b0;
        end else begin
            counter_reg <= counter_reg + 1'b1;
            out <= (counter_reg == 8'hff);
        end
    end

endmodule
