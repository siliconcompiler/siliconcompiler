module heartbeat #(parameter N = 8)
   (
    input      _vdd,
    input      _vss,

    //unused padring connections
    output [1:0] we_dout,
    inout [1:0] we_ie,
    inout [1:0] we_oen,
    inout [35:0] we_tech_cfg,
    input ea_din,
    inout ea_ie,
    inout ea_oen,
    inout [17:0] ea_tech_cfg,

    //module inputs
    input      clk,// clock
    input      nreset,//async active low reset
    output reg out //heartbeat
    );

   // unused padring pins
   // we[0]: clk input
   assign we_dout[0] = 1'b0;
   assign we_oen[0] = 1'b0;
   assign we_ie[0] = ~we_oen[0];
   // we[1]: nreset input
   assign we_dout[1] = 1'b0;
   assign we_oen[1] = 1'b0;
   assign we_ie[1] = ~we_oen[1];
   // TODO: Document techcfg values. Also use Verilog-compatible for loop or SystemVerilog
   assign tie_lo_esd_0 = we_tech_cfg[16];
   assign tie_hi_esd_0 = we_tech_cfg[17];
   assign we_tech_cfg[0] = _vdd;
   assign we_tech_cfg[1] = _vdd;
   assign we_tech_cfg[2] = tie_lo_esd_0;
   assign we_tech_cfg[3] = _vdd;
   assign we_tech_cfg[4] = _vdd;
   assign we_tech_cfg[5] = 1'b0; // (disable vddio; no vddio in design)
   assign we_tech_cfg[6] = 1'b0;
   assign we_tech_cfg[7] = 1'b0;
   assign we_tech_cfg[8] = 1'b0;
   assign we_tech_cfg[9] = 1'b0;
   assign we_tech_cfg[10] = 1'b0;
   assign we_tech_cfg[11] = 1'b0;
   assign we_tech_cfg[12] = 1'b0;
   assign we_tech_cfg[15 : 13] = 3'b110;
   assign tie_lo_esd_1 = we_tech_cfg[34];
   assign tie_hi_esd_1 = we_tech_cfg[35];
   assign we_tech_cfg[18] = _vdd;
   assign we_tech_cfg[19] = _vdd;
   assign we_tech_cfg[20] = tie_lo_esd_0;
   assign we_tech_cfg[21] = _vdd;
   assign we_tech_cfg[22] = _vdd;
   assign we_tech_cfg[23] = 1'b0; // (disable vddio; no vddio in design)
   assign we_tech_cfg[24] = 1'b0;
   assign we_tech_cfg[25] = 1'b0;
   assign we_tech_cfg[26] = 1'b0;
   assign we_tech_cfg[27] = 1'b0;
   assign we_tech_cfg[28] = 1'b0;
   assign we_tech_cfg[29] = 1'b0;
   assign we_tech_cfg[30] = 1'b0;
   assign we_tech_cfg[33 : 31] = 3'b110;
   // ea: heartbeat output.
   assign ea_din[0] = 1'b0;
   assign ea_oen = 1'b1;
   assign ea_ie = ~ea_oen[1];
   assign tie_lo_esd_e = ea_tech_cfg[16];
   assign tie_hi_esd_e = ea_tech_cfg[17];
   assign ea_tech_cfg[0] = _vdd;
   assign ea_tech_cfg[1] = _vdd;
   assign ea_tech_cfg[2] = tie_lo_esd_e;
   assign ea_tech_cfg[3] = _vdd;
   assign ea_tech_cfg[4] = _vdd;
   assign ea_tech_cfg[5] = 1'b0; // (disable vddio; no vddio in design)
   assign ea_tech_cfg[6] = 1'b0;
   assign ea_tech_cfg[7] = 1'b0;
   assign ea_tech_cfg[8] = 1'b0;
   assign ea_tech_cfg[9] = 1'b0;
   assign ea_tech_cfg[10] = 1'b0;
   assign ea_tech_cfg[11] = 1'b0;
   assign ea_tech_cfg[12] = 1'b0;
   assign ea_tech_cfg[15 : 13] = 3'b110;

   // Actual heartbeat module.
   reg [N-1:0] counter_reg;

   always @ (posedge clk or negedge nreset)
     if(!nreset)
       begin
	  counter_reg <= 'b0;
	  out <= 1'b0;
       end
     else
       begin
	  counter_reg[N-1:0] <= counter_reg[N-1:0] + 1'b1;
	  out <= (counter_reg[N-1:0]=={(N){1'b1}});
       end

endmodule
