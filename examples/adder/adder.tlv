\m4_TLV_version 1d: tl-x.org

\SV
   m4_ifelse_block(M4_MAKERCHIP, 1,['
   m4_makerchip_module   
   '],['
   module adder#(parameter DATA_WIDTH = 32)(
    input clk,
    input axi_reset_n,

    //AXI-S Slave interface --incoming data

    input s_axis_valid, //from master
    input [DATA_WIDTH-1:0] s_axis_data,
    output s_axis_ready,

    //AXI-M Master interface --outgoing data

    output reg m_axis_valid,
    output reg [DATA_WIDTH-1:0] m_axis_data,
    input m_axis_ready
    );

   ']) 

\TLV
   
   m4_ifelse_block(M4_MAKERCHIP, 1,['
   $reset = *reset;
   '],['

   // Template connections
   // $axi_reset_n = *axi_reset_n;
   $s_axis_valid = *s_axis_valid;
   $s_axis_data[31:0] = *s_axis_data; //parametize
   $m_axis_ready = *m_axis_ready;
   $s_axis_ready = $m_axis_ready;
   *s_axis_ready = $s_axis_ready;
   //---------------------------------------------------
   //User connections here
   $aa[15:0] = $s_axis_data[15:0];
   $bb[15:0] = $s_axis_data[31:16];
   //---------------------------------------------------

   '])   

   $cc[31:0] = $aa[15:0] + $bb[15:0];
   


   

   //--------- USER LOGIC SPACE BEGIN --------------  
   //            --- Sample ---
   // /datas[(DATA_WIDTH / 8)-1:0]
   //   $m_axis_data[7:0] = ($s_axis_valid & $s_axis_ready) ? 255 - $s_axis_data[#datas * 8+:8]) : $RETAIN;
   //   $m_axis_valid = $s_axis_valid & $s_axis_ready;
   //-------- USER LOGIC SPACE END --------------




   m4_ifelse_block(M4_MAKERCHIP, 1,['
   *passed = *cyc_cnt > 40;
   *failed = 1\'b0;
    '],['
   \SV_plus
      always_ff @(posedge *clk) begin
         *m_axis_valid <= $s_axis_valid & $s_axis_ready;
      end

   //--------------------------------------------
   //Map TLV signals to Verilog 
   $m_axis_data[31:0] = $cc;
   //--------------------------------------------

   //AXI Stream Outputs
   //*s_axis_ready = $s_axis_ready;
   //*m_axis_valid = $m_axis_valid;
   *m_axis_data = $m_axis_data;
   '])   


\SV
   endmodule