//This block describes a parameterized multiplexer that takes a matrix of
//data as input and returns one row or column of that matrix as output

module row_col_data_mux #(
    parameter DATA_WIDTH = 16,
    parameter ROW_COL_SIZE = 16,
    parameter MATRIX_SIZE = 16,
    parameter NUM_SELECT_BITS = $clog2(MATRIX_SIZE)
) (
    input  [(MATRIX_SIZE*ROW_COL_SIZE*DATA_WIDTH-1):0] row_col_datain,
    input  [                    (NUM_SELECT_BITS-1):0] select,
    output [            (ROW_COL_SIZE*DATA_WIDTH-1):0] row_col_selected
);


    localparam ROW_COL_DATA_WIDTH = ROW_COL_SIZE * DATA_WIDTH;

`ifdef VERILATOR
    wire [(ROW_COL_DATA_WIDTH*MATRIX_SIZE-1):0] row_col_data;

    genvar i;
    generate
        for (i = 0; i < MATRIX_SIZE; i = i + 1) begin : gen_datain_organize
            assign row_col_data[(i+1)*ROW_COL_DATA_WIDTH-1-:ROW_COL_DATA_WIDTH]
                     = row_col_datain[(i*ROW_COL_DATA_WIDTH)+:ROW_COL_DATA_WIDTH];
        end
    endgenerate

    assign row_col_selected = row_col_data[(select+1)*ROW_COL_DATA_WIDTH-1-:ROW_COL_DATA_WIDTH];

`else  // !`ifdef VERILATOR
    wire [(ROW_COL_DATA_WIDTH-1):0] row_col_data[MATRIX_SIZE];

    genvar i;
    generate
        for (i = 0; i < MATRIX_SIZE; i = i + 1) begin : gen_datain_organize
            assign row_col_data[i] = row_col_datain[(i*ROW_COL_DATA_WIDTH)+:ROW_COL_DATA_WIDTH];
        end
    endgenerate

    assign row_col_selected = row_col_data[select];
`endif
endmodule  // row_col_data_mux
