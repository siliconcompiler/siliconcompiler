//multiplier.v
//Peter Grossmann
//13 September 2022

module multiplier #(
    parameter DATA_WIDTH = 16
) (
    input  [  (DATA_WIDTH-1):0] a,
    input  [  (DATA_WIDTH-1):0] b,
    output [(2*DATA_WIDTH-1):0] y
);

    assign y = a * b;

endmodule  // multiplier
