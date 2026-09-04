// A resettable counter, for the sequential equivalence checks.
//
// The LEC data next door is deliberately reset-less, which is fine for a
// combinational-boundary check but not for SEC: with no reset there is nothing
// to anchor the state to, so kepler-formal refuses the design pair rather than
// prove an equivalence that does not hold for arbitrary initial state.
module foo (
    input clk,
    input rst,
    output reg [1:0] out
);

    always @(posedge clk) begin
        if (rst)
            out <= 2'b00;
        else
            out <= out + 1'b1;
    end

endmodule
