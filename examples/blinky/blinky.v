module blinky(
  input  CLK,
  output LED1
);
  // Blink LED 1 on/off for 2^22 clock cycles, or ~0.35 seconds at 12 Mhz
  reg [22:0] count;

  always @(posedge CLK) begin
    count <= count + 1'b1;
  end

  assign LED1 = count[22];
endmodule
