
module adder_extract #(
    parameter INPUT_WIDTH = 18,
    parameter OUTPUT_WIDTH = 40
) (
    input  [(INPUT_WIDTH-1):0] a,
    input  [(INPUT_WIDTH-1):0] b,
    output [  (OUTPUT_WIDTH-1):0] y
);

    assign y = a + b;

endmodule  // adder_extract
