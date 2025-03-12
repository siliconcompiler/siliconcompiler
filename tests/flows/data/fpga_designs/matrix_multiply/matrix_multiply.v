//This module implements a parameterized matrix multiplication accelerator.
//It multiplies two matrices A and B together by doing all of the
//multiplies and adds for a single row/column pair of A and B concurrently.
//Optional configurations are available for
//
//This code is provided as-is for the purposes of running FPGA RTL to bitstream
//experiments, and may not be suitable for simulation or performing a function
//in the field.
//
//The key parameters are:
//
//DATA_WIDTH -- the width of the input matrix data
//RESULT_WIDTH -- the width of the output matrix data
//ROW_COL_SIZE -- the number of columns in matrix A and number of rows in
//                matrix B
//A_MATRIX_HEIGHT -- the number of rows in matrix A
//B_MATRIX_WIDTH -- the number of columns in matrix B
//NUM_PARALLEL_OUTPUTS -- the number of entries in the result matrix that
//                        are calculated in parallel

//The work of this code is divided into several submodules:
//
//matrix_multiply_control.v -- sequences data from input memory through
//                             the multiply-add datapath by generating
//                             multiplexer selects.
//row_col_data_mux.v -- selects data from storage to feed to multipliers
//row_col_memory.v -- stores matrix data in a row or column wise format so that
//                    a read from a given address fetches rows from matrix A
//                    to multiply by columns from matrix B.
//row_col_multiply.v -- wrapper for permorming the parallel multiplies on an
//                      entire A row/B column pair.
//row_col_product_adder.v -- wrapper for the tree adder needed to sum the
//                           output of the parallel multiply into a single
//                           sum

