module counter (
    input clk,
    output reg [5:0] count
);
    initial count = 0;

    always @(posedge clk) begin
        if (count == 15) count <= 0;
        else count <= count + 1'b1;
    end

`ifdef FORMAL
    always @(posedge clk) begin
        assert (count < 32);
    end
`endif
endmodule
