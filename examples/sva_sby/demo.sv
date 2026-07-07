// Adapted from the SymbiYosys (sby) project examples (ISC license),
// reformatted to the SiliconCompiler style. Original source:
// https://github.com/YosysHQ/sby/blob/f57802a16613f013e84e024df50fc3f0ea74f88b/docs/examples/quickstart/demo.sv

module demo (
    input clk,
    output reg [5:0] counter
);
    initial counter = 0;

    always @(posedge clk) begin
        if (counter == 15) counter <= 0;
        else counter <= counter + 1;
    end

`ifdef FORMAL
    always @(posedge clk) begin
        assert (counter < 32);
    end
`endif
endmodule