module matrix_multiply #(
    parameter DATA_WIDTH = 4,
    parameter RESULT_WIDTH = 8,
    parameter ROW_COL_SIZE = 3,
    parameter A_MATRIX_HEIGHT = 3,
    parameter B_MATRIX_WIDTH = 3,
    parameter NUM_PARALLEL_OUTPUTS = 1,
    parameter ROW_COL_ALL_ACCESS = (NUM_PARALLEL_OUTPUTS == 1) ? 0 : 1,
    parameter ROW_DATA_BUS_WIDTH = (ROW_COL_ALL_ACCESS == 1) ?
                  A_MATRIX_HEIGHT*ROW_COL_SIZE*DATA_WIDTH : ROW_COL_SIZE*DATA_WIDTH,
    parameter COL_DATA_BUS_WIDTH = (ROW_COL_ALL_ACCESS == 1) ?
                  B_MATRIX_WIDTH*ROW_COL_SIZE*DATA_WIDTH : ROW_COL_SIZE*DATA_WIDTH,
    parameter A_MAT_ADDR_WIDTH = $clog2(A_MATRIX_HEIGHT),
    parameter B_MAT_ADDR_WIDTH = $clog2(B_MATRIX_WIDTH),
    parameter RESULT_MATRIX_HEIGHT = A_MATRIX_HEIGHT,
    parameter RESULT_MATRIX_WIDTH = B_MATRIX_WIDTH,
    parameter RESULT_ADDRESS_WIDTH = $clog2(RESULT_MATRIX_HEIGHT)
) (
    input clk,
    input resetn,
    input start,
    input read,

    input row_write_enable,
    input col_write_enable,

    input      [  (ROW_COL_SIZE*DATA_WIDTH-1):0] mem_datain,
    input      [         (A_MAT_ADDR_WIDTH-1):0] mem_address,
    output     [(ROW_COL_SIZE*RESULT_WIDTH-1):0] mem_dataout,
    output reg [     (RESULT_ADDRESS_WIDTH-1):0] mem_address_out,
    output reg                                   mem_dataout_valid,

    output done,
    output read_done
);

    localparam RC_DATA_WIDTH = ROW_COL_SIZE * DATA_WIDTH;
    localparam RC_RESULT_WIDTH = ROW_COL_SIZE * RESULT_WIDTH;

    genvar i;
    genvar k;

    wire [               (ROW_DATA_BUS_WIDTH-1):0] row_dataout;
    wire [                    (RC_DATA_WIDTH-1):0] row_datain;

    wire [                    (RC_DATA_WIDTH-1):0] col_datain;
    wire [               (COL_DATA_BUS_WIDTH-1):0] col_dataout;

    reg  [(RESULT_MATRIX_HEIGHT*RESULT_WIDTH-1):0] all_row_col_sums;
    wire [             (RESULT_MATRIX_HEIGHT-1):0] output_write_enable;

    wire                                           col_done;
    wire                                           busy;
    wire                                           read_busy;


    wire [                 (A_MAT_ADDR_WIDTH-1):0] rowsel_base;
    reg  [                 (A_MAT_ADDR_WIDTH-1):0] rowsel_base_sync;
    wire [                 (B_MAT_ADDR_WIDTH-1):0] colsel_base;

    wire [                 (A_MAT_ADDR_WIDTH-1):0] row_address;
    wire [                 (B_MAT_ADDR_WIDTH-1):0] col_address;

    wire [                  (RC_RESULT_WIDTH-1):0] output_buffer_dataout;

    wire                                           row_data_write_enable;
    wire                                           col_data_write_enable;

    reg                                            result_write_enable;
    reg  [             (RESULT_ADDRESS_WIDTH-1):0] result_address;
    wire [ (RESULT_MATRIX_WIDTH*RESULT_WIDTH-1):0] result_datain;
    wire [                  (RC_RESULT_WIDTH-1):0] result_dataout;

    wire [             (RESULT_ADDRESS_WIDTH-1):0] outputsel;

    assign row_address = (start || busy) ? rowsel_base : mem_address;
    assign col_address = (start || busy) ? colsel_base : mem_address;

    assign row_datain  = mem_datain;
    assign col_datain  = mem_datain;

    assign mem_dataout = result_dataout;

    always @(posedge clk) begin
        rowsel_base_sync <= rowsel_base;
    end

    reg read_busy_sync;

    always @(posedge clk) begin
        mem_address_out <= result_address;
        read_busy_sync <= read_busy;
        mem_dataout_valid <= read_busy_sync;
    end

    always @(posedge clk) begin
        if (~resetn) begin
            result_address <= 'h0;
        end else begin
            if (read) begin
                result_address <= outputsel;
            end else begin
                result_address <= rowsel_base_sync;
            end
        end
    end

    assign result_datain = all_row_col_sums;

    always @(posedge clk) begin
        if (~resetn) begin
            result_write_enable <= 1'b0;
        end else begin
            result_write_enable <= col_done;
        end
    end


    row_col_memory #(
        .DATA_WIDTH(DATA_WIDTH),
        .ROW_COL_SIZE(ROW_COL_SIZE),
        .MATRIX_SIZE(A_MATRIX_HEIGHT),
        .ALL_ACCESS_OUTPUT(ROW_COL_ALL_ACCESS)
    ) row_memory (
        .clk(clk),
        .address(row_address),
        .write_enable(row_write_enable),
        .datain(row_datain),
        .dataout(row_dataout)
    );

    row_col_memory #(
        .DATA_WIDTH(DATA_WIDTH),
        .ROW_COL_SIZE(ROW_COL_SIZE),
        .MATRIX_SIZE(B_MATRIX_WIDTH),
        .ALL_ACCESS_OUTPUT(ROW_COL_ALL_ACCESS)
    ) col_memory (
        .clk(clk),
        .address(col_address),
        .write_enable(col_write_enable),
        .datain(col_datain),
        .dataout(col_dataout)
    );


    row_col_memory #(
        .DATA_WIDTH(RESULT_WIDTH),
        .ROW_COL_SIZE(RESULT_MATRIX_HEIGHT),
        .MATRIX_SIZE(RESULT_MATRIX_WIDTH),
        .ALL_ACCESS_OUTPUT(0)
    ) result_memory (
        .clk(clk),
        .address(result_address),
        .write_enable(result_write_enable),
        .datain(result_datain),
        .dataout(result_dataout)
    );

    matrix_multiply_control #(
        .ROW_COL_SIZE(ROW_COL_SIZE),
        .MATRIX_SIZE(A_MATRIX_HEIGHT),
        .NUM_PARALLEL_OUTPUTS(NUM_PARALLEL_OUTPUTS)
    ) matrix_multiply_control (
        .clk(clk),
        .resetn(resetn),
        .start(start),
        .col_done(col_done),
        .done(done),
        .read(read),
        .busy(busy),
        .read_busy(read_busy),
        .row_select(rowsel_base),
        .col_select(colsel_base),
        .output_select(outputsel),
        .read_done(read_done)
    );

