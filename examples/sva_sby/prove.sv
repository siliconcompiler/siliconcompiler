// Adapted from the SymbiYosys (sby) project examples (ISC license),
// reformatted to the SiliconCompiler style. Original source:
// https://github.com/YosysHQ/sby/blob/f57802a16613f013e84e024df50fc3f0ea74f88b/docs/examples/quickstart/prove.sv

module testbench (
    input clk,
    input reset,
    input [7:0] din,
    output reg [7:0] dout
);
    demo uut (
        .clk  (clk),
        .reset(reset),
        .din  (din),
        .dout (dout)
    );

    reg init = 1;
    always @(posedge clk) begin
        if (init) assume (reset);
        if (!reset) assert (!dout[1:0]);
        init <= 0;
    end
endmodule

module demo (
    input clk,
    input reset,
    input [7:0] din,
    output reg [7:0] dout
);
    reg [7:0] buffer;
    reg [1:0] state;

    always @(posedge clk) begin
        if (reset) begin
            dout  <= 0;
            state <= 0;
        end else
            case (state)
                0: begin
                    buffer <= din;
                    state  <= 1;
                end
                1: begin
                    if (buffer[1:0]) buffer <= buffer + 1;
                    else state <= 2;
                end
                2: begin
                    dout  <= dout + buffer;
                    state <= 0;
                end
                default: ;
            endcase
    end
endmodule
