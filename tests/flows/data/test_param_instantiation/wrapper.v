module wrapper (
    input a,
    input b,
    output c
);
    gate #(
        .Impl(1'b1)
    ) mygate (
        .a(a),
        .b(b),
        .c(c)
    );

endmodule
