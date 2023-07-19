//macc_pipe.v
//Peter Grossmann
//26 May 2023

module macc_pipe #(
    parameter INPUT_WIDTH =  8,
    parameter OUTPUT_WIDTH = 20
) (
    input 			clk,
    input 			resetn,
    input  [ (INPUT_WIDTH-1):0] a,
    input  [ (INPUT_WIDTH-1):0] b,
    output [(OUTPUT_WIDTH-1):0] y
);

    wire [(2*INPUT_WIDTH-1):0] mult_out;
    reg  [(2*INPUT_WIDTH-1):0] mult_reg;
    wire [ (OUTPUT_WIDTH-1):0] macc_out;

    multiplier #(
        .WIDTH(INPUT_WIDTH)
    ) mult_stage (
        .a(a),
        .b(b),
        .y(mult_out)
    );

    adder #(
        .WIDTH(OUTPUT_WIDTH)
    ) add_stage (
        .a(mult_out),
        .b(y),
        .y(macc_out)
    );

    always @(posedge clk) begin
        if (~resetn) begin
            mult_reg <= 'h0;
            y <= 'h0;
        end else begin
            mult_reg <= mult_out;
            y <= macc_out;
        end
    end

endmodule  // macc_pipe
