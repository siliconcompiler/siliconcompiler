module blinky #(
    parameter CLK_FREQ_HZ = 256
) (
    input clk,
    output reg q = 1'b0
);

    reg [$clog2(CLK_FREQ_HZ)-1:0] count = 0;

    always @(posedge clk) begin
        count <= count + 1;
        if (count == CLK_FREQ_HZ - 1) begin
            q <= !q;
            count <= 0;
        end
    end

endmodule  // blinky
