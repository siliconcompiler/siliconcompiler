module test(input A, input E, output B);

assign B = E ? A : 1'bz;

endmodule
