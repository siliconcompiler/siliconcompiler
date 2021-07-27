
module data_arrays_0_ext(
  input RW0_clk,
  input [5:0] RW0_addr,
  input RW0_en,
  input RW0_wmode,
  input [3:0] RW0_wmask,
  input [31:0] RW0_wdata,
  output [31:0] RW0_rdata
);

  fakeram45_64x32 mem (
    .clk      (RW0_clk   ),
    .rd_out   (RW0_rdata  ),
    .ce_in    (RW0_en    ),
    .we_in    (RW0_wmode     ),
    .w_mask_in({  {8{RW0_wmask[3]}}
                 ,{8{RW0_wmask[2]}}
                 ,{8{RW0_wmask[1]}}
                 ,{8{RW0_wmask[0]}}}
      ),
    .addr_in  (RW0_addr  ),
    .wd_in    (RW0_wdata  )
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


  fakeram45_64x32 mem (
    .clk      (RW0_clk   ),
    .rd_out   (RW0_rdata  ),
    .ce_in    (RW0_en    ),
    .we_in    (RW0_wmode     ),
    .w_mask_in({  {8{RW0_wmask[3]}}
                 ,{8{RW0_wmask[2]}}
                 ,{8{RW0_wmask[1]}}
                 ,{8{RW0_wmask[0]}}}
      ),
    .addr_in  (RW0_addr  ),
    .wd_in    (RW0_wdata  )
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

  // WARNING: This should be a true dual port RAM (1read and 1write), however
  //          bsg_fakeram doesn't support this yet. Using a simple 1 rw as a
  //          place holder.
  // WARNING: Ignoring R0_clk (assuming it is the same as W0_clk)
  wire [9:0] addr;
  wire en;
  assign addr_int = W0_en ? W0_addr : R0_addr;
  assign en = W0_en | R0_en;


  fakeram45_1024x32 mem (
    .clk      (W0_clk   ),
    .rd_out   (R0_data  ),
    .ce_in    (en    ),
    .we_in    (W0_en     ),
    .w_mask_in({  {8{W0_mask[3]}}
                 ,{8{W0_mask[2]}}
                 ,{8{W0_mask[1]}}
                 ,{8{W0_mask[0]}}}
      ),
    .addr_in  (addr_int  ),
    .wd_in    (W0_data  )
  );


endmodule
