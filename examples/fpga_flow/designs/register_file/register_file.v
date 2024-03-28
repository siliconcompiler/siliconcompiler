module register_file #(
    parameter DEPTH = 32,
    parameter DATA_WIDTH = 32,
    parameter ADDR_BITS = $clog2(DEPTH)
) (
    input                     clk,
    input                     wen,
    input  [ (ADDR_BITS-1):0] wraddr,
    input  [ (ADDR_BITS-1):0] rdaddr,
    input  [(DATA_WIDTH-1):0] datain,
    output [(DATA_WIDTH-1):0] dataout
);

    reg [(DATA_WIDTH-1):0] reg_file[DEPTH];

    always @(posedge clk) begin
        if (wen) begin
            reg_file[wraddr] <= datain;
        end
    end

    assign dataout = reg_file[rdaddr];


endmodule  // register_file
