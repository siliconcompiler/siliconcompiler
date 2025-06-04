module heartbeat
  #(parameter N = 8)
   (
    //inputs
    input      clk,    // clock
    input      nreset, // async active low reset
    //outputs
    output reg out     // heartbeat
    );

   reg [N-1:0] counter_reg;
   wire [N-1:0] counter_new;

   // state
   always @(posedge clk or negedge nreset) begin
      if (!nreset) begin
         counter_reg <= {(N) {1'b0}};
         out <= 1'b0;
      end else begin
         counter_reg <= counter_new;
         out <= (counter_reg == {(N) {1'b1}});
      end
    end

   // increment module
   increment #(.N(N)) i0 (.out(counter_new[N-1:0]),
                          .in(counter_reg[N-1:0]));


endmodule
