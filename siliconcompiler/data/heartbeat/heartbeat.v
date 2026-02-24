module heartbeat #(
    parameter N = 8
) (
    input clk,
    input nreset,
    output reg out
);

    reg [N-1:0] counter_reg;
    always @(posedge clk or negedge nreset)
        if (!nreset) begin
            counter_reg <= 'b0;
            out <= 1'b0;
        end else begin
            counter_reg[N-1:0] <= counter_reg[N-1:0] + 1'b1;
            out <= (counter_reg[N-1:0] == {(N) {1'b1}});
        end
endmodule
