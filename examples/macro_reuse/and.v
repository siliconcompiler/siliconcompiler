module mod_and (
    input  wire       clk,
    input  wire [7:0] a,
    input  wire [7:0] b,
    output reg  [7:0] y
);

    always @(posedge clk) begin
        y <= a & b;
    end

endmodule
