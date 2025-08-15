module top(in0, in1, in2, in3, out);

  input  in0;
  input  in1;
  input  in2;
  input  in3;
  output  out;

  // wires

  wire  net0;
  wire  net1;

  // components

  and2 i0 (
    .a(in0),
    .b(in1),
    .z(net0)
  );

  and2 i1 (
    .a(in2),
    .b(in3),
    .z(net1)
  );

  and2 i2 (
    .a(net0),
    .b(net1),
    .z(out)
  );


endmodule
