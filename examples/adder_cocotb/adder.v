
module adder #(
    parameter WIDTH = 8
) (
    input  [WIDTH-1:0] a,
    input  [WIDTH-1:0] b,
    output [  WIDTH:0] sum
);

    assign sum = a + b;

endmodule
