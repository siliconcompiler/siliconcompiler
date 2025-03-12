//this module implements an array of multipliers with parameters that tune it
//for matrix_multiply to generate all partial products in a single dot product,
//i.e. calculate all products for one entry in the output of a matrix
//multiplication.

module row_col_multiply #(
    parameter DATA_WIDTH = 16,
    parameter PRODUCT_WIDTH = 32,
    parameter ROW_COL_SIZE = 16
) (
    input [(ROW_COL_SIZE*DATA_WIDTH-1):0] a,
    input [(ROW_COL_SIZE*DATA_WIDTH-1):0] b,

    output [(ROW_COL_SIZE*PRODUCT_WIDTH-1):0] y
);

    genvar i;

    generate
        for (i = 0; i < ROW_COL_SIZE; i = i + 1) begin : gen_mult

            assign y[((i+1)*PRODUCT_WIDTH-1):(i*PRODUCT_WIDTH)]
           = a[((i+1)*DATA_WIDTH-1):(i*DATA_WIDTH)]
             * b[((i+1)*DATA_WIDTH-1):(i*DATA_WIDTH)];

        end
    endgenerate

endmodule  // row_col_multiply
