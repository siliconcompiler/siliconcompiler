////////////////////////////////////////////////////////////////////////////////////////////////////

module hard_mem_1rw_bit_mask_d64_w7_wrapper #( parameter width_p = 7
                                             , parameter els_p   = 64
                                             , parameter addr_width_lp = $clog2(els_p)
                                             )
  ( input                      clk_i
  , input                      reset_i
  , input [width_p-1:0]        data_i
  , input [addr_width_lp-1:0]  addr_i
  , input                      v_i
  , input [width_p-1:0]        w_mask_i
  , input                      w_i
  , output wire [width_p-1:0]  data_o
  );

  // TODO: Replace the sythesizable RTL model below with the hardened
  // equivilant. Use the RTL model to check the sematics of the harden block
  // match.
  //
  // NOTE: The instance name of the hardened block is expected to be "mem".

  //hard_mem_1rw_bit_mask_d64_w7
  //  mem
  //    ( ...
  //    );

  wire [7:0] Q;
  wire [7:0] D;
  wire [7:0] WEN;

  assign data_o = Q[6:0];
  assign D      = {1'b0,data_i};
  assign WEN    = {1'b0,w_mask_i};

  tsmc65lp_1rf_lg6_w8_bit mem (
    .CLK  (clk_i   ),
    .Q    (Q  ), // out
    .CEN  (~v_i      ), // lo true
    .WEN  (WEN),
    .GWEN (~w_i     ), // lo true
    .A    (addr_i  ), // in
    .D    (D  ), // in
    //
    .EMA  (3'd3    ), // Extra Margin Adjustment - default value
    .EMAW (2'd1    ), // Extra Margin Adjustment Write - default value
    .RET1N(1'b1    )  // Retention Mode (active low) - disabled
    );

endmodule

////////////////////////////////////////////////////////////////////////////////////////////////////

module hard_mem_1rw_bit_mask_d64_w96_wrapper #( parameter width_p = 96
                                              , parameter els_p   = 64
                                              , parameter addr_width_lp = $clog2(els_p)
                                              )
  ( input                      clk_i
  , input                      reset_i
  , input [width_p-1:0]        data_i
  , input [addr_width_lp-1:0]  addr_i
  , input                      v_i
  , input [width_p-1:0]        w_mask_i
  , input                      w_i
  , output wire [width_p-1:0]  data_o
  );

  // TODO: Replace the sythesizable RTL model below with the hardened
  // equivilant. Use the RTL model to check the sematics of the harden block
  // match.
  //
  // NOTE: The instance name of the hardened block is expected to be "mem".

  //hard_mem_1rw_bit_mask_d64_w96
  //  mem
  //    ( ...
  //    );


  tsmc65lp_1rf_lg6_w96_bit mem (
    .CLK  (clk_i   ),
    .Q    (data_o  ), // out
    .CEN  (~v_i      ), // lo true
    .WEN  (w_mask_i),
    .GWEN (~w_i     ), // lo true
    .A    (addr_i  ), // in
    .D    (data_i  ), // in
    //
    .EMA  (3'd3    ), // Extra Margin Adjustment - default value
    .EMAW (2'd1    ), // Extra Margin Adjustment Write - default value
    .RET1N(1'b1    )  // Retention Mode (active low) - disabled
    );

endmodule

////////////////////////////////////////////////////////////////////////////////////////////////////

module hard_mem_1rw_byte_mask_d512_w64_wrapper #( parameter width_p = 64
                                                , parameter els_p = 512
                                                , parameter addr_width_lp = $clog2(els_p)
                                                , parameter write_mask_width_lp = width_p>>3
                                                )
  ( input                            clk_i
  , input                            reset_i
  , input [width_p-1:0]              data_i
  , input [addr_width_lp-1:0]        addr_i
  , input                            v_i
  , input [write_mask_width_lp-1:0]  write_mask_i
  , input                            w_i
  , output wire [width_p-1:0]        data_o
  );

  // TODO: Replace the sythesizable RTL model below with the hardened
  // equivilant. Use the RTL model to check the sematics of the harden block
  // match.
  //
  // NOTE: The instance name of the hardened block is expected to be "mem".

  //hard_mem_1rw_byte_mask_d512_w64
  //  mem
  //    ( ...
  //    );

   wire [63:0] wen = ~{{8{write_mask_i[7]}}
                      ,{8{write_mask_i[6]}}
                      ,{8{write_mask_i[5]}}
                      ,{8{write_mask_i[4]}}
                      ,{8{write_mask_i[3]}}
                      ,{8{write_mask_i[2]}}
                      ,{8{write_mask_i[1]}}
                      ,{8{write_mask_i[0]}}};

  tsmc65lp_1rf_lg9_w64_bit mem (
    .CLK  (clk_i   ),
    .Q    (data_o  ), // out
    .CEN  (~v_i      ), // lo true
    .WEN  (wen),
    .GWEN (~w_i     ), // lo true
    .A    (addr_i  ), // in
    .D    (data_i  ), // in
    //
    .EMA  (3'd3    ), // Extra Margin Adjustment - default value
    .EMAW (2'd1    ), // Extra Margin Adjustment Write - default value
    .RET1N(1'b1    )  // Retention Mode (active low) - disabled
    );

endmodule

////////////////////////////////////////////////////////////////////////////////////////////////////

module hard_mem_1rw_d512_w64_wrapper #( parameter width_p = 64
                                      , parameter els_p = 512
                                      , parameter addr_width_lp = $clog2(els_p)
                                      )
  ( input                     clk_i
  , input                     v_i
  , input                     reset_i
  , input [width_p-1:0]       data_i
  , input [addr_width_lp-1:0] addr_i
  , input                     w_i
  , output wire [width_p-1:0] data_o
  );

  // TODO: Replace the sythesizable RTL model below with the hardened
  // equivilant. Use the RTL model to check the sematics of the harden block
  // match.
  //
  // NOTE: The instance name of the hardened block is expected to be "mem".

  //hard_mem_1rw_d512_w64
  //  mem
  //    ( ...
  //    );

  tsmc65lp_1rf_lg9_w64_all mem (
    .CLK  (clk_i   ),
    .Q    (data_o  ), // out
    .CEN  (~v_i      ), // lo true
    .WEN (~w_i     ), // lo true
    .A    (addr_i  ), // in
    .D    (data_i  ), // in
    //
    .EMA  (3'd3    ), // Extra Margin Adjustment - default value
    .EMAW (2'd1    ), // Extra Margin Adjustment Write - default value
    .RET1N(1'b1    )  // Retention Mode (active low) - disabled
    );


endmodule

////////////////////////////////////////////////////////////////////////////////////////////////////

