module bad (input a, output b);

    wire a;
    reg b // missing semicolon

    assign b = a;

endmodule
