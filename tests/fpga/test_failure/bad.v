module bad (input a, output b);

    // redefinition of ports is okay with Yosys, but an error with Verilator
    wire a;
    reg b;

    assign b = a;

endmodule
