
module macc #(
    parameter INPUT_WIDTH  = 18,
    parameter OUTPUT_WIDTH = 40
) (
    input      [ (INPUT_WIDTH-1):0] a,
    input      [ (INPUT_WIDTH-1):0] b,
    input                           clk,
    input                           reset,
    output reg [(OUTPUT_WIDTH-1):0] y
);

    wire [(2*INPUT_WIDTH-1):0] mult_out;

    dsp_mult dsp_mult (
        .A(a),
        .B(b),
        .Y(mult_out)
    );

    always @(posedge clk) begin
        if (reset) y <= 'h0;
        else y <= mult_out + y;
    end

endmodule  // macc
