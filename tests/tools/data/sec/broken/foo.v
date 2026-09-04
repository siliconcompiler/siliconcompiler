// The mismatching source of the netlist beside it: the same interface and the
// same reset, counting down where foo.v counts up. Both bits stay live and the
// structure stays comparable, so the check has to come from the sequential
// behaviour rather than from a boundary or a folded-away constant.
module foo (
    input clk,
    input rst,
    output reg [1:0] out
);

    always @(posedge clk) begin
        if (rst)
            out <= 2'b00;
        else
            out <= out - 1'b1;
    end

endmodule
