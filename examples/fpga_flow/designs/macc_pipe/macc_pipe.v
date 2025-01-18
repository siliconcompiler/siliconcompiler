
module macc_pipe #(
    parameter INPUT_WIDTH  = 18,
    parameter OUTPUT_WIDTH = 40
) (
    input                           clk,
    input                           resetn,
    input      [ (INPUT_WIDTH-1):0] a,
    input      [ (INPUT_WIDTH-1):0] b,
    output reg [(OUTPUT_WIDTH-1):0] y
);

    wire [(2*INPUT_WIDTH-1):0] mult_out;
    reg  [(2*INPUT_WIDTH-1):0] mult_reg;
    wire [ (OUTPUT_WIDTH-1):0] macc_out;

    assign mult_out = a * b;
    assign macc_out = mult_out + y;

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
