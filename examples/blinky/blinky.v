module blinky(
  input  CLK,
  output LED1,
  output LED2,
  output LED3
);
  // Blink LED 1 on/off for 2^22 clock cycles, or ~0.35 seconds at 12 Mhz
  reg [24:0] count;

  always @(posedge CLK) begin
    count <= count + 1'b1;
  end

  assign LED1 = count[22];
  assign LED2 = count[23];
  assign LED3 = count[24];
endmodule
