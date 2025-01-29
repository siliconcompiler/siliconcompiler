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

    wire [15:0] gcd_scala;
    GCD_Scala u2 (
        .clock(clk),
        .reset(reset),
        .io_value1(num0),
        .io_value2(num1),
        .io_loadingValues(1'b1),
        .io_outputGCD(gcd_scala)
    );

    wire [15:0] gcd_c;
    gcd_cpp u3 (
        .clk(clk),
        .reset(reset),
        .start_port(1'b1),
        .a(num0),
        .b(num1),
        .done_port(),
        .return_port(gcd_c)
    );

    wire [31:0] fib;
    mkFibOne u4 (
        .CLK(clk),
        .RST_N(~reset),
        .EN_nextFib(1'b1),
        .RDY_nextFib(),
        .EN_getFib(1'b1),
        .getFib(fib),
        .RDY_getFib()
    );

    always @(posedge clk) begin
        out <= (sel == 0) ? gcd_verilog_out :
           (sel == 1) ? adder_vhdl :
           (sel == 2) ? gcd_scala :
           (sel == 3) ? gcd_c :
           (sel == 4) ? fib :
           'bx;
    end

endmodule