`ifdef VERILATOR
    wire [(NUM_PARALLEL_OUTPUTS*RESULT_MATRIX_HEIGHT-1):0] row_active;
    wire [(NUM_PARALLEL_OUTPUTS*RESULT_MATRIX_HEIGHT-1):0] col_active;

    wire [    (A_MAT_ADDR_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] rowsel;
    reg  [    (A_MAT_ADDR_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] rowsel_sync;
    wire [       (RC_DATA_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] row_data_mult;

    wire [    (B_MAT_ADDR_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] colsel;
    reg  [    (B_MAT_ADDR_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] colsel_sync;
    wire [       (RC_DATA_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] col_data_mult;

    wire [     (RC_RESULT_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] row_col_product;

    wire [        (RESULT_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] row_col_sum;

    wire [                     (NUM_PARALLEL_OUTPUTS-1):0] row_col_output_write_enable;

    generate
        for (k = 0; k < RESULT_MATRIX_HEIGHT; k = k + 1) begin : gen_row_active_k
            for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1) begin : gen_row_active_i
                assign row_active[k*NUM_PARALLEL_OUTPUTS+i]
                          = (rowsel_sync[(i+1)*A_MAT_ADDR_WIDTH-1-:A_MAT_ADDR_WIDTH] == k);
                assign col_active[k*NUM_PARALLEL_OUTPUTS+i]
                          = (colsel_sync[(i+1)*A_MAT_ADDR_WIDTH-1-:B_MAT_ADDR_WIDTH] == k);
            end
        end
    endgenerate

    generate
        for (k = 0; k < RESULT_MATRIX_HEIGHT; k = k + 1) begin : gen_output_write_enable
            assign output_write_enable[k] = |(col_active[k]) && start;
        end
    endgenerate


    generate
        if (NUM_PARALLEL_OUTPUTS == 1) begin : gen_serial_dot_product

            assign rowsel = rowsel_base;
            assign colsel = colsel_base;

            assign row_data_mult = row_dataout;
            assign col_data_mult = col_dataout;

            row_col_multiply #(
                .DATA_WIDTH(DATA_WIDTH),
                .PRODUCT_WIDTH(RESULT_WIDTH),
                .ROW_COL_SIZE(ROW_COL_SIZE)
            ) row_col_multiplier (
                .a(row_data_mult),
                .b(col_data_mult),
                .y(row_col_product)
            );

            row_col_product_adder #(
                .PRODUCT_WIDTH(RESULT_WIDTH),
                .SUM_WIDTH(RESULT_WIDTH),
                .ROW_COL_SIZE(ROW_COL_SIZE)
            ) row_col_product_adder (
                .product(row_col_product),
                .sum(row_col_sum)
            );


            always @(posedge clk) begin
                if (~resetn) begin
                    all_row_col_sums <= 'h0;
                end else begin
                    if (output_write_enable[colsel_sync]) begin
                        all_row_col_sums[((colsel_sync)*RESULT_WIDTH)+:RESULT_WIDTH] <= row_col_sum;
                    end
                end
            end

        end // if (NUM_PARALLEL_OUTPUTS == 1)
        else begin : gen_parallel_dot_product

            for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1) begin : gen_dot_product

                assign rowsel[(i+1)*A_MAT_ADDR_WIDTH-1-:A_MAT_ADDR_WIDTH] = rowsel_base + i;
                assign colsel[(i+1)*B_MAT_ADDR_WIDTH-1-:B_MAT_ADDR_WIDTH] = colsel_base + i;

                assign row_col_output_write_enable[i]
                   = output_write_enable[colsel[(i+1)*B_MAT_ADDR_WIDTH-1-:B_MAT_ADDR_WIDTH]];

                row_col_data_mux #() row_mux (
                    .row_col_datain(row_dataout),
                    .select(rowsel[(i+1)*A_MAT_ADDR_WIDTH-1-:A_MAT_ADDR_WIDTH]),
                    .row_colseled(row_data_mult[(i+1)*RC_DATA_WIDTH-1-:RC_DATA_WIDTH])
                );

                row_col_data_mux #() col_mux (
                    .row_col_datain(col_dataout),
                    .select(colsel[(i+1)*B_MAT_ADDR_WIDTH-1-:B_MAT_ADDR_WIDTH]),
                    .row_colseled(col_data_mult[(i+1)*RC_DATA_WIDTH-1-:RC_DATA_WIDTH])
                );

                row_col_multiply #(
                    .DATA_WIDTH(DATA_WIDTH),
                    .PRODUCT_WIDTH(RESULT_WIDTH)
                ) row_col_multiplier (
                    .a(row_data_mult[(i+1)*RC_DATA_WIDTH-1-:RC_DATA_WIDTH]),
                    .b(col_data_mult[(i+1)*RC_DATA_WIDTH-1-:RC_DATA_WIDTH]),
                    .y(row_col_product[(i+1)*RC_RESULT_WIDTH-1-:RC_RESULT_WIDTH])
                );

                row_col_product_adder #(
                    .PRODUCT_WIDTH(RESULT_WIDTH),
                    .SUM_WIDTH(RESULT_WIDTH),
                    .ROW_COL_SIZE(ROW_COL_SIZE)
                ) row_col_product_adder (
                    .product(row_col_product[(i+1)*RC_RESULT_WIDTH-1-:RC_RESULT_WIDTH]),
                    .sum(row_col_sum[(i+1)*RESULT_WIDTH-1-:RESULT_WIDTH])
                );

                always @(posedge clk) begin
                    if (~resetn) begin
                        all_row_col_sums <= 'h0;
                    end else begin
                        if (row_col_output_write_enable[i]) begin
                            all_row_col_sums[(
                                             (colsel[
                                               (i+1)*B_MAT_ADDR_WIDTH-1
                                               -:B_MAT_ADDR_WIDTH
                                             ])
                                               *RESULT_WIDTH)+:RESULT_WIDTH]
                                <= row_col_sum[(i+1)*RESULT_WIDTH-1-:RESULT_WIDTH];
                        end
                    end
                end

            end  // for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1)

        end  // else: !if(NUM_PARALLEL_OUTPUTS == 1)
    endgenerate

    generate
        for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1) begin : gen_sel_sync
            always @(posedge clk) begin
                rowsel_sync[(i+1)*A_MAT_ADDR_WIDTH-1-:A_MAT_ADDR_WIDTH]
                    <= rowsel[(i+1)*A_MAT_ADDR_WIDTH-1-:A_MAT_ADDR_WIDTH];
                colsel_sync[(i+1)*B_MAT_ADDR_WIDTH-1-:B_MAT_ADDR_WIDTH]
                    <= colsel[(i+1)*B_MAT_ADDR_WIDTH-1-:B_MAT_ADDR_WIDTH];
            end
        end
    endgenerate

`else  // !`ifdef VERILATOR
    wire [(NUM_PARALLEL_OUTPUTS-1):0] row_active     [RESULT_MATRIX_HEIGHT];
    wire [(NUM_PARALLEL_OUTPUTS-1):0] col_active     [RESULT_MATRIX_HEIGHT];

    wire [    (A_MAT_ADDR_WIDTH-1):0] rowsel         [NUM_PARALLEL_OUTPUTS];
    reg  [    (A_MAT_ADDR_WIDTH-1):0] rowsel_sync    [NUM_PARALLEL_OUTPUTS];
    wire [       (RC_DATA_WIDTH-1):0] row_data_mult  [NUM_PARALLEL_OUTPUTS];

    wire [    (B_MAT_ADDR_WIDTH-1):0] colsel         [NUM_PARALLEL_OUTPUTS];
    reg  [    (B_MAT_ADDR_WIDTH-1):0] colsel_sync    [NUM_PARALLEL_OUTPUTS];
    wire [       (RC_DATA_WIDTH-1):0] col_data_mult  [NUM_PARALLEL_OUTPUTS];

    wire [     (RC_RESULT_WIDTH-1):0] row_col_product[NUM_PARALLEL_OUTPUTS];

    wire [        (RESULT_WIDTH-1):0] row_col_sum    [NUM_PARALLEL_OUTPUTS];

    generate
        for (k = 0; k < RESULT_MATRIX_HEIGHT; k = k + 1) begin : gen_row_active_k
            for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1) begin : gen_row_active_i
                assign row_active[k][i] = (rowsel_sync[i] == k);
                assign col_active[k][i] = (colsel_sync[i] == k);
            end
        end
    endgenerate

    generate
        for (k = 0; k < RESULT_MATRIX_HEIGHT; k = k + 1) begin : gen_output_write_enable
            assign output_write_enable[k] = |(col_active[k]) && start;
        end
    endgenerate


    generate
        if (NUM_PARALLEL_OUTPUTS == 1) begin : gen_serial_dot_product

            assign rowsel[0] = rowsel_base;
            assign colsel[0] = colsel_base;

            assign row_data_mult[0] = row_dataout;
            assign col_data_mult[0] = col_dataout;

            row_col_multiply #(
                .DATA_WIDTH(DATA_WIDTH),
                .PRODUCT_WIDTH(RESULT_WIDTH),
                .ROW_COL_SIZE(ROW_COL_SIZE)
            ) row_col_multiplier (
                .a(row_data_mult[0]),
                .b(col_data_mult[0]),
                .y(row_col_product[0])
            );

            row_col_product_adder #(
                .PRODUCT_WIDTH(RESULT_WIDTH),
                .SUM_WIDTH(RESULT_WIDTH),
                .ROW_COL_SIZE(ROW_COL_SIZE)
            ) row_col_product_adder (
                .product(row_col_product[0]),
                .sum(row_col_sum[0])
            );


            always @(posedge clk) begin
                if (~resetn) begin
                    all_row_col_sums <= 'h0;
                end else begin
                    if (output_write_enable[colsel_sync[0]]) begin
                        all_row_col_sums[((colsel_sync[0])*RESULT_WIDTH)+:RESULT_WIDTH]
                        <= row_col_sum[0];
                    end
                end
            end

        end // if (NUM_PARALLEL_OUTPUTS == 1)

        else begin : gen_parallel_dot_product

            for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1) begin : gen_dot_product

                assign rowsel[i] = rowsel_base + i;
                assign colsel[i] = colsel_base + i;

                row_col_data_mux #() row_mux (
                    .row_col_datain(row_dataout),
                    .select(rowsel[i]),
                    .row_colseled(row_data_mult[i])
                );

                row_col_data_mux #() col_mux (
                    .row_col_datain(col_dataout),
                    .select(colsel[i]),
                    .row_colseled(col_data_mult[i])
                );

                row_col_multiply #(
                    .DATA_WIDTH(DATA_WIDTH),
                    .PRODUCT_WIDTH(RESULT_WIDTH)
                ) row_col_multiplier (
                    .a(row_data_mult[i]),
                    .b(col_data_mult[i]),
                    .y(row_col_product[i])
                );

                row_col_product_adder #(
                    .PRODUCT_WIDTH(RESULT_WIDTH),
                    .SUM_WIDTH(RESULT_WIDTH),
                    .ROW_COL_SIZE(ROW_COL_SIZE)
                ) row_col_product_adder (
                    .product(row_col_product[i]),
                    .sum(row_col_sum[i])
                );

                always @(posedge clk) begin
                    if (~resetn) begin
                        all_row_col_sums <= 'h0;
                    end else begin
                        if (output_write_enable[colsel[i]]) begin
                            all_row_col_sums[((colsel[i])*RESULT_WIDTH)+:RESULT_WIDTH]
                                <= row_col_sum[i];
                        end
                    end
                end

            end  // for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1)

        end  // else: !if(NUM_PARALLEL_OUTPUTS == 1)
    endgenerate

    generate
        for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1) begin : gen_sel_sync
            always @(posedge clk) begin
                rowsel_sync[i] <= rowsel[i];
                colsel_sync[i] <= colsel[i];
            end
        end
    endgenerate

`endif

endmodule  // matrix_multiply
