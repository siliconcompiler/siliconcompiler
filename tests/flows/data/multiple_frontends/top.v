module top (
    input clk,
    input reset,
    input [2:0] sel,
    input [31:0] num0,
    input [31:0] num1,
    output reg [31:0] out
);

    wire [31:0] gcd_verilog_out;
    gcd u0 (
        .clk(clk),
        .req_msg(num0),
        .req_rdy(),
        .req_val(1'b0),
        .reset(reset),
        .resp_msg(gcd_verilog_out),
        .resp_rdy(1'b0),
        .resp_val()
    );

    wire [4:0] adder_vhdl;
    binary_4_bit_adder_top u1 (
        .NUM1(num0),
        .NUM2(num1),
        .SUM (adder_vhdl)
    );

    always @(posedge clk) begin
        out <= (sel == 0) ? gcd_verilog_out :
           (sel == 1) ? adder_vhdl :
           'bx;
    end

endmodule
