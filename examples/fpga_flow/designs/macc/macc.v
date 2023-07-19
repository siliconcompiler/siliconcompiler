//macc.v
//Peter Grossmann
//16 May 2023

module macc #(
    parameter INPUT_WIDTH = 8,
    parameter OUTPUT_WIDTH = 20
) (
    input      [ (INPUT_WIDTH-1):0] a,
    input      [ (INPUT_WIDTH-1):0] b,
    input                           clk,
    input                           reset,
    output reg [(OUTPUT_WIDTH-1):0] y
);

    always @(posedge clk) begin
        if (reset) y <= 'h0;
        else y <= a * b + y;
    end

endmodule  // macc
