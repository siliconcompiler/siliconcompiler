module foo (
    input clk,
    output reg [1:0] out
);

    always @(posedge clk) begin
        out <= out + 1'b1;
    end

endmodule
