//This module instantiates a memory with input and output buses sized for
//compatibility with storing a matrix to be used in the matrix_multiply block.

module row_col_memory #(
    parameter DATA_WIDTH = 16,
    parameter ROW_COL_SIZE = 16,
    parameter MATRIX_SIZE = 16,
    parameter ALL_ACCESS_OUTPUT = 0,
    parameter OUTPUT_BUS_WIDTH = (ALL_ACCESS_OUTPUT == 1) ?
                                  MATRIX_SIZE*ROW_COL_SIZE*DATA_WIDTH : ROW_COL_SIZE*DATA_WIDTH,
    parameter ADDR_BITS = $clog2(MATRIX_SIZE)
) (
    input                                      clk,
    input      [              (ADDR_BITS-1):0] address,
    input                                      write_enable,
    input      [(ROW_COL_SIZE*DATA_WIDTH-1):0] datain,
    output reg [       (OUTPUT_BUS_WIDTH-1):0] dataout
);

    localparam ROW_COL_DATA_WIDTH = ROW_COL_SIZE * DATA_WIDTH;

`ifdef VERILATOR
    genvar i;

    generate
        if (ALL_ACCESS_OUTPUT == 0) begin : gen_single_access_output

            reg [(ROW_COL_DATA_WIDTH*MATRIX_SIZE-1):0] data_memory;

            always @(posedge clk) begin
                if (write_enable) begin
                    data_memory[(address+1)*ROW_COL_DATA_WIDTH-1-:ROW_COL_DATA_WIDTH] <= datain;
                end
            end

            always @(posedge clk) begin
                dataout <= data_memory[(address+1)*ROW_COL_DATA_WIDTH-1-:ROW_COL_DATA_WIDTH];
            end

        end // if (ALL_ACCESS_OUTPUT == 1)

         else begin : gen_all_access_output

            //***NOTE:  Yosys will still try and synthesize a memory if we map all the 2-D
            //          array data to a big bus, so take that choice away from it by
            //          storing the data in a big 1-D array to get it to synthesize flops
            //          -PG 7/20/2023

            for (i = 0; i < MATRIX_SIZE; i = i + 1) begin : gen_memory_map

                always @(posedge clk) begin
                    if (write_enable && (address == i)) begin
                        dataout[((i+1)*ROW_COL_DATA_WIDTH-1):((i)*ROW_COL_DATA_WIDTH)] = datain;
                    end
                end

            end

        end  // else: !if(ALL_ACCESS_OUTPUT == 1)

    endgenerate

`else  // !`ifdef VERILATOR

    genvar i;

    generate
        if (ALL_ACCESS_OUTPUT == 0) begin : gen_single_access_output

            reg [(ROW_COL_DATA_WIDTH-1):0] data_memory[MATRIX_SIZE];

            always @(posedge clk) begin
                if (write_enable) begin
                    data_memory[address] <= datain;
                end
            end

            always @(posedge clk) begin
                dataout <= data_memory[address];
            end

        end // if (ALL_ACCESS_OUTPUT == 1)

         else begin : gen_all_access_output

            //***NOTE:  Yosys will still try and synthesize a memory if we map all the 2-D
            //          array data to a big bus, so take that choice away from it by
            //          storing the data in a big 1-D array to get it to synthesize flops
            //          -PG 7/20/2023

            for (i = 0; i < MATRIX_SIZE; i = i + 1) begin : gen_memory_map

                always @(posedge clk) begin
                    if (write_enable && (address == i)) begin
                        dataout[((i+1)*ROW_COL_DATA_WIDTH-1):((i)*ROW_COL_DATA_WIDTH)] = datain;
                    end
                end

            end

        end  // else: !if(ALL_ACCESS_OUTPUT == 1)

    endgenerate
`endif  // !`ifdef VERILATOR

endmodule  // row_col_memory

