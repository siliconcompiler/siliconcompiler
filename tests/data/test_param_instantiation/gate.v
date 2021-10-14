module gate (
	input a,
	input b,
	output c
);
    parameter [0:0] Impl = 1'b0;

    generate 
        if (Impl == 1'b0) begin
            and2 impl(
                .a(a),
                .b(b),
                .c(c)
            );
        end else if (Impl == 1'b1) begin
            or2 impl(
                .a(a),
                .b(b),
                .c(c)
            );
        end
    endgenerate
endmodule
