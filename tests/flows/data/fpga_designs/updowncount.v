module updowncount #(
    parameter DATA_WIDTH = 8
) (
    input                         clk,
    input                         enable,
    input                         countdown,
    input                         setn,
    input                         resetn,
    output reg [(DATA_WIDTH-1):0] y
);

    always @(posedge clk or negedge setn or negedge resetn) begin
        if (~resetn) y <= {DATA_WIDTH{1'b0}};
        else if (~setn) y <= {DATA_WIDTH{1'b1}};
        else if (enable) begin
            if (countdown) y <= y - 1;
            else y <= y + 1;
        end
    end

endmodule  // updowncount
