// A simple enabled counter with formal properties.
//
// The properties are guarded by `ifdef FORMAL, which yosys defines
// automatically when the sources are read with `read_verilog -formal`
// (as the sby tasks do), so they are invisible to synthesis/simulation
// flows.

module counter #(
    parameter WIDTH = 8
) (
    input clk,
    input rst,
    input en,
    output reg [WIDTH-1:0] count
);

    always @(posedge clk) begin
        if (rst) count <= {WIDTH{1'b0}};
        else if (en) count <= count + 1'b1;
    end

`ifdef FORMAL
    // $past() is only valid after the first clock edge
    reg past_valid = 1'b0;
    always @(posedge clk) past_valid <= 1'b1;

    always @(posedge clk) begin
        if (past_valid) begin
            // exactly one of these holds each cycle
            if ($past(rst)) begin
                a_reset : assert (count == {WIDTH{1'b0}});
            end else if (!$past(en)) begin
                a_hold : assert (count == $past(count));
            end else begin
                a_increment : assert (count == $past(count) + 1'b1);
            end

            // reachability targets for cover mode
            c_rollover : cover (count == {WIDTH{1'b1}});
            c_counting : cover (!rst && en && count != {WIDTH{1'b0}});
        end
    end
`endif

endmodule
