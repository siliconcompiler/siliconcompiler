// From the SymbiYosys (sby) project examples (ISC license):
// https://github.com/YosysHQ/sby -- docs/examples/quickstart/cover.sv

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
		cover (state == 'd 12345678);
		cover (state == 'h 12345678);
	end
`endif
endmodule
