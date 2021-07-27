
module data_arrays_0_ext(
  input RW0_clk,
  input [5:0] RW0_addr,
  input RW0_en,
  input RW0_wmode,
  input [3:0] RW0_wmask,
  input [31:0] RW0_wdata,
  output [31:0] RW0_rdata
);

      wire [31:0] wen = ~ {  {8{RW0_wmask[3]}}
                            ,{8{RW0_wmask[2]}}
                            ,{8{RW0_wmask[1]}}
                            ,{8{RW0_wmask[0]}}};

    gf12_1rf_lg6_w32_byte mem (
      .CLK  (RW0_clk   ),
      .Q    (RW0_rdata), // out
      .CEN  (~RW0_en  ), // lo true
      .WEN  (wen      ), // lo true
      .GWEN (~RW0_wmode  ), // lo true
      .A    (RW0_addr  ), // in
      .D    (RW0_wdata), // in
      .EMA  (3'd3     ), // Extra Margin Adjustment - default value
      .EMAW (2'd1     ), // Extra Margin Adjustment Write - default value
      .RET1N(1'b1     )  // Retention Mode (active low) - disabled
    );

endmodule


// # This is a very small array. Leaving is as synthesized

module tag_array_ext(
  input RW0_clk,
  input [1:0] RW0_addr,
  input RW0_en,
  input RW0_wmode,
  input [0:0] RW0_wmask,
  input [24:0] RW0_wdata,
  output [24:0] RW0_rdata
);

  reg reg_RW0_ren;
  reg [1:0] reg_RW0_addr;
  reg [24:0] ram [3:0];
  `ifdef RANDOMIZE_MEM_INIT
    integer initvar;
    initial begin
      #`RANDOMIZE_DELAY begin end
      for (initvar = 0; initvar < 4; initvar = initvar+1)
        ram[initvar] = {1 {$random}};
      reg_RW0_addr = {1 {$random}};
    end
  `endif
  integer i;
  always @(posedge RW0_clk)
    reg_RW0_ren <= RW0_en && !RW0_wmode;
  always @(posedge RW0_clk)
    if (RW0_en && !RW0_wmode) reg_RW0_addr <= RW0_addr;
  always @(posedge RW0_clk)
    if (RW0_en && RW0_wmode) begin
      for(i=0;i<1;i=i+1) begin
        if(RW0_wmask[i]) begin
          ram[RW0_addr][i*25 +: 25] <= RW0_wdata[i*25 +: 25];
        end
      end
    end
  `ifdef RANDOMIZE_GARBAGE_ASSIGN
  reg [31:0] RW0_random;
  `ifdef RANDOMIZE_MEM_INIT
    initial begin
      #`RANDOMIZE_DELAY begin end
      RW0_random = {$random};
      reg_RW0_ren = RW0_random[0];
    end
  `endif
  always @(posedge RW0_clk) RW0_random <= {$random};
  assign RW0_rdata = reg_RW0_ren ? ram[reg_RW0_addr] : RW0_random[24:0];
  `else
  assign RW0_rdata = ram[reg_RW0_addr];
  `endif

endmodule

module data_arrays_0_0_ext(
  input RW0_clk,
  input [5:0] RW0_addr,
  input RW0_en,
  input RW0_wmode,
  input [0:0] RW0_wmask,
  input [31:0] RW0_wdata,
  output [31:0] RW0_rdata
);

    gf12_1rf_lg6_w32_all mem (
      .CLK  (RW0_clk   ),
      .Q    (RW0_rdata), // out
      .CEN  (~RW0_en  ), // lo true
      .GWEN (~RW0_wmode  ), // lo true
      .A    (RW0_addr  ), // in
      .D    (RW0_wdata), // in
      .EMA  (3'd3     ), // Extra Margin Adjustment - default value
      .EMAW (2'd1     ), // Extra Margin Adjustment Write - default value
      .RET1N(1'b1     )  // Retention Mode (active low) - disabled
    );

endmodule

module mem_ext(
  input W0_clk,
  input [9:0] W0_addr,
  input W0_en,
  input [31:0] W0_data,
  input [3:0] W0_mask,
  input R0_clk,
  input [9:0] R0_addr,
  input R0_en,
  output [31:0] R0_data
);

      wire [31:0] wen = ~ {  {8{W0_mask[3]}}
                            ,{8{W0_mask[2]}}
                            ,{8{W0_mask[1]}}
                            ,{8{W0_mask[0]}}};

      gf12_2rf_lg10_w32_bit mem (
         .CLKA   (W0_clk)
        ,.CLKB   (W0_clk)
        /// Read port
        ,.AA    (R0_addr)
        ,.CENA  (~R0_en)
        ,.QA    (R0_data)

        /// Write port
        ,.AB    (W0_addr)
        ,.DB    (W0_data)
        ,.CENB  (~W0_en)
        ,.WENB  (~wen)

        ,.EMAA   (3'd3  )
        ,.EMAB   (3'd3  )
        ,.RET1N (1'b1  )
        );


endmodule
