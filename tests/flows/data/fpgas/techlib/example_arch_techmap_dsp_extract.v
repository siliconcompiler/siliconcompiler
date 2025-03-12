
module dsp_mult #(
    parameter INPUT_WIDTH  = 18,
    parameter OUTPUT_WIDTH = 36
) (
    input  [ (INPUT_WIDTH-1):0] A,
    input  [ (INPUT_WIDTH-1):0] B,
    output [(OUTPUT_WIDTH-1):0] Y
);

    assign Y = A * B;

endmodule

