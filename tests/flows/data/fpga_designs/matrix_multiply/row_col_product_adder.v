//this module implements a tree adder with parameters that tune it
//for matrix_multiply to specify the correct tree adder size to sum all
//the terms in a single dot product, i.e. calculate the final answer for
//one entry in the output of a matrix multiplication.

module row_col_product_adder #(
    parameter PRODUCT_WIDTH = 16,
    parameter SUM_WIDTH = 32,
    parameter ROW_COL_SIZE = 16
) (
    input [(ROW_COL_SIZE*PRODUCT_WIDTH-1):0] product,
    output [(SUM_WIDTH-1):0] sum
);

`ifdef VERILATOR
    genvar i;

    /* verilator lint_off UNOPTFLAT */
    wire [(SUM_WIDTH*ROW_COL_SIZE-1):0] partial_sum;
    /* verilator lint_on UNOPTFLAT */

    assign sum = partial_sum[ROW_COL_SIZE*SUM_WIDTH-1-:SUM_WIDTH];

    generate
        for (i = 0; i < ROW_COL_SIZE; i = i + 1) begin : gen_adder

            if (i == 0) begin : g_0
                /* verilator lint_off WIDTH */
                assign partial_sum[(i+1)*SUM_WIDTH-1-:SUM_WIDTH] = product[(PRODUCT_WIDTH-1):0];
                /* verilator lint_on WIDTH */
            end else begin : g_other
                /* verilator lint_off WIDTH */
                assign partial_sum[(i+1)*SUM_WIDTH-1-:SUM_WIDTH]
                   = partial_sum[i*SUM_WIDTH-1-:SUM_WIDTH]
                     + product[((i+1)*PRODUCT_WIDTH-1):(i*PRODUCT_WIDTH)];
                /* verilator lint_on WIDTH */
            end

        end  // block: adder_gen
    endgenerate
`else  // !`ifdef VERILATOR
    genvar i;

    /* verilator lint_off UNOPTFLAT */
    wire [(SUM_WIDTH-1):0] partial_sum[ROW_COL_SIZE];
    /* verilator lint_on UNOPTFLAT */

    assign sum = partial_sum[(ROW_COL_SIZE-1)][(SUM_WIDTH-1):0];

    generate
        for (i = 0; i < ROW_COL_SIZE; i = i + 1) begin : gen_adder

            if (i == 0) begin : g_0
                /* verilator lint_off WIDTH */
                assign partial_sum[i] = product[(PRODUCT_WIDTH-1):0];
                /* verilator lint_on WIDTH */
            end else begin : g_other
                /* verilator lint_off WIDTH */
                assign partial_sum[i]
                   = partial_sum[i-1] + product[((i+1)*PRODUCT_WIDTH-1):(i*PRODUCT_WIDTH)];
                /* verilator lint_on WIDTH */
            end

        end  // block: adder_gen
    endgenerate
`endif
endmodule  // row_col_product_adder

