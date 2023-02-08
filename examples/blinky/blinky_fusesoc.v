module blinky
  #(parameter clk_freq_hz = 256)
   (input  clk,
    output reg q = 1'b0);

   reg [$clog2(clk_freq_hz)-1:0] count = 0;

   always @(posedge clk) begin
      count <= count + 1;
      if (count == clk_freq_hz-1) begin
	 q <= !q;
	 count <= 0;
      end
   end

endmodule // blinky
