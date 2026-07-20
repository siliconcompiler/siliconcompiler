// A second parameterized module, to show uniquifying multiple module names at
// once. Its port width tracks the parameter.
module prescaler #(
    parameter W = 4
) (
    input          clk,
    input          nreset,
    output [W-1:0] count
);
    reg [W-1:0] r;
    always @(posedge clk or negedge nreset)
        if (!nreset) r <= {W{1'b0}};
        else r <= r + 1'b1;
    assign count = r;
endmodule
