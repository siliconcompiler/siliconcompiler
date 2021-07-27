module hard_mem_1rw_d512_w64_wrapper(clk_i, v_i, reset_i, data_i,
     addr_i, w_i, data_o);
  input clk_i, v_i, reset_i, w_i;
  input [63:0] data_i;
  input [8:0] addr_i;
  output [63:0] data_o;
  wire clk_i, v_i, reset_i, w_i;
  wire [63:0] data_i;
  wire [8:0] addr_i;
  wire [63:0] data_o;

  fakeram45_512x64 mem (
    .clk      (clk_i   ),
    .rd_out   (data_o  ),
    .ce_in    (1'b1    ),
    .we_in    (w_i     ),
    .w_mask_in({64{w_i}}),
    .addr_in  (addr_i  ),
    .wd_in    (data_i  )
  );

endmodule

module hard_mem_1rw_bit_mask_d64_w96_wrapper(clk_i, reset_i, data_i,
     addr_i, v_i, w_mask_i, w_i, data_o);
  input clk_i, reset_i, v_i, w_i;
  input [95:0] data_i, w_mask_i;
  input [5:0] addr_i;
  output [95:0] data_o;
  wire clk_i, reset_i, v_i, w_i;
  wire [95:0] data_i, w_mask_i;
  wire [5:0] addr_i;
  wire [95:0] data_o;

  fakeram45_64x96 mem (
    .clk      (clk_i   ),
    .rd_out   (data_o  ),
    .ce_in    (1'b1    ),
    .we_in    (w_i     ),
    .w_mask_in(w_mask_i),
    .addr_in  (addr_i  ),
    .wd_in    (data_i  )
  );

endmodule


module hard_mem_1rw_byte_mask_d512_w64_wrapper(clk_i, reset_i, data_i,
     addr_i, v_i, write_mask_i, w_i, data_o);
  input clk_i, reset_i, v_i, w_i;
  input [63:0] data_i;
  input [8:0] addr_i;
  input [7:0] write_mask_i;
  output [63:0] data_o;
  wire clk_i, reset_i, v_i, w_i;
  wire [63:0] data_i;
  wire [8:0] addr_i;
  wire [7:0] write_mask_i;
  wire [63:0] data_o;
  wire [63:0] wen;

  fakeram45_512x64 mem (
    .clk      (clk_i   ),
    .rd_out   (data_o  ),
    .ce_in    (1'b1    ),
    .we_in    (w_i     ),
    .w_mask_in({{8{write_mask_i[7]}},
                {8{write_mask_i[6]}},
                {8{write_mask_i[5]}},
                {8{write_mask_i[4]}},
                {8{write_mask_i[3]}},
                {8{write_mask_i[2]}},
                {8{write_mask_i[1]}},
                {8{write_mask_i[0]}}}
      ),
    .addr_in  (addr_i  ),
    .wd_in    (data_i  )
  );

endmodule

module hard_mem_1rw_bit_mask_d64_w7_wrapper(clk_i, reset_i, data_i,
     addr_i, v_i, w_mask_i, w_i, data_o);
  input clk_i, reset_i, v_i, w_i;
  input [6:0] data_i, w_mask_i;
  input [5:0] addr_i;
  output [6:0] data_o;
  wire clk_i, reset_i, v_i, w_i;
  wire [6:0] data_i, w_mask_i;
  wire [5:0] addr_i;
  wire [6:0] data_o;

  fakeram45_64x7 mem (
    .clk      (clk_i   ),
    .rd_out   (data_o  ),
    .ce_in    (1'b1    ),
    .we_in    (w_i     ),
    .w_mask_in(w_mask_i),
    .addr_in  (addr_i  ),
    .wd_in    (data_i  )
  );

endmodule

module hard_mem_1r1w_d32_w64_wrapper(clk_i, reset_i, w_v_i, w_addr_i,
     w_data_i, r_v_i, r_addr_i, r_data_o);
  input clk_i, reset_i, w_v_i, r_v_i;
  input [4:0] w_addr_i, r_addr_i;
  input [63:0] w_data_i;
  output [63:0] r_data_o;
  wire clk_i, reset_i, w_v_i, r_v_i;
  wire [4:0] w_addr_i, r_addr_i;
  wire [63:0] w_data_i;
  wire [63:0] r_data_o;

  // WARNING: This should be a simple 2 port RAM (1read and 1write), however
  //          bsg_fakeram doesn't support this yet. Using a simple 1 rw as a
  //          place holder.
  wire [4:0] addr;
  assign addr_int = w_v_i ? w_addr_i : r_addr_i;

  fakeram45_32x64 mem (
    .clk      (clk_i   ),
    .rd_out   (r_data_o  ),
    .ce_in    (1'b1    ),
    .we_in    (w_v_i     ),
    .w_mask_in({64{w_v_i}}),
    .addr_in  (addr_int  ),
    .wd_in    (w_data_i  )
  );

endmodule

module hard_mem_1rw_bit_mask_d64_w15_wrapper(clk_i, reset_i, data_i,
     addr_i, v_i, w_mask_i, w_i, data_o);
  input clk_i, reset_i, v_i, w_i;
  input [14:0] data_i, w_mask_i;
  input [5:0] addr_i;
  output [14:0] data_o;
  wire clk_i, reset_i, v_i, w_i;
  wire [14:0] data_i, w_mask_i;
  wire [5:0] addr_i;
  wire [14:0] data_o;

  fakeram45_64x15 mem (
    .clk      (clk_i   ),
    .rd_out   (data_o  ),
    .ce_in    (1'b1    ),
    .we_in    (w_i     ),
    .w_mask_in(w_mask_i),
    .addr_in  (addr_i  ),
    .wd_in    (data_i  )
  );

endmodule

module hard_mem_1rw_d256_w96_wrapper(clk_i, v_i, reset_i, data_i,
     addr_i, w_i, data_o);
  input clk_i, v_i, reset_i, w_i;
  input [95:0] data_i;
  input [7:0] addr_i;
  output [95:0] data_o;
  wire clk_i, v_i, reset_i, w_i;
  wire [95:0] data_i;
  wire [7:0] addr_i;
  wire [95:0] data_o;

  fakeram45_256x96 mem (
    .clk      (clk_i   ),
    .rd_out   (data_o  ),
    .ce_in    (1'b1    ),
    .we_in    (w_i     ),
    .w_mask_in({96{w_i}}),
    .addr_in  (addr_i  ),
    .wd_in    (data_i  )
  );

endmodule
