module heartbeat #(
    parameter N = 8
) (
    //inputs
    input      clk,     // clock
    input      nreset,  //async active low reset
    //outputs
    output reg out      //heartbeat
);

    reg [N-1:0] counter_reg;

    always @(posedge clk or negedge nreset) begin
        if (!nreset) begin
            counter_reg <= {(N) {1'b0}};
            out <= 1'b0;
        end else begin
            counter_reg <= counter_reg + 1'b1;
            out <= (counter_reg == {(N) {1'b1}});
        end
    end

endmodule
