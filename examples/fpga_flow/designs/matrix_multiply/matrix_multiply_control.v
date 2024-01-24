//This block contains control logic for the matrix_multiply circuit so that
//it can iterate over all the rows/columns while multiplying two matrices
//one row/column pair (or more) at a time.


module matrix_multiply_control #(
    parameter ROW_COL_SIZE = 16,
    parameter MATRIX_SIZE = 16,
    parameter NUM_PARALLEL_OUTPUTS = 1,
    parameter COL_COUNTER_SIZE = $clog2(ROW_COL_SIZE),
    parameter MATRIX_COUNTER_SIZE = $clog2(MATRIX_SIZE),
    parameter MATRIX_COUNTER_MAX = MATRIX_SIZE - 1,
    parameter COL_COUNTER_MAX = ROW_COL_SIZE - 1
) (
    input clk,
    input resetn,

    input start,
    input read,

    output     [   (COL_COUNTER_SIZE-1):0] col_select,
    output     [(MATRIX_COUNTER_SIZE-1):0] row_select,
    output     [(MATRIX_COUNTER_SIZE-1):0] output_select,
    output reg                             busy,
    output reg                             read_busy,

    output reg col_done,
    output reg done,
    output reg read_done
);


    reg  [   (COL_COUNTER_SIZE-1):0] col_counter;
    reg  [(MATRIX_COUNTER_SIZE-1):0] matrix_counter;
    reg  [(MATRIX_COUNTER_SIZE-1):0] output_counter;

    reg                              finish;
    reg                              finish_sync;
    reg                              read_finish;

    wire                             col_counter_enable;
    wire                             matrix_counter_enable;
    wire                             output_counter_enable;

    assign col_select = col_counter;
    assign row_select = matrix_counter;
    assign output_select = output_counter;

    assign col_counter_enable = start || busy;
    /* verilator lint_off WIDTH */
    assign matrix_counter_enable = busy && (col_counter == COL_COUNTER_MAX);
    /* verilator lint_on WIDTH */

    assign output_counter_enable = read_busy;

    always @(posedge clk) begin
        if (~resetn) begin
            busy <= 1'b0;
        end else begin
            if (finish_sync) begin
                busy <= 1'b0;
            end else begin
                if (start) begin
                    busy <= 1'b1;
                end
            end
        end  // else: !if(~resetn)
    end  // always @ (posedge clk)

    always @(posedge clk) begin
        if (~resetn) begin
            read_busy <= 1'b0;
        end else begin
            /* verilator lint_off WIDTH */
            if (output_counter == MATRIX_COUNTER_MAX) begin
                /* verilator lint_on WIDTH */
                read_busy <= 1'b0;
            end else begin
                if (read) begin
                    read_busy <= 1'b1;
                end
            end
        end  // else: !if(~resetn)
    end  // always @ (posedge clk)

    always @(posedge clk) begin
        if (~resetn) begin
            col_counter <= 'h0;
        end else begin
            if (col_counter_enable) begin
                col_counter <= col_counter + NUM_PARALLEL_OUTPUTS;
            end
        end
    end

    always @(posedge clk) begin
        if (~resetn) begin
            matrix_counter <= 'h0;
        end else begin
            if (matrix_counter_enable) begin
                matrix_counter <= matrix_counter + 1;
            end
        end
    end

    always @(posedge clk) begin
        if (~resetn) begin
            output_counter <= 'h0;
        end else begin
            if (output_counter_enable) begin
                output_counter <= output_counter + 1;
            end
        end
    end

    always @(posedge clk) begin
        if (~resetn) begin
            finish <= 1'b0;
        end else begin
            /* verilator lint_off WIDTH */
            if ((matrix_counter == MATRIX_COUNTER_MAX) && matrix_counter_enable) begin
                /* verilator lint_on WIDTH */
                finish <= 1'b1;
            end
        end
    end

    always @(posedge clk) begin
        if (~resetn) begin
            done <= 1'b0;
            finish_sync <= 1'b0;
        end else begin
            finish_sync <= finish;
            done <= finish_sync;
        end
    end

    always @(posedge clk) begin
        if (~resetn) begin
            read_done   <= 1'b0;
            read_finish <= 1'b0;
        end else begin
            /* verilator lint_off WIDTH */
            read_finish <= (output_counter == MATRIX_COUNTER_MAX);
            /* verilator lint_on WIDTH */
            read_done   <= read_finish;
        end
    end

    always @(posedge clk) begin
        if (~resetn) begin
            col_done <= 1'b0;
        end else begin
            if (matrix_counter_enable) begin
                col_done <= 1'b1;
            end else begin
                col_done <= 1'b0;
            end
        end
    end

endmodule  // matrix_multiply_control
