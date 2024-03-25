
module adder #(
    parameter DATA_WIDTH = 8
) (
    input  [(DATA_WIDTH-1):0] a,
    input  [(DATA_WIDTH-1):0] b,
    output [  (DATA_WIDTH):0] y
);

    always_comb begin
       y = a + b;
    end
   
endmodule  // adder
