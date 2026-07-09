// Adapted from the SymbiYosys (sby) project examples (ISC license),
// reformatted to the SiliconCompiler style. Original source:
// https://github.com/YosysHQ/sby/blob/f57802a16613f013e84e024df50fc3f0ea74f88b/docs/examples/quickstart/cover.sv

module top (
    input clk,
    input [7:0] din
);
    reg [31:0] state = 0;

    always @(posedge clk) begin
        state <= ((state << 5) + state) ^ din;
    end

`ifdef FORMAL
    always @(posedge clk) begin
        cover (state == 'd12345678);
        cover (state == 'h12345678);
    end
`endif
endmodule
