// From the SymbiYosys (sby) project examples (ISC license):
// https://github.com/YosysHQ/sby -- docs/examples/quickstart/demo.sv

module demo (
  input clk,
  output reg [5:0] counter
);
  initial counter = 0;

  always @(posedge clk) begin
    if (counter == 15)
      counter <= 0;
    else
      counter <= counter + 1;
  end

`ifdef FORMAL
  always @(posedge clk) begin
    assert (counter < 32);
  end
`endif
endmodule
