module eq2
    (
        input wire [1:0] a, b,
        output wire aeqb
    );
    wire e0, e1;

    eq1 eq1_unit_0 (.i0(a[0]), .i1(b[0]), .eq(e0));
    eq1 eq1_unit_1 (.i0(a[1]), .i1(b[1]), .eq(e1));

    assign aeqb = e0 & e1;
endmodule
