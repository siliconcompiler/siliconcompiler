// A parameterized module, instantiated with several distinct N values by the
// parent. Hardening it requires knowing which concrete N values are actually
// used -- that is what the uniquify enumeration answers.
module heartbeat #(
    parameter N = 8
) (
    input      clk,
    input      nreset,
    output reg out
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
