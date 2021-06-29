

module bsg_mem_1r1w_synth_width_p76_els_p2_read_write_same_addr_p0_harden_p0
(
  w_clk_i,
  w_reset_i,
  w_v_i,
  w_addr_i,
  w_data_i,
  r_v_i,
  r_addr_i,
  r_data_o
);

  input [0:0] w_addr_i;
  input [75:0] w_data_i;
  input [0:0] r_addr_i;
  output [75:0] r_data_o;
  input w_clk_i;
  input w_reset_i;
  input w_v_i;
  input r_v_i;
  wire [75:0] r_data_o;
  wire N0,N1,N2,N3,N4,N5,N7,N8;
  reg [151:0] mem;
  assign r_data_o[75] = (N3)? mem[75] : 
                        (N0)? mem[151] : 1'b0;
  assign N0 = r_addr_i[0];
  assign r_data_o[74] = (N3)? mem[74] : 
                        (N0)? mem[150] : 1'b0;
  assign r_data_o[73] = (N3)? mem[73] : 
                        (N0)? mem[149] : 1'b0;
  assign r_data_o[72] = (N3)? mem[72] : 
                        (N0)? mem[148] : 1'b0;
  assign r_data_o[71] = (N3)? mem[71] : 
                        (N0)? mem[147] : 1'b0;
  assign r_data_o[70] = (N3)? mem[70] : 
                        (N0)? mem[146] : 1'b0;
  assign r_data_o[69] = (N3)? mem[69] : 
                        (N0)? mem[145] : 1'b0;
  assign r_data_o[68] = (N3)? mem[68] : 
                        (N0)? mem[144] : 1'b0;
  assign r_data_o[67] = (N3)? mem[67] : 
                        (N0)? mem[143] : 1'b0;
  assign r_data_o[66] = (N3)? mem[66] : 
                        (N0)? mem[142] : 1'b0;
  assign r_data_o[65] = (N3)? mem[65] : 
                        (N0)? mem[141] : 1'b0;
  assign r_data_o[64] = (N3)? mem[64] : 
                        (N0)? mem[140] : 1'b0;
  assign r_data_o[63] = (N3)? mem[63] : 
                        (N0)? mem[139] : 1'b0;
  assign r_data_o[62] = (N3)? mem[62] : 
                        (N0)? mem[138] : 1'b0;
  assign r_data_o[61] = (N3)? mem[61] : 
                        (N0)? mem[137] : 1'b0;
  assign r_data_o[60] = (N3)? mem[60] : 
                        (N0)? mem[136] : 1'b0;
  assign r_data_o[59] = (N3)? mem[59] : 
                        (N0)? mem[135] : 1'b0;
  assign r_data_o[58] = (N3)? mem[58] : 
                        (N0)? mem[134] : 1'b0;
  assign r_data_o[57] = (N3)? mem[57] : 
                        (N0)? mem[133] : 1'b0;
  assign r_data_o[56] = (N3)? mem[56] : 
                        (N0)? mem[132] : 1'b0;
  assign r_data_o[55] = (N3)? mem[55] : 
                        (N0)? mem[131] : 1'b0;
  assign r_data_o[54] = (N3)? mem[54] : 
                        (N0)? mem[130] : 1'b0;
  assign r_data_o[53] = (N3)? mem[53] : 
                        (N0)? mem[129] : 1'b0;
  assign r_data_o[52] = (N3)? mem[52] : 
                        (N0)? mem[128] : 1'b0;
  assign r_data_o[51] = (N3)? mem[51] : 
                        (N0)? mem[127] : 1'b0;
  assign r_data_o[50] = (N3)? mem[50] : 
                        (N0)? mem[126] : 1'b0;
  assign r_data_o[49] = (N3)? mem[49] : 
                        (N0)? mem[125] : 1'b0;
  assign r_data_o[48] = (N3)? mem[48] : 
                        (N0)? mem[124] : 1'b0;
  assign r_data_o[47] = (N3)? mem[47] : 
                        (N0)? mem[123] : 1'b0;
  assign r_data_o[46] = (N3)? mem[46] : 
                        (N0)? mem[122] : 1'b0;
  assign r_data_o[45] = (N3)? mem[45] : 
                        (N0)? mem[121] : 1'b0;
  assign r_data_o[44] = (N3)? mem[44] : 
                        (N0)? mem[120] : 1'b0;
  assign r_data_o[43] = (N3)? mem[43] : 
                        (N0)? mem[119] : 1'b0;
  assign r_data_o[42] = (N3)? mem[42] : 
                        (N0)? mem[118] : 1'b0;
  assign r_data_o[41] = (N3)? mem[41] : 
                        (N0)? mem[117] : 1'b0;
  assign r_data_o[40] = (N3)? mem[40] : 
                        (N0)? mem[116] : 1'b0;
  assign r_data_o[39] = (N3)? mem[39] : 
                        (N0)? mem[115] : 1'b0;
  assign r_data_o[38] = (N3)? mem[38] : 
                        (N0)? mem[114] : 1'b0;
  assign r_data_o[37] = (N3)? mem[37] : 
                        (N0)? mem[113] : 1'b0;
  assign r_data_o[36] = (N3)? mem[36] : 
                        (N0)? mem[112] : 1'b0;
  assign r_data_o[35] = (N3)? mem[35] : 
                        (N0)? mem[111] : 1'b0;
  assign r_data_o[34] = (N3)? mem[34] : 
                        (N0)? mem[110] : 1'b0;
  assign r_data_o[33] = (N3)? mem[33] : 
                        (N0)? mem[109] : 1'b0;
  assign r_data_o[32] = (N3)? mem[32] : 
                        (N0)? mem[108] : 1'b0;
  assign r_data_o[31] = (N3)? mem[31] : 
                        (N0)? mem[107] : 1'b0;
  assign r_data_o[30] = (N3)? mem[30] : 
                        (N0)? mem[106] : 1'b0;
  assign r_data_o[29] = (N3)? mem[29] : 
                        (N0)? mem[105] : 1'b0;
  assign r_data_o[28] = (N3)? mem[28] : 
                        (N0)? mem[104] : 1'b0;
  assign r_data_o[27] = (N3)? mem[27] : 
                        (N0)? mem[103] : 1'b0;
  assign r_data_o[26] = (N3)? mem[26] : 
                        (N0)? mem[102] : 1'b0;
  assign r_data_o[25] = (N3)? mem[25] : 
                        (N0)? mem[101] : 1'b0;
  assign r_data_o[24] = (N3)? mem[24] : 
                        (N0)? mem[100] : 1'b0;
  assign r_data_o[23] = (N3)? mem[23] : 
                        (N0)? mem[99] : 1'b0;
  assign r_data_o[22] = (N3)? mem[22] : 
                        (N0)? mem[98] : 1'b0;
  assign r_data_o[21] = (N3)? mem[21] : 
                        (N0)? mem[97] : 1'b0;
  assign r_data_o[20] = (N3)? mem[20] : 
                        (N0)? mem[96] : 1'b0;
  assign r_data_o[19] = (N3)? mem[19] : 
                        (N0)? mem[95] : 1'b0;
  assign r_data_o[18] = (N3)? mem[18] : 
                        (N0)? mem[94] : 1'b0;
  assign r_data_o[17] = (N3)? mem[17] : 
                        (N0)? mem[93] : 1'b0;
  assign r_data_o[16] = (N3)? mem[16] : 
                        (N0)? mem[92] : 1'b0;
  assign r_data_o[15] = (N3)? mem[15] : 
                        (N0)? mem[91] : 1'b0;
  assign r_data_o[14] = (N3)? mem[14] : 
                        (N0)? mem[90] : 1'b0;
  assign r_data_o[13] = (N3)? mem[13] : 
                        (N0)? mem[89] : 1'b0;
  assign r_data_o[12] = (N3)? mem[12] : 
                        (N0)? mem[88] : 1'b0;
  assign r_data_o[11] = (N3)? mem[11] : 
                        (N0)? mem[87] : 1'b0;
  assign r_data_o[10] = (N3)? mem[10] : 
                        (N0)? mem[86] : 1'b0;
  assign r_data_o[9] = (N3)? mem[9] : 
                       (N0)? mem[85] : 1'b0;
  assign r_data_o[8] = (N3)? mem[8] : 
                       (N0)? mem[84] : 1'b0;
  assign r_data_o[7] = (N3)? mem[7] : 
                       (N0)? mem[83] : 1'b0;
  assign r_data_o[6] = (N3)? mem[6] : 
                       (N0)? mem[82] : 1'b0;
  assign r_data_o[5] = (N3)? mem[5] : 
                       (N0)? mem[81] : 1'b0;
  assign r_data_o[4] = (N3)? mem[4] : 
                       (N0)? mem[80] : 1'b0;
  assign r_data_o[3] = (N3)? mem[3] : 
                       (N0)? mem[79] : 1'b0;
  assign r_data_o[2] = (N3)? mem[2] : 
                       (N0)? mem[78] : 1'b0;
  assign r_data_o[1] = (N3)? mem[1] : 
                       (N0)? mem[77] : 1'b0;
  assign r_data_o[0] = (N3)? mem[0] : 
                       (N0)? mem[76] : 1'b0;

  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[151] <= w_data_i[75];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[150] <= w_data_i[74];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[149] <= w_data_i[73];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[148] <= w_data_i[72];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[147] <= w_data_i[71];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[146] <= w_data_i[70];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[145] <= w_data_i[69];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[144] <= w_data_i[68];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[143] <= w_data_i[67];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[142] <= w_data_i[66];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[141] <= w_data_i[65];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[140] <= w_data_i[64];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[139] <= w_data_i[63];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[138] <= w_data_i[62];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[137] <= w_data_i[61];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[136] <= w_data_i[60];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[135] <= w_data_i[59];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[134] <= w_data_i[58];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[133] <= w_data_i[57];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[132] <= w_data_i[56];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[131] <= w_data_i[55];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[130] <= w_data_i[54];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[129] <= w_data_i[53];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[128] <= w_data_i[52];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[127] <= w_data_i[51];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[126] <= w_data_i[50];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[125] <= w_data_i[49];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[124] <= w_data_i[48];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[123] <= w_data_i[47];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[122] <= w_data_i[46];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[121] <= w_data_i[45];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[120] <= w_data_i[44];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[119] <= w_data_i[43];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[118] <= w_data_i[42];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[117] <= w_data_i[41];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[116] <= w_data_i[40];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[115] <= w_data_i[39];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[114] <= w_data_i[38];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[113] <= w_data_i[37];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[112] <= w_data_i[36];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[111] <= w_data_i[35];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[110] <= w_data_i[34];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[109] <= w_data_i[33];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[108] <= w_data_i[32];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[107] <= w_data_i[31];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[106] <= w_data_i[30];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[105] <= w_data_i[29];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[104] <= w_data_i[28];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[103] <= w_data_i[27];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[102] <= w_data_i[26];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[101] <= w_data_i[25];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[100] <= w_data_i[24];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[99] <= w_data_i[23];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[98] <= w_data_i[22];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[97] <= w_data_i[21];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[96] <= w_data_i[20];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[95] <= w_data_i[19];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[94] <= w_data_i[18];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[93] <= w_data_i[17];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[92] <= w_data_i[16];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[91] <= w_data_i[15];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[90] <= w_data_i[14];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[89] <= w_data_i[13];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[88] <= w_data_i[12];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[87] <= w_data_i[11];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[86] <= w_data_i[10];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[85] <= w_data_i[9];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[84] <= w_data_i[8];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[83] <= w_data_i[7];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[82] <= w_data_i[6];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[81] <= w_data_i[5];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[80] <= w_data_i[4];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[79] <= w_data_i[3];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[78] <= w_data_i[2];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[77] <= w_data_i[1];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[76] <= w_data_i[0];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[75] <= w_data_i[75];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[74] <= w_data_i[74];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[73] <= w_data_i[73];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[72] <= w_data_i[72];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[71] <= w_data_i[71];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[70] <= w_data_i[70];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[69] <= w_data_i[69];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[68] <= w_data_i[68];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[67] <= w_data_i[67];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[66] <= w_data_i[66];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[65] <= w_data_i[65];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[64] <= w_data_i[64];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[63] <= w_data_i[63];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[62] <= w_data_i[62];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[61] <= w_data_i[61];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[60] <= w_data_i[60];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[59] <= w_data_i[59];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[58] <= w_data_i[58];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[57] <= w_data_i[57];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[56] <= w_data_i[56];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[55] <= w_data_i[55];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[54] <= w_data_i[54];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[53] <= w_data_i[53];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[52] <= w_data_i[52];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[51] <= w_data_i[51];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[50] <= w_data_i[50];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[49] <= w_data_i[49];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[48] <= w_data_i[48];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[47] <= w_data_i[47];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[46] <= w_data_i[46];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[45] <= w_data_i[45];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[44] <= w_data_i[44];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[43] <= w_data_i[43];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[42] <= w_data_i[42];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[41] <= w_data_i[41];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[40] <= w_data_i[40];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[39] <= w_data_i[39];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[38] <= w_data_i[38];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[37] <= w_data_i[37];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[36] <= w_data_i[36];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[35] <= w_data_i[35];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[34] <= w_data_i[34];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[33] <= w_data_i[33];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[32] <= w_data_i[32];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[31] <= w_data_i[31];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[30] <= w_data_i[30];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[29] <= w_data_i[29];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[28] <= w_data_i[28];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[27] <= w_data_i[27];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[26] <= w_data_i[26];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[25] <= w_data_i[25];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[24] <= w_data_i[24];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[23] <= w_data_i[23];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[22] <= w_data_i[22];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[21] <= w_data_i[21];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[20] <= w_data_i[20];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[19] <= w_data_i[19];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[18] <= w_data_i[18];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[17] <= w_data_i[17];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[16] <= w_data_i[16];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[15] <= w_data_i[15];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[14] <= w_data_i[14];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[13] <= w_data_i[13];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[12] <= w_data_i[12];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[11] <= w_data_i[11];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[10] <= w_data_i[10];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[9] <= w_data_i[9];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[8] <= w_data_i[8];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[7] <= w_data_i[7];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[6] <= w_data_i[6];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[5] <= w_data_i[5];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[4] <= w_data_i[4];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[3] <= w_data_i[3];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[2] <= w_data_i[2];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[1] <= w_data_i[1];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[0] <= w_data_i[0];
    end 
  end

  assign N5 = ~w_addr_i[0];
  assign { N8, N7 } = (N1)? { w_addr_i[0:0], N5 } : 
                      (N2)? { 1'b0, 1'b0 } : 1'b0;
  assign N1 = w_v_i;
  assign N2 = N4;
  assign N3 = ~r_addr_i[0];
  assign N4 = ~w_v_i;

endmodule



module bsg_mem_1r1w_width_p76_els_p2_read_write_same_addr_p0
(
  w_clk_i,
  w_reset_i,
  w_v_i,
  w_addr_i,
  w_data_i,
  r_v_i,
  r_addr_i,
  r_data_o
);

  input [0:0] w_addr_i;
  input [75:0] w_data_i;
  input [0:0] r_addr_i;
  output [75:0] r_data_o;
  input w_clk_i;
  input w_reset_i;
  input w_v_i;
  input r_v_i;
  wire [75:0] r_data_o;

  bsg_mem_1r1w_synth_width_p76_els_p2_read_write_same_addr_p0_harden_p0
  synth
  (
    .w_clk_i(w_clk_i),
    .w_reset_i(w_reset_i),
    .w_v_i(w_v_i),
    .w_addr_i(w_addr_i[0]),
    .w_data_i(w_data_i),
    .r_v_i(r_v_i),
    .r_addr_i(r_addr_i[0]),
    .r_data_o(r_data_o)
  );


endmodule



module bsg_two_fifo_width_p76
(
  clk_i,
  reset_i,
  ready_o,
  data_i,
  v_i,
  v_o,
  data_o,
  yumi_i
);

  input [75:0] data_i;
  output [75:0] data_o;
  input clk_i;
  input reset_i;
  input v_i;
  input yumi_i;
  output ready_o;
  output v_o;
  wire [75:0] data_o;
  wire ready_o,v_o,N0,N1,enq_i,n_0_net_,n_cse_4,n_cse_6,n_cse_7,N2,N3,N4,N5,N6,N7,N8,
  N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21;
  reg full_r,tail_r,head_r,empty_r;

  bsg_mem_1r1w_width_p76_els_p2_read_write_same_addr_p0
  mem_1r1w
  (
    .w_clk_i(clk_i),
    .w_reset_i(reset_i),
    .w_v_i(enq_i),
    .w_addr_i(tail_r),
    .w_data_i(data_i),
    .r_v_i(n_0_net_),
    .r_addr_i(head_r),
    .r_data_o(data_o)
  );


  always @(posedge clk_i) begin
    if(1'b1) begin
      full_r <= N14;
    end 
  end


  always @(posedge clk_i) begin
    if(N9) begin
      tail_r <= N10;
    end 
  end


  always @(posedge clk_i) begin
    if(N11) begin
      head_r <= N12;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      empty_r <= N13;
    end 
  end

  assign N9 = (N0)? 1'b1 : 
              (N1)? N5 : 1'b0;
  assign N0 = N3;
  assign N1 = N2;
  assign N10 = (N0)? 1'b0 : 
               (N1)? N4 : 1'b0;
  assign N11 = (N0)? 1'b1 : 
               (N1)? yumi_i : 1'b0;
  assign N12 = (N0)? 1'b0 : 
               (N1)? N6 : 1'b0;
  assign N13 = (N0)? 1'b1 : 
               (N1)? N7 : 1'b0;
  assign N14 = (N0)? 1'b0 : 
               (N1)? N8 : 1'b0;
  assign n_0_net_ = ~empty_r;
  assign v_o = ~empty_r;
  assign ready_o = ~full_r;
  assign enq_i = v_i & N15;
  assign N15 = ~full_r;
  assign n_cse_4 = ~enq_i;
  assign n_cse_6 = ~yumi_i;
  assign n_cse_7 = N17 & n_cse_6;
  assign N17 = N16 & enq_i;
  assign N16 = ~empty_r;
  assign N2 = ~reset_i;
  assign N3 = reset_i;
  assign N5 = enq_i;
  assign N4 = ~tail_r;
  assign N6 = ~head_r;
  assign N7 = N18 | N20;
  assign N18 = empty_r & n_cse_4;
  assign N20 = N19 & n_cse_4;
  assign N19 = N15 & yumi_i;
  assign N8 = n_cse_7 | N21;
  assign N21 = full_r & n_cse_6;

endmodule



module bsg_mesh_router_dor_decoder_4_5_5_1
(
  clk_i,
  v_i,
  x_dirs_i,
  y_dirs_i,
  my_x_i,
  my_y_i,
  req_o
);

  input [4:0] v_i;
  input [19:0] x_dirs_i;
  input [24:0] y_dirs_i;
  input [3:0] my_x_i;
  input [4:0] my_y_i;
  output [24:0] req_o;
  input clk_i;
  wire [24:0] req_o;
  wire x_eq_4,x_gt_0,NS_req_4__weird_route,N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,
  N13,N14,N15,N16,N17,N18,N19,N20,N21,N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32;
  wire [2:0] x_eq,y_gt,y_lt;
  wire [4:0] y_eq;
  wire [4:3] x_gt;
  wire [0:0] x_lt;
  assign req_o[24] = 1'b0;
  assign req_o[18] = 1'b0;
  assign req_o[12] = 1'b0;
  assign req_o[6] = 1'b0;
  assign x_eq[0] = x_dirs_i[3:0] == my_x_i;
  assign y_eq[0] = y_dirs_i[4:0] == my_y_i;
  assign x_gt_0 = x_dirs_i[3:0] > my_x_i;
  assign y_gt[0] = y_dirs_i[4:0] > my_y_i;
  assign x_eq[1] = x_dirs_i[7:4] == my_x_i;
  assign y_eq[1] = y_dirs_i[9:5] == my_y_i;
  assign y_gt[1] = y_dirs_i[9:5] > my_y_i;
  assign x_eq[2] = x_dirs_i[11:8] == my_x_i;
  assign y_eq[2] = y_dirs_i[14:10] == my_y_i;
  assign y_gt[2] = y_dirs_i[14:10] > my_y_i;
  assign y_eq[3] = y_dirs_i[19:15] == my_y_i;
  assign x_gt[3] = x_dirs_i[15:12] > my_x_i;
  assign x_eq_4 = x_dirs_i[19:16] == my_x_i;
  assign y_eq[4] = y_dirs_i[24:20] == my_y_i;
  assign x_gt[4] = x_dirs_i[19:16] > my_x_i;
  assign x_lt[0] = N0 & N1;
  assign N0 = ~x_gt_0;
  assign N1 = ~x_eq[0];
  assign y_lt[0] = N2 & N3;
  assign N2 = ~y_gt[0];
  assign N3 = ~y_eq[0];
  assign y_lt[1] = N4 & N5;
  assign N4 = ~y_gt[1];
  assign N5 = ~y_eq[1];
  assign y_lt[2] = N6 & N7;
  assign N6 = ~y_gt[2];
  assign N7 = ~y_eq[2];
  assign req_o[7] = v_i[1] & N8;
  assign N8 = ~x_eq[1];
  assign req_o[5] = N9 & y_eq[1];
  assign N9 = v_i[1] & x_eq[1];
  assign req_o[9] = N10 & y_gt[1];
  assign N10 = v_i[1] & x_eq[1];
  assign req_o[8] = N11 & y_lt[1];
  assign N11 = v_i[1] & x_eq[1];
  assign req_o[11] = v_i[2] & N12;
  assign N12 = ~x_eq[2];
  assign req_o[10] = N13 & y_eq[2];
  assign N13 = v_i[2] & x_eq[2];
  assign req_o[14] = N14 & y_gt[2];
  assign N14 = v_i[2] & x_eq[2];
  assign req_o[13] = N15 & y_lt[2];
  assign N15 = v_i[2] & x_eq[2];
  assign req_o[19] = N17 & N18;
  assign N17 = v_i[3] & N16;
  assign N16 = ~y_eq[3];
  assign N18 = ~1'b0;
  assign req_o[15] = N19 & N18;
  assign N19 = v_i[3] & y_eq[3];
  assign req_o[16] = N20 & N21;
  assign N20 = v_i[3] & 1'b0;
  assign N21 = ~x_gt[3];
  assign req_o[17] = N22 & x_gt[3];
  assign N22 = v_i[3] & 1'b0;
  assign NS_req_4__weird_route = ~x_eq_4;
  assign req_o[23] = N24 & N25;
  assign N24 = v_i[4] & N23;
  assign N23 = ~y_eq[4];
  assign N25 = ~NS_req_4__weird_route;
  assign req_o[20] = N26 & N25;
  assign N26 = v_i[4] & y_eq[4];
  assign req_o[21] = N27 & N28;
  assign N27 = v_i[4] & NS_req_4__weird_route;
  assign N28 = ~x_gt[4];
  assign req_o[22] = N29 & x_gt[4];
  assign N29 = v_i[4] & NS_req_4__weird_route;
  assign req_o[2] = v_i[0] & x_gt_0;
  assign req_o[1] = v_i[0] & x_lt[0];
  assign req_o[4] = N30 & y_gt[0];
  assign N30 = v_i[0] & x_eq[0];
  assign req_o[3] = N31 & y_lt[0];
  assign N31 = v_i[0] & x_eq[0];
  assign req_o[0] = N32 & y_eq[0];
  assign N32 = v_i[0] & x_eq[0];

endmodule



module bsg_round_robin_arb_inputs_p3
(
  clk_i,
  reset_i,
  grants_en_i,
  reqs_i,
  grants_o,
  v_o,
  tag_o,
  yumi_i
);

  input [2:0] reqs_i;
  output [2:0] grants_o;
  output [1:0] tag_o;
  input clk_i;
  input reset_i;
  input grants_en_i;
  input yumi_i;
  output v_o;
  wire [2:0] grants_o;
  wire [1:0] tag_o;
  wire v_o,N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,
  N21,N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32,N33,N34,N35,N36,N37,N38,N39,N40,
  N41,N42,N43,N44,N45,N46,N47,N48,N49,N50,N51,N52,N53,N54,N55,N56,N57,N58,N59,N60,
  N61,N62,N63,N64,N65,N66,N67,N68,N69,N70,N71,N72,N73,N74,N75;
  reg [1:0] last_r;
  assign N10 = grants_en_i & N8;
  assign N11 = N9 & N46;
  assign N12 = N10 & N11;
  assign N15 = grants_en_i & N13;
  assign N16 = N14 & reqs_i[1];
  assign N17 = N15 & N16;
  assign N18 = N7 | last_r[1];
  assign N19 = last_r[0] | N8;
  assign N20 = N18 | N19;
  assign N21 = N20 | reqs_i[1];
  assign N23 = N7 | last_r[1];
  assign N24 = last_r[0] | reqs_i[2];
  assign N25 = reqs_i[1] | N46;
  assign N26 = N23 | N24;
  assign N27 = N26 | N25;
  assign N29 = N7 | last_r[1];
  assign N30 = N14 | N8;
  assign N31 = N29 | N30;
  assign N33 = grants_en_i & N13;
  assign N34 = last_r[0] & N8;
  assign N35 = N33 & N34;
  assign N36 = N35 & reqs_i[0];
  assign N37 = N7 | last_r[1];
  assign N38 = N14 | reqs_i[2];
  assign N39 = N9 | reqs_i[0];
  assign N40 = N37 | N38;
  assign N41 = N40 | N39;
  assign N43 = grants_en_i & last_r[1];
  assign N44 = N14 & reqs_i[0];
  assign N45 = N43 & N44;
  assign N47 = grants_en_i & last_r[1];
  assign N48 = N14 & reqs_i[1];
  assign N49 = N47 & N48;
  assign N50 = N49 & N46;
  assign N51 = N7 | N13;
  assign N52 = last_r[0] | N8;
  assign N53 = reqs_i[1] | reqs_i[0];
  assign N54 = N51 | N52;
  assign N55 = N54 | N53;
  assign N57 = grants_en_i & last_r[1];
  assign N58 = last_r[0] & reqs_i[2];
  assign N59 = N57 & N58;
  assign N60 = grants_en_i & last_r[1];
  assign N61 = last_r[0] & reqs_i[0];
  assign N62 = N60 & N61;
  assign N63 = grants_en_i & last_r[1];
  assign N64 = last_r[0] & reqs_i[1];
  assign N65 = N63 & N64;

  always @(posedge clk_i) begin
    if(N72) begin
      last_r[1] <= N70;
    end 
  end


  always @(posedge clk_i) begin
    if(N72) begin
      last_r[0] <= N69;
    end 
  end

  assign grants_o = (N7)? { 1'b0, 1'b0, 1'b0 } : 
                    (N0)? { 1'b0, 1'b0, 1'b0 } : 
                    (N1)? { 1'b0, 1'b1, 1'b0 } : 
                    (N22)? { 1'b1, 1'b0, 1'b0 } : 
                    (N28)? { 1'b0, 1'b0, 1'b1 } : 
                    (N32)? { 1'b1, 1'b0, 1'b0 } : 
                    (N2)? { 1'b0, 1'b0, 1'b1 } : 
                    (N42)? { 1'b0, 1'b1, 1'b0 } : 
                    (N3)? { 1'b0, 1'b0, 1'b1 } : 
                    (N4)? { 1'b0, 1'b1, 1'b0 } : 
                    (N56)? { 1'b1, 1'b0, 1'b0 } : 1'b0;
  assign N0 = N12;
  assign N1 = N17;
  assign N2 = N36;
  assign N3 = N45;
  assign N4 = N50;
  assign tag_o = (N7)? { 1'b0, 1'b0 } : 
                 (N0)? { 1'b0, 1'b0 } : 
                 (N1)? { 1'b0, 1'b1 } : 
                 (N22)? { 1'b1, 1'b0 } : 
                 (N28)? { 1'b0, 1'b0 } : 
                 (N32)? { 1'b1, 1'b0 } : 
                 (N2)? { 1'b0, 1'b0 } : 
                 (N42)? { 1'b0, 1'b1 } : 
                 (N3)? { 1'b0, 1'b0 } : 
                 (N4)? { 1'b0, 1'b1 } : 
                 (N56)? { 1'b1, 1'b0 } : 
                 (N66)? { 1'b0, 1'b0 } : 1'b0;
  assign { N70, N69 } = (N5)? { 1'b0, 1'b0 } : 
                        (N6)? tag_o : 1'b0;
  assign N5 = reset_i;
  assign N6 = N68;
  assign N7 = ~grants_en_i;
  assign N8 = ~reqs_i[2];
  assign N9 = ~reqs_i[1];
  assign N13 = ~last_r[1];
  assign N14 = ~last_r[0];
  assign N22 = ~N21;
  assign N28 = ~N27;
  assign N32 = ~N31;
  assign N42 = ~N41;
  assign N46 = ~reqs_i[0];
  assign N56 = ~N55;
  assign N66 = N59 | N73;
  assign N73 = N62 | N65;
  assign v_o = N75 & grants_en_i;
  assign N75 = N74 | reqs_i[0];
  assign N74 = reqs_i[2] | reqs_i[1];
  assign N67 = ~yumi_i;
  assign N68 = ~reset_i;
  assign N71 = N67 & N68;
  assign N72 = ~N71;

endmodule



module bsg_round_robin_arb_inputs_p4
(
  clk_i,
  reset_i,
  grants_en_i,
  reqs_i,
  grants_o,
  v_o,
  tag_o,
  yumi_i
);

  input [3:0] reqs_i;
  output [3:0] grants_o;
  output [1:0] tag_o;
  input clk_i;
  input reset_i;
  input grants_en_i;
  input yumi_i;
  output v_o;
  wire [3:0] grants_o;
  wire [1:0] tag_o;
  wire v_o,N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,
  N21,N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32,N33,N34,N35,N36,N37,N38,N39,N40,
  N41,N42,N43,N44,N45,N46,N47,N48,N49,N50,N51,N52,N53,N54,N55,N56,N57,N58,N59,N60,
  N61,N62,N63,N64,N65,N66,N67,N68,N69,N70,N71,N72,N73,N74,N75,N76,N77,N78,N79,N80,
  N81,N82,N83,N84,N85,N86,N87,N88,N89,N90,N91,N92,N93,N94,N95,N96,N97,N98,N99,N100,
  N101,N102,N103,N104,N105,N106,N107,N108,N109,N110,N111,N112,N113,N114,N115,N116,
  N117,N118,N119,N120,N121,N122,N123,N124,N125,N126;
  reg [1:0] last_r;

  always @(posedge clk_i) begin
    if(N123) begin
      last_r[1] <= N121;
    end 
  end


  always @(posedge clk_i) begin
    if(N123) begin
      last_r[0] <= N120;
    end 
  end

  assign N100 = ~grants_en_i;
  assign N101 = grants_en_i & N0 & (N1 & N2) & N3;
  assign N0 = ~reqs_i[0];
  assign N1 = ~reqs_i[1];
  assign N2 = ~reqs_i[2];
  assign N3 = ~reqs_i[3];
  assign N102 = grants_en_i & reqs_i[1] & (N4 & N5);
  assign N4 = ~last_r[0];
  assign N5 = ~last_r[1];
  assign N103 = grants_en_i & N6 & (N7 & reqs_i[2]) & N8;
  assign N6 = ~reqs_i[1];
  assign N7 = ~last_r[0];
  assign N8 = ~last_r[1];
  assign N9 = grants_en_i & N13;
  assign N10 = N9 & N14;
  assign N11 = N10 & N15;
  assign N12 = N11 & N16;
  assign N104 = N12 & reqs_i[3];
  assign N13 = ~reqs_i[1];
  assign N14 = ~last_r[0];
  assign N15 = ~reqs_i[2];
  assign N16 = ~last_r[1];
  assign N17 = grants_en_i & reqs_i[0];
  assign N18 = N17 & N22;
  assign N19 = N18 & N23;
  assign N20 = N19 & N24;
  assign N21 = N20 & N25;
  assign N105 = N21 & N26;
  assign N22 = ~reqs_i[1];
  assign N23 = ~last_r[0];
  assign N24 = ~reqs_i[2];
  assign N25 = ~last_r[1];
  assign N26 = ~reqs_i[3];
  assign N106 = grants_en_i & last_r[0] & (reqs_i[2] & N27);
  assign N27 = ~last_r[1];
  assign N107 = grants_en_i & last_r[0] & (N28 & N29) & reqs_i[3];
  assign N28 = ~reqs_i[2];
  assign N29 = ~last_r[1];
  assign N30 = grants_en_i & reqs_i[0];
  assign N31 = N30 & last_r[0];
  assign N32 = N31 & N34;
  assign N33 = N32 & N35;
  assign N108 = N33 & N36;
  assign N34 = ~reqs_i[2];
  assign N35 = ~last_r[1];
  assign N36 = ~reqs_i[3];
  assign N37 = grants_en_i & N42;
  assign N38 = N37 & reqs_i[1];
  assign N39 = N38 & last_r[0];
  assign N40 = N39 & N43;
  assign N41 = N40 & N44;
  assign N109 = N41 & N45;
  assign N42 = ~reqs_i[0];
  assign N43 = ~reqs_i[2];
  assign N44 = ~last_r[1];
  assign N45 = ~reqs_i[3];
  assign N110 = grants_en_i & N46 & (last_r[1] & reqs_i[3]);
  assign N46 = ~last_r[0];
  assign N111 = grants_en_i & reqs_i[0] & (N47 & last_r[1]) & N48;
  assign N47 = ~last_r[0];
  assign N48 = ~reqs_i[3];
  assign N49 = grants_en_i & N53;
  assign N50 = N49 & reqs_i[1];
  assign N51 = N50 & N54;
  assign N52 = N51 & last_r[1];
  assign N112 = N52 & N55;
  assign N53 = ~reqs_i[0];
  assign N54 = ~last_r[0];
  assign N55 = ~reqs_i[3];
  assign N56 = grants_en_i & N61;
  assign N57 = N56 & N62;
  assign N58 = N57 & N63;
  assign N59 = N58 & reqs_i[2];
  assign N60 = N59 & last_r[1];
  assign N113 = N60 & N64;
  assign N61 = ~reqs_i[0];
  assign N62 = ~reqs_i[1];
  assign N63 = ~last_r[0];
  assign N64 = ~reqs_i[3];
  assign N114 = grants_en_i & reqs_i[0] & (last_r[0] & last_r[1]);
  assign N115 = grants_en_i & N65 & (reqs_i[1] & last_r[0]) & last_r[1];
  assign N65 = ~reqs_i[0];
  assign N66 = grants_en_i & N70;
  assign N67 = N66 & N71;
  assign N68 = N67 & last_r[0];
  assign N69 = N68 & reqs_i[2];
  assign N116 = N69 & last_r[1];
  assign N70 = ~reqs_i[0];
  assign N71 = ~reqs_i[1];
  assign N72 = grants_en_i & N77;
  assign N73 = N72 & N78;
  assign N74 = N73 & last_r[0];
  assign N75 = N74 & N79;
  assign N76 = N75 & last_r[1];
  assign N117 = N76 & reqs_i[3];
  assign N77 = ~reqs_i[0];
  assign N78 = ~reqs_i[1];
  assign N79 = ~reqs_i[2];
  assign grants_o = (N80)? { 1'b0, 1'b0, 1'b0, 1'b0 } : 
                    (N81)? { 1'b0, 1'b0, 1'b0, 1'b0 } : 
                    (N82)? { 1'b0, 1'b0, 1'b1, 1'b0 } : 
                    (N83)? { 1'b0, 1'b1, 1'b0, 1'b0 } : 
                    (N84)? { 1'b1, 1'b0, 1'b0, 1'b0 } : 
                    (N85)? { 1'b0, 1'b0, 1'b0, 1'b1 } : 
                    (N86)? { 1'b0, 1'b1, 1'b0, 1'b0 } : 
                    (N87)? { 1'b1, 1'b0, 1'b0, 1'b0 } : 
                    (N88)? { 1'b0, 1'b0, 1'b0, 1'b1 } : 
                    (N89)? { 1'b0, 1'b0, 1'b1, 1'b0 } : 
                    (N90)? { 1'b1, 1'b0, 1'b0, 1'b0 } : 
                    (N91)? { 1'b0, 1'b0, 1'b0, 1'b1 } : 
                    (N92)? { 1'b0, 1'b0, 1'b1, 1'b0 } : 
                    (N93)? { 1'b0, 1'b1, 1'b0, 1'b0 } : 
                    (N94)? { 1'b0, 1'b0, 1'b0, 1'b1 } : 
                    (N95)? { 1'b0, 1'b0, 1'b1, 1'b0 } : 
                    (N96)? { 1'b0, 1'b1, 1'b0, 1'b0 } : 
                    (N97)? { 1'b1, 1'b0, 1'b0, 1'b0 } : 1'b0;
  assign N80 = N100;
  assign N81 = N101;
  assign N82 = N102;
  assign N83 = N103;
  assign N84 = N104;
  assign N85 = N105;
  assign N86 = N106;
  assign N87 = N107;
  assign N88 = N108;
  assign N89 = N109;
  assign N90 = N110;
  assign N91 = N111;
  assign N92 = N112;
  assign N93 = N113;
  assign N94 = N114;
  assign N95 = N115;
  assign N96 = N116;
  assign N97 = N117;
  assign tag_o = (N80)? { 1'b0, 1'b0 } : 
                 (N81)? { 1'b0, 1'b0 } : 
                 (N82)? { 1'b0, 1'b1 } : 
                 (N83)? { 1'b1, 1'b0 } : 
                 (N84)? { 1'b1, 1'b1 } : 
                 (N85)? { 1'b0, 1'b0 } : 
                 (N86)? { 1'b1, 1'b0 } : 
                 (N87)? { 1'b1, 1'b1 } : 
                 (N88)? { 1'b0, 1'b0 } : 
                 (N89)? { 1'b0, 1'b1 } : 
                 (N90)? { 1'b1, 1'b1 } : 
                 (N91)? { 1'b0, 1'b0 } : 
                 (N92)? { 1'b0, 1'b1 } : 
                 (N93)? { 1'b1, 1'b0 } : 
                 (N94)? { 1'b0, 1'b0 } : 
                 (N95)? { 1'b0, 1'b1 } : 
                 (N96)? { 1'b1, 1'b0 } : 
                 (N97)? { 1'b1, 1'b1 } : 1'b0;
  assign { N121, N120 } = (N98)? { 1'b0, 1'b0 } : 
                          (N99)? tag_o : 1'b0;
  assign N98 = reset_i;
  assign N99 = N119;
  assign v_o = N126 & grants_en_i;
  assign N126 = N125 | reqs_i[0];
  assign N125 = N124 | reqs_i[1];
  assign N124 = reqs_i[3] | reqs_i[2];
  assign N118 = ~yumi_i;
  assign N119 = ~reset_i;
  assign N122 = N118 & N119;
  assign N123 = ~N122;

endmodule



module bsg_round_robin_arb_inputs_p5
(
  clk_i,
  reset_i,
  grants_en_i,
  reqs_i,
  grants_o,
  v_o,
  tag_o,
  yumi_i
);

  input [4:0] reqs_i;
  output [4:0] grants_o;
  output [2:0] tag_o;
  input clk_i;
  input reset_i;
  input grants_en_i;
  input yumi_i;
  output v_o;
  wire [4:0] grants_o;
  wire [2:0] tag_o;
  wire v_o,N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,
  N21,N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32,N33,N34,N35,N36,N37,N38,N39,N40,
  N41,N42,N43,N44,N45,N46,N47,N48,N49,N50,N51,N52,N53,N54,N55,N56,N57,N58,N59,N60,
  N61,N62,N63,N64,N65,N66,N67,N68,N69,N70,N71,N72,N73,N74,N75,N76,N77,N78,N79,N80,
  N81,N82,N83,N84,N85,N86,N87,N88,N89,N90,N91,N92,N93,N94,N95,N96,N97,N98,N99,N100,
  N101,N102,N103,N104,N105,N106,N107,N108,N109,N110,N111,N112,N113,N114,N115,N116,
  N117,N118,N119,N120,N121,N122,N123,N124,N125,N126,N127,N128,N129,N130,N131,N132,
  N133,N134,N135,N136,N137,N138,N139,N140,N141,N142,N143,N144,N145,N146,N147,N148,
  N149,N150,N151,N152,N153,N154,N155,N156,N157,N158,N159,N160,N161,N162,N163,N164,
  N165,N166,N167,N168,N169,N170,N171,N172,N173,N174,N175,N176,N177,N178,N179,N180,
  N181,N182,N183,N184,N185,N186,N187,N188,N189,N190,N191,N192,N193,N194,N195,N196,
  N197,N198,N199,N200,N201,N202,N203,N204,N205,N206,N207,N208,N209,N210,N211,N212,
  N213,N214,N215,N216,N217,N218,N219,N220,N221,N222,N223,N224;
  reg [2:0] last_r;
  assign N23 = grants_en_i & N119;
  assign N24 = N20 & N64;
  assign N25 = N21 & N22;
  assign N26 = N23 & N24;
  assign N27 = N26 & N25;
  assign N31 = grants_en_i & N28;
  assign N32 = N29 & N30;
  assign N33 = N31 & N32;
  assign N34 = N33 & reqs_i[1];
  assign N35 = grants_en_i & N28;
  assign N36 = N29 & N30;
  assign N37 = reqs_i[2] & N21;
  assign N38 = N35 & N36;
  assign N39 = N38 & N37;
  assign N40 = grants_en_i & N28;
  assign N41 = N29 & N30;
  assign N42 = N40 & N41;
  assign N43 = N67 & N21;
  assign N44 = N42 & N43;
  assign N45 = N19 | last_r[2];
  assign N46 = last_r[1] | last_r[0];
  assign N47 = reqs_i[2] | reqs_i[1];
  assign N48 = N45 | N46;
  assign N49 = N97 | N47;
  assign N50 = N48 | N49;
  assign N52 = N19 | last_r[2];
  assign N53 = last_r[1] | last_r[0];
  assign N54 = reqs_i[4] | reqs_i[3];
  assign N55 = N52 | N53;
  assign N56 = N54 | N47;
  assign N57 = N55 | N56;
  assign N58 = N57 | N22;
  assign N60 = grants_en_i & N28;
  assign N61 = N29 & last_r[0];
  assign N62 = N60 & N61;
  assign N63 = N62 & reqs_i[2];
  assign N65 = grants_en_i & N28;
  assign N66 = N29 & last_r[0];
  assign N67 = reqs_i[3] & N64;
  assign N68 = N65 & N66;
  assign N69 = N68 & N67;
  assign N70 = N19 | last_r[2];
  assign N71 = last_r[1] | N30;
  assign N72 = N70 | N71;
  assign N73 = N97 | reqs_i[2];
  assign N74 = N72 | N73;
  assign N76 = grants_en_i & N28;
  assign N77 = N29 & last_r[0];
  assign N78 = N119 & N20;
  assign N79 = N64 & reqs_i[0];
  assign N80 = N76 & N77;
  assign N81 = N78 & N79;
  assign N82 = N80 & N81;
  assign N83 = N19 | last_r[2];
  assign N84 = last_r[1] | N30;
  assign N85 = reqs_i[2] | N21;
  assign N86 = N83 | N84;
  assign N87 = N54 | N85;
  assign N88 = N86 | N87;
  assign N89 = N88 | reqs_i[0];
  assign N91 = grants_en_i & N28;
  assign N92 = last_r[1] & N30;
  assign N93 = N91 & N92;
  assign N94 = N93 & reqs_i[3];
  assign N95 = N19 | last_r[2];
  assign N96 = N29 | last_r[0];
  assign N97 = N119 | reqs_i[3];
  assign N98 = N95 | N96;
  assign N99 = N98 | N97;
  assign N101 = grants_en_i & N28;
  assign N102 = last_r[1] & N30;
  assign N103 = N101 & N102;
  assign N104 = N78 & reqs_i[0];
  assign N105 = N103 & N104;
  assign N106 = grants_en_i & N28;
  assign N107 = last_r[1] & N30;
  assign N108 = N106 & N107;
  assign N109 = N78 & N156;
  assign N110 = N108 & N109;
  assign N111 = N19 | last_r[2];
  assign N112 = N29 | last_r[0];
  assign N113 = N64 | reqs_i[1];
  assign N114 = N111 | N112;
  assign N115 = N54 | N113;
  assign N116 = N114 | N115;
  assign N117 = N116 | reqs_i[0];
  assign N120 = N19 | last_r[2];
  assign N121 = N29 | N30;
  assign N122 = N120 | N121;
  assign N123 = N122 | N119;
  assign N125 = grants_en_i & N28;
  assign N126 = last_r[1] & last_r[0];
  assign N127 = N119 & reqs_i[0];
  assign N128 = N125 & N126;
  assign N129 = N128 & N127;
  assign N130 = grants_en_i & N28;
  assign N131 = last_r[1] & last_r[0];
  assign N132 = N119 & reqs_i[1];
  assign N133 = N130 & N131;
  assign N134 = N132 & N22;
  assign N135 = N133 & N134;
  assign N136 = grants_en_i & N28;
  assign N137 = last_r[1] & last_r[0];
  assign N138 = N119 & reqs_i[2];
  assign N139 = N136 & N137;
  assign N140 = N138 & N25;
  assign N141 = N139 & N140;
  assign N142 = N19 | last_r[2];
  assign N143 = N29 | N30;
  assign N144 = reqs_i[4] | N20;
  assign N145 = N142 | N143;
  assign N146 = N144 | N47;
  assign N147 = N145 | N146;
  assign N148 = N147 | reqs_i[0];
  assign N150 = grants_en_i & last_r[2];
  assign N151 = N29 & N30;
  assign N152 = N150 & N151;
  assign N153 = N152 & reqs_i[0];
  assign N154 = grants_en_i & last_r[2];
  assign N155 = N29 & N30;
  assign N156 = reqs_i[1] & N22;
  assign N157 = N154 & N155;
  assign N158 = N157 & N156;
  assign N159 = grants_en_i & last_r[2];
  assign N160 = N29 & N30;
  assign N161 = N159 & N160;
  assign N162 = N37 & N22;
  assign N163 = N161 & N162;
  assign N164 = grants_en_i & last_r[2];
  assign N165 = N29 & N30;
  assign N166 = N164 & N165;
  assign N167 = N67 & N25;
  assign N168 = N166 & N167;
  assign N169 = N19 | N28;
  assign N170 = last_r[1] | last_r[0];
  assign N171 = N169 | N170;
  assign N172 = N171 | N49;
  assign N173 = N172 | reqs_i[0];
  assign N175 = grants_en_i & last_r[2];
  assign N176 = last_r[0] & reqs_i[2];
  assign N177 = N175 & N176;
  assign N178 = grants_en_i & last_r[2];
  assign N179 = last_r[0] & reqs_i[3];
  assign N180 = N178 & N179;
  assign N181 = grants_en_i & last_r[2];
  assign N182 = last_r[0] & reqs_i[4];
  assign N183 = N181 & N182;
  assign N184 = grants_en_i & last_r[2];
  assign N185 = last_r[0] & reqs_i[0];
  assign N186 = N184 & N185;
  assign N187 = grants_en_i & last_r[2];
  assign N188 = last_r[0] & reqs_i[1];
  assign N189 = N187 & N188;
  assign N190 = grants_en_i & last_r[2];
  assign N191 = last_r[1] & reqs_i[3];
  assign N192 = N190 & N191;
  assign N193 = grants_en_i & last_r[2];
  assign N194 = last_r[1] & reqs_i[4];
  assign N195 = N193 & N194;
  assign N196 = grants_en_i & last_r[2];
  assign N197 = last_r[1] & reqs_i[0];
  assign N198 = N196 & N197;
  assign N199 = grants_en_i & last_r[2];
  assign N200 = last_r[1] & reqs_i[1];
  assign N201 = N199 & N200;
  assign N202 = grants_en_i & last_r[2];
  assign N203 = last_r[1] & reqs_i[2];
  assign N204 = N202 & N203;

  always @(posedge clk_i) begin
    if(N212) begin
      last_r[2] <= N210;
    end 
  end


  always @(posedge clk_i) begin
    if(N212) begin
      last_r[1] <= N209;
    end 
  end


  always @(posedge clk_i) begin
    if(N212) begin
      last_r[0] <= N208;
    end 
  end

  assign grants_o = (N19)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                    (N0)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                    (N1)? { 1'b0, 1'b0, 1'b0, 1'b1, 1'b0 } : 
                    (N2)? { 1'b0, 1'b0, 1'b1, 1'b0, 1'b0 } : 
                    (N3)? { 1'b0, 1'b1, 1'b0, 1'b0, 1'b0 } : 
                    (N51)? { 1'b1, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                    (N59)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b1 } : 
                    (N4)? { 1'b0, 1'b0, 1'b1, 1'b0, 1'b0 } : 
                    (N5)? { 1'b0, 1'b1, 1'b0, 1'b0, 1'b0 } : 
                    (N75)? { 1'b1, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                    (N6)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b1 } : 
                    (N90)? { 1'b0, 1'b0, 1'b0, 1'b1, 1'b0 } : 
                    (N7)? { 1'b0, 1'b1, 1'b0, 1'b0, 1'b0 } : 
                    (N100)? { 1'b1, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                    (N8)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b1 } : 
                    (N9)? { 1'b0, 1'b0, 1'b0, 1'b1, 1'b0 } : 
                    (N118)? { 1'b0, 1'b0, 1'b1, 1'b0, 1'b0 } : 
                    (N124)? { 1'b1, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                    (N10)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b1 } : 
                    (N11)? { 1'b0, 1'b0, 1'b0, 1'b1, 1'b0 } : 
                    (N12)? { 1'b0, 1'b0, 1'b1, 1'b0, 1'b0 } : 
                    (N149)? { 1'b0, 1'b1, 1'b0, 1'b0, 1'b0 } : 
                    (N13)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b1 } : 
                    (N14)? { 1'b0, 1'b0, 1'b0, 1'b1, 1'b0 } : 
                    (N15)? { 1'b0, 1'b0, 1'b1, 1'b0, 1'b0 } : 
                    (N16)? { 1'b0, 1'b1, 1'b0, 1'b0, 1'b0 } : 
                    (N174)? { 1'b1, 1'b0, 1'b0, 1'b0, 1'b0 } : 1'b0;
  assign N0 = N27;
  assign N1 = N34;
  assign N2 = N39;
  assign N3 = N44;
  assign N4 = N63;
  assign N5 = N69;
  assign N6 = N82;
  assign N7 = N94;
  assign N8 = N105;
  assign N9 = N110;
  assign N10 = N129;
  assign N11 = N135;
  assign N12 = N141;
  assign N13 = N153;
  assign N14 = N158;
  assign N15 = N163;
  assign N16 = N168;
  assign tag_o = (N19)? { 1'b0, 1'b0, 1'b0 } : 
                 (N0)? { 1'b0, 1'b0, 1'b0 } : 
                 (N1)? { 1'b0, 1'b0, 1'b1 } : 
                 (N2)? { 1'b0, 1'b1, 1'b0 } : 
                 (N3)? { 1'b0, 1'b1, 1'b1 } : 
                 (N51)? { 1'b1, 1'b0, 1'b0 } : 
                 (N59)? { 1'b0, 1'b0, 1'b0 } : 
                 (N4)? { 1'b0, 1'b1, 1'b0 } : 
                 (N5)? { 1'b0, 1'b1, 1'b1 } : 
                 (N75)? { 1'b1, 1'b0, 1'b0 } : 
                 (N6)? { 1'b0, 1'b0, 1'b0 } : 
                 (N90)? { 1'b0, 1'b0, 1'b1 } : 
                 (N7)? { 1'b0, 1'b1, 1'b1 } : 
                 (N100)? { 1'b1, 1'b0, 1'b0 } : 
                 (N8)? { 1'b0, 1'b0, 1'b0 } : 
                 (N9)? { 1'b0, 1'b0, 1'b1 } : 
                 (N118)? { 1'b0, 1'b1, 1'b0 } : 
                 (N124)? { 1'b1, 1'b0, 1'b0 } : 
                 (N10)? { 1'b0, 1'b0, 1'b0 } : 
                 (N11)? { 1'b0, 1'b0, 1'b1 } : 
                 (N12)? { 1'b0, 1'b1, 1'b0 } : 
                 (N149)? { 1'b0, 1'b1, 1'b1 } : 
                 (N13)? { 1'b0, 1'b0, 1'b0 } : 
                 (N14)? { 1'b0, 1'b0, 1'b1 } : 
                 (N15)? { 1'b0, 1'b1, 1'b0 } : 
                 (N16)? { 1'b0, 1'b1, 1'b1 } : 
                 (N174)? { 1'b1, 1'b0, 1'b0 } : 
                 (N205)? { 1'b0, 1'b0, 1'b0 } : 1'b0;
  assign { N210, N209, N208 } = (N17)? { 1'b0, 1'b0, 1'b0 } : 
                                (N18)? tag_o : 1'b0;
  assign N17 = reset_i;
  assign N18 = N207;
  assign N19 = ~grants_en_i;
  assign N20 = ~reqs_i[3];
  assign N21 = ~reqs_i[1];
  assign N22 = ~reqs_i[0];
  assign N28 = ~last_r[2];
  assign N29 = ~last_r[1];
  assign N30 = ~last_r[0];
  assign N51 = ~N50;
  assign N59 = ~N58;
  assign N64 = ~reqs_i[2];
  assign N75 = ~N74;
  assign N90 = ~N89;
  assign N100 = ~N99;
  assign N118 = ~N117;
  assign N119 = ~reqs_i[4];
  assign N124 = ~N123;
  assign N149 = ~N148;
  assign N174 = ~N173;
  assign N205 = N177 | N220;
  assign N220 = N180 | N219;
  assign N219 = N183 | N218;
  assign N218 = N186 | N217;
  assign N217 = N189 | N216;
  assign N216 = N192 | N215;
  assign N215 = N195 | N214;
  assign N214 = N198 | N213;
  assign N213 = N201 | N204;
  assign v_o = N224 & grants_en_i;
  assign N224 = N223 | reqs_i[0];
  assign N223 = N222 | reqs_i[1];
  assign N222 = N221 | reqs_i[2];
  assign N221 = reqs_i[4] | reqs_i[3];
  assign N206 = ~yumi_i;
  assign N207 = ~reset_i;
  assign N211 = N206 & N207;
  assign N212 = ~N211;

endmodule



module bsg_mux_one_hot_width_p76_els_p3
(
  data_i,
  sel_one_hot_i,
  data_o
);

  input [227:0] data_i;
  input [2:0] sel_one_hot_i;
  output [75:0] data_o;
  wire [75:0] data_o;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,
  N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32,N33,N34,N35,N36,N37,N38,N39,N40,N41,
  N42,N43,N44,N45,N46,N47,N48,N49,N50,N51,N52,N53,N54,N55,N56,N57,N58,N59,N60,N61,
  N62,N63,N64,N65,N66,N67,N68,N69,N70,N71,N72,N73,N74,N75;
  wire [227:0] data_masked;
  assign data_masked[75] = data_i[75] & sel_one_hot_i[0];
  assign data_masked[74] = data_i[74] & sel_one_hot_i[0];
  assign data_masked[73] = data_i[73] & sel_one_hot_i[0];
  assign data_masked[72] = data_i[72] & sel_one_hot_i[0];
  assign data_masked[71] = data_i[71] & sel_one_hot_i[0];
  assign data_masked[70] = data_i[70] & sel_one_hot_i[0];
  assign data_masked[69] = data_i[69] & sel_one_hot_i[0];
  assign data_masked[68] = data_i[68] & sel_one_hot_i[0];
  assign data_masked[67] = data_i[67] & sel_one_hot_i[0];
  assign data_masked[66] = data_i[66] & sel_one_hot_i[0];
  assign data_masked[65] = data_i[65] & sel_one_hot_i[0];
  assign data_masked[64] = data_i[64] & sel_one_hot_i[0];
  assign data_masked[63] = data_i[63] & sel_one_hot_i[0];
  assign data_masked[62] = data_i[62] & sel_one_hot_i[0];
  assign data_masked[61] = data_i[61] & sel_one_hot_i[0];
  assign data_masked[60] = data_i[60] & sel_one_hot_i[0];
  assign data_masked[59] = data_i[59] & sel_one_hot_i[0];
  assign data_masked[58] = data_i[58] & sel_one_hot_i[0];
  assign data_masked[57] = data_i[57] & sel_one_hot_i[0];
  assign data_masked[56] = data_i[56] & sel_one_hot_i[0];
  assign data_masked[55] = data_i[55] & sel_one_hot_i[0];
  assign data_masked[54] = data_i[54] & sel_one_hot_i[0];
  assign data_masked[53] = data_i[53] & sel_one_hot_i[0];
  assign data_masked[52] = data_i[52] & sel_one_hot_i[0];
  assign data_masked[51] = data_i[51] & sel_one_hot_i[0];
  assign data_masked[50] = data_i[50] & sel_one_hot_i[0];
  assign data_masked[49] = data_i[49] & sel_one_hot_i[0];
  assign data_masked[48] = data_i[48] & sel_one_hot_i[0];
  assign data_masked[47] = data_i[47] & sel_one_hot_i[0];
  assign data_masked[46] = data_i[46] & sel_one_hot_i[0];
  assign data_masked[45] = data_i[45] & sel_one_hot_i[0];
  assign data_masked[44] = data_i[44] & sel_one_hot_i[0];
  assign data_masked[43] = data_i[43] & sel_one_hot_i[0];
  assign data_masked[42] = data_i[42] & sel_one_hot_i[0];
  assign data_masked[41] = data_i[41] & sel_one_hot_i[0];
  assign data_masked[40] = data_i[40] & sel_one_hot_i[0];
  assign data_masked[39] = data_i[39] & sel_one_hot_i[0];
  assign data_masked[38] = data_i[38] & sel_one_hot_i[0];
  assign data_masked[37] = data_i[37] & sel_one_hot_i[0];
  assign data_masked[36] = data_i[36] & sel_one_hot_i[0];
  assign data_masked[35] = data_i[35] & sel_one_hot_i[0];
  assign data_masked[34] = data_i[34] & sel_one_hot_i[0];
  assign data_masked[33] = data_i[33] & sel_one_hot_i[0];
  assign data_masked[32] = data_i[32] & sel_one_hot_i[0];
  assign data_masked[31] = data_i[31] & sel_one_hot_i[0];
  assign data_masked[30] = data_i[30] & sel_one_hot_i[0];
  assign data_masked[29] = data_i[29] & sel_one_hot_i[0];
  assign data_masked[28] = data_i[28] & sel_one_hot_i[0];
  assign data_masked[27] = data_i[27] & sel_one_hot_i[0];
  assign data_masked[26] = data_i[26] & sel_one_hot_i[0];
  assign data_masked[25] = data_i[25] & sel_one_hot_i[0];
  assign data_masked[24] = data_i[24] & sel_one_hot_i[0];
  assign data_masked[23] = data_i[23] & sel_one_hot_i[0];
  assign data_masked[22] = data_i[22] & sel_one_hot_i[0];
  assign data_masked[21] = data_i[21] & sel_one_hot_i[0];
  assign data_masked[20] = data_i[20] & sel_one_hot_i[0];
  assign data_masked[19] = data_i[19] & sel_one_hot_i[0];
  assign data_masked[18] = data_i[18] & sel_one_hot_i[0];
  assign data_masked[17] = data_i[17] & sel_one_hot_i[0];
  assign data_masked[16] = data_i[16] & sel_one_hot_i[0];
  assign data_masked[15] = data_i[15] & sel_one_hot_i[0];
  assign data_masked[14] = data_i[14] & sel_one_hot_i[0];
  assign data_masked[13] = data_i[13] & sel_one_hot_i[0];
  assign data_masked[12] = data_i[12] & sel_one_hot_i[0];
  assign data_masked[11] = data_i[11] & sel_one_hot_i[0];
  assign data_masked[10] = data_i[10] & sel_one_hot_i[0];
  assign data_masked[9] = data_i[9] & sel_one_hot_i[0];
  assign data_masked[8] = data_i[8] & sel_one_hot_i[0];
  assign data_masked[7] = data_i[7] & sel_one_hot_i[0];
  assign data_masked[6] = data_i[6] & sel_one_hot_i[0];
  assign data_masked[5] = data_i[5] & sel_one_hot_i[0];
  assign data_masked[4] = data_i[4] & sel_one_hot_i[0];
  assign data_masked[3] = data_i[3] & sel_one_hot_i[0];
  assign data_masked[2] = data_i[2] & sel_one_hot_i[0];
  assign data_masked[1] = data_i[1] & sel_one_hot_i[0];
  assign data_masked[0] = data_i[0] & sel_one_hot_i[0];
  assign data_masked[151] = data_i[151] & sel_one_hot_i[1];
  assign data_masked[150] = data_i[150] & sel_one_hot_i[1];
  assign data_masked[149] = data_i[149] & sel_one_hot_i[1];
  assign data_masked[148] = data_i[148] & sel_one_hot_i[1];
  assign data_masked[147] = data_i[147] & sel_one_hot_i[1];
  assign data_masked[146] = data_i[146] & sel_one_hot_i[1];
  assign data_masked[145] = data_i[145] & sel_one_hot_i[1];
  assign data_masked[144] = data_i[144] & sel_one_hot_i[1];
  assign data_masked[143] = data_i[143] & sel_one_hot_i[1];
  assign data_masked[142] = data_i[142] & sel_one_hot_i[1];
  assign data_masked[141] = data_i[141] & sel_one_hot_i[1];
  assign data_masked[140] = data_i[140] & sel_one_hot_i[1];
  assign data_masked[139] = data_i[139] & sel_one_hot_i[1];
  assign data_masked[138] = data_i[138] & sel_one_hot_i[1];
  assign data_masked[137] = data_i[137] & sel_one_hot_i[1];
  assign data_masked[136] = data_i[136] & sel_one_hot_i[1];
  assign data_masked[135] = data_i[135] & sel_one_hot_i[1];
  assign data_masked[134] = data_i[134] & sel_one_hot_i[1];
  assign data_masked[133] = data_i[133] & sel_one_hot_i[1];
  assign data_masked[132] = data_i[132] & sel_one_hot_i[1];
  assign data_masked[131] = data_i[131] & sel_one_hot_i[1];
  assign data_masked[130] = data_i[130] & sel_one_hot_i[1];
  assign data_masked[129] = data_i[129] & sel_one_hot_i[1];
  assign data_masked[128] = data_i[128] & sel_one_hot_i[1];
  assign data_masked[127] = data_i[127] & sel_one_hot_i[1];
  assign data_masked[126] = data_i[126] & sel_one_hot_i[1];
  assign data_masked[125] = data_i[125] & sel_one_hot_i[1];
  assign data_masked[124] = data_i[124] & sel_one_hot_i[1];
  assign data_masked[123] = data_i[123] & sel_one_hot_i[1];
  assign data_masked[122] = data_i[122] & sel_one_hot_i[1];
  assign data_masked[121] = data_i[121] & sel_one_hot_i[1];
  assign data_masked[120] = data_i[120] & sel_one_hot_i[1];
  assign data_masked[119] = data_i[119] & sel_one_hot_i[1];
  assign data_masked[118] = data_i[118] & sel_one_hot_i[1];
  assign data_masked[117] = data_i[117] & sel_one_hot_i[1];
  assign data_masked[116] = data_i[116] & sel_one_hot_i[1];
  assign data_masked[115] = data_i[115] & sel_one_hot_i[1];
  assign data_masked[114] = data_i[114] & sel_one_hot_i[1];
  assign data_masked[113] = data_i[113] & sel_one_hot_i[1];
  assign data_masked[112] = data_i[112] & sel_one_hot_i[1];
  assign data_masked[111] = data_i[111] & sel_one_hot_i[1];
  assign data_masked[110] = data_i[110] & sel_one_hot_i[1];
  assign data_masked[109] = data_i[109] & sel_one_hot_i[1];
  assign data_masked[108] = data_i[108] & sel_one_hot_i[1];
  assign data_masked[107] = data_i[107] & sel_one_hot_i[1];
  assign data_masked[106] = data_i[106] & sel_one_hot_i[1];
  assign data_masked[105] = data_i[105] & sel_one_hot_i[1];
  assign data_masked[104] = data_i[104] & sel_one_hot_i[1];
  assign data_masked[103] = data_i[103] & sel_one_hot_i[1];
  assign data_masked[102] = data_i[102] & sel_one_hot_i[1];
  assign data_masked[101] = data_i[101] & sel_one_hot_i[1];
  assign data_masked[100] = data_i[100] & sel_one_hot_i[1];
  assign data_masked[99] = data_i[99] & sel_one_hot_i[1];
  assign data_masked[98] = data_i[98] & sel_one_hot_i[1];
  assign data_masked[97] = data_i[97] & sel_one_hot_i[1];
  assign data_masked[96] = data_i[96] & sel_one_hot_i[1];
  assign data_masked[95] = data_i[95] & sel_one_hot_i[1];
  assign data_masked[94] = data_i[94] & sel_one_hot_i[1];
  assign data_masked[93] = data_i[93] & sel_one_hot_i[1];
  assign data_masked[92] = data_i[92] & sel_one_hot_i[1];
  assign data_masked[91] = data_i[91] & sel_one_hot_i[1];
  assign data_masked[90] = data_i[90] & sel_one_hot_i[1];
  assign data_masked[89] = data_i[89] & sel_one_hot_i[1];
  assign data_masked[88] = data_i[88] & sel_one_hot_i[1];
  assign data_masked[87] = data_i[87] & sel_one_hot_i[1];
  assign data_masked[86] = data_i[86] & sel_one_hot_i[1];
  assign data_masked[85] = data_i[85] & sel_one_hot_i[1];
  assign data_masked[84] = data_i[84] & sel_one_hot_i[1];
  assign data_masked[83] = data_i[83] & sel_one_hot_i[1];
  assign data_masked[82] = data_i[82] & sel_one_hot_i[1];
  assign data_masked[81] = data_i[81] & sel_one_hot_i[1];
  assign data_masked[80] = data_i[80] & sel_one_hot_i[1];
  assign data_masked[79] = data_i[79] & sel_one_hot_i[1];
  assign data_masked[78] = data_i[78] & sel_one_hot_i[1];
  assign data_masked[77] = data_i[77] & sel_one_hot_i[1];
  assign data_masked[76] = data_i[76] & sel_one_hot_i[1];
  assign data_masked[227] = data_i[227] & sel_one_hot_i[2];
  assign data_masked[226] = data_i[226] & sel_one_hot_i[2];
  assign data_masked[225] = data_i[225] & sel_one_hot_i[2];
  assign data_masked[224] = data_i[224] & sel_one_hot_i[2];
  assign data_masked[223] = data_i[223] & sel_one_hot_i[2];
  assign data_masked[222] = data_i[222] & sel_one_hot_i[2];
  assign data_masked[221] = data_i[221] & sel_one_hot_i[2];
  assign data_masked[220] = data_i[220] & sel_one_hot_i[2];
  assign data_masked[219] = data_i[219] & sel_one_hot_i[2];
  assign data_masked[218] = data_i[218] & sel_one_hot_i[2];
  assign data_masked[217] = data_i[217] & sel_one_hot_i[2];
  assign data_masked[216] = data_i[216] & sel_one_hot_i[2];
  assign data_masked[215] = data_i[215] & sel_one_hot_i[2];
  assign data_masked[214] = data_i[214] & sel_one_hot_i[2];
  assign data_masked[213] = data_i[213] & sel_one_hot_i[2];
  assign data_masked[212] = data_i[212] & sel_one_hot_i[2];
  assign data_masked[211] = data_i[211] & sel_one_hot_i[2];
  assign data_masked[210] = data_i[210] & sel_one_hot_i[2];
  assign data_masked[209] = data_i[209] & sel_one_hot_i[2];
  assign data_masked[208] = data_i[208] & sel_one_hot_i[2];
  assign data_masked[207] = data_i[207] & sel_one_hot_i[2];
  assign data_masked[206] = data_i[206] & sel_one_hot_i[2];
  assign data_masked[205] = data_i[205] & sel_one_hot_i[2];
  assign data_masked[204] = data_i[204] & sel_one_hot_i[2];
  assign data_masked[203] = data_i[203] & sel_one_hot_i[2];
  assign data_masked[202] = data_i[202] & sel_one_hot_i[2];
  assign data_masked[201] = data_i[201] & sel_one_hot_i[2];
  assign data_masked[200] = data_i[200] & sel_one_hot_i[2];
  assign data_masked[199] = data_i[199] & sel_one_hot_i[2];
  assign data_masked[198] = data_i[198] & sel_one_hot_i[2];
  assign data_masked[197] = data_i[197] & sel_one_hot_i[2];
  assign data_masked[196] = data_i[196] & sel_one_hot_i[2];
  assign data_masked[195] = data_i[195] & sel_one_hot_i[2];
  assign data_masked[194] = data_i[194] & sel_one_hot_i[2];
  assign data_masked[193] = data_i[193] & sel_one_hot_i[2];
  assign data_masked[192] = data_i[192] & sel_one_hot_i[2];
  assign data_masked[191] = data_i[191] & sel_one_hot_i[2];
  assign data_masked[190] = data_i[190] & sel_one_hot_i[2];
  assign data_masked[189] = data_i[189] & sel_one_hot_i[2];
  assign data_masked[188] = data_i[188] & sel_one_hot_i[2];
  assign data_masked[187] = data_i[187] & sel_one_hot_i[2];
  assign data_masked[186] = data_i[186] & sel_one_hot_i[2];
  assign data_masked[185] = data_i[185] & sel_one_hot_i[2];
  assign data_masked[184] = data_i[184] & sel_one_hot_i[2];
  assign data_masked[183] = data_i[183] & sel_one_hot_i[2];
  assign data_masked[182] = data_i[182] & sel_one_hot_i[2];
  assign data_masked[181] = data_i[181] & sel_one_hot_i[2];
  assign data_masked[180] = data_i[180] & sel_one_hot_i[2];
  assign data_masked[179] = data_i[179] & sel_one_hot_i[2];
  assign data_masked[178] = data_i[178] & sel_one_hot_i[2];
  assign data_masked[177] = data_i[177] & sel_one_hot_i[2];
  assign data_masked[176] = data_i[176] & sel_one_hot_i[2];
  assign data_masked[175] = data_i[175] & sel_one_hot_i[2];
  assign data_masked[174] = data_i[174] & sel_one_hot_i[2];
  assign data_masked[173] = data_i[173] & sel_one_hot_i[2];
  assign data_masked[172] = data_i[172] & sel_one_hot_i[2];
  assign data_masked[171] = data_i[171] & sel_one_hot_i[2];
  assign data_masked[170] = data_i[170] & sel_one_hot_i[2];
  assign data_masked[169] = data_i[169] & sel_one_hot_i[2];
  assign data_masked[168] = data_i[168] & sel_one_hot_i[2];
  assign data_masked[167] = data_i[167] & sel_one_hot_i[2];
  assign data_masked[166] = data_i[166] & sel_one_hot_i[2];
  assign data_masked[165] = data_i[165] & sel_one_hot_i[2];
  assign data_masked[164] = data_i[164] & sel_one_hot_i[2];
  assign data_masked[163] = data_i[163] & sel_one_hot_i[2];
  assign data_masked[162] = data_i[162] & sel_one_hot_i[2];
  assign data_masked[161] = data_i[161] & sel_one_hot_i[2];
  assign data_masked[160] = data_i[160] & sel_one_hot_i[2];
  assign data_masked[159] = data_i[159] & sel_one_hot_i[2];
  assign data_masked[158] = data_i[158] & sel_one_hot_i[2];
  assign data_masked[157] = data_i[157] & sel_one_hot_i[2];
  assign data_masked[156] = data_i[156] & sel_one_hot_i[2];
  assign data_masked[155] = data_i[155] & sel_one_hot_i[2];
  assign data_masked[154] = data_i[154] & sel_one_hot_i[2];
  assign data_masked[153] = data_i[153] & sel_one_hot_i[2];
  assign data_masked[152] = data_i[152] & sel_one_hot_i[2];
  assign data_o[0] = N0 | data_masked[0];
  assign N0 = data_masked[152] | data_masked[76];
  assign data_o[1] = N1 | data_masked[1];
  assign N1 = data_masked[153] | data_masked[77];
  assign data_o[2] = N2 | data_masked[2];
  assign N2 = data_masked[154] | data_masked[78];
  assign data_o[3] = N3 | data_masked[3];
  assign N3 = data_masked[155] | data_masked[79];
  assign data_o[4] = N4 | data_masked[4];
  assign N4 = data_masked[156] | data_masked[80];
  assign data_o[5] = N5 | data_masked[5];
  assign N5 = data_masked[157] | data_masked[81];
  assign data_o[6] = N6 | data_masked[6];
  assign N6 = data_masked[158] | data_masked[82];
  assign data_o[7] = N7 | data_masked[7];
  assign N7 = data_masked[159] | data_masked[83];
  assign data_o[8] = N8 | data_masked[8];
  assign N8 = data_masked[160] | data_masked[84];
  assign data_o[9] = N9 | data_masked[9];
  assign N9 = data_masked[161] | data_masked[85];
  assign data_o[10] = N10 | data_masked[10];
  assign N10 = data_masked[162] | data_masked[86];
  assign data_o[11] = N11 | data_masked[11];
  assign N11 = data_masked[163] | data_masked[87];
  assign data_o[12] = N12 | data_masked[12];
  assign N12 = data_masked[164] | data_masked[88];
  assign data_o[13] = N13 | data_masked[13];
  assign N13 = data_masked[165] | data_masked[89];
  assign data_o[14] = N14 | data_masked[14];
  assign N14 = data_masked[166] | data_masked[90];
  assign data_o[15] = N15 | data_masked[15];
  assign N15 = data_masked[167] | data_masked[91];
  assign data_o[16] = N16 | data_masked[16];
  assign N16 = data_masked[168] | data_masked[92];
  assign data_o[17] = N17 | data_masked[17];
  assign N17 = data_masked[169] | data_masked[93];
  assign data_o[18] = N18 | data_masked[18];
  assign N18 = data_masked[170] | data_masked[94];
  assign data_o[19] = N19 | data_masked[19];
  assign N19 = data_masked[171] | data_masked[95];
  assign data_o[20] = N20 | data_masked[20];
  assign N20 = data_masked[172] | data_masked[96];
  assign data_o[21] = N21 | data_masked[21];
  assign N21 = data_masked[173] | data_masked[97];
  assign data_o[22] = N22 | data_masked[22];
  assign N22 = data_masked[174] | data_masked[98];
  assign data_o[23] = N23 | data_masked[23];
  assign N23 = data_masked[175] | data_masked[99];
  assign data_o[24] = N24 | data_masked[24];
  assign N24 = data_masked[176] | data_masked[100];
  assign data_o[25] = N25 | data_masked[25];
  assign N25 = data_masked[177] | data_masked[101];
  assign data_o[26] = N26 | data_masked[26];
  assign N26 = data_masked[178] | data_masked[102];
  assign data_o[27] = N27 | data_masked[27];
  assign N27 = data_masked[179] | data_masked[103];
  assign data_o[28] = N28 | data_masked[28];
  assign N28 = data_masked[180] | data_masked[104];
  assign data_o[29] = N29 | data_masked[29];
  assign N29 = data_masked[181] | data_masked[105];
  assign data_o[30] = N30 | data_masked[30];
  assign N30 = data_masked[182] | data_masked[106];
  assign data_o[31] = N31 | data_masked[31];
  assign N31 = data_masked[183] | data_masked[107];
  assign data_o[32] = N32 | data_masked[32];
  assign N32 = data_masked[184] | data_masked[108];
  assign data_o[33] = N33 | data_masked[33];
  assign N33 = data_masked[185] | data_masked[109];
  assign data_o[34] = N34 | data_masked[34];
  assign N34 = data_masked[186] | data_masked[110];
  assign data_o[35] = N35 | data_masked[35];
  assign N35 = data_masked[187] | data_masked[111];
  assign data_o[36] = N36 | data_masked[36];
  assign N36 = data_masked[188] | data_masked[112];
  assign data_o[37] = N37 | data_masked[37];
  assign N37 = data_masked[189] | data_masked[113];
  assign data_o[38] = N38 | data_masked[38];
  assign N38 = data_masked[190] | data_masked[114];
  assign data_o[39] = N39 | data_masked[39];
  assign N39 = data_masked[191] | data_masked[115];
  assign data_o[40] = N40 | data_masked[40];
  assign N40 = data_masked[192] | data_masked[116];
  assign data_o[41] = N41 | data_masked[41];
  assign N41 = data_masked[193] | data_masked[117];
  assign data_o[42] = N42 | data_masked[42];
  assign N42 = data_masked[194] | data_masked[118];
  assign data_o[43] = N43 | data_masked[43];
  assign N43 = data_masked[195] | data_masked[119];
  assign data_o[44] = N44 | data_masked[44];
  assign N44 = data_masked[196] | data_masked[120];
  assign data_o[45] = N45 | data_masked[45];
  assign N45 = data_masked[197] | data_masked[121];
  assign data_o[46] = N46 | data_masked[46];
  assign N46 = data_masked[198] | data_masked[122];
  assign data_o[47] = N47 | data_masked[47];
  assign N47 = data_masked[199] | data_masked[123];
  assign data_o[48] = N48 | data_masked[48];
  assign N48 = data_masked[200] | data_masked[124];
  assign data_o[49] = N49 | data_masked[49];
  assign N49 = data_masked[201] | data_masked[125];
  assign data_o[50] = N50 | data_masked[50];
  assign N50 = data_masked[202] | data_masked[126];
  assign data_o[51] = N51 | data_masked[51];
  assign N51 = data_masked[203] | data_masked[127];
  assign data_o[52] = N52 | data_masked[52];
  assign N52 = data_masked[204] | data_masked[128];
  assign data_o[53] = N53 | data_masked[53];
  assign N53 = data_masked[205] | data_masked[129];
  assign data_o[54] = N54 | data_masked[54];
  assign N54 = data_masked[206] | data_masked[130];
  assign data_o[55] = N55 | data_masked[55];
  assign N55 = data_masked[207] | data_masked[131];
  assign data_o[56] = N56 | data_masked[56];
  assign N56 = data_masked[208] | data_masked[132];
  assign data_o[57] = N57 | data_masked[57];
  assign N57 = data_masked[209] | data_masked[133];
  assign data_o[58] = N58 | data_masked[58];
  assign N58 = data_masked[210] | data_masked[134];
  assign data_o[59] = N59 | data_masked[59];
  assign N59 = data_masked[211] | data_masked[135];
  assign data_o[60] = N60 | data_masked[60];
  assign N60 = data_masked[212] | data_masked[136];
  assign data_o[61] = N61 | data_masked[61];
  assign N61 = data_masked[213] | data_masked[137];
  assign data_o[62] = N62 | data_masked[62];
  assign N62 = data_masked[214] | data_masked[138];
  assign data_o[63] = N63 | data_masked[63];
  assign N63 = data_masked[215] | data_masked[139];
  assign data_o[64] = N64 | data_masked[64];
  assign N64 = data_masked[216] | data_masked[140];
  assign data_o[65] = N65 | data_masked[65];
  assign N65 = data_masked[217] | data_masked[141];
  assign data_o[66] = N66 | data_masked[66];
  assign N66 = data_masked[218] | data_masked[142];
  assign data_o[67] = N67 | data_masked[67];
  assign N67 = data_masked[219] | data_masked[143];
  assign data_o[68] = N68 | data_masked[68];
  assign N68 = data_masked[220] | data_masked[144];
  assign data_o[69] = N69 | data_masked[69];
  assign N69 = data_masked[221] | data_masked[145];
  assign data_o[70] = N70 | data_masked[70];
  assign N70 = data_masked[222] | data_masked[146];
  assign data_o[71] = N71 | data_masked[71];
  assign N71 = data_masked[223] | data_masked[147];
  assign data_o[72] = N72 | data_masked[72];
  assign N72 = data_masked[224] | data_masked[148];
  assign data_o[73] = N73 | data_masked[73];
  assign N73 = data_masked[225] | data_masked[149];
  assign data_o[74] = N74 | data_masked[74];
  assign N74 = data_masked[226] | data_masked[150];
  assign data_o[75] = N75 | data_masked[75];
  assign N75 = data_masked[227] | data_masked[151];

endmodule



module bsg_mux_one_hot_width_p76_els_p5
(
  data_i,
  sel_one_hot_i,
  data_o
);

  input [379:0] data_i;
  input [4:0] sel_one_hot_i;
  output [75:0] data_o;
  wire [75:0] data_o;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,
  N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32,N33,N34,N35,N36,N37,N38,N39,N40,N41,
  N42,N43,N44,N45,N46,N47,N48,N49,N50,N51,N52,N53,N54,N55,N56,N57,N58,N59,N60,N61,
  N62,N63,N64,N65,N66,N67,N68,N69,N70,N71,N72,N73,N74,N75,N76,N77,N78,N79,N80,N81,
  N82,N83,N84,N85,N86,N87,N88,N89,N90,N91,N92,N93,N94,N95,N96,N97,N98,N99,N100,N101,
  N102,N103,N104,N105,N106,N107,N108,N109,N110,N111,N112,N113,N114,N115,N116,N117,
  N118,N119,N120,N121,N122,N123,N124,N125,N126,N127,N128,N129,N130,N131,N132,N133,
  N134,N135,N136,N137,N138,N139,N140,N141,N142,N143,N144,N145,N146,N147,N148,N149,
  N150,N151,N152,N153,N154,N155,N156,N157,N158,N159,N160,N161,N162,N163,N164,N165,
  N166,N167,N168,N169,N170,N171,N172,N173,N174,N175,N176,N177,N178,N179,N180,N181,
  N182,N183,N184,N185,N186,N187,N188,N189,N190,N191,N192,N193,N194,N195,N196,N197,
  N198,N199,N200,N201,N202,N203,N204,N205,N206,N207,N208,N209,N210,N211,N212,N213,
  N214,N215,N216,N217,N218,N219,N220,N221,N222,N223,N224,N225,N226,N227;
  wire [379:0] data_masked;
  assign data_masked[75] = data_i[75] & sel_one_hot_i[0];
  assign data_masked[74] = data_i[74] & sel_one_hot_i[0];
  assign data_masked[73] = data_i[73] & sel_one_hot_i[0];
  assign data_masked[72] = data_i[72] & sel_one_hot_i[0];
  assign data_masked[71] = data_i[71] & sel_one_hot_i[0];
  assign data_masked[70] = data_i[70] & sel_one_hot_i[0];
  assign data_masked[69] = data_i[69] & sel_one_hot_i[0];
  assign data_masked[68] = data_i[68] & sel_one_hot_i[0];
  assign data_masked[67] = data_i[67] & sel_one_hot_i[0];
  assign data_masked[66] = data_i[66] & sel_one_hot_i[0];
  assign data_masked[65] = data_i[65] & sel_one_hot_i[0];
  assign data_masked[64] = data_i[64] & sel_one_hot_i[0];
  assign data_masked[63] = data_i[63] & sel_one_hot_i[0];
  assign data_masked[62] = data_i[62] & sel_one_hot_i[0];
  assign data_masked[61] = data_i[61] & sel_one_hot_i[0];
  assign data_masked[60] = data_i[60] & sel_one_hot_i[0];
  assign data_masked[59] = data_i[59] & sel_one_hot_i[0];
  assign data_masked[58] = data_i[58] & sel_one_hot_i[0];
  assign data_masked[57] = data_i[57] & sel_one_hot_i[0];
  assign data_masked[56] = data_i[56] & sel_one_hot_i[0];
  assign data_masked[55] = data_i[55] & sel_one_hot_i[0];
  assign data_masked[54] = data_i[54] & sel_one_hot_i[0];
  assign data_masked[53] = data_i[53] & sel_one_hot_i[0];
  assign data_masked[52] = data_i[52] & sel_one_hot_i[0];
  assign data_masked[51] = data_i[51] & sel_one_hot_i[0];
  assign data_masked[50] = data_i[50] & sel_one_hot_i[0];
  assign data_masked[49] = data_i[49] & sel_one_hot_i[0];
  assign data_masked[48] = data_i[48] & sel_one_hot_i[0];
  assign data_masked[47] = data_i[47] & sel_one_hot_i[0];
  assign data_masked[46] = data_i[46] & sel_one_hot_i[0];
  assign data_masked[45] = data_i[45] & sel_one_hot_i[0];
  assign data_masked[44] = data_i[44] & sel_one_hot_i[0];
  assign data_masked[43] = data_i[43] & sel_one_hot_i[0];
  assign data_masked[42] = data_i[42] & sel_one_hot_i[0];
  assign data_masked[41] = data_i[41] & sel_one_hot_i[0];
  assign data_masked[40] = data_i[40] & sel_one_hot_i[0];
  assign data_masked[39] = data_i[39] & sel_one_hot_i[0];
  assign data_masked[38] = data_i[38] & sel_one_hot_i[0];
  assign data_masked[37] = data_i[37] & sel_one_hot_i[0];
  assign data_masked[36] = data_i[36] & sel_one_hot_i[0];
  assign data_masked[35] = data_i[35] & sel_one_hot_i[0];
  assign data_masked[34] = data_i[34] & sel_one_hot_i[0];
  assign data_masked[33] = data_i[33] & sel_one_hot_i[0];
  assign data_masked[32] = data_i[32] & sel_one_hot_i[0];
  assign data_masked[31] = data_i[31] & sel_one_hot_i[0];
  assign data_masked[30] = data_i[30] & sel_one_hot_i[0];
  assign data_masked[29] = data_i[29] & sel_one_hot_i[0];
  assign data_masked[28] = data_i[28] & sel_one_hot_i[0];
  assign data_masked[27] = data_i[27] & sel_one_hot_i[0];
  assign data_masked[26] = data_i[26] & sel_one_hot_i[0];
  assign data_masked[25] = data_i[25] & sel_one_hot_i[0];
  assign data_masked[24] = data_i[24] & sel_one_hot_i[0];
  assign data_masked[23] = data_i[23] & sel_one_hot_i[0];
  assign data_masked[22] = data_i[22] & sel_one_hot_i[0];
  assign data_masked[21] = data_i[21] & sel_one_hot_i[0];
  assign data_masked[20] = data_i[20] & sel_one_hot_i[0];
  assign data_masked[19] = data_i[19] & sel_one_hot_i[0];
  assign data_masked[18] = data_i[18] & sel_one_hot_i[0];
  assign data_masked[17] = data_i[17] & sel_one_hot_i[0];
  assign data_masked[16] = data_i[16] & sel_one_hot_i[0];
  assign data_masked[15] = data_i[15] & sel_one_hot_i[0];
  assign data_masked[14] = data_i[14] & sel_one_hot_i[0];
  assign data_masked[13] = data_i[13] & sel_one_hot_i[0];
  assign data_masked[12] = data_i[12] & sel_one_hot_i[0];
  assign data_masked[11] = data_i[11] & sel_one_hot_i[0];
  assign data_masked[10] = data_i[10] & sel_one_hot_i[0];
  assign data_masked[9] = data_i[9] & sel_one_hot_i[0];
  assign data_masked[8] = data_i[8] & sel_one_hot_i[0];
  assign data_masked[7] = data_i[7] & sel_one_hot_i[0];
  assign data_masked[6] = data_i[6] & sel_one_hot_i[0];
  assign data_masked[5] = data_i[5] & sel_one_hot_i[0];
  assign data_masked[4] = data_i[4] & sel_one_hot_i[0];
  assign data_masked[3] = data_i[3] & sel_one_hot_i[0];
  assign data_masked[2] = data_i[2] & sel_one_hot_i[0];
  assign data_masked[1] = data_i[1] & sel_one_hot_i[0];
  assign data_masked[0] = data_i[0] & sel_one_hot_i[0];
  assign data_masked[151] = data_i[151] & sel_one_hot_i[1];
  assign data_masked[150] = data_i[150] & sel_one_hot_i[1];
  assign data_masked[149] = data_i[149] & sel_one_hot_i[1];
  assign data_masked[148] = data_i[148] & sel_one_hot_i[1];
  assign data_masked[147] = data_i[147] & sel_one_hot_i[1];
  assign data_masked[146] = data_i[146] & sel_one_hot_i[1];
  assign data_masked[145] = data_i[145] & sel_one_hot_i[1];
  assign data_masked[144] = data_i[144] & sel_one_hot_i[1];
  assign data_masked[143] = data_i[143] & sel_one_hot_i[1];
  assign data_masked[142] = data_i[142] & sel_one_hot_i[1];
  assign data_masked[141] = data_i[141] & sel_one_hot_i[1];
  assign data_masked[140] = data_i[140] & sel_one_hot_i[1];
  assign data_masked[139] = data_i[139] & sel_one_hot_i[1];
  assign data_masked[138] = data_i[138] & sel_one_hot_i[1];
  assign data_masked[137] = data_i[137] & sel_one_hot_i[1];
  assign data_masked[136] = data_i[136] & sel_one_hot_i[1];
  assign data_masked[135] = data_i[135] & sel_one_hot_i[1];
  assign data_masked[134] = data_i[134] & sel_one_hot_i[1];
  assign data_masked[133] = data_i[133] & sel_one_hot_i[1];
  assign data_masked[132] = data_i[132] & sel_one_hot_i[1];
  assign data_masked[131] = data_i[131] & sel_one_hot_i[1];
  assign data_masked[130] = data_i[130] & sel_one_hot_i[1];
  assign data_masked[129] = data_i[129] & sel_one_hot_i[1];
  assign data_masked[128] = data_i[128] & sel_one_hot_i[1];
  assign data_masked[127] = data_i[127] & sel_one_hot_i[1];
  assign data_masked[126] = data_i[126] & sel_one_hot_i[1];
  assign data_masked[125] = data_i[125] & sel_one_hot_i[1];
  assign data_masked[124] = data_i[124] & sel_one_hot_i[1];
  assign data_masked[123] = data_i[123] & sel_one_hot_i[1];
  assign data_masked[122] = data_i[122] & sel_one_hot_i[1];
  assign data_masked[121] = data_i[121] & sel_one_hot_i[1];
  assign data_masked[120] = data_i[120] & sel_one_hot_i[1];
  assign data_masked[119] = data_i[119] & sel_one_hot_i[1];
  assign data_masked[118] = data_i[118] & sel_one_hot_i[1];
  assign data_masked[117] = data_i[117] & sel_one_hot_i[1];
  assign data_masked[116] = data_i[116] & sel_one_hot_i[1];
  assign data_masked[115] = data_i[115] & sel_one_hot_i[1];
  assign data_masked[114] = data_i[114] & sel_one_hot_i[1];
  assign data_masked[113] = data_i[113] & sel_one_hot_i[1];
  assign data_masked[112] = data_i[112] & sel_one_hot_i[1];
  assign data_masked[111] = data_i[111] & sel_one_hot_i[1];
  assign data_masked[110] = data_i[110] & sel_one_hot_i[1];
  assign data_masked[109] = data_i[109] & sel_one_hot_i[1];
  assign data_masked[108] = data_i[108] & sel_one_hot_i[1];
  assign data_masked[107] = data_i[107] & sel_one_hot_i[1];
  assign data_masked[106] = data_i[106] & sel_one_hot_i[1];
  assign data_masked[105] = data_i[105] & sel_one_hot_i[1];
  assign data_masked[104] = data_i[104] & sel_one_hot_i[1];
  assign data_masked[103] = data_i[103] & sel_one_hot_i[1];
  assign data_masked[102] = data_i[102] & sel_one_hot_i[1];
  assign data_masked[101] = data_i[101] & sel_one_hot_i[1];
  assign data_masked[100] = data_i[100] & sel_one_hot_i[1];
  assign data_masked[99] = data_i[99] & sel_one_hot_i[1];
  assign data_masked[98] = data_i[98] & sel_one_hot_i[1];
  assign data_masked[97] = data_i[97] & sel_one_hot_i[1];
  assign data_masked[96] = data_i[96] & sel_one_hot_i[1];
  assign data_masked[95] = data_i[95] & sel_one_hot_i[1];
  assign data_masked[94] = data_i[94] & sel_one_hot_i[1];
  assign data_masked[93] = data_i[93] & sel_one_hot_i[1];
  assign data_masked[92] = data_i[92] & sel_one_hot_i[1];
  assign data_masked[91] = data_i[91] & sel_one_hot_i[1];
  assign data_masked[90] = data_i[90] & sel_one_hot_i[1];
  assign data_masked[89] = data_i[89] & sel_one_hot_i[1];
  assign data_masked[88] = data_i[88] & sel_one_hot_i[1];
  assign data_masked[87] = data_i[87] & sel_one_hot_i[1];
  assign data_masked[86] = data_i[86] & sel_one_hot_i[1];
  assign data_masked[85] = data_i[85] & sel_one_hot_i[1];
  assign data_masked[84] = data_i[84] & sel_one_hot_i[1];
  assign data_masked[83] = data_i[83] & sel_one_hot_i[1];
  assign data_masked[82] = data_i[82] & sel_one_hot_i[1];
  assign data_masked[81] = data_i[81] & sel_one_hot_i[1];
  assign data_masked[80] = data_i[80] & sel_one_hot_i[1];
  assign data_masked[79] = data_i[79] & sel_one_hot_i[1];
  assign data_masked[78] = data_i[78] & sel_one_hot_i[1];
  assign data_masked[77] = data_i[77] & sel_one_hot_i[1];
  assign data_masked[76] = data_i[76] & sel_one_hot_i[1];
  assign data_masked[227] = data_i[227] & sel_one_hot_i[2];
  assign data_masked[226] = data_i[226] & sel_one_hot_i[2];
  assign data_masked[225] = data_i[225] & sel_one_hot_i[2];
  assign data_masked[224] = data_i[224] & sel_one_hot_i[2];
  assign data_masked[223] = data_i[223] & sel_one_hot_i[2];
  assign data_masked[222] = data_i[222] & sel_one_hot_i[2];
  assign data_masked[221] = data_i[221] & sel_one_hot_i[2];
  assign data_masked[220] = data_i[220] & sel_one_hot_i[2];
  assign data_masked[219] = data_i[219] & sel_one_hot_i[2];
  assign data_masked[218] = data_i[218] & sel_one_hot_i[2];
  assign data_masked[217] = data_i[217] & sel_one_hot_i[2];
  assign data_masked[216] = data_i[216] & sel_one_hot_i[2];
  assign data_masked[215] = data_i[215] & sel_one_hot_i[2];
  assign data_masked[214] = data_i[214] & sel_one_hot_i[2];
  assign data_masked[213] = data_i[213] & sel_one_hot_i[2];
  assign data_masked[212] = data_i[212] & sel_one_hot_i[2];
  assign data_masked[211] = data_i[211] & sel_one_hot_i[2];
  assign data_masked[210] = data_i[210] & sel_one_hot_i[2];
  assign data_masked[209] = data_i[209] & sel_one_hot_i[2];
  assign data_masked[208] = data_i[208] & sel_one_hot_i[2];
  assign data_masked[207] = data_i[207] & sel_one_hot_i[2];
  assign data_masked[206] = data_i[206] & sel_one_hot_i[2];
  assign data_masked[205] = data_i[205] & sel_one_hot_i[2];
  assign data_masked[204] = data_i[204] & sel_one_hot_i[2];
  assign data_masked[203] = data_i[203] & sel_one_hot_i[2];
  assign data_masked[202] = data_i[202] & sel_one_hot_i[2];
  assign data_masked[201] = data_i[201] & sel_one_hot_i[2];
  assign data_masked[200] = data_i[200] & sel_one_hot_i[2];
  assign data_masked[199] = data_i[199] & sel_one_hot_i[2];
  assign data_masked[198] = data_i[198] & sel_one_hot_i[2];
  assign data_masked[197] = data_i[197] & sel_one_hot_i[2];
  assign data_masked[196] = data_i[196] & sel_one_hot_i[2];
  assign data_masked[195] = data_i[195] & sel_one_hot_i[2];
  assign data_masked[194] = data_i[194] & sel_one_hot_i[2];
  assign data_masked[193] = data_i[193] & sel_one_hot_i[2];
  assign data_masked[192] = data_i[192] & sel_one_hot_i[2];
  assign data_masked[191] = data_i[191] & sel_one_hot_i[2];
  assign data_masked[190] = data_i[190] & sel_one_hot_i[2];
  assign data_masked[189] = data_i[189] & sel_one_hot_i[2];
  assign data_masked[188] = data_i[188] & sel_one_hot_i[2];
  assign data_masked[187] = data_i[187] & sel_one_hot_i[2];
  assign data_masked[186] = data_i[186] & sel_one_hot_i[2];
  assign data_masked[185] = data_i[185] & sel_one_hot_i[2];
  assign data_masked[184] = data_i[184] & sel_one_hot_i[2];
  assign data_masked[183] = data_i[183] & sel_one_hot_i[2];
  assign data_masked[182] = data_i[182] & sel_one_hot_i[2];
  assign data_masked[181] = data_i[181] & sel_one_hot_i[2];
  assign data_masked[180] = data_i[180] & sel_one_hot_i[2];
  assign data_masked[179] = data_i[179] & sel_one_hot_i[2];
  assign data_masked[178] = data_i[178] & sel_one_hot_i[2];
  assign data_masked[177] = data_i[177] & sel_one_hot_i[2];
  assign data_masked[176] = data_i[176] & sel_one_hot_i[2];
  assign data_masked[175] = data_i[175] & sel_one_hot_i[2];
  assign data_masked[174] = data_i[174] & sel_one_hot_i[2];
  assign data_masked[173] = data_i[173] & sel_one_hot_i[2];
  assign data_masked[172] = data_i[172] & sel_one_hot_i[2];
  assign data_masked[171] = data_i[171] & sel_one_hot_i[2];
  assign data_masked[170] = data_i[170] & sel_one_hot_i[2];
  assign data_masked[169] = data_i[169] & sel_one_hot_i[2];
  assign data_masked[168] = data_i[168] & sel_one_hot_i[2];
  assign data_masked[167] = data_i[167] & sel_one_hot_i[2];
  assign data_masked[166] = data_i[166] & sel_one_hot_i[2];
  assign data_masked[165] = data_i[165] & sel_one_hot_i[2];
  assign data_masked[164] = data_i[164] & sel_one_hot_i[2];
  assign data_masked[163] = data_i[163] & sel_one_hot_i[2];
  assign data_masked[162] = data_i[162] & sel_one_hot_i[2];
  assign data_masked[161] = data_i[161] & sel_one_hot_i[2];
  assign data_masked[160] = data_i[160] & sel_one_hot_i[2];
  assign data_masked[159] = data_i[159] & sel_one_hot_i[2];
  assign data_masked[158] = data_i[158] & sel_one_hot_i[2];
  assign data_masked[157] = data_i[157] & sel_one_hot_i[2];
  assign data_masked[156] = data_i[156] & sel_one_hot_i[2];
  assign data_masked[155] = data_i[155] & sel_one_hot_i[2];
  assign data_masked[154] = data_i[154] & sel_one_hot_i[2];
  assign data_masked[153] = data_i[153] & sel_one_hot_i[2];
  assign data_masked[152] = data_i[152] & sel_one_hot_i[2];
  assign data_masked[303] = data_i[303] & sel_one_hot_i[3];
  assign data_masked[302] = data_i[302] & sel_one_hot_i[3];
  assign data_masked[301] = data_i[301] & sel_one_hot_i[3];
  assign data_masked[300] = data_i[300] & sel_one_hot_i[3];
  assign data_masked[299] = data_i[299] & sel_one_hot_i[3];
  assign data_masked[298] = data_i[298] & sel_one_hot_i[3];
  assign data_masked[297] = data_i[297] & sel_one_hot_i[3];
  assign data_masked[296] = data_i[296] & sel_one_hot_i[3];
  assign data_masked[295] = data_i[295] & sel_one_hot_i[3];
  assign data_masked[294] = data_i[294] & sel_one_hot_i[3];
  assign data_masked[293] = data_i[293] & sel_one_hot_i[3];
  assign data_masked[292] = data_i[292] & sel_one_hot_i[3];
  assign data_masked[291] = data_i[291] & sel_one_hot_i[3];
  assign data_masked[290] = data_i[290] & sel_one_hot_i[3];
  assign data_masked[289] = data_i[289] & sel_one_hot_i[3];
  assign data_masked[288] = data_i[288] & sel_one_hot_i[3];
  assign data_masked[287] = data_i[287] & sel_one_hot_i[3];
  assign data_masked[286] = data_i[286] & sel_one_hot_i[3];
  assign data_masked[285] = data_i[285] & sel_one_hot_i[3];
  assign data_masked[284] = data_i[284] & sel_one_hot_i[3];
  assign data_masked[283] = data_i[283] & sel_one_hot_i[3];
  assign data_masked[282] = data_i[282] & sel_one_hot_i[3];
  assign data_masked[281] = data_i[281] & sel_one_hot_i[3];
  assign data_masked[280] = data_i[280] & sel_one_hot_i[3];
  assign data_masked[279] = data_i[279] & sel_one_hot_i[3];
  assign data_masked[278] = data_i[278] & sel_one_hot_i[3];
  assign data_masked[277] = data_i[277] & sel_one_hot_i[3];
  assign data_masked[276] = data_i[276] & sel_one_hot_i[3];
  assign data_masked[275] = data_i[275] & sel_one_hot_i[3];
  assign data_masked[274] = data_i[274] & sel_one_hot_i[3];
  assign data_masked[273] = data_i[273] & sel_one_hot_i[3];
  assign data_masked[272] = data_i[272] & sel_one_hot_i[3];
  assign data_masked[271] = data_i[271] & sel_one_hot_i[3];
  assign data_masked[270] = data_i[270] & sel_one_hot_i[3];
  assign data_masked[269] = data_i[269] & sel_one_hot_i[3];
  assign data_masked[268] = data_i[268] & sel_one_hot_i[3];
  assign data_masked[267] = data_i[267] & sel_one_hot_i[3];
  assign data_masked[266] = data_i[266] & sel_one_hot_i[3];
  assign data_masked[265] = data_i[265] & sel_one_hot_i[3];
  assign data_masked[264] = data_i[264] & sel_one_hot_i[3];
  assign data_masked[263] = data_i[263] & sel_one_hot_i[3];
  assign data_masked[262] = data_i[262] & sel_one_hot_i[3];
  assign data_masked[261] = data_i[261] & sel_one_hot_i[3];
  assign data_masked[260] = data_i[260] & sel_one_hot_i[3];
  assign data_masked[259] = data_i[259] & sel_one_hot_i[3];
  assign data_masked[258] = data_i[258] & sel_one_hot_i[3];
  assign data_masked[257] = data_i[257] & sel_one_hot_i[3];
  assign data_masked[256] = data_i[256] & sel_one_hot_i[3];
  assign data_masked[255] = data_i[255] & sel_one_hot_i[3];
  assign data_masked[254] = data_i[254] & sel_one_hot_i[3];
  assign data_masked[253] = data_i[253] & sel_one_hot_i[3];
  assign data_masked[252] = data_i[252] & sel_one_hot_i[3];
  assign data_masked[251] = data_i[251] & sel_one_hot_i[3];
  assign data_masked[250] = data_i[250] & sel_one_hot_i[3];
  assign data_masked[249] = data_i[249] & sel_one_hot_i[3];
  assign data_masked[248] = data_i[248] & sel_one_hot_i[3];
  assign data_masked[247] = data_i[247] & sel_one_hot_i[3];
  assign data_masked[246] = data_i[246] & sel_one_hot_i[3];
  assign data_masked[245] = data_i[245] & sel_one_hot_i[3];
  assign data_masked[244] = data_i[244] & sel_one_hot_i[3];
  assign data_masked[243] = data_i[243] & sel_one_hot_i[3];
  assign data_masked[242] = data_i[242] & sel_one_hot_i[3];
  assign data_masked[241] = data_i[241] & sel_one_hot_i[3];
  assign data_masked[240] = data_i[240] & sel_one_hot_i[3];
  assign data_masked[239] = data_i[239] & sel_one_hot_i[3];
  assign data_masked[238] = data_i[238] & sel_one_hot_i[3];
  assign data_masked[237] = data_i[237] & sel_one_hot_i[3];
  assign data_masked[236] = data_i[236] & sel_one_hot_i[3];
  assign data_masked[235] = data_i[235] & sel_one_hot_i[3];
  assign data_masked[234] = data_i[234] & sel_one_hot_i[3];
  assign data_masked[233] = data_i[233] & sel_one_hot_i[3];
  assign data_masked[232] = data_i[232] & sel_one_hot_i[3];
  assign data_masked[231] = data_i[231] & sel_one_hot_i[3];
  assign data_masked[230] = data_i[230] & sel_one_hot_i[3];
  assign data_masked[229] = data_i[229] & sel_one_hot_i[3];
  assign data_masked[228] = data_i[228] & sel_one_hot_i[3];
  assign data_masked[379] = data_i[379] & sel_one_hot_i[4];
  assign data_masked[378] = data_i[378] & sel_one_hot_i[4];
  assign data_masked[377] = data_i[377] & sel_one_hot_i[4];
  assign data_masked[376] = data_i[376] & sel_one_hot_i[4];
  assign data_masked[375] = data_i[375] & sel_one_hot_i[4];
  assign data_masked[374] = data_i[374] & sel_one_hot_i[4];
  assign data_masked[373] = data_i[373] & sel_one_hot_i[4];
  assign data_masked[372] = data_i[372] & sel_one_hot_i[4];
  assign data_masked[371] = data_i[371] & sel_one_hot_i[4];
  assign data_masked[370] = data_i[370] & sel_one_hot_i[4];
  assign data_masked[369] = data_i[369] & sel_one_hot_i[4];
  assign data_masked[368] = data_i[368] & sel_one_hot_i[4];
  assign data_masked[367] = data_i[367] & sel_one_hot_i[4];
  assign data_masked[366] = data_i[366] & sel_one_hot_i[4];
  assign data_masked[365] = data_i[365] & sel_one_hot_i[4];
  assign data_masked[364] = data_i[364] & sel_one_hot_i[4];
  assign data_masked[363] = data_i[363] & sel_one_hot_i[4];
  assign data_masked[362] = data_i[362] & sel_one_hot_i[4];
  assign data_masked[361] = data_i[361] & sel_one_hot_i[4];
  assign data_masked[360] = data_i[360] & sel_one_hot_i[4];
  assign data_masked[359] = data_i[359] & sel_one_hot_i[4];
  assign data_masked[358] = data_i[358] & sel_one_hot_i[4];
  assign data_masked[357] = data_i[357] & sel_one_hot_i[4];
  assign data_masked[356] = data_i[356] & sel_one_hot_i[4];
  assign data_masked[355] = data_i[355] & sel_one_hot_i[4];
  assign data_masked[354] = data_i[354] & sel_one_hot_i[4];
  assign data_masked[353] = data_i[353] & sel_one_hot_i[4];
  assign data_masked[352] = data_i[352] & sel_one_hot_i[4];
  assign data_masked[351] = data_i[351] & sel_one_hot_i[4];
  assign data_masked[350] = data_i[350] & sel_one_hot_i[4];
  assign data_masked[349] = data_i[349] & sel_one_hot_i[4];
  assign data_masked[348] = data_i[348] & sel_one_hot_i[4];
  assign data_masked[347] = data_i[347] & sel_one_hot_i[4];
  assign data_masked[346] = data_i[346] & sel_one_hot_i[4];
  assign data_masked[345] = data_i[345] & sel_one_hot_i[4];
  assign data_masked[344] = data_i[344] & sel_one_hot_i[4];
  assign data_masked[343] = data_i[343] & sel_one_hot_i[4];
  assign data_masked[342] = data_i[342] & sel_one_hot_i[4];
  assign data_masked[341] = data_i[341] & sel_one_hot_i[4];
  assign data_masked[340] = data_i[340] & sel_one_hot_i[4];
  assign data_masked[339] = data_i[339] & sel_one_hot_i[4];
  assign data_masked[338] = data_i[338] & sel_one_hot_i[4];
  assign data_masked[337] = data_i[337] & sel_one_hot_i[4];
  assign data_masked[336] = data_i[336] & sel_one_hot_i[4];
  assign data_masked[335] = data_i[335] & sel_one_hot_i[4];
  assign data_masked[334] = data_i[334] & sel_one_hot_i[4];
  assign data_masked[333] = data_i[333] & sel_one_hot_i[4];
  assign data_masked[332] = data_i[332] & sel_one_hot_i[4];
  assign data_masked[331] = data_i[331] & sel_one_hot_i[4];
  assign data_masked[330] = data_i[330] & sel_one_hot_i[4];
  assign data_masked[329] = data_i[329] & sel_one_hot_i[4];
  assign data_masked[328] = data_i[328] & sel_one_hot_i[4];
  assign data_masked[327] = data_i[327] & sel_one_hot_i[4];
  assign data_masked[326] = data_i[326] & sel_one_hot_i[4];
  assign data_masked[325] = data_i[325] & sel_one_hot_i[4];
  assign data_masked[324] = data_i[324] & sel_one_hot_i[4];
  assign data_masked[323] = data_i[323] & sel_one_hot_i[4];
  assign data_masked[322] = data_i[322] & sel_one_hot_i[4];
  assign data_masked[321] = data_i[321] & sel_one_hot_i[4];
  assign data_masked[320] = data_i[320] & sel_one_hot_i[4];
  assign data_masked[319] = data_i[319] & sel_one_hot_i[4];
  assign data_masked[318] = data_i[318] & sel_one_hot_i[4];
  assign data_masked[317] = data_i[317] & sel_one_hot_i[4];
  assign data_masked[316] = data_i[316] & sel_one_hot_i[4];
  assign data_masked[315] = data_i[315] & sel_one_hot_i[4];
  assign data_masked[314] = data_i[314] & sel_one_hot_i[4];
  assign data_masked[313] = data_i[313] & sel_one_hot_i[4];
  assign data_masked[312] = data_i[312] & sel_one_hot_i[4];
  assign data_masked[311] = data_i[311] & sel_one_hot_i[4];
  assign data_masked[310] = data_i[310] & sel_one_hot_i[4];
  assign data_masked[309] = data_i[309] & sel_one_hot_i[4];
  assign data_masked[308] = data_i[308] & sel_one_hot_i[4];
  assign data_masked[307] = data_i[307] & sel_one_hot_i[4];
  assign data_masked[306] = data_i[306] & sel_one_hot_i[4];
  assign data_masked[305] = data_i[305] & sel_one_hot_i[4];
  assign data_masked[304] = data_i[304] & sel_one_hot_i[4];
  assign data_o[0] = N2 | data_masked[0];
  assign N2 = N1 | data_masked[76];
  assign N1 = N0 | data_masked[152];
  assign N0 = data_masked[304] | data_masked[228];
  assign data_o[1] = N5 | data_masked[1];
  assign N5 = N4 | data_masked[77];
  assign N4 = N3 | data_masked[153];
  assign N3 = data_masked[305] | data_masked[229];
  assign data_o[2] = N8 | data_masked[2];
  assign N8 = N7 | data_masked[78];
  assign N7 = N6 | data_masked[154];
  assign N6 = data_masked[306] | data_masked[230];
  assign data_o[3] = N11 | data_masked[3];
  assign N11 = N10 | data_masked[79];
  assign N10 = N9 | data_masked[155];
  assign N9 = data_masked[307] | data_masked[231];
  assign data_o[4] = N14 | data_masked[4];
  assign N14 = N13 | data_masked[80];
  assign N13 = N12 | data_masked[156];
  assign N12 = data_masked[308] | data_masked[232];
  assign data_o[5] = N17 | data_masked[5];
  assign N17 = N16 | data_masked[81];
  assign N16 = N15 | data_masked[157];
  assign N15 = data_masked[309] | data_masked[233];
  assign data_o[6] = N20 | data_masked[6];
  assign N20 = N19 | data_masked[82];
  assign N19 = N18 | data_masked[158];
  assign N18 = data_masked[310] | data_masked[234];
  assign data_o[7] = N23 | data_masked[7];
  assign N23 = N22 | data_masked[83];
  assign N22 = N21 | data_masked[159];
  assign N21 = data_masked[311] | data_masked[235];
  assign data_o[8] = N26 | data_masked[8];
  assign N26 = N25 | data_masked[84];
  assign N25 = N24 | data_masked[160];
  assign N24 = data_masked[312] | data_masked[236];
  assign data_o[9] = N29 | data_masked[9];
  assign N29 = N28 | data_masked[85];
  assign N28 = N27 | data_masked[161];
  assign N27 = data_masked[313] | data_masked[237];
  assign data_o[10] = N32 | data_masked[10];
  assign N32 = N31 | data_masked[86];
  assign N31 = N30 | data_masked[162];
  assign N30 = data_masked[314] | data_masked[238];
  assign data_o[11] = N35 | data_masked[11];
  assign N35 = N34 | data_masked[87];
  assign N34 = N33 | data_masked[163];
  assign N33 = data_masked[315] | data_masked[239];
  assign data_o[12] = N38 | data_masked[12];
  assign N38 = N37 | data_masked[88];
  assign N37 = N36 | data_masked[164];
  assign N36 = data_masked[316] | data_masked[240];
  assign data_o[13] = N41 | data_masked[13];
  assign N41 = N40 | data_masked[89];
  assign N40 = N39 | data_masked[165];
  assign N39 = data_masked[317] | data_masked[241];
  assign data_o[14] = N44 | data_masked[14];
  assign N44 = N43 | data_masked[90];
  assign N43 = N42 | data_masked[166];
  assign N42 = data_masked[318] | data_masked[242];
  assign data_o[15] = N47 | data_masked[15];
  assign N47 = N46 | data_masked[91];
  assign N46 = N45 | data_masked[167];
  assign N45 = data_masked[319] | data_masked[243];
  assign data_o[16] = N50 | data_masked[16];
  assign N50 = N49 | data_masked[92];
  assign N49 = N48 | data_masked[168];
  assign N48 = data_masked[320] | data_masked[244];
  assign data_o[17] = N53 | data_masked[17];
  assign N53 = N52 | data_masked[93];
  assign N52 = N51 | data_masked[169];
  assign N51 = data_masked[321] | data_masked[245];
  assign data_o[18] = N56 | data_masked[18];
  assign N56 = N55 | data_masked[94];
  assign N55 = N54 | data_masked[170];
  assign N54 = data_masked[322] | data_masked[246];
  assign data_o[19] = N59 | data_masked[19];
  assign N59 = N58 | data_masked[95];
  assign N58 = N57 | data_masked[171];
  assign N57 = data_masked[323] | data_masked[247];
  assign data_o[20] = N62 | data_masked[20];
  assign N62 = N61 | data_masked[96];
  assign N61 = N60 | data_masked[172];
  assign N60 = data_masked[324] | data_masked[248];
  assign data_o[21] = N65 | data_masked[21];
  assign N65 = N64 | data_masked[97];
  assign N64 = N63 | data_masked[173];
  assign N63 = data_masked[325] | data_masked[249];
  assign data_o[22] = N68 | data_masked[22];
  assign N68 = N67 | data_masked[98];
  assign N67 = N66 | data_masked[174];
  assign N66 = data_masked[326] | data_masked[250];
  assign data_o[23] = N71 | data_masked[23];
  assign N71 = N70 | data_masked[99];
  assign N70 = N69 | data_masked[175];
  assign N69 = data_masked[327] | data_masked[251];
  assign data_o[24] = N74 | data_masked[24];
  assign N74 = N73 | data_masked[100];
  assign N73 = N72 | data_masked[176];
  assign N72 = data_masked[328] | data_masked[252];
  assign data_o[25] = N77 | data_masked[25];
  assign N77 = N76 | data_masked[101];
  assign N76 = N75 | data_masked[177];
  assign N75 = data_masked[329] | data_masked[253];
  assign data_o[26] = N80 | data_masked[26];
  assign N80 = N79 | data_masked[102];
  assign N79 = N78 | data_masked[178];
  assign N78 = data_masked[330] | data_masked[254];
  assign data_o[27] = N83 | data_masked[27];
  assign N83 = N82 | data_masked[103];
  assign N82 = N81 | data_masked[179];
  assign N81 = data_masked[331] | data_masked[255];
  assign data_o[28] = N86 | data_masked[28];
  assign N86 = N85 | data_masked[104];
  assign N85 = N84 | data_masked[180];
  assign N84 = data_masked[332] | data_masked[256];
  assign data_o[29] = N89 | data_masked[29];
  assign N89 = N88 | data_masked[105];
  assign N88 = N87 | data_masked[181];
  assign N87 = data_masked[333] | data_masked[257];
  assign data_o[30] = N92 | data_masked[30];
  assign N92 = N91 | data_masked[106];
  assign N91 = N90 | data_masked[182];
  assign N90 = data_masked[334] | data_masked[258];
  assign data_o[31] = N95 | data_masked[31];
  assign N95 = N94 | data_masked[107];
  assign N94 = N93 | data_masked[183];
  assign N93 = data_masked[335] | data_masked[259];
  assign data_o[32] = N98 | data_masked[32];
  assign N98 = N97 | data_masked[108];
  assign N97 = N96 | data_masked[184];
  assign N96 = data_masked[336] | data_masked[260];
  assign data_o[33] = N101 | data_masked[33];
  assign N101 = N100 | data_masked[109];
  assign N100 = N99 | data_masked[185];
  assign N99 = data_masked[337] | data_masked[261];
  assign data_o[34] = N104 | data_masked[34];
  assign N104 = N103 | data_masked[110];
  assign N103 = N102 | data_masked[186];
  assign N102 = data_masked[338] | data_masked[262];
  assign data_o[35] = N107 | data_masked[35];
  assign N107 = N106 | data_masked[111];
  assign N106 = N105 | data_masked[187];
  assign N105 = data_masked[339] | data_masked[263];
  assign data_o[36] = N110 | data_masked[36];
  assign N110 = N109 | data_masked[112];
  assign N109 = N108 | data_masked[188];
  assign N108 = data_masked[340] | data_masked[264];
  assign data_o[37] = N113 | data_masked[37];
  assign N113 = N112 | data_masked[113];
  assign N112 = N111 | data_masked[189];
  assign N111 = data_masked[341] | data_masked[265];
  assign data_o[38] = N116 | data_masked[38];
  assign N116 = N115 | data_masked[114];
  assign N115 = N114 | data_masked[190];
  assign N114 = data_masked[342] | data_masked[266];
  assign data_o[39] = N119 | data_masked[39];
  assign N119 = N118 | data_masked[115];
  assign N118 = N117 | data_masked[191];
  assign N117 = data_masked[343] | data_masked[267];
  assign data_o[40] = N122 | data_masked[40];
  assign N122 = N121 | data_masked[116];
  assign N121 = N120 | data_masked[192];
  assign N120 = data_masked[344] | data_masked[268];
  assign data_o[41] = N125 | data_masked[41];
  assign N125 = N124 | data_masked[117];
  assign N124 = N123 | data_masked[193];
  assign N123 = data_masked[345] | data_masked[269];
  assign data_o[42] = N128 | data_masked[42];
  assign N128 = N127 | data_masked[118];
  assign N127 = N126 | data_masked[194];
  assign N126 = data_masked[346] | data_masked[270];
  assign data_o[43] = N131 | data_masked[43];
  assign N131 = N130 | data_masked[119];
  assign N130 = N129 | data_masked[195];
  assign N129 = data_masked[347] | data_masked[271];
  assign data_o[44] = N134 | data_masked[44];
  assign N134 = N133 | data_masked[120];
  assign N133 = N132 | data_masked[196];
  assign N132 = data_masked[348] | data_masked[272];
  assign data_o[45] = N137 | data_masked[45];
  assign N137 = N136 | data_masked[121];
  assign N136 = N135 | data_masked[197];
  assign N135 = data_masked[349] | data_masked[273];
  assign data_o[46] = N140 | data_masked[46];
  assign N140 = N139 | data_masked[122];
  assign N139 = N138 | data_masked[198];
  assign N138 = data_masked[350] | data_masked[274];
  assign data_o[47] = N143 | data_masked[47];
  assign N143 = N142 | data_masked[123];
  assign N142 = N141 | data_masked[199];
  assign N141 = data_masked[351] | data_masked[275];
  assign data_o[48] = N146 | data_masked[48];
  assign N146 = N145 | data_masked[124];
  assign N145 = N144 | data_masked[200];
  assign N144 = data_masked[352] | data_masked[276];
  assign data_o[49] = N149 | data_masked[49];
  assign N149 = N148 | data_masked[125];
  assign N148 = N147 | data_masked[201];
  assign N147 = data_masked[353] | data_masked[277];
  assign data_o[50] = N152 | data_masked[50];
  assign N152 = N151 | data_masked[126];
  assign N151 = N150 | data_masked[202];
  assign N150 = data_masked[354] | data_masked[278];
  assign data_o[51] = N155 | data_masked[51];
  assign N155 = N154 | data_masked[127];
  assign N154 = N153 | data_masked[203];
  assign N153 = data_masked[355] | data_masked[279];
  assign data_o[52] = N158 | data_masked[52];
  assign N158 = N157 | data_masked[128];
  assign N157 = N156 | data_masked[204];
  assign N156 = data_masked[356] | data_masked[280];
  assign data_o[53] = N161 | data_masked[53];
  assign N161 = N160 | data_masked[129];
  assign N160 = N159 | data_masked[205];
  assign N159 = data_masked[357] | data_masked[281];
  assign data_o[54] = N164 | data_masked[54];
  assign N164 = N163 | data_masked[130];
  assign N163 = N162 | data_masked[206];
  assign N162 = data_masked[358] | data_masked[282];
  assign data_o[55] = N167 | data_masked[55];
  assign N167 = N166 | data_masked[131];
  assign N166 = N165 | data_masked[207];
  assign N165 = data_masked[359] | data_masked[283];
  assign data_o[56] = N170 | data_masked[56];
  assign N170 = N169 | data_masked[132];
  assign N169 = N168 | data_masked[208];
  assign N168 = data_masked[360] | data_masked[284];
  assign data_o[57] = N173 | data_masked[57];
  assign N173 = N172 | data_masked[133];
  assign N172 = N171 | data_masked[209];
  assign N171 = data_masked[361] | data_masked[285];
  assign data_o[58] = N176 | data_masked[58];
  assign N176 = N175 | data_masked[134];
  assign N175 = N174 | data_masked[210];
  assign N174 = data_masked[362] | data_masked[286];
  assign data_o[59] = N179 | data_masked[59];
  assign N179 = N178 | data_masked[135];
  assign N178 = N177 | data_masked[211];
  assign N177 = data_masked[363] | data_masked[287];
  assign data_o[60] = N182 | data_masked[60];
  assign N182 = N181 | data_masked[136];
  assign N181 = N180 | data_masked[212];
  assign N180 = data_masked[364] | data_masked[288];
  assign data_o[61] = N185 | data_masked[61];
  assign N185 = N184 | data_masked[137];
  assign N184 = N183 | data_masked[213];
  assign N183 = data_masked[365] | data_masked[289];
  assign data_o[62] = N188 | data_masked[62];
  assign N188 = N187 | data_masked[138];
  assign N187 = N186 | data_masked[214];
  assign N186 = data_masked[366] | data_masked[290];
  assign data_o[63] = N191 | data_masked[63];
  assign N191 = N190 | data_masked[139];
  assign N190 = N189 | data_masked[215];
  assign N189 = data_masked[367] | data_masked[291];
  assign data_o[64] = N194 | data_masked[64];
  assign N194 = N193 | data_masked[140];
  assign N193 = N192 | data_masked[216];
  assign N192 = data_masked[368] | data_masked[292];
  assign data_o[65] = N197 | data_masked[65];
  assign N197 = N196 | data_masked[141];
  assign N196 = N195 | data_masked[217];
  assign N195 = data_masked[369] | data_masked[293];
  assign data_o[66] = N200 | data_masked[66];
  assign N200 = N199 | data_masked[142];
  assign N199 = N198 | data_masked[218];
  assign N198 = data_masked[370] | data_masked[294];
  assign data_o[67] = N203 | data_masked[67];
  assign N203 = N202 | data_masked[143];
  assign N202 = N201 | data_masked[219];
  assign N201 = data_masked[371] | data_masked[295];
  assign data_o[68] = N206 | data_masked[68];
  assign N206 = N205 | data_masked[144];
  assign N205 = N204 | data_masked[220];
  assign N204 = data_masked[372] | data_masked[296];
  assign data_o[69] = N209 | data_masked[69];
  assign N209 = N208 | data_masked[145];
  assign N208 = N207 | data_masked[221];
  assign N207 = data_masked[373] | data_masked[297];
  assign data_o[70] = N212 | data_masked[70];
  assign N212 = N211 | data_masked[146];
  assign N211 = N210 | data_masked[222];
  assign N210 = data_masked[374] | data_masked[298];
  assign data_o[71] = N215 | data_masked[71];
  assign N215 = N214 | data_masked[147];
  assign N214 = N213 | data_masked[223];
  assign N213 = data_masked[375] | data_masked[299];
  assign data_o[72] = N218 | data_masked[72];
  assign N218 = N217 | data_masked[148];
  assign N217 = N216 | data_masked[224];
  assign N216 = data_masked[376] | data_masked[300];
  assign data_o[73] = N221 | data_masked[73];
  assign N221 = N220 | data_masked[149];
  assign N220 = N219 | data_masked[225];
  assign N219 = data_masked[377] | data_masked[301];
  assign data_o[74] = N224 | data_masked[74];
  assign N224 = N223 | data_masked[150];
  assign N223 = N222 | data_masked[226];
  assign N222 = data_masked[378] | data_masked[302];
  assign data_o[75] = N227 | data_masked[75];
  assign N227 = N226 | data_masked[151];
  assign N226 = N225 | data_masked[227];
  assign N225 = data_masked[379] | data_masked[303];

endmodule



module bsg_mux_one_hot_width_p76_els_p4
(
  data_i,
  sel_one_hot_i,
  data_o
);

  input [303:0] data_i;
  input [3:0] sel_one_hot_i;
  output [75:0] data_o;
  wire [75:0] data_o;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,
  N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32,N33,N34,N35,N36,N37,N38,N39,N40,N41,
  N42,N43,N44,N45,N46,N47,N48,N49,N50,N51,N52,N53,N54,N55,N56,N57,N58,N59,N60,N61,
  N62,N63,N64,N65,N66,N67,N68,N69,N70,N71,N72,N73,N74,N75,N76,N77,N78,N79,N80,N81,
  N82,N83,N84,N85,N86,N87,N88,N89,N90,N91,N92,N93,N94,N95,N96,N97,N98,N99,N100,N101,
  N102,N103,N104,N105,N106,N107,N108,N109,N110,N111,N112,N113,N114,N115,N116,N117,
  N118,N119,N120,N121,N122,N123,N124,N125,N126,N127,N128,N129,N130,N131,N132,N133,
  N134,N135,N136,N137,N138,N139,N140,N141,N142,N143,N144,N145,N146,N147,N148,N149,
  N150,N151;
  wire [303:0] data_masked;
  assign data_masked[75] = data_i[75] & sel_one_hot_i[0];
  assign data_masked[74] = data_i[74] & sel_one_hot_i[0];
  assign data_masked[73] = data_i[73] & sel_one_hot_i[0];
  assign data_masked[72] = data_i[72] & sel_one_hot_i[0];
  assign data_masked[71] = data_i[71] & sel_one_hot_i[0];
  assign data_masked[70] = data_i[70] & sel_one_hot_i[0];
  assign data_masked[69] = data_i[69] & sel_one_hot_i[0];
  assign data_masked[68] = data_i[68] & sel_one_hot_i[0];
  assign data_masked[67] = data_i[67] & sel_one_hot_i[0];
  assign data_masked[66] = data_i[66] & sel_one_hot_i[0];
  assign data_masked[65] = data_i[65] & sel_one_hot_i[0];
  assign data_masked[64] = data_i[64] & sel_one_hot_i[0];
  assign data_masked[63] = data_i[63] & sel_one_hot_i[0];
  assign data_masked[62] = data_i[62] & sel_one_hot_i[0];
  assign data_masked[61] = data_i[61] & sel_one_hot_i[0];
  assign data_masked[60] = data_i[60] & sel_one_hot_i[0];
  assign data_masked[59] = data_i[59] & sel_one_hot_i[0];
  assign data_masked[58] = data_i[58] & sel_one_hot_i[0];
  assign data_masked[57] = data_i[57] & sel_one_hot_i[0];
  assign data_masked[56] = data_i[56] & sel_one_hot_i[0];
  assign data_masked[55] = data_i[55] & sel_one_hot_i[0];
  assign data_masked[54] = data_i[54] & sel_one_hot_i[0];
  assign data_masked[53] = data_i[53] & sel_one_hot_i[0];
  assign data_masked[52] = data_i[52] & sel_one_hot_i[0];
  assign data_masked[51] = data_i[51] & sel_one_hot_i[0];
  assign data_masked[50] = data_i[50] & sel_one_hot_i[0];
  assign data_masked[49] = data_i[49] & sel_one_hot_i[0];
  assign data_masked[48] = data_i[48] & sel_one_hot_i[0];
  assign data_masked[47] = data_i[47] & sel_one_hot_i[0];
  assign data_masked[46] = data_i[46] & sel_one_hot_i[0];
  assign data_masked[45] = data_i[45] & sel_one_hot_i[0];
  assign data_masked[44] = data_i[44] & sel_one_hot_i[0];
  assign data_masked[43] = data_i[43] & sel_one_hot_i[0];
  assign data_masked[42] = data_i[42] & sel_one_hot_i[0];
  assign data_masked[41] = data_i[41] & sel_one_hot_i[0];
  assign data_masked[40] = data_i[40] & sel_one_hot_i[0];
  assign data_masked[39] = data_i[39] & sel_one_hot_i[0];
  assign data_masked[38] = data_i[38] & sel_one_hot_i[0];
  assign data_masked[37] = data_i[37] & sel_one_hot_i[0];
  assign data_masked[36] = data_i[36] & sel_one_hot_i[0];
  assign data_masked[35] = data_i[35] & sel_one_hot_i[0];
  assign data_masked[34] = data_i[34] & sel_one_hot_i[0];
  assign data_masked[33] = data_i[33] & sel_one_hot_i[0];
  assign data_masked[32] = data_i[32] & sel_one_hot_i[0];
  assign data_masked[31] = data_i[31] & sel_one_hot_i[0];
  assign data_masked[30] = data_i[30] & sel_one_hot_i[0];
  assign data_masked[29] = data_i[29] & sel_one_hot_i[0];
  assign data_masked[28] = data_i[28] & sel_one_hot_i[0];
  assign data_masked[27] = data_i[27] & sel_one_hot_i[0];
  assign data_masked[26] = data_i[26] & sel_one_hot_i[0];
  assign data_masked[25] = data_i[25] & sel_one_hot_i[0];
  assign data_masked[24] = data_i[24] & sel_one_hot_i[0];
  assign data_masked[23] = data_i[23] & sel_one_hot_i[0];
  assign data_masked[22] = data_i[22] & sel_one_hot_i[0];
  assign data_masked[21] = data_i[21] & sel_one_hot_i[0];
  assign data_masked[20] = data_i[20] & sel_one_hot_i[0];
  assign data_masked[19] = data_i[19] & sel_one_hot_i[0];
  assign data_masked[18] = data_i[18] & sel_one_hot_i[0];
  assign data_masked[17] = data_i[17] & sel_one_hot_i[0];
  assign data_masked[16] = data_i[16] & sel_one_hot_i[0];
  assign data_masked[15] = data_i[15] & sel_one_hot_i[0];
  assign data_masked[14] = data_i[14] & sel_one_hot_i[0];
  assign data_masked[13] = data_i[13] & sel_one_hot_i[0];
  assign data_masked[12] = data_i[12] & sel_one_hot_i[0];
  assign data_masked[11] = data_i[11] & sel_one_hot_i[0];
  assign data_masked[10] = data_i[10] & sel_one_hot_i[0];
  assign data_masked[9] = data_i[9] & sel_one_hot_i[0];
  assign data_masked[8] = data_i[8] & sel_one_hot_i[0];
  assign data_masked[7] = data_i[7] & sel_one_hot_i[0];
  assign data_masked[6] = data_i[6] & sel_one_hot_i[0];
  assign data_masked[5] = data_i[5] & sel_one_hot_i[0];
  assign data_masked[4] = data_i[4] & sel_one_hot_i[0];
  assign data_masked[3] = data_i[3] & sel_one_hot_i[0];
  assign data_masked[2] = data_i[2] & sel_one_hot_i[0];
  assign data_masked[1] = data_i[1] & sel_one_hot_i[0];
  assign data_masked[0] = data_i[0] & sel_one_hot_i[0];
  assign data_masked[151] = data_i[151] & sel_one_hot_i[1];
  assign data_masked[150] = data_i[150] & sel_one_hot_i[1];
  assign data_masked[149] = data_i[149] & sel_one_hot_i[1];
  assign data_masked[148] = data_i[148] & sel_one_hot_i[1];
  assign data_masked[147] = data_i[147] & sel_one_hot_i[1];
  assign data_masked[146] = data_i[146] & sel_one_hot_i[1];
  assign data_masked[145] = data_i[145] & sel_one_hot_i[1];
  assign data_masked[144] = data_i[144] & sel_one_hot_i[1];
  assign data_masked[143] = data_i[143] & sel_one_hot_i[1];
  assign data_masked[142] = data_i[142] & sel_one_hot_i[1];
  assign data_masked[141] = data_i[141] & sel_one_hot_i[1];
  assign data_masked[140] = data_i[140] & sel_one_hot_i[1];
  assign data_masked[139] = data_i[139] & sel_one_hot_i[1];
  assign data_masked[138] = data_i[138] & sel_one_hot_i[1];
  assign data_masked[137] = data_i[137] & sel_one_hot_i[1];
  assign data_masked[136] = data_i[136] & sel_one_hot_i[1];
  assign data_masked[135] = data_i[135] & sel_one_hot_i[1];
  assign data_masked[134] = data_i[134] & sel_one_hot_i[1];
  assign data_masked[133] = data_i[133] & sel_one_hot_i[1];
  assign data_masked[132] = data_i[132] & sel_one_hot_i[1];
  assign data_masked[131] = data_i[131] & sel_one_hot_i[1];
  assign data_masked[130] = data_i[130] & sel_one_hot_i[1];
  assign data_masked[129] = data_i[129] & sel_one_hot_i[1];
  assign data_masked[128] = data_i[128] & sel_one_hot_i[1];
  assign data_masked[127] = data_i[127] & sel_one_hot_i[1];
  assign data_masked[126] = data_i[126] & sel_one_hot_i[1];
  assign data_masked[125] = data_i[125] & sel_one_hot_i[1];
  assign data_masked[124] = data_i[124] & sel_one_hot_i[1];
  assign data_masked[123] = data_i[123] & sel_one_hot_i[1];
  assign data_masked[122] = data_i[122] & sel_one_hot_i[1];
  assign data_masked[121] = data_i[121] & sel_one_hot_i[1];
  assign data_masked[120] = data_i[120] & sel_one_hot_i[1];
  assign data_masked[119] = data_i[119] & sel_one_hot_i[1];
  assign data_masked[118] = data_i[118] & sel_one_hot_i[1];
  assign data_masked[117] = data_i[117] & sel_one_hot_i[1];
  assign data_masked[116] = data_i[116] & sel_one_hot_i[1];
  assign data_masked[115] = data_i[115] & sel_one_hot_i[1];
  assign data_masked[114] = data_i[114] & sel_one_hot_i[1];
  assign data_masked[113] = data_i[113] & sel_one_hot_i[1];
  assign data_masked[112] = data_i[112] & sel_one_hot_i[1];
  assign data_masked[111] = data_i[111] & sel_one_hot_i[1];
  assign data_masked[110] = data_i[110] & sel_one_hot_i[1];
  assign data_masked[109] = data_i[109] & sel_one_hot_i[1];
  assign data_masked[108] = data_i[108] & sel_one_hot_i[1];
  assign data_masked[107] = data_i[107] & sel_one_hot_i[1];
  assign data_masked[106] = data_i[106] & sel_one_hot_i[1];
  assign data_masked[105] = data_i[105] & sel_one_hot_i[1];
  assign data_masked[104] = data_i[104] & sel_one_hot_i[1];
  assign data_masked[103] = data_i[103] & sel_one_hot_i[1];
  assign data_masked[102] = data_i[102] & sel_one_hot_i[1];
  assign data_masked[101] = data_i[101] & sel_one_hot_i[1];
  assign data_masked[100] = data_i[100] & sel_one_hot_i[1];
  assign data_masked[99] = data_i[99] & sel_one_hot_i[1];
  assign data_masked[98] = data_i[98] & sel_one_hot_i[1];
  assign data_masked[97] = data_i[97] & sel_one_hot_i[1];
  assign data_masked[96] = data_i[96] & sel_one_hot_i[1];
  assign data_masked[95] = data_i[95] & sel_one_hot_i[1];
  assign data_masked[94] = data_i[94] & sel_one_hot_i[1];
  assign data_masked[93] = data_i[93] & sel_one_hot_i[1];
  assign data_masked[92] = data_i[92] & sel_one_hot_i[1];
  assign data_masked[91] = data_i[91] & sel_one_hot_i[1];
  assign data_masked[90] = data_i[90] & sel_one_hot_i[1];
  assign data_masked[89] = data_i[89] & sel_one_hot_i[1];
  assign data_masked[88] = data_i[88] & sel_one_hot_i[1];
  assign data_masked[87] = data_i[87] & sel_one_hot_i[1];
  assign data_masked[86] = data_i[86] & sel_one_hot_i[1];
  assign data_masked[85] = data_i[85] & sel_one_hot_i[1];
  assign data_masked[84] = data_i[84] & sel_one_hot_i[1];
  assign data_masked[83] = data_i[83] & sel_one_hot_i[1];
  assign data_masked[82] = data_i[82] & sel_one_hot_i[1];
  assign data_masked[81] = data_i[81] & sel_one_hot_i[1];
  assign data_masked[80] = data_i[80] & sel_one_hot_i[1];
  assign data_masked[79] = data_i[79] & sel_one_hot_i[1];
  assign data_masked[78] = data_i[78] & sel_one_hot_i[1];
  assign data_masked[77] = data_i[77] & sel_one_hot_i[1];
  assign data_masked[76] = data_i[76] & sel_one_hot_i[1];
  assign data_masked[227] = data_i[227] & sel_one_hot_i[2];
  assign data_masked[226] = data_i[226] & sel_one_hot_i[2];
  assign data_masked[225] = data_i[225] & sel_one_hot_i[2];
  assign data_masked[224] = data_i[224] & sel_one_hot_i[2];
  assign data_masked[223] = data_i[223] & sel_one_hot_i[2];
  assign data_masked[222] = data_i[222] & sel_one_hot_i[2];
  assign data_masked[221] = data_i[221] & sel_one_hot_i[2];
  assign data_masked[220] = data_i[220] & sel_one_hot_i[2];
  assign data_masked[219] = data_i[219] & sel_one_hot_i[2];
  assign data_masked[218] = data_i[218] & sel_one_hot_i[2];
  assign data_masked[217] = data_i[217] & sel_one_hot_i[2];
  assign data_masked[216] = data_i[216] & sel_one_hot_i[2];
  assign data_masked[215] = data_i[215] & sel_one_hot_i[2];
  assign data_masked[214] = data_i[214] & sel_one_hot_i[2];
  assign data_masked[213] = data_i[213] & sel_one_hot_i[2];
  assign data_masked[212] = data_i[212] & sel_one_hot_i[2];
  assign data_masked[211] = data_i[211] & sel_one_hot_i[2];
  assign data_masked[210] = data_i[210] & sel_one_hot_i[2];
  assign data_masked[209] = data_i[209] & sel_one_hot_i[2];
  assign data_masked[208] = data_i[208] & sel_one_hot_i[2];
  assign data_masked[207] = data_i[207] & sel_one_hot_i[2];
  assign data_masked[206] = data_i[206] & sel_one_hot_i[2];
  assign data_masked[205] = data_i[205] & sel_one_hot_i[2];
  assign data_masked[204] = data_i[204] & sel_one_hot_i[2];
  assign data_masked[203] = data_i[203] & sel_one_hot_i[2];
  assign data_masked[202] = data_i[202] & sel_one_hot_i[2];
  assign data_masked[201] = data_i[201] & sel_one_hot_i[2];
  assign data_masked[200] = data_i[200] & sel_one_hot_i[2];
  assign data_masked[199] = data_i[199] & sel_one_hot_i[2];
  assign data_masked[198] = data_i[198] & sel_one_hot_i[2];
  assign data_masked[197] = data_i[197] & sel_one_hot_i[2];
  assign data_masked[196] = data_i[196] & sel_one_hot_i[2];
  assign data_masked[195] = data_i[195] & sel_one_hot_i[2];
  assign data_masked[194] = data_i[194] & sel_one_hot_i[2];
  assign data_masked[193] = data_i[193] & sel_one_hot_i[2];
  assign data_masked[192] = data_i[192] & sel_one_hot_i[2];
  assign data_masked[191] = data_i[191] & sel_one_hot_i[2];
  assign data_masked[190] = data_i[190] & sel_one_hot_i[2];
  assign data_masked[189] = data_i[189] & sel_one_hot_i[2];
  assign data_masked[188] = data_i[188] & sel_one_hot_i[2];
  assign data_masked[187] = data_i[187] & sel_one_hot_i[2];
  assign data_masked[186] = data_i[186] & sel_one_hot_i[2];
  assign data_masked[185] = data_i[185] & sel_one_hot_i[2];
  assign data_masked[184] = data_i[184] & sel_one_hot_i[2];
  assign data_masked[183] = data_i[183] & sel_one_hot_i[2];
  assign data_masked[182] = data_i[182] & sel_one_hot_i[2];
  assign data_masked[181] = data_i[181] & sel_one_hot_i[2];
  assign data_masked[180] = data_i[180] & sel_one_hot_i[2];
  assign data_masked[179] = data_i[179] & sel_one_hot_i[2];
  assign data_masked[178] = data_i[178] & sel_one_hot_i[2];
  assign data_masked[177] = data_i[177] & sel_one_hot_i[2];
  assign data_masked[176] = data_i[176] & sel_one_hot_i[2];
  assign data_masked[175] = data_i[175] & sel_one_hot_i[2];
  assign data_masked[174] = data_i[174] & sel_one_hot_i[2];
  assign data_masked[173] = data_i[173] & sel_one_hot_i[2];
  assign data_masked[172] = data_i[172] & sel_one_hot_i[2];
  assign data_masked[171] = data_i[171] & sel_one_hot_i[2];
  assign data_masked[170] = data_i[170] & sel_one_hot_i[2];
  assign data_masked[169] = data_i[169] & sel_one_hot_i[2];
  assign data_masked[168] = data_i[168] & sel_one_hot_i[2];
  assign data_masked[167] = data_i[167] & sel_one_hot_i[2];
  assign data_masked[166] = data_i[166] & sel_one_hot_i[2];
  assign data_masked[165] = data_i[165] & sel_one_hot_i[2];
  assign data_masked[164] = data_i[164] & sel_one_hot_i[2];
  assign data_masked[163] = data_i[163] & sel_one_hot_i[2];
  assign data_masked[162] = data_i[162] & sel_one_hot_i[2];
  assign data_masked[161] = data_i[161] & sel_one_hot_i[2];
  assign data_masked[160] = data_i[160] & sel_one_hot_i[2];
  assign data_masked[159] = data_i[159] & sel_one_hot_i[2];
  assign data_masked[158] = data_i[158] & sel_one_hot_i[2];
  assign data_masked[157] = data_i[157] & sel_one_hot_i[2];
  assign data_masked[156] = data_i[156] & sel_one_hot_i[2];
  assign data_masked[155] = data_i[155] & sel_one_hot_i[2];
  assign data_masked[154] = data_i[154] & sel_one_hot_i[2];
  assign data_masked[153] = data_i[153] & sel_one_hot_i[2];
  assign data_masked[152] = data_i[152] & sel_one_hot_i[2];
  assign data_masked[303] = data_i[303] & sel_one_hot_i[3];
  assign data_masked[302] = data_i[302] & sel_one_hot_i[3];
  assign data_masked[301] = data_i[301] & sel_one_hot_i[3];
  assign data_masked[300] = data_i[300] & sel_one_hot_i[3];
  assign data_masked[299] = data_i[299] & sel_one_hot_i[3];
  assign data_masked[298] = data_i[298] & sel_one_hot_i[3];
  assign data_masked[297] = data_i[297] & sel_one_hot_i[3];
  assign data_masked[296] = data_i[296] & sel_one_hot_i[3];
  assign data_masked[295] = data_i[295] & sel_one_hot_i[3];
  assign data_masked[294] = data_i[294] & sel_one_hot_i[3];
  assign data_masked[293] = data_i[293] & sel_one_hot_i[3];
  assign data_masked[292] = data_i[292] & sel_one_hot_i[3];
  assign data_masked[291] = data_i[291] & sel_one_hot_i[3];
  assign data_masked[290] = data_i[290] & sel_one_hot_i[3];
  assign data_masked[289] = data_i[289] & sel_one_hot_i[3];
  assign data_masked[288] = data_i[288] & sel_one_hot_i[3];
  assign data_masked[287] = data_i[287] & sel_one_hot_i[3];
  assign data_masked[286] = data_i[286] & sel_one_hot_i[3];
  assign data_masked[285] = data_i[285] & sel_one_hot_i[3];
  assign data_masked[284] = data_i[284] & sel_one_hot_i[3];
  assign data_masked[283] = data_i[283] & sel_one_hot_i[3];
  assign data_masked[282] = data_i[282] & sel_one_hot_i[3];
  assign data_masked[281] = data_i[281] & sel_one_hot_i[3];
  assign data_masked[280] = data_i[280] & sel_one_hot_i[3];
  assign data_masked[279] = data_i[279] & sel_one_hot_i[3];
  assign data_masked[278] = data_i[278] & sel_one_hot_i[3];
  assign data_masked[277] = data_i[277] & sel_one_hot_i[3];
  assign data_masked[276] = data_i[276] & sel_one_hot_i[3];
  assign data_masked[275] = data_i[275] & sel_one_hot_i[3];
  assign data_masked[274] = data_i[274] & sel_one_hot_i[3];
  assign data_masked[273] = data_i[273] & sel_one_hot_i[3];
  assign data_masked[272] = data_i[272] & sel_one_hot_i[3];
  assign data_masked[271] = data_i[271] & sel_one_hot_i[3];
  assign data_masked[270] = data_i[270] & sel_one_hot_i[3];
  assign data_masked[269] = data_i[269] & sel_one_hot_i[3];
  assign data_masked[268] = data_i[268] & sel_one_hot_i[3];
  assign data_masked[267] = data_i[267] & sel_one_hot_i[3];
  assign data_masked[266] = data_i[266] & sel_one_hot_i[3];
  assign data_masked[265] = data_i[265] & sel_one_hot_i[3];
  assign data_masked[264] = data_i[264] & sel_one_hot_i[3];
  assign data_masked[263] = data_i[263] & sel_one_hot_i[3];
  assign data_masked[262] = data_i[262] & sel_one_hot_i[3];
  assign data_masked[261] = data_i[261] & sel_one_hot_i[3];
  assign data_masked[260] = data_i[260] & sel_one_hot_i[3];
  assign data_masked[259] = data_i[259] & sel_one_hot_i[3];
  assign data_masked[258] = data_i[258] & sel_one_hot_i[3];
  assign data_masked[257] = data_i[257] & sel_one_hot_i[3];
  assign data_masked[256] = data_i[256] & sel_one_hot_i[3];
  assign data_masked[255] = data_i[255] & sel_one_hot_i[3];
  assign data_masked[254] = data_i[254] & sel_one_hot_i[3];
  assign data_masked[253] = data_i[253] & sel_one_hot_i[3];
  assign data_masked[252] = data_i[252] & sel_one_hot_i[3];
  assign data_masked[251] = data_i[251] & sel_one_hot_i[3];
  assign data_masked[250] = data_i[250] & sel_one_hot_i[3];
  assign data_masked[249] = data_i[249] & sel_one_hot_i[3];
  assign data_masked[248] = data_i[248] & sel_one_hot_i[3];
  assign data_masked[247] = data_i[247] & sel_one_hot_i[3];
  assign data_masked[246] = data_i[246] & sel_one_hot_i[3];
  assign data_masked[245] = data_i[245] & sel_one_hot_i[3];
  assign data_masked[244] = data_i[244] & sel_one_hot_i[3];
  assign data_masked[243] = data_i[243] & sel_one_hot_i[3];
  assign data_masked[242] = data_i[242] & sel_one_hot_i[3];
  assign data_masked[241] = data_i[241] & sel_one_hot_i[3];
  assign data_masked[240] = data_i[240] & sel_one_hot_i[3];
  assign data_masked[239] = data_i[239] & sel_one_hot_i[3];
  assign data_masked[238] = data_i[238] & sel_one_hot_i[3];
  assign data_masked[237] = data_i[237] & sel_one_hot_i[3];
  assign data_masked[236] = data_i[236] & sel_one_hot_i[3];
  assign data_masked[235] = data_i[235] & sel_one_hot_i[3];
  assign data_masked[234] = data_i[234] & sel_one_hot_i[3];
  assign data_masked[233] = data_i[233] & sel_one_hot_i[3];
  assign data_masked[232] = data_i[232] & sel_one_hot_i[3];
  assign data_masked[231] = data_i[231] & sel_one_hot_i[3];
  assign data_masked[230] = data_i[230] & sel_one_hot_i[3];
  assign data_masked[229] = data_i[229] & sel_one_hot_i[3];
  assign data_masked[228] = data_i[228] & sel_one_hot_i[3];
  assign data_o[0] = N1 | data_masked[0];
  assign N1 = N0 | data_masked[76];
  assign N0 = data_masked[228] | data_masked[152];
  assign data_o[1] = N3 | data_masked[1];
  assign N3 = N2 | data_masked[77];
  assign N2 = data_masked[229] | data_masked[153];
  assign data_o[2] = N5 | data_masked[2];
  assign N5 = N4 | data_masked[78];
  assign N4 = data_masked[230] | data_masked[154];
  assign data_o[3] = N7 | data_masked[3];
  assign N7 = N6 | data_masked[79];
  assign N6 = data_masked[231] | data_masked[155];
  assign data_o[4] = N9 | data_masked[4];
  assign N9 = N8 | data_masked[80];
  assign N8 = data_masked[232] | data_masked[156];
  assign data_o[5] = N11 | data_masked[5];
  assign N11 = N10 | data_masked[81];
  assign N10 = data_masked[233] | data_masked[157];
  assign data_o[6] = N13 | data_masked[6];
  assign N13 = N12 | data_masked[82];
  assign N12 = data_masked[234] | data_masked[158];
  assign data_o[7] = N15 | data_masked[7];
  assign N15 = N14 | data_masked[83];
  assign N14 = data_masked[235] | data_masked[159];
  assign data_o[8] = N17 | data_masked[8];
  assign N17 = N16 | data_masked[84];
  assign N16 = data_masked[236] | data_masked[160];
  assign data_o[9] = N19 | data_masked[9];
  assign N19 = N18 | data_masked[85];
  assign N18 = data_masked[237] | data_masked[161];
  assign data_o[10] = N21 | data_masked[10];
  assign N21 = N20 | data_masked[86];
  assign N20 = data_masked[238] | data_masked[162];
  assign data_o[11] = N23 | data_masked[11];
  assign N23 = N22 | data_masked[87];
  assign N22 = data_masked[239] | data_masked[163];
  assign data_o[12] = N25 | data_masked[12];
  assign N25 = N24 | data_masked[88];
  assign N24 = data_masked[240] | data_masked[164];
  assign data_o[13] = N27 | data_masked[13];
  assign N27 = N26 | data_masked[89];
  assign N26 = data_masked[241] | data_masked[165];
  assign data_o[14] = N29 | data_masked[14];
  assign N29 = N28 | data_masked[90];
  assign N28 = data_masked[242] | data_masked[166];
  assign data_o[15] = N31 | data_masked[15];
  assign N31 = N30 | data_masked[91];
  assign N30 = data_masked[243] | data_masked[167];
  assign data_o[16] = N33 | data_masked[16];
  assign N33 = N32 | data_masked[92];
  assign N32 = data_masked[244] | data_masked[168];
  assign data_o[17] = N35 | data_masked[17];
  assign N35 = N34 | data_masked[93];
  assign N34 = data_masked[245] | data_masked[169];
  assign data_o[18] = N37 | data_masked[18];
  assign N37 = N36 | data_masked[94];
  assign N36 = data_masked[246] | data_masked[170];
  assign data_o[19] = N39 | data_masked[19];
  assign N39 = N38 | data_masked[95];
  assign N38 = data_masked[247] | data_masked[171];
  assign data_o[20] = N41 | data_masked[20];
  assign N41 = N40 | data_masked[96];
  assign N40 = data_masked[248] | data_masked[172];
  assign data_o[21] = N43 | data_masked[21];
  assign N43 = N42 | data_masked[97];
  assign N42 = data_masked[249] | data_masked[173];
  assign data_o[22] = N45 | data_masked[22];
  assign N45 = N44 | data_masked[98];
  assign N44 = data_masked[250] | data_masked[174];
  assign data_o[23] = N47 | data_masked[23];
  assign N47 = N46 | data_masked[99];
  assign N46 = data_masked[251] | data_masked[175];
  assign data_o[24] = N49 | data_masked[24];
  assign N49 = N48 | data_masked[100];
  assign N48 = data_masked[252] | data_masked[176];
  assign data_o[25] = N51 | data_masked[25];
  assign N51 = N50 | data_masked[101];
  assign N50 = data_masked[253] | data_masked[177];
  assign data_o[26] = N53 | data_masked[26];
  assign N53 = N52 | data_masked[102];
  assign N52 = data_masked[254] | data_masked[178];
  assign data_o[27] = N55 | data_masked[27];
  assign N55 = N54 | data_masked[103];
  assign N54 = data_masked[255] | data_masked[179];
  assign data_o[28] = N57 | data_masked[28];
  assign N57 = N56 | data_masked[104];
  assign N56 = data_masked[256] | data_masked[180];
  assign data_o[29] = N59 | data_masked[29];
  assign N59 = N58 | data_masked[105];
  assign N58 = data_masked[257] | data_masked[181];
  assign data_o[30] = N61 | data_masked[30];
  assign N61 = N60 | data_masked[106];
  assign N60 = data_masked[258] | data_masked[182];
  assign data_o[31] = N63 | data_masked[31];
  assign N63 = N62 | data_masked[107];
  assign N62 = data_masked[259] | data_masked[183];
  assign data_o[32] = N65 | data_masked[32];
  assign N65 = N64 | data_masked[108];
  assign N64 = data_masked[260] | data_masked[184];
  assign data_o[33] = N67 | data_masked[33];
  assign N67 = N66 | data_masked[109];
  assign N66 = data_masked[261] | data_masked[185];
  assign data_o[34] = N69 | data_masked[34];
  assign N69 = N68 | data_masked[110];
  assign N68 = data_masked[262] | data_masked[186];
  assign data_o[35] = N71 | data_masked[35];
  assign N71 = N70 | data_masked[111];
  assign N70 = data_masked[263] | data_masked[187];
  assign data_o[36] = N73 | data_masked[36];
  assign N73 = N72 | data_masked[112];
  assign N72 = data_masked[264] | data_masked[188];
  assign data_o[37] = N75 | data_masked[37];
  assign N75 = N74 | data_masked[113];
  assign N74 = data_masked[265] | data_masked[189];
  assign data_o[38] = N77 | data_masked[38];
  assign N77 = N76 | data_masked[114];
  assign N76 = data_masked[266] | data_masked[190];
  assign data_o[39] = N79 | data_masked[39];
  assign N79 = N78 | data_masked[115];
  assign N78 = data_masked[267] | data_masked[191];
  assign data_o[40] = N81 | data_masked[40];
  assign N81 = N80 | data_masked[116];
  assign N80 = data_masked[268] | data_masked[192];
  assign data_o[41] = N83 | data_masked[41];
  assign N83 = N82 | data_masked[117];
  assign N82 = data_masked[269] | data_masked[193];
  assign data_o[42] = N85 | data_masked[42];
  assign N85 = N84 | data_masked[118];
  assign N84 = data_masked[270] | data_masked[194];
  assign data_o[43] = N87 | data_masked[43];
  assign N87 = N86 | data_masked[119];
  assign N86 = data_masked[271] | data_masked[195];
  assign data_o[44] = N89 | data_masked[44];
  assign N89 = N88 | data_masked[120];
  assign N88 = data_masked[272] | data_masked[196];
  assign data_o[45] = N91 | data_masked[45];
  assign N91 = N90 | data_masked[121];
  assign N90 = data_masked[273] | data_masked[197];
  assign data_o[46] = N93 | data_masked[46];
  assign N93 = N92 | data_masked[122];
  assign N92 = data_masked[274] | data_masked[198];
  assign data_o[47] = N95 | data_masked[47];
  assign N95 = N94 | data_masked[123];
  assign N94 = data_masked[275] | data_masked[199];
  assign data_o[48] = N97 | data_masked[48];
  assign N97 = N96 | data_masked[124];
  assign N96 = data_masked[276] | data_masked[200];
  assign data_o[49] = N99 | data_masked[49];
  assign N99 = N98 | data_masked[125];
  assign N98 = data_masked[277] | data_masked[201];
  assign data_o[50] = N101 | data_masked[50];
  assign N101 = N100 | data_masked[126];
  assign N100 = data_masked[278] | data_masked[202];
  assign data_o[51] = N103 | data_masked[51];
  assign N103 = N102 | data_masked[127];
  assign N102 = data_masked[279] | data_masked[203];
  assign data_o[52] = N105 | data_masked[52];
  assign N105 = N104 | data_masked[128];
  assign N104 = data_masked[280] | data_masked[204];
  assign data_o[53] = N107 | data_masked[53];
  assign N107 = N106 | data_masked[129];
  assign N106 = data_masked[281] | data_masked[205];
  assign data_o[54] = N109 | data_masked[54];
  assign N109 = N108 | data_masked[130];
  assign N108 = data_masked[282] | data_masked[206];
  assign data_o[55] = N111 | data_masked[55];
  assign N111 = N110 | data_masked[131];
  assign N110 = data_masked[283] | data_masked[207];
  assign data_o[56] = N113 | data_masked[56];
  assign N113 = N112 | data_masked[132];
  assign N112 = data_masked[284] | data_masked[208];
  assign data_o[57] = N115 | data_masked[57];
  assign N115 = N114 | data_masked[133];
  assign N114 = data_masked[285] | data_masked[209];
  assign data_o[58] = N117 | data_masked[58];
  assign N117 = N116 | data_masked[134];
  assign N116 = data_masked[286] | data_masked[210];
  assign data_o[59] = N119 | data_masked[59];
  assign N119 = N118 | data_masked[135];
  assign N118 = data_masked[287] | data_masked[211];
  assign data_o[60] = N121 | data_masked[60];
  assign N121 = N120 | data_masked[136];
  assign N120 = data_masked[288] | data_masked[212];
  assign data_o[61] = N123 | data_masked[61];
  assign N123 = N122 | data_masked[137];
  assign N122 = data_masked[289] | data_masked[213];
  assign data_o[62] = N125 | data_masked[62];
  assign N125 = N124 | data_masked[138];
  assign N124 = data_masked[290] | data_masked[214];
  assign data_o[63] = N127 | data_masked[63];
  assign N127 = N126 | data_masked[139];
  assign N126 = data_masked[291] | data_masked[215];
  assign data_o[64] = N129 | data_masked[64];
  assign N129 = N128 | data_masked[140];
  assign N128 = data_masked[292] | data_masked[216];
  assign data_o[65] = N131 | data_masked[65];
  assign N131 = N130 | data_masked[141];
  assign N130 = data_masked[293] | data_masked[217];
  assign data_o[66] = N133 | data_masked[66];
  assign N133 = N132 | data_masked[142];
  assign N132 = data_masked[294] | data_masked[218];
  assign data_o[67] = N135 | data_masked[67];
  assign N135 = N134 | data_masked[143];
  assign N134 = data_masked[295] | data_masked[219];
  assign data_o[68] = N137 | data_masked[68];
  assign N137 = N136 | data_masked[144];
  assign N136 = data_masked[296] | data_masked[220];
  assign data_o[69] = N139 | data_masked[69];
  assign N139 = N138 | data_masked[145];
  assign N138 = data_masked[297] | data_masked[221];
  assign data_o[70] = N141 | data_masked[70];
  assign N141 = N140 | data_masked[146];
  assign N140 = data_masked[298] | data_masked[222];
  assign data_o[71] = N143 | data_masked[71];
  assign N143 = N142 | data_masked[147];
  assign N142 = data_masked[299] | data_masked[223];
  assign data_o[72] = N145 | data_masked[72];
  assign N145 = N144 | data_masked[148];
  assign N144 = data_masked[300] | data_masked[224];
  assign data_o[73] = N147 | data_masked[73];
  assign N147 = N146 | data_masked[149];
  assign N146 = data_masked[301] | data_masked[225];
  assign data_o[74] = N149 | data_masked[74];
  assign N149 = N148 | data_masked[150];
  assign N148 = data_masked[302] | data_masked[226];
  assign data_o[75] = N151 | data_masked[75];
  assign N151 = N150 | data_masked[151];
  assign N150 = data_masked[303] | data_masked[227];

endmodule



module bsg_mesh_router_76_4_5_0_00_1
(
  clk_i,
  reset_i,
  data_i,
  v_i,
  yumi_o,
  ready_i,
  data_o,
  v_o,
  my_x_i,
  my_y_i
);

  input [379:0] data_i;
  input [4:0] v_i;
  output [4:0] yumi_o;
  input [4:0] ready_i;
  output [379:0] data_o;
  output [4:0] v_o;
  input [3:0] my_x_i;
  input [4:0] my_y_i;
  input clk_i;
  input reset_i;
  wire [4:0] yumi_o,v_o;
  wire [379:0] data_o;
  wire W_gnt_e,W_gnt_p,W_gnt_s,E_gnt_w,E_gnt_p,E_gnt_s,N_gnt_s,N_gnt_e,N_gnt_w,N_gnt_p,
  S_gnt_n,S_gnt_e,S_gnt_w,S_gnt_p,P_gnt_s,P_gnt_n,P_gnt_e,P_gnt_w,P_gnt_p,N0,N1,
  N2,N3,N4,N5,N6,N7,N8,SV2V_UNCONNECTED_1,SV2V_UNCONNECTED_2,
  SV2V_UNCONNECTED_3,SV2V_UNCONNECTED_4,SV2V_UNCONNECTED_5,SV2V_UNCONNECTED_6,
  SV2V_UNCONNECTED_7,SV2V_UNCONNECTED_8,SV2V_UNCONNECTED_9,
  SV2V_UNCONNECTED_10,SV2V_UNCONNECTED_11;
  wire [24:0] req;

  bsg_mesh_router_dor_decoder_4_5_5_1
  dor_decoder
  (
    .clk_i(clk_i),
    .v_i(v_i),
    .x_dirs_i({ data_i[307:304], data_i[231:228], data_i[155:152], data_i[79:76], data_i[3:0] }),
    .y_dirs_i({ data_i[312:308], data_i[236:232], data_i[160:156], data_i[84:80], data_i[8:4] }),
    .my_x_i(my_x_i),
    .my_y_i(my_y_i),
    .req_o(req)
  );


  bsg_round_robin_arb_inputs_p3
  fi_west_rr_arb
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .grants_en_i(ready_i[1]),
    .reqs_i({ req[11:11], req[1:1], req[21:21] }),
    .grants_o({ W_gnt_e, W_gnt_p, W_gnt_s }),
    .v_o(v_o[1]),
    .tag_o({ SV2V_UNCONNECTED_1, SV2V_UNCONNECTED_2 }),
    .yumi_i(v_o[1])
  );


  bsg_round_robin_arb_inputs_p3
  fi_east_rr_arb
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .grants_en_i(ready_i[2]),
    .reqs_i({ req[7:7], req[2:2], req[22:22] }),
    .grants_o({ E_gnt_w, E_gnt_p, E_gnt_s }),
    .v_o(v_o[2]),
    .tag_o({ SV2V_UNCONNECTED_3, SV2V_UNCONNECTED_4 }),
    .yumi_i(v_o[2])
  );


  bsg_round_robin_arb_inputs_p4
  north_rr_arb
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .grants_en_i(ready_i[3]),
    .reqs_i({ req[23:23], req[13:13], req[8:8], req[3:3] }),
    .grants_o({ N_gnt_s, N_gnt_e, N_gnt_w, N_gnt_p }),
    .v_o(v_o[3]),
    .tag_o({ SV2V_UNCONNECTED_5, SV2V_UNCONNECTED_6 }),
    .yumi_i(v_o[3])
  );


  bsg_round_robin_arb_inputs_p4
  south_rr_arb
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .grants_en_i(ready_i[4]),
    .reqs_i({ req[19:19], req[14:14], req[9:9], req[4:4] }),
    .grants_o({ S_gnt_n, S_gnt_e, S_gnt_w, S_gnt_p }),
    .v_o(v_o[4]),
    .tag_o({ SV2V_UNCONNECTED_7, SV2V_UNCONNECTED_8 }),
    .yumi_i(v_o[4])
  );


  bsg_round_robin_arb_inputs_p5
  proc_rr_arb
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .grants_en_i(ready_i[0]),
    .reqs_i({ req[20:20], req[15:15], req[10:10], req[5:5], req[0:0] }),
    .grants_o({ P_gnt_s, P_gnt_n, P_gnt_e, P_gnt_w, P_gnt_p }),
    .v_o(v_o[0]),
    .tag_o({ SV2V_UNCONNECTED_9, SV2V_UNCONNECTED_10, SV2V_UNCONNECTED_11 }),
    .yumi_i(v_o[0])
  );


  bsg_mux_one_hot_width_p76_els_p3
  genblk3_mux_data_west
  (
    .data_i({ data_i[75:0], data_i[227:152], data_i[379:304] }),
    .sel_one_hot_i({ W_gnt_p, W_gnt_e, W_gnt_s }),
    .data_o(data_o[151:76])
  );


  bsg_mux_one_hot_width_p76_els_p3
  genblk3_mux_data_east
  (
    .data_i({ data_i[75:0], data_i[151:76], data_i[379:304] }),
    .sel_one_hot_i({ E_gnt_p, E_gnt_w, E_gnt_s }),
    .data_o(data_o[227:152])
  );


  bsg_mux_one_hot_width_p76_els_p5
  mux_data_proc
  (
    .data_i({ data_i[75:0], data_i[227:152], data_i[379:304], data_i[151:76], data_i[303:228] }),
    .sel_one_hot_i({ P_gnt_p, P_gnt_e, P_gnt_s, P_gnt_w, P_gnt_n }),
    .data_o(data_o[75:0])
  );


  bsg_mux_one_hot_width_p76_els_p4
  mux_data_north
  (
    .data_i({ data_i[75:0], data_i[227:152], data_i[379:304], data_i[151:76] }),
    .sel_one_hot_i({ N_gnt_p, N_gnt_e, N_gnt_s, N_gnt_w }),
    .data_o(data_o[303:228])
  );


  bsg_mux_one_hot_width_p76_els_p4
  mux_data_south
  (
    .data_i({ data_i[75:0], data_i[227:152], data_i[303:228], data_i[151:76] }),
    .sel_one_hot_i({ S_gnt_p, S_gnt_e, S_gnt_n, S_gnt_w }),
    .data_o(data_o[379:304])
  );

  assign yumi_o[1] = N1 | P_gnt_w;
  assign N1 = N0 | S_gnt_w;
  assign N0 = E_gnt_w | N_gnt_w;
  assign yumi_o[2] = N3 | P_gnt_e;
  assign N3 = N2 | S_gnt_e;
  assign N2 = W_gnt_e | N_gnt_e;
  assign yumi_o[0] = N6 | W_gnt_p;
  assign N6 = N5 | P_gnt_p;
  assign N5 = N4 | S_gnt_p;
  assign N4 = E_gnt_p | N_gnt_p;
  assign yumi_o[3] = S_gnt_n | P_gnt_n;
  assign yumi_o[4] = N8 | E_gnt_s;
  assign N8 = N7 | W_gnt_s;
  assign N7 = N_gnt_s | P_gnt_s;

endmodule



module bsg_mesh_router_buffered_76_4_5_0_00_1_00
(
  clk_i,
  reset_i,
  link_i,
  link_o,
  my_x_i,
  my_y_i
);

  input [389:0] link_i;
  output [389:0] link_o;
  input [3:0] my_x_i;
  input [4:0] my_y_i;
  input clk_i;
  input reset_i;
  wire [389:0] link_o;
  wire [4:0] fifo_valid,fifo_yumi;
  wire [379:0] fifo_data;

  bsg_two_fifo_width_p76
  rof_0__fi_twofer
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .ready_o(link_o[76]),
    .data_i(link_i[75:0]),
    .v_i(link_i[77]),
    .v_o(fifo_valid[0]),
    .data_o(fifo_data[75:0]),
    .yumi_i(fifo_yumi[0])
  );


  bsg_two_fifo_width_p76
  rof_1__fi_twofer
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .ready_o(link_o[154]),
    .data_i(link_i[153:78]),
    .v_i(link_i[155]),
    .v_o(fifo_valid[1]),
    .data_o(fifo_data[151:76]),
    .yumi_i(fifo_yumi[1])
  );


  bsg_two_fifo_width_p76
  rof_2__fi_twofer
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .ready_o(link_o[232]),
    .data_i(link_i[231:156]),
    .v_i(link_i[233]),
    .v_o(fifo_valid[2]),
    .data_o(fifo_data[227:152]),
    .yumi_i(fifo_yumi[2])
  );


  bsg_two_fifo_width_p76
  rof_3__fi_twofer
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .ready_o(link_o[310]),
    .data_i(link_i[309:234]),
    .v_i(link_i[311]),
    .v_o(fifo_valid[3]),
    .data_o(fifo_data[303:228]),
    .yumi_i(fifo_yumi[3])
  );


  bsg_two_fifo_width_p76
  rof_4__fi_twofer
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .ready_o(link_o[388]),
    .data_i(link_i[387:312]),
    .v_i(link_i[389]),
    .v_o(fifo_valid[4]),
    .data_o(fifo_data[379:304]),
    .yumi_i(fifo_yumi[4])
  );


  bsg_mesh_router_76_4_5_0_00_1
  bmr
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .data_i(fifo_data),
    .v_i(fifo_valid),
    .yumi_o(fifo_yumi),
    .ready_i({ link_i[388:388], link_i[310:310], link_i[232:232], link_i[154:154], link_i[76:76] }),
    .data_o({ link_o[387:312], link_o[309:234], link_o[231:156], link_o[153:78], link_o[75:0] }),
    .v_o({ link_o[389:389], link_o[311:311], link_o[233:233], link_o[155:155], link_o[77:77] }),
    .my_x_i(my_x_i),
    .my_y_i(my_y_i)
  );


endmodule



module bsg_mem_1r1w_synth_width_p9_els_p2_read_write_same_addr_p0_harden_p0
(
  w_clk_i,
  w_reset_i,
  w_v_i,
  w_addr_i,
  w_data_i,
  r_v_i,
  r_addr_i,
  r_data_o
);

  input [0:0] w_addr_i;
  input [8:0] w_data_i;
  input [0:0] r_addr_i;
  output [8:0] r_data_o;
  input w_clk_i;
  input w_reset_i;
  input w_v_i;
  input r_v_i;
  wire [8:0] r_data_o;
  wire N0,N1,N2,N3,N4,N5,N7,N8;
  reg [17:0] mem;
  assign r_data_o[8] = (N3)? mem[8] : 
                       (N0)? mem[17] : 1'b0;
  assign N0 = r_addr_i[0];
  assign r_data_o[7] = (N3)? mem[7] : 
                       (N0)? mem[16] : 1'b0;
  assign r_data_o[6] = (N3)? mem[6] : 
                       (N0)? mem[15] : 1'b0;
  assign r_data_o[5] = (N3)? mem[5] : 
                       (N0)? mem[14] : 1'b0;
  assign r_data_o[4] = (N3)? mem[4] : 
                       (N0)? mem[13] : 1'b0;
  assign r_data_o[3] = (N3)? mem[3] : 
                       (N0)? mem[12] : 1'b0;
  assign r_data_o[2] = (N3)? mem[2] : 
                       (N0)? mem[11] : 1'b0;
  assign r_data_o[1] = (N3)? mem[1] : 
                       (N0)? mem[10] : 1'b0;
  assign r_data_o[0] = (N3)? mem[0] : 
                       (N0)? mem[9] : 1'b0;

  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[17] <= w_data_i[8];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[16] <= w_data_i[7];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[15] <= w_data_i[6];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[14] <= w_data_i[5];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[13] <= w_data_i[4];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[12] <= w_data_i[3];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[11] <= w_data_i[2];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[10] <= w_data_i[1];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N8) begin
      mem[9] <= w_data_i[0];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[8] <= w_data_i[8];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[7] <= w_data_i[7];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[6] <= w_data_i[6];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[5] <= w_data_i[5];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[4] <= w_data_i[4];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[3] <= w_data_i[3];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[2] <= w_data_i[2];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[1] <= w_data_i[1];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N7) begin
      mem[0] <= w_data_i[0];
    end 
  end

  assign N5 = ~w_addr_i[0];
  assign { N8, N7 } = (N1)? { w_addr_i[0:0], N5 } : 
                      (N2)? { 1'b0, 1'b0 } : 1'b0;
  assign N1 = w_v_i;
  assign N2 = N4;
  assign N3 = ~r_addr_i[0];
  assign N4 = ~w_v_i;

endmodule



module bsg_mem_1r1w_width_p9_els_p2_read_write_same_addr_p0
(
  w_clk_i,
  w_reset_i,
  w_v_i,
  w_addr_i,
  w_data_i,
  r_v_i,
  r_addr_i,
  r_data_o
);

  input [0:0] w_addr_i;
  input [8:0] w_data_i;
  input [0:0] r_addr_i;
  output [8:0] r_data_o;
  input w_clk_i;
  input w_reset_i;
  input w_v_i;
  input r_v_i;
  wire [8:0] r_data_o;

  bsg_mem_1r1w_synth_width_p9_els_p2_read_write_same_addr_p0_harden_p0
  synth
  (
    .w_clk_i(w_clk_i),
    .w_reset_i(w_reset_i),
    .w_v_i(w_v_i),
    .w_addr_i(w_addr_i[0]),
    .w_data_i(w_data_i),
    .r_v_i(r_v_i),
    .r_addr_i(r_addr_i[0]),
    .r_data_o(r_data_o)
  );


endmodule



module bsg_two_fifo_width_p9
(
  clk_i,
  reset_i,
  ready_o,
  data_i,
  v_i,
  v_o,
  data_o,
  yumi_i
);

  input [8:0] data_i;
  output [8:0] data_o;
  input clk_i;
  input reset_i;
  input v_i;
  input yumi_i;
  output ready_o;
  output v_o;
  wire [8:0] data_o;
  wire ready_o,v_o,N0,N1,enq_i,n_0_net_,n_cse_4,n_cse_6,n_cse_7,N2,N3,N4,N5,N6,N7,N8,
  N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21;
  reg full_r,tail_r,head_r,empty_r;

  bsg_mem_1r1w_width_p9_els_p2_read_write_same_addr_p0
  mem_1r1w
  (
    .w_clk_i(clk_i),
    .w_reset_i(reset_i),
    .w_v_i(enq_i),
    .w_addr_i(tail_r),
    .w_data_i(data_i),
    .r_v_i(n_0_net_),
    .r_addr_i(head_r),
    .r_data_o(data_o)
  );


  always @(posedge clk_i) begin
    if(1'b1) begin
      full_r <= N14;
    end 
  end


  always @(posedge clk_i) begin
    if(N9) begin
      tail_r <= N10;
    end 
  end


  always @(posedge clk_i) begin
    if(N11) begin
      head_r <= N12;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      empty_r <= N13;
    end 
  end

  assign N9 = (N0)? 1'b1 : 
              (N1)? N5 : 1'b0;
  assign N0 = N3;
  assign N1 = N2;
  assign N10 = (N0)? 1'b0 : 
               (N1)? N4 : 1'b0;
  assign N11 = (N0)? 1'b1 : 
               (N1)? yumi_i : 1'b0;
  assign N12 = (N0)? 1'b0 : 
               (N1)? N6 : 1'b0;
  assign N13 = (N0)? 1'b1 : 
               (N1)? N7 : 1'b0;
  assign N14 = (N0)? 1'b0 : 
               (N1)? N8 : 1'b0;
  assign n_0_net_ = ~empty_r;
  assign v_o = ~empty_r;
  assign ready_o = ~full_r;
  assign enq_i = v_i & N15;
  assign N15 = ~full_r;
  assign n_cse_4 = ~enq_i;
  assign n_cse_6 = ~yumi_i;
  assign n_cse_7 = N17 & n_cse_6;
  assign N17 = N16 & enq_i;
  assign N16 = ~empty_r;
  assign N2 = ~reset_i;
  assign N3 = reset_i;
  assign N5 = enq_i;
  assign N4 = ~tail_r;
  assign N6 = ~head_r;
  assign N7 = N18 | N20;
  assign N18 = empty_r & n_cse_4;
  assign N20 = N19 & n_cse_4;
  assign N19 = N15 & yumi_i;
  assign N8 = n_cse_7 | N21;
  assign N21 = full_r & n_cse_6;

endmodule



module bsg_mux_one_hot_width_p9_els_p3
(
  data_i,
  sel_one_hot_i,
  data_o
);

  input [26:0] data_i;
  input [2:0] sel_one_hot_i;
  output [8:0] data_o;
  wire [8:0] data_o;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8;
  wire [26:0] data_masked;
  assign data_masked[8] = data_i[8] & sel_one_hot_i[0];
  assign data_masked[7] = data_i[7] & sel_one_hot_i[0];
  assign data_masked[6] = data_i[6] & sel_one_hot_i[0];
  assign data_masked[5] = data_i[5] & sel_one_hot_i[0];
  assign data_masked[4] = data_i[4] & sel_one_hot_i[0];
  assign data_masked[3] = data_i[3] & sel_one_hot_i[0];
  assign data_masked[2] = data_i[2] & sel_one_hot_i[0];
  assign data_masked[1] = data_i[1] & sel_one_hot_i[0];
  assign data_masked[0] = data_i[0] & sel_one_hot_i[0];
  assign data_masked[17] = data_i[17] & sel_one_hot_i[1];
  assign data_masked[16] = data_i[16] & sel_one_hot_i[1];
  assign data_masked[15] = data_i[15] & sel_one_hot_i[1];
  assign data_masked[14] = data_i[14] & sel_one_hot_i[1];
  assign data_masked[13] = data_i[13] & sel_one_hot_i[1];
  assign data_masked[12] = data_i[12] & sel_one_hot_i[1];
  assign data_masked[11] = data_i[11] & sel_one_hot_i[1];
  assign data_masked[10] = data_i[10] & sel_one_hot_i[1];
  assign data_masked[9] = data_i[9] & sel_one_hot_i[1];
  assign data_masked[26] = data_i[26] & sel_one_hot_i[2];
  assign data_masked[25] = data_i[25] & sel_one_hot_i[2];
  assign data_masked[24] = data_i[24] & sel_one_hot_i[2];
  assign data_masked[23] = data_i[23] & sel_one_hot_i[2];
  assign data_masked[22] = data_i[22] & sel_one_hot_i[2];
  assign data_masked[21] = data_i[21] & sel_one_hot_i[2];
  assign data_masked[20] = data_i[20] & sel_one_hot_i[2];
  assign data_masked[19] = data_i[19] & sel_one_hot_i[2];
  assign data_masked[18] = data_i[18] & sel_one_hot_i[2];
  assign data_o[0] = N0 | data_masked[0];
  assign N0 = data_masked[18] | data_masked[9];
  assign data_o[1] = N1 | data_masked[1];
  assign N1 = data_masked[19] | data_masked[10];
  assign data_o[2] = N2 | data_masked[2];
  assign N2 = data_masked[20] | data_masked[11];
  assign data_o[3] = N3 | data_masked[3];
  assign N3 = data_masked[21] | data_masked[12];
  assign data_o[4] = N4 | data_masked[4];
  assign N4 = data_masked[22] | data_masked[13];
  assign data_o[5] = N5 | data_masked[5];
  assign N5 = data_masked[23] | data_masked[14];
  assign data_o[6] = N6 | data_masked[6];
  assign N6 = data_masked[24] | data_masked[15];
  assign data_o[7] = N7 | data_masked[7];
  assign N7 = data_masked[25] | data_masked[16];
  assign data_o[8] = N8 | data_masked[8];
  assign N8 = data_masked[26] | data_masked[17];

endmodule



module bsg_mux_one_hot_width_p9_els_p5
(
  data_i,
  sel_one_hot_i,
  data_o
);

  input [44:0] data_i;
  input [4:0] sel_one_hot_i;
  output [8:0] data_o;
  wire [8:0] data_o;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,
  N22,N23,N24,N25,N26;
  wire [44:0] data_masked;
  assign data_masked[8] = data_i[8] & sel_one_hot_i[0];
  assign data_masked[7] = data_i[7] & sel_one_hot_i[0];
  assign data_masked[6] = data_i[6] & sel_one_hot_i[0];
  assign data_masked[5] = data_i[5] & sel_one_hot_i[0];
  assign data_masked[4] = data_i[4] & sel_one_hot_i[0];
  assign data_masked[3] = data_i[3] & sel_one_hot_i[0];
  assign data_masked[2] = data_i[2] & sel_one_hot_i[0];
  assign data_masked[1] = data_i[1] & sel_one_hot_i[0];
  assign data_masked[0] = data_i[0] & sel_one_hot_i[0];
  assign data_masked[17] = data_i[17] & sel_one_hot_i[1];
  assign data_masked[16] = data_i[16] & sel_one_hot_i[1];
  assign data_masked[15] = data_i[15] & sel_one_hot_i[1];
  assign data_masked[14] = data_i[14] & sel_one_hot_i[1];
  assign data_masked[13] = data_i[13] & sel_one_hot_i[1];
  assign data_masked[12] = data_i[12] & sel_one_hot_i[1];
  assign data_masked[11] = data_i[11] & sel_one_hot_i[1];
  assign data_masked[10] = data_i[10] & sel_one_hot_i[1];
  assign data_masked[9] = data_i[9] & sel_one_hot_i[1];
  assign data_masked[26] = data_i[26] & sel_one_hot_i[2];
  assign data_masked[25] = data_i[25] & sel_one_hot_i[2];
  assign data_masked[24] = data_i[24] & sel_one_hot_i[2];
  assign data_masked[23] = data_i[23] & sel_one_hot_i[2];
  assign data_masked[22] = data_i[22] & sel_one_hot_i[2];
  assign data_masked[21] = data_i[21] & sel_one_hot_i[2];
  assign data_masked[20] = data_i[20] & sel_one_hot_i[2];
  assign data_masked[19] = data_i[19] & sel_one_hot_i[2];
  assign data_masked[18] = data_i[18] & sel_one_hot_i[2];
  assign data_masked[35] = data_i[35] & sel_one_hot_i[3];
  assign data_masked[34] = data_i[34] & sel_one_hot_i[3];
  assign data_masked[33] = data_i[33] & sel_one_hot_i[3];
  assign data_masked[32] = data_i[32] & sel_one_hot_i[3];
  assign data_masked[31] = data_i[31] & sel_one_hot_i[3];
  assign data_masked[30] = data_i[30] & sel_one_hot_i[3];
  assign data_masked[29] = data_i[29] & sel_one_hot_i[3];
  assign data_masked[28] = data_i[28] & sel_one_hot_i[3];
  assign data_masked[27] = data_i[27] & sel_one_hot_i[3];
  assign data_masked[44] = data_i[44] & sel_one_hot_i[4];
  assign data_masked[43] = data_i[43] & sel_one_hot_i[4];
  assign data_masked[42] = data_i[42] & sel_one_hot_i[4];
  assign data_masked[41] = data_i[41] & sel_one_hot_i[4];
  assign data_masked[40] = data_i[40] & sel_one_hot_i[4];
  assign data_masked[39] = data_i[39] & sel_one_hot_i[4];
  assign data_masked[38] = data_i[38] & sel_one_hot_i[4];
  assign data_masked[37] = data_i[37] & sel_one_hot_i[4];
  assign data_masked[36] = data_i[36] & sel_one_hot_i[4];
  assign data_o[0] = N2 | data_masked[0];
  assign N2 = N1 | data_masked[9];
  assign N1 = N0 | data_masked[18];
  assign N0 = data_masked[36] | data_masked[27];
  assign data_o[1] = N5 | data_masked[1];
  assign N5 = N4 | data_masked[10];
  assign N4 = N3 | data_masked[19];
  assign N3 = data_masked[37] | data_masked[28];
  assign data_o[2] = N8 | data_masked[2];
  assign N8 = N7 | data_masked[11];
  assign N7 = N6 | data_masked[20];
  assign N6 = data_masked[38] | data_masked[29];
  assign data_o[3] = N11 | data_masked[3];
  assign N11 = N10 | data_masked[12];
  assign N10 = N9 | data_masked[21];
  assign N9 = data_masked[39] | data_masked[30];
  assign data_o[4] = N14 | data_masked[4];
  assign N14 = N13 | data_masked[13];
  assign N13 = N12 | data_masked[22];
  assign N12 = data_masked[40] | data_masked[31];
  assign data_o[5] = N17 | data_masked[5];
  assign N17 = N16 | data_masked[14];
  assign N16 = N15 | data_masked[23];
  assign N15 = data_masked[41] | data_masked[32];
  assign data_o[6] = N20 | data_masked[6];
  assign N20 = N19 | data_masked[15];
  assign N19 = N18 | data_masked[24];
  assign N18 = data_masked[42] | data_masked[33];
  assign data_o[7] = N23 | data_masked[7];
  assign N23 = N22 | data_masked[16];
  assign N22 = N21 | data_masked[25];
  assign N21 = data_masked[43] | data_masked[34];
  assign data_o[8] = N26 | data_masked[8];
  assign N26 = N25 | data_masked[17];
  assign N25 = N24 | data_masked[26];
  assign N24 = data_masked[44] | data_masked[35];

endmodule



module bsg_mux_one_hot_width_p9_els_p4
(
  data_i,
  sel_one_hot_i,
  data_o
);

  input [35:0] data_i;
  input [3:0] sel_one_hot_i;
  output [8:0] data_o;
  wire [8:0] data_o;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17;
  wire [35:0] data_masked;
  assign data_masked[8] = data_i[8] & sel_one_hot_i[0];
  assign data_masked[7] = data_i[7] & sel_one_hot_i[0];
  assign data_masked[6] = data_i[6] & sel_one_hot_i[0];
  assign data_masked[5] = data_i[5] & sel_one_hot_i[0];
  assign data_masked[4] = data_i[4] & sel_one_hot_i[0];
  assign data_masked[3] = data_i[3] & sel_one_hot_i[0];
  assign data_masked[2] = data_i[2] & sel_one_hot_i[0];
  assign data_masked[1] = data_i[1] & sel_one_hot_i[0];
  assign data_masked[0] = data_i[0] & sel_one_hot_i[0];
  assign data_masked[17] = data_i[17] & sel_one_hot_i[1];
  assign data_masked[16] = data_i[16] & sel_one_hot_i[1];
  assign data_masked[15] = data_i[15] & sel_one_hot_i[1];
  assign data_masked[14] = data_i[14] & sel_one_hot_i[1];
  assign data_masked[13] = data_i[13] & sel_one_hot_i[1];
  assign data_masked[12] = data_i[12] & sel_one_hot_i[1];
  assign data_masked[11] = data_i[11] & sel_one_hot_i[1];
  assign data_masked[10] = data_i[10] & sel_one_hot_i[1];
  assign data_masked[9] = data_i[9] & sel_one_hot_i[1];
  assign data_masked[26] = data_i[26] & sel_one_hot_i[2];
  assign data_masked[25] = data_i[25] & sel_one_hot_i[2];
  assign data_masked[24] = data_i[24] & sel_one_hot_i[2];
  assign data_masked[23] = data_i[23] & sel_one_hot_i[2];
  assign data_masked[22] = data_i[22] & sel_one_hot_i[2];
  assign data_masked[21] = data_i[21] & sel_one_hot_i[2];
  assign data_masked[20] = data_i[20] & sel_one_hot_i[2];
  assign data_masked[19] = data_i[19] & sel_one_hot_i[2];
  assign data_masked[18] = data_i[18] & sel_one_hot_i[2];
  assign data_masked[35] = data_i[35] & sel_one_hot_i[3];
  assign data_masked[34] = data_i[34] & sel_one_hot_i[3];
  assign data_masked[33] = data_i[33] & sel_one_hot_i[3];
  assign data_masked[32] = data_i[32] & sel_one_hot_i[3];
  assign data_masked[31] = data_i[31] & sel_one_hot_i[3];
  assign data_masked[30] = data_i[30] & sel_one_hot_i[3];
  assign data_masked[29] = data_i[29] & sel_one_hot_i[3];
  assign data_masked[28] = data_i[28] & sel_one_hot_i[3];
  assign data_masked[27] = data_i[27] & sel_one_hot_i[3];
  assign data_o[0] = N1 | data_masked[0];
  assign N1 = N0 | data_masked[9];
  assign N0 = data_masked[27] | data_masked[18];
  assign data_o[1] = N3 | data_masked[1];
  assign N3 = N2 | data_masked[10];
  assign N2 = data_masked[28] | data_masked[19];
  assign data_o[2] = N5 | data_masked[2];
  assign N5 = N4 | data_masked[11];
  assign N4 = data_masked[29] | data_masked[20];
  assign data_o[3] = N7 | data_masked[3];
  assign N7 = N6 | data_masked[12];
  assign N6 = data_masked[30] | data_masked[21];
  assign data_o[4] = N9 | data_masked[4];
  assign N9 = N8 | data_masked[13];
  assign N8 = data_masked[31] | data_masked[22];
  assign data_o[5] = N11 | data_masked[5];
  assign N11 = N10 | data_masked[14];
  assign N10 = data_masked[32] | data_masked[23];
  assign data_o[6] = N13 | data_masked[6];
  assign N13 = N12 | data_masked[15];
  assign N12 = data_masked[33] | data_masked[24];
  assign data_o[7] = N15 | data_masked[7];
  assign N15 = N14 | data_masked[16];
  assign N14 = data_masked[34] | data_masked[25];
  assign data_o[8] = N17 | data_masked[8];
  assign N17 = N16 | data_masked[17];
  assign N16 = data_masked[35] | data_masked[26];

endmodule



module bsg_mesh_router_9_4_5_0_00_1
(
  clk_i,
  reset_i,
  data_i,
  v_i,
  yumi_o,
  ready_i,
  data_o,
  v_o,
  my_x_i,
  my_y_i
);

  input [44:0] data_i;
  input [4:0] v_i;
  output [4:0] yumi_o;
  input [4:0] ready_i;
  output [44:0] data_o;
  output [4:0] v_o;
  input [3:0] my_x_i;
  input [4:0] my_y_i;
  input clk_i;
  input reset_i;
  wire [4:0] yumi_o,v_o;
  wire [44:0] data_o;
  wire W_gnt_e,W_gnt_p,W_gnt_s,E_gnt_w,E_gnt_p,E_gnt_s,N_gnt_s,N_gnt_e,N_gnt_w,N_gnt_p,
  S_gnt_n,S_gnt_e,S_gnt_w,S_gnt_p,P_gnt_s,P_gnt_n,P_gnt_e,P_gnt_w,P_gnt_p,N0,N1,
  N2,N3,N4,N5,N6,N7,N8,SV2V_UNCONNECTED_1,SV2V_UNCONNECTED_2,
  SV2V_UNCONNECTED_3,SV2V_UNCONNECTED_4,SV2V_UNCONNECTED_5,SV2V_UNCONNECTED_6,
  SV2V_UNCONNECTED_7,SV2V_UNCONNECTED_8,SV2V_UNCONNECTED_9,
  SV2V_UNCONNECTED_10,SV2V_UNCONNECTED_11;
  wire [24:0] req;

  bsg_mesh_router_dor_decoder_4_5_5_1
  dor_decoder
  (
    .clk_i(clk_i),
    .v_i(v_i),
    .x_dirs_i({ data_i[39:36], data_i[30:27], data_i[21:18], data_i[12:9], data_i[3:0] }),
    .y_dirs_i({ data_i[44:40], data_i[35:31], data_i[26:22], data_i[17:13], data_i[8:4] }),
    .my_x_i(my_x_i),
    .my_y_i(my_y_i),
    .req_o(req)
  );


  bsg_round_robin_arb_inputs_p3
  fi_west_rr_arb
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .grants_en_i(ready_i[1]),
    .reqs_i({ req[11:11], req[1:1], req[21:21] }),
    .grants_o({ W_gnt_e, W_gnt_p, W_gnt_s }),
    .v_o(v_o[1]),
    .tag_o({ SV2V_UNCONNECTED_1, SV2V_UNCONNECTED_2 }),
    .yumi_i(v_o[1])
  );


  bsg_round_robin_arb_inputs_p3
  fi_east_rr_arb
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .grants_en_i(ready_i[2]),
    .reqs_i({ req[7:7], req[2:2], req[22:22] }),
    .grants_o({ E_gnt_w, E_gnt_p, E_gnt_s }),
    .v_o(v_o[2]),
    .tag_o({ SV2V_UNCONNECTED_3, SV2V_UNCONNECTED_4 }),
    .yumi_i(v_o[2])
  );


  bsg_round_robin_arb_inputs_p4
  north_rr_arb
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .grants_en_i(ready_i[3]),
    .reqs_i({ req[23:23], req[13:13], req[8:8], req[3:3] }),
    .grants_o({ N_gnt_s, N_gnt_e, N_gnt_w, N_gnt_p }),
    .v_o(v_o[3]),
    .tag_o({ SV2V_UNCONNECTED_5, SV2V_UNCONNECTED_6 }),
    .yumi_i(v_o[3])
  );


  bsg_round_robin_arb_inputs_p4
  south_rr_arb
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .grants_en_i(ready_i[4]),
    .reqs_i({ req[19:19], req[14:14], req[9:9], req[4:4] }),
    .grants_o({ S_gnt_n, S_gnt_e, S_gnt_w, S_gnt_p }),
    .v_o(v_o[4]),
    .tag_o({ SV2V_UNCONNECTED_7, SV2V_UNCONNECTED_8 }),
    .yumi_i(v_o[4])
  );


  bsg_round_robin_arb_inputs_p5
  proc_rr_arb
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .grants_en_i(ready_i[0]),
    .reqs_i({ req[20:20], req[15:15], req[10:10], req[5:5], req[0:0] }),
    .grants_o({ P_gnt_s, P_gnt_n, P_gnt_e, P_gnt_w, P_gnt_p }),
    .v_o(v_o[0]),
    .tag_o({ SV2V_UNCONNECTED_9, SV2V_UNCONNECTED_10, SV2V_UNCONNECTED_11 }),
    .yumi_i(v_o[0])
  );


  bsg_mux_one_hot_width_p9_els_p3
  genblk3_mux_data_west
  (
    .data_i({ data_i[8:0], data_i[26:18], data_i[44:36] }),
    .sel_one_hot_i({ W_gnt_p, W_gnt_e, W_gnt_s }),
    .data_o(data_o[17:9])
  );


  bsg_mux_one_hot_width_p9_els_p3
  genblk3_mux_data_east
  (
    .data_i({ data_i[8:0], data_i[17:9], data_i[44:36] }),
    .sel_one_hot_i({ E_gnt_p, E_gnt_w, E_gnt_s }),
    .data_o(data_o[26:18])
  );


  bsg_mux_one_hot_width_p9_els_p5
  mux_data_proc
  (
    .data_i({ data_i[8:0], data_i[26:18], data_i[44:36], data_i[17:9], data_i[35:27] }),
    .sel_one_hot_i({ P_gnt_p, P_gnt_e, P_gnt_s, P_gnt_w, P_gnt_n }),
    .data_o(data_o[8:0])
  );


  bsg_mux_one_hot_width_p9_els_p4
  mux_data_north
  (
    .data_i({ data_i[8:0], data_i[26:18], data_i[44:36], data_i[17:9] }),
    .sel_one_hot_i({ N_gnt_p, N_gnt_e, N_gnt_s, N_gnt_w }),
    .data_o(data_o[35:27])
  );


  bsg_mux_one_hot_width_p9_els_p4
  mux_data_south
  (
    .data_i({ data_i[8:0], data_i[26:18], data_i[35:27], data_i[17:9] }),
    .sel_one_hot_i({ S_gnt_p, S_gnt_e, S_gnt_n, S_gnt_w }),
    .data_o(data_o[44:36])
  );

  assign yumi_o[1] = N1 | P_gnt_w;
  assign N1 = N0 | S_gnt_w;
  assign N0 = E_gnt_w | N_gnt_w;
  assign yumi_o[2] = N3 | P_gnt_e;
  assign N3 = N2 | S_gnt_e;
  assign N2 = W_gnt_e | N_gnt_e;
  assign yumi_o[0] = N6 | W_gnt_p;
  assign N6 = N5 | P_gnt_p;
  assign N5 = N4 | S_gnt_p;
  assign N4 = E_gnt_p | N_gnt_p;
  assign yumi_o[3] = S_gnt_n | P_gnt_n;
  assign yumi_o[4] = N8 | E_gnt_s;
  assign N8 = N7 | W_gnt_s;
  assign N7 = N_gnt_s | P_gnt_s;

endmodule



module bsg_mesh_router_buffered_9_4_5_0_00_1_00
(
  clk_i,
  reset_i,
  link_i,
  link_o,
  my_x_i,
  my_y_i
);

  input [54:0] link_i;
  output [54:0] link_o;
  input [3:0] my_x_i;
  input [4:0] my_y_i;
  input clk_i;
  input reset_i;
  wire [54:0] link_o;
  wire [4:0] fifo_valid,fifo_yumi;
  wire [44:0] fifo_data;

  bsg_two_fifo_width_p9
  rof_0__fi_twofer
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .ready_o(link_o[9]),
    .data_i(link_i[8:0]),
    .v_i(link_i[10]),
    .v_o(fifo_valid[0]),
    .data_o(fifo_data[8:0]),
    .yumi_i(fifo_yumi[0])
  );


  bsg_two_fifo_width_p9
  rof_1__fi_twofer
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .ready_o(link_o[20]),
    .data_i(link_i[19:11]),
    .v_i(link_i[21]),
    .v_o(fifo_valid[1]),
    .data_o(fifo_data[17:9]),
    .yumi_i(fifo_yumi[1])
  );


  bsg_two_fifo_width_p9
  rof_2__fi_twofer
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .ready_o(link_o[31]),
    .data_i(link_i[30:22]),
    .v_i(link_i[32]),
    .v_o(fifo_valid[2]),
    .data_o(fifo_data[26:18]),
    .yumi_i(fifo_yumi[2])
  );


  bsg_two_fifo_width_p9
  rof_3__fi_twofer
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .ready_o(link_o[42]),
    .data_i(link_i[41:33]),
    .v_i(link_i[43]),
    .v_o(fifo_valid[3]),
    .data_o(fifo_data[35:27]),
    .yumi_i(fifo_yumi[3])
  );


  bsg_two_fifo_width_p9
  rof_4__fi_twofer
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .ready_o(link_o[53]),
    .data_i(link_i[52:44]),
    .v_i(link_i[54]),
    .v_o(fifo_valid[4]),
    .data_o(fifo_data[44:36]),
    .yumi_i(fifo_yumi[4])
  );


  bsg_mesh_router_9_4_5_0_00_1
  bmr
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .data_i(fifo_data),
    .v_i(fifo_valid),
    .yumi_o(fifo_yumi),
    .ready_i({ link_i[53:53], link_i[42:42], link_i[31:31], link_i[20:20], link_i[9:9] }),
    .data_o({ link_o[52:44], link_o[41:33], link_o[30:22], link_o[19:11], link_o[8:0] }),
    .v_o({ link_o[54:54], link_o[43:43], link_o[32:32], link_o[21:21], link_o[10:10] }),
    .my_x_i(my_x_i),
    .my_y_i(my_y_i)
  );


endmodule



module bsg_manycore_mesh_node_4_5_32_20_0_0_0
(
  clk_i,
  reset_i,
  links_sif_i,
  links_sif_o,
  proc_link_sif_i,
  proc_link_sif_o,
  my_x_i,
  my_y_i
);

  input [355:0] links_sif_i;
  output [355:0] links_sif_o;
  input [88:0] proc_link_sif_i;
  output [88:0] proc_link_sif_o;
  input [3:0] my_x_i;
  input [4:0] my_y_i;
  input clk_i;
  input reset_i;
  wire [355:0] links_sif_o;
  wire [88:0] proc_link_sif_o;

  bsg_mesh_router_buffered_76_4_5_0_00_1_00
  rof_0__bmrb
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .link_i({ links_sif_i[355:278], links_sif_i[266:189], links_sif_i[177:100], links_sif_i[88:11], proc_link_sif_i[88:11] }),
    .link_o({ links_sif_o[355:278], links_sif_o[266:189], links_sif_o[177:100], links_sif_o[88:11], proc_link_sif_o[88:11] }),
    .my_x_i(my_x_i),
    .my_y_i(my_y_i)
  );


  bsg_mesh_router_buffered_9_4_5_0_00_1_00
  rof_1__bmrb
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .link_i({ links_sif_i[277:267], links_sif_i[188:178], links_sif_i[99:89], links_sif_i[10:0], proc_link_sif_i[10:0] }),
    .link_o({ links_sif_o[277:267], links_sif_o[188:178], links_sif_o[99:89], links_sif_o[10:0], proc_link_sif_o[10:0] }),
    .my_x_i(my_x_i),
    .my_y_i(my_y_i)
  );


endmodule



module bsg_circular_ptr_slots_p4_max_add_p1
(
  clk,
  reset_i,
  add_i,
  o
);

  input [0:0] add_i;
  output [1:0] o;
  input clk;
  input reset_i;
  wire N0,N1,N2,N3,N4,N5,N6,N7;
  wire [1:0] genblk1_genblk1_ptr_r_p1;
  reg [1:0] o;

  always @(posedge clk) begin
    if(N7) begin
      o[1] <= N4;
    end 
  end


  always @(posedge clk) begin
    if(N7) begin
      o[0] <= N3;
    end 
  end

  assign genblk1_genblk1_ptr_r_p1 = o + 1'b1;
  assign { N4, N3 } = (N0)? { 1'b0, 1'b0 } : 
                      (N1)? genblk1_genblk1_ptr_r_p1 : 1'b0;
  assign N0 = reset_i;
  assign N1 = N2;
  assign N2 = ~reset_i;
  assign N5 = ~add_i[0];
  assign N6 = N5 & N2;
  assign N7 = ~N6;

endmodule



module bsg_fifo_tracker_els_p4
(
  clk_i,
  reset_i,
  enq_i,
  deq_i,
  wptr_r_o,
  rptr_r_o,
  full_o,
  empty_o
);

  output [1:0] wptr_r_o;
  output [1:0] rptr_r_o;
  input clk_i;
  input reset_i;
  input enq_i;
  input deq_i;
  output full_o;
  output empty_o;
  wire [1:0] wptr_r_o,rptr_r_o;
  wire full_o,empty_o,N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,equal_ptrs;
  reg deq_r,enq_r;

  bsg_circular_ptr_slots_p4_max_add_p1
  rptr
  (
    .clk(clk_i),
    .reset_i(reset_i),
    .add_i(deq_i),
    .o(rptr_r_o)
  );


  bsg_circular_ptr_slots_p4_max_add_p1
  wptr
  (
    .clk(clk_i),
    .reset_i(reset_i),
    .add_i(enq_i),
    .o(wptr_r_o)
  );


  always @(posedge clk_i) begin
    if(N5) begin
      deq_r <= N7;
    end 
  end


  always @(posedge clk_i) begin
    if(N5) begin
      enq_r <= N6;
    end 
  end

  assign equal_ptrs = rptr_r_o == wptr_r_o;
  assign N5 = (N0)? 1'b1 : 
              (N9)? 1'b1 : 
              (N4)? 1'b0 : 1'b0;
  assign N0 = N2;
  assign N6 = (N0)? 1'b0 : 
              (N9)? enq_i : 1'b0;
  assign N7 = (N0)? 1'b1 : 
              (N9)? deq_i : 1'b0;
  assign N1 = enq_i | deq_i;
  assign N2 = reset_i;
  assign N3 = N1 | N2;
  assign N4 = ~N3;
  assign N8 = ~N2;
  assign N9 = N1 & N8;
  assign empty_o = equal_ptrs & deq_r;
  assign full_o = equal_ptrs & enq_r;

endmodule



module bsg_mem_1r1w_synth_width_p76_els_p4_read_write_same_addr_p0_harden_p0
(
  w_clk_i,
  w_reset_i,
  w_v_i,
  w_addr_i,
  w_data_i,
  r_v_i,
  r_addr_i,
  r_data_o
);

  input [1:0] w_addr_i;
  input [75:0] w_data_i;
  input [1:0] r_addr_i;
  output [75:0] r_data_o;
  input w_clk_i;
  input w_reset_i;
  input w_v_i;
  input r_v_i;
  wire [75:0] r_data_o;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20;
  reg [303:0] mem;
  assign r_data_o[75] = (N8)? mem[75] : 
                        (N10)? mem[151] : 
                        (N9)? mem[227] : 
                        (N11)? mem[303] : 1'b0;
  assign r_data_o[74] = (N8)? mem[74] : 
                        (N10)? mem[150] : 
                        (N9)? mem[226] : 
                        (N11)? mem[302] : 1'b0;
  assign r_data_o[73] = (N8)? mem[73] : 
                        (N10)? mem[149] : 
                        (N9)? mem[225] : 
                        (N11)? mem[301] : 1'b0;
  assign r_data_o[72] = (N8)? mem[72] : 
                        (N10)? mem[148] : 
                        (N9)? mem[224] : 
                        (N11)? mem[300] : 1'b0;
  assign r_data_o[71] = (N8)? mem[71] : 
                        (N10)? mem[147] : 
                        (N9)? mem[223] : 
                        (N11)? mem[299] : 1'b0;
  assign r_data_o[70] = (N8)? mem[70] : 
                        (N10)? mem[146] : 
                        (N9)? mem[222] : 
                        (N11)? mem[298] : 1'b0;
  assign r_data_o[69] = (N8)? mem[69] : 
                        (N10)? mem[145] : 
                        (N9)? mem[221] : 
                        (N11)? mem[297] : 1'b0;
  assign r_data_o[68] = (N8)? mem[68] : 
                        (N10)? mem[144] : 
                        (N9)? mem[220] : 
                        (N11)? mem[296] : 1'b0;
  assign r_data_o[67] = (N8)? mem[67] : 
                        (N10)? mem[143] : 
                        (N9)? mem[219] : 
                        (N11)? mem[295] : 1'b0;
  assign r_data_o[66] = (N8)? mem[66] : 
                        (N10)? mem[142] : 
                        (N9)? mem[218] : 
                        (N11)? mem[294] : 1'b0;
  assign r_data_o[65] = (N8)? mem[65] : 
                        (N10)? mem[141] : 
                        (N9)? mem[217] : 
                        (N11)? mem[293] : 1'b0;
  assign r_data_o[64] = (N8)? mem[64] : 
                        (N10)? mem[140] : 
                        (N9)? mem[216] : 
                        (N11)? mem[292] : 1'b0;
  assign r_data_o[63] = (N8)? mem[63] : 
                        (N10)? mem[139] : 
                        (N9)? mem[215] : 
                        (N11)? mem[291] : 1'b0;
  assign r_data_o[62] = (N8)? mem[62] : 
                        (N10)? mem[138] : 
                        (N9)? mem[214] : 
                        (N11)? mem[290] : 1'b0;
  assign r_data_o[61] = (N8)? mem[61] : 
                        (N10)? mem[137] : 
                        (N9)? mem[213] : 
                        (N11)? mem[289] : 1'b0;
  assign r_data_o[60] = (N8)? mem[60] : 
                        (N10)? mem[136] : 
                        (N9)? mem[212] : 
                        (N11)? mem[288] : 1'b0;
  assign r_data_o[59] = (N8)? mem[59] : 
                        (N10)? mem[135] : 
                        (N9)? mem[211] : 
                        (N11)? mem[287] : 1'b0;
  assign r_data_o[58] = (N8)? mem[58] : 
                        (N10)? mem[134] : 
                        (N9)? mem[210] : 
                        (N11)? mem[286] : 1'b0;
  assign r_data_o[57] = (N8)? mem[57] : 
                        (N10)? mem[133] : 
                        (N9)? mem[209] : 
                        (N11)? mem[285] : 1'b0;
  assign r_data_o[56] = (N8)? mem[56] : 
                        (N10)? mem[132] : 
                        (N9)? mem[208] : 
                        (N11)? mem[284] : 1'b0;
  assign r_data_o[55] = (N8)? mem[55] : 
                        (N10)? mem[131] : 
                        (N9)? mem[207] : 
                        (N11)? mem[283] : 1'b0;
  assign r_data_o[54] = (N8)? mem[54] : 
                        (N10)? mem[130] : 
                        (N9)? mem[206] : 
                        (N11)? mem[282] : 1'b0;
  assign r_data_o[53] = (N8)? mem[53] : 
                        (N10)? mem[129] : 
                        (N9)? mem[205] : 
                        (N11)? mem[281] : 1'b0;
  assign r_data_o[52] = (N8)? mem[52] : 
                        (N10)? mem[128] : 
                        (N9)? mem[204] : 
                        (N11)? mem[280] : 1'b0;
  assign r_data_o[51] = (N8)? mem[51] : 
                        (N10)? mem[127] : 
                        (N9)? mem[203] : 
                        (N11)? mem[279] : 1'b0;
  assign r_data_o[50] = (N8)? mem[50] : 
                        (N10)? mem[126] : 
                        (N9)? mem[202] : 
                        (N11)? mem[278] : 1'b0;
  assign r_data_o[49] = (N8)? mem[49] : 
                        (N10)? mem[125] : 
                        (N9)? mem[201] : 
                        (N11)? mem[277] : 1'b0;
  assign r_data_o[48] = (N8)? mem[48] : 
                        (N10)? mem[124] : 
                        (N9)? mem[200] : 
                        (N11)? mem[276] : 1'b0;
  assign r_data_o[47] = (N8)? mem[47] : 
                        (N10)? mem[123] : 
                        (N9)? mem[199] : 
                        (N11)? mem[275] : 1'b0;
  assign r_data_o[46] = (N8)? mem[46] : 
                        (N10)? mem[122] : 
                        (N9)? mem[198] : 
                        (N11)? mem[274] : 1'b0;
  assign r_data_o[45] = (N8)? mem[45] : 
                        (N10)? mem[121] : 
                        (N9)? mem[197] : 
                        (N11)? mem[273] : 1'b0;
  assign r_data_o[44] = (N8)? mem[44] : 
                        (N10)? mem[120] : 
                        (N9)? mem[196] : 
                        (N11)? mem[272] : 1'b0;
  assign r_data_o[43] = (N8)? mem[43] : 
                        (N10)? mem[119] : 
                        (N9)? mem[195] : 
                        (N11)? mem[271] : 1'b0;
  assign r_data_o[42] = (N8)? mem[42] : 
                        (N10)? mem[118] : 
                        (N9)? mem[194] : 
                        (N11)? mem[270] : 1'b0;
  assign r_data_o[41] = (N8)? mem[41] : 
                        (N10)? mem[117] : 
                        (N9)? mem[193] : 
                        (N11)? mem[269] : 1'b0;
  assign r_data_o[40] = (N8)? mem[40] : 
                        (N10)? mem[116] : 
                        (N9)? mem[192] : 
                        (N11)? mem[268] : 1'b0;
  assign r_data_o[39] = (N8)? mem[39] : 
                        (N10)? mem[115] : 
                        (N9)? mem[191] : 
                        (N11)? mem[267] : 1'b0;
  assign r_data_o[38] = (N8)? mem[38] : 
                        (N10)? mem[114] : 
                        (N9)? mem[190] : 
                        (N11)? mem[266] : 1'b0;
  assign r_data_o[37] = (N8)? mem[37] : 
                        (N10)? mem[113] : 
                        (N9)? mem[189] : 
                        (N11)? mem[265] : 1'b0;
  assign r_data_o[36] = (N8)? mem[36] : 
                        (N10)? mem[112] : 
                        (N9)? mem[188] : 
                        (N11)? mem[264] : 1'b0;
  assign r_data_o[35] = (N8)? mem[35] : 
                        (N10)? mem[111] : 
                        (N9)? mem[187] : 
                        (N11)? mem[263] : 1'b0;
  assign r_data_o[34] = (N8)? mem[34] : 
                        (N10)? mem[110] : 
                        (N9)? mem[186] : 
                        (N11)? mem[262] : 1'b0;
  assign r_data_o[33] = (N8)? mem[33] : 
                        (N10)? mem[109] : 
                        (N9)? mem[185] : 
                        (N11)? mem[261] : 1'b0;
  assign r_data_o[32] = (N8)? mem[32] : 
                        (N10)? mem[108] : 
                        (N9)? mem[184] : 
                        (N11)? mem[260] : 1'b0;
  assign r_data_o[31] = (N8)? mem[31] : 
                        (N10)? mem[107] : 
                        (N9)? mem[183] : 
                        (N11)? mem[259] : 1'b0;
  assign r_data_o[30] = (N8)? mem[30] : 
                        (N10)? mem[106] : 
                        (N9)? mem[182] : 
                        (N11)? mem[258] : 1'b0;
  assign r_data_o[29] = (N8)? mem[29] : 
                        (N10)? mem[105] : 
                        (N9)? mem[181] : 
                        (N11)? mem[257] : 1'b0;
  assign r_data_o[28] = (N8)? mem[28] : 
                        (N10)? mem[104] : 
                        (N9)? mem[180] : 
                        (N11)? mem[256] : 1'b0;
  assign r_data_o[27] = (N8)? mem[27] : 
                        (N10)? mem[103] : 
                        (N9)? mem[179] : 
                        (N11)? mem[255] : 1'b0;
  assign r_data_o[26] = (N8)? mem[26] : 
                        (N10)? mem[102] : 
                        (N9)? mem[178] : 
                        (N11)? mem[254] : 1'b0;
  assign r_data_o[25] = (N8)? mem[25] : 
                        (N10)? mem[101] : 
                        (N9)? mem[177] : 
                        (N11)? mem[253] : 1'b0;
  assign r_data_o[24] = (N8)? mem[24] : 
                        (N10)? mem[100] : 
                        (N9)? mem[176] : 
                        (N11)? mem[252] : 1'b0;
  assign r_data_o[23] = (N8)? mem[23] : 
                        (N10)? mem[99] : 
                        (N9)? mem[175] : 
                        (N11)? mem[251] : 1'b0;
  assign r_data_o[22] = (N8)? mem[22] : 
                        (N10)? mem[98] : 
                        (N9)? mem[174] : 
                        (N11)? mem[250] : 1'b0;
  assign r_data_o[21] = (N8)? mem[21] : 
                        (N10)? mem[97] : 
                        (N9)? mem[173] : 
                        (N11)? mem[249] : 1'b0;
  assign r_data_o[20] = (N8)? mem[20] : 
                        (N10)? mem[96] : 
                        (N9)? mem[172] : 
                        (N11)? mem[248] : 1'b0;
  assign r_data_o[19] = (N8)? mem[19] : 
                        (N10)? mem[95] : 
                        (N9)? mem[171] : 
                        (N11)? mem[247] : 1'b0;
  assign r_data_o[18] = (N8)? mem[18] : 
                        (N10)? mem[94] : 
                        (N9)? mem[170] : 
                        (N11)? mem[246] : 1'b0;
  assign r_data_o[17] = (N8)? mem[17] : 
                        (N10)? mem[93] : 
                        (N9)? mem[169] : 
                        (N11)? mem[245] : 1'b0;
  assign r_data_o[16] = (N8)? mem[16] : 
                        (N10)? mem[92] : 
                        (N9)? mem[168] : 
                        (N11)? mem[244] : 1'b0;
  assign r_data_o[15] = (N8)? mem[15] : 
                        (N10)? mem[91] : 
                        (N9)? mem[167] : 
                        (N11)? mem[243] : 1'b0;
  assign r_data_o[14] = (N8)? mem[14] : 
                        (N10)? mem[90] : 
                        (N9)? mem[166] : 
                        (N11)? mem[242] : 1'b0;
  assign r_data_o[13] = (N8)? mem[13] : 
                        (N10)? mem[89] : 
                        (N9)? mem[165] : 
                        (N11)? mem[241] : 1'b0;
  assign r_data_o[12] = (N8)? mem[12] : 
                        (N10)? mem[88] : 
                        (N9)? mem[164] : 
                        (N11)? mem[240] : 1'b0;
  assign r_data_o[11] = (N8)? mem[11] : 
                        (N10)? mem[87] : 
                        (N9)? mem[163] : 
                        (N11)? mem[239] : 1'b0;
  assign r_data_o[10] = (N8)? mem[10] : 
                        (N10)? mem[86] : 
                        (N9)? mem[162] : 
                        (N11)? mem[238] : 1'b0;
  assign r_data_o[9] = (N8)? mem[9] : 
                       (N10)? mem[85] : 
                       (N9)? mem[161] : 
                       (N11)? mem[237] : 1'b0;
  assign r_data_o[8] = (N8)? mem[8] : 
                       (N10)? mem[84] : 
                       (N9)? mem[160] : 
                       (N11)? mem[236] : 1'b0;
  assign r_data_o[7] = (N8)? mem[7] : 
                       (N10)? mem[83] : 
                       (N9)? mem[159] : 
                       (N11)? mem[235] : 1'b0;
  assign r_data_o[6] = (N8)? mem[6] : 
                       (N10)? mem[82] : 
                       (N9)? mem[158] : 
                       (N11)? mem[234] : 1'b0;
  assign r_data_o[5] = (N8)? mem[5] : 
                       (N10)? mem[81] : 
                       (N9)? mem[157] : 
                       (N11)? mem[233] : 1'b0;
  assign r_data_o[4] = (N8)? mem[4] : 
                       (N10)? mem[80] : 
                       (N9)? mem[156] : 
                       (N11)? mem[232] : 1'b0;
  assign r_data_o[3] = (N8)? mem[3] : 
                       (N10)? mem[79] : 
                       (N9)? mem[155] : 
                       (N11)? mem[231] : 1'b0;
  assign r_data_o[2] = (N8)? mem[2] : 
                       (N10)? mem[78] : 
                       (N9)? mem[154] : 
                       (N11)? mem[230] : 1'b0;
  assign r_data_o[1] = (N8)? mem[1] : 
                       (N10)? mem[77] : 
                       (N9)? mem[153] : 
                       (N11)? mem[229] : 1'b0;
  assign r_data_o[0] = (N8)? mem[0] : 
                       (N10)? mem[76] : 
                       (N9)? mem[152] : 
                       (N11)? mem[228] : 1'b0;

  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[303] <= w_data_i[75];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[302] <= w_data_i[74];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[301] <= w_data_i[73];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[300] <= w_data_i[72];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[299] <= w_data_i[71];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[298] <= w_data_i[70];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[297] <= w_data_i[69];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[296] <= w_data_i[68];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[295] <= w_data_i[67];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[294] <= w_data_i[66];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[293] <= w_data_i[65];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[292] <= w_data_i[64];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[291] <= w_data_i[63];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[290] <= w_data_i[62];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[289] <= w_data_i[61];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[288] <= w_data_i[60];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[287] <= w_data_i[59];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[286] <= w_data_i[58];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[285] <= w_data_i[57];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[284] <= w_data_i[56];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[283] <= w_data_i[55];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[282] <= w_data_i[54];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[281] <= w_data_i[53];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[280] <= w_data_i[52];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[279] <= w_data_i[51];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[278] <= w_data_i[50];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[277] <= w_data_i[49];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[276] <= w_data_i[48];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[275] <= w_data_i[47];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[274] <= w_data_i[46];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[273] <= w_data_i[45];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[272] <= w_data_i[44];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[271] <= w_data_i[43];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[270] <= w_data_i[42];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[269] <= w_data_i[41];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[268] <= w_data_i[40];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[267] <= w_data_i[39];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[266] <= w_data_i[38];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[265] <= w_data_i[37];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[264] <= w_data_i[36];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[263] <= w_data_i[35];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[262] <= w_data_i[34];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[261] <= w_data_i[33];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[260] <= w_data_i[32];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[259] <= w_data_i[31];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[258] <= w_data_i[30];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[257] <= w_data_i[29];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[256] <= w_data_i[28];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[255] <= w_data_i[27];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[254] <= w_data_i[26];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[253] <= w_data_i[25];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[252] <= w_data_i[24];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[251] <= w_data_i[23];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[250] <= w_data_i[22];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[249] <= w_data_i[21];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[248] <= w_data_i[20];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[247] <= w_data_i[19];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[246] <= w_data_i[18];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[245] <= w_data_i[17];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[244] <= w_data_i[16];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[243] <= w_data_i[15];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[242] <= w_data_i[14];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[241] <= w_data_i[13];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[240] <= w_data_i[12];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[239] <= w_data_i[11];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[238] <= w_data_i[10];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[237] <= w_data_i[9];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[236] <= w_data_i[8];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[235] <= w_data_i[7];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[234] <= w_data_i[6];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[233] <= w_data_i[5];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[232] <= w_data_i[4];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[231] <= w_data_i[3];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[230] <= w_data_i[2];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[229] <= w_data_i[1];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N20) begin
      mem[228] <= w_data_i[0];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[227] <= w_data_i[75];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[226] <= w_data_i[74];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[225] <= w_data_i[73];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[224] <= w_data_i[72];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[223] <= w_data_i[71];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[222] <= w_data_i[70];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[221] <= w_data_i[69];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[220] <= w_data_i[68];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[219] <= w_data_i[67];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[218] <= w_data_i[66];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[217] <= w_data_i[65];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[216] <= w_data_i[64];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[215] <= w_data_i[63];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[214] <= w_data_i[62];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[213] <= w_data_i[61];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[212] <= w_data_i[60];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[211] <= w_data_i[59];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[210] <= w_data_i[58];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[209] <= w_data_i[57];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[208] <= w_data_i[56];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[207] <= w_data_i[55];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[206] <= w_data_i[54];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[205] <= w_data_i[53];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[204] <= w_data_i[52];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[203] <= w_data_i[51];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[202] <= w_data_i[50];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[201] <= w_data_i[49];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[200] <= w_data_i[48];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[199] <= w_data_i[47];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[198] <= w_data_i[46];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[197] <= w_data_i[45];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[196] <= w_data_i[44];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[195] <= w_data_i[43];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[194] <= w_data_i[42];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[193] <= w_data_i[41];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[192] <= w_data_i[40];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[191] <= w_data_i[39];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[190] <= w_data_i[38];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[189] <= w_data_i[37];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[188] <= w_data_i[36];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[187] <= w_data_i[35];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[186] <= w_data_i[34];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[185] <= w_data_i[33];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[184] <= w_data_i[32];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[183] <= w_data_i[31];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[182] <= w_data_i[30];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[181] <= w_data_i[29];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[180] <= w_data_i[28];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[179] <= w_data_i[27];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[178] <= w_data_i[26];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[177] <= w_data_i[25];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[176] <= w_data_i[24];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[175] <= w_data_i[23];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[174] <= w_data_i[22];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[173] <= w_data_i[21];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[172] <= w_data_i[20];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[171] <= w_data_i[19];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[170] <= w_data_i[18];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[169] <= w_data_i[17];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[168] <= w_data_i[16];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[167] <= w_data_i[15];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[166] <= w_data_i[14];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[165] <= w_data_i[13];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[164] <= w_data_i[12];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[163] <= w_data_i[11];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[162] <= w_data_i[10];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[161] <= w_data_i[9];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[160] <= w_data_i[8];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[159] <= w_data_i[7];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[158] <= w_data_i[6];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[157] <= w_data_i[5];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[156] <= w_data_i[4];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[155] <= w_data_i[3];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[154] <= w_data_i[2];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[153] <= w_data_i[1];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N19) begin
      mem[152] <= w_data_i[0];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[151] <= w_data_i[75];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[150] <= w_data_i[74];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[149] <= w_data_i[73];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[148] <= w_data_i[72];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[147] <= w_data_i[71];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[146] <= w_data_i[70];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[145] <= w_data_i[69];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[144] <= w_data_i[68];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[143] <= w_data_i[67];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[142] <= w_data_i[66];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[141] <= w_data_i[65];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[140] <= w_data_i[64];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[139] <= w_data_i[63];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[138] <= w_data_i[62];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[137] <= w_data_i[61];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[136] <= w_data_i[60];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[135] <= w_data_i[59];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[134] <= w_data_i[58];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[133] <= w_data_i[57];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[132] <= w_data_i[56];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[131] <= w_data_i[55];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[130] <= w_data_i[54];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[129] <= w_data_i[53];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[128] <= w_data_i[52];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[127] <= w_data_i[51];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[126] <= w_data_i[50];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[125] <= w_data_i[49];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[124] <= w_data_i[48];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[123] <= w_data_i[47];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[122] <= w_data_i[46];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[121] <= w_data_i[45];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[120] <= w_data_i[44];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[119] <= w_data_i[43];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[118] <= w_data_i[42];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[117] <= w_data_i[41];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[116] <= w_data_i[40];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[115] <= w_data_i[39];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[114] <= w_data_i[38];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[113] <= w_data_i[37];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[112] <= w_data_i[36];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[111] <= w_data_i[35];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[110] <= w_data_i[34];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[109] <= w_data_i[33];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[108] <= w_data_i[32];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[107] <= w_data_i[31];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[106] <= w_data_i[30];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[105] <= w_data_i[29];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[104] <= w_data_i[28];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[103] <= w_data_i[27];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[102] <= w_data_i[26];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[101] <= w_data_i[25];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[100] <= w_data_i[24];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[99] <= w_data_i[23];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[98] <= w_data_i[22];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[97] <= w_data_i[21];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[96] <= w_data_i[20];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[95] <= w_data_i[19];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[94] <= w_data_i[18];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[93] <= w_data_i[17];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[92] <= w_data_i[16];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[91] <= w_data_i[15];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[90] <= w_data_i[14];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[89] <= w_data_i[13];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[88] <= w_data_i[12];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[87] <= w_data_i[11];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[86] <= w_data_i[10];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[85] <= w_data_i[9];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[84] <= w_data_i[8];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[83] <= w_data_i[7];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[82] <= w_data_i[6];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[81] <= w_data_i[5];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[80] <= w_data_i[4];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[79] <= w_data_i[3];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[78] <= w_data_i[2];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[77] <= w_data_i[1];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N18) begin
      mem[76] <= w_data_i[0];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[75] <= w_data_i[75];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[74] <= w_data_i[74];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[73] <= w_data_i[73];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[72] <= w_data_i[72];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[71] <= w_data_i[71];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[70] <= w_data_i[70];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[69] <= w_data_i[69];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[68] <= w_data_i[68];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[67] <= w_data_i[67];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[66] <= w_data_i[66];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[65] <= w_data_i[65];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[64] <= w_data_i[64];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[63] <= w_data_i[63];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[62] <= w_data_i[62];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[61] <= w_data_i[61];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[60] <= w_data_i[60];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[59] <= w_data_i[59];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[58] <= w_data_i[58];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[57] <= w_data_i[57];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[56] <= w_data_i[56];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[55] <= w_data_i[55];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[54] <= w_data_i[54];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[53] <= w_data_i[53];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[52] <= w_data_i[52];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[51] <= w_data_i[51];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[50] <= w_data_i[50];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[49] <= w_data_i[49];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[48] <= w_data_i[48];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[47] <= w_data_i[47];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[46] <= w_data_i[46];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[45] <= w_data_i[45];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[44] <= w_data_i[44];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[43] <= w_data_i[43];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[42] <= w_data_i[42];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[41] <= w_data_i[41];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[40] <= w_data_i[40];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[39] <= w_data_i[39];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[38] <= w_data_i[38];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[37] <= w_data_i[37];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[36] <= w_data_i[36];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[35] <= w_data_i[35];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[34] <= w_data_i[34];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[33] <= w_data_i[33];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[32] <= w_data_i[32];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[31] <= w_data_i[31];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[30] <= w_data_i[30];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[29] <= w_data_i[29];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[28] <= w_data_i[28];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[27] <= w_data_i[27];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[26] <= w_data_i[26];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[25] <= w_data_i[25];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[24] <= w_data_i[24];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[23] <= w_data_i[23];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[22] <= w_data_i[22];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[21] <= w_data_i[21];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[20] <= w_data_i[20];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[19] <= w_data_i[19];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[18] <= w_data_i[18];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[17] <= w_data_i[17];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[16] <= w_data_i[16];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[15] <= w_data_i[15];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[14] <= w_data_i[14];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[13] <= w_data_i[13];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[12] <= w_data_i[12];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[11] <= w_data_i[11];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[10] <= w_data_i[10];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[9] <= w_data_i[9];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[8] <= w_data_i[8];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[7] <= w_data_i[7];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[6] <= w_data_i[6];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[5] <= w_data_i[5];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[4] <= w_data_i[4];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[3] <= w_data_i[3];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[2] <= w_data_i[2];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[1] <= w_data_i[1];
    end 
  end


  always @(posedge w_clk_i) begin
    if(N17) begin
      mem[0] <= w_data_i[0];
    end 
  end

  assign N16 = w_addr_i[0] & w_addr_i[1];
  assign N15 = N0 & w_addr_i[1];
  assign N0 = ~w_addr_i[0];
  assign N14 = w_addr_i[0] & N1;
  assign N1 = ~w_addr_i[1];
  assign N13 = N2 & N3;
  assign N2 = ~w_addr_i[0];
  assign N3 = ~w_addr_i[1];
  assign { N20, N19, N18, N17 } = (N4)? { N16, N15, N14, N13 } : 
                                  (N5)? { 1'b0, 1'b0, 1'b0, 1'b0 } : 1'b0;
  assign N4 = w_v_i;
  assign N5 = N12;
  assign N6 = ~r_addr_i[0];
  assign N7 = ~r_addr_i[1];
  assign N8 = N6 & N7;
  assign N9 = N6 & r_addr_i[1];
  assign N10 = r_addr_i[0] & N7;
  assign N11 = r_addr_i[0] & r_addr_i[1];
  assign N12 = ~w_v_i;

endmodule



module bsg_mem_1r1w_width_p76_els_p4_read_write_same_addr_p0
(
  w_clk_i,
  w_reset_i,
  w_v_i,
  w_addr_i,
  w_data_i,
  r_v_i,
  r_addr_i,
  r_data_o
);

  input [1:0] w_addr_i;
  input [75:0] w_data_i;
  input [1:0] r_addr_i;
  output [75:0] r_data_o;
  input w_clk_i;
  input w_reset_i;
  input w_v_i;
  input r_v_i;
  wire [75:0] r_data_o;

  bsg_mem_1r1w_synth_width_p76_els_p4_read_write_same_addr_p0_harden_p0
  synth
  (
    .w_clk_i(w_clk_i),
    .w_reset_i(w_reset_i),
    .w_v_i(w_v_i),
    .w_addr_i(w_addr_i),
    .w_data_i(w_data_i),
    .r_v_i(r_v_i),
    .r_addr_i(r_addr_i),
    .r_data_o(r_data_o)
  );


endmodule



module bsg_fifo_1r1w_small_width_p76_els_p4
(
  clk_i,
  reset_i,
  v_i,
  ready_o,
  data_i,
  v_o,
  data_o,
  yumi_i
);

  input [75:0] data_i;
  output [75:0] data_o;
  input clk_i;
  input reset_i;
  input v_i;
  input yumi_i;
  output ready_o;
  output v_o;
  wire [75:0] data_o;
  wire ready_o,v_o,enque,full,empty,N0,N1;
  wire [1:0] wptr_r,rptr_r;

  bsg_fifo_tracker_els_p4
  ft
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .enq_i(enque),
    .deq_i(yumi_i),
    .wptr_r_o(wptr_r),
    .rptr_r_o(rptr_r),
    .full_o(full),
    .empty_o(empty)
  );


  bsg_mem_1r1w_width_p76_els_p4_read_write_same_addr_p0
  mem_1r1w
  (
    .w_clk_i(clk_i),
    .w_reset_i(reset_i),
    .w_v_i(enque),
    .w_addr_i(wptr_r),
    .w_data_i(data_i),
    .r_v_i(v_o),
    .r_addr_i(rptr_r),
    .r_data_o(data_o)
  );

  assign enque = v_i & ready_o;
  assign ready_o = N0 & N1;
  assign N0 = ~full;
  assign N1 = ~reset_i;
  assign v_o = ~empty;

endmodule



module bsg_manycore_endpoint_x_cord_width_p4_y_cord_width_p5_fifo_els_p4_data_width_p32_addr_width_p20
(
  clk_i,
  reset_i,
  link_sif_i,
  link_sif_o,
  fifo_data_o,
  fifo_v_o,
  fifo_yumi_i,
  out_packet_i,
  out_v_i,
  out_ready_o,
  credit_v_r_o,
  in_fifo_full_o
);

  input [88:0] link_sif_i;
  output [88:0] link_sif_o;
  output [75:0] fifo_data_o;
  input [75:0] out_packet_i;
  input clk_i;
  input reset_i;
  input fifo_yumi_i;
  input out_v_i;
  output fifo_v_o;
  output out_ready_o;
  output credit_v_r_o;
  output in_fifo_full_o;
  wire [88:0] link_sif_o;
  wire [75:0] fifo_data_o;
  wire fifo_v_o,out_ready_o,in_fifo_full_o,out_v_i,fifo_yumi_i,fifo_v;
  reg credit_v_r_o;
  assign link_sif_o[9] = 1'b1;
  assign out_ready_o = link_sif_i[87];
  assign link_sif_o[88] = out_v_i;
  assign link_sif_o[86] = out_packet_i[75];
  assign link_sif_o[85] = out_packet_i[74];
  assign link_sif_o[84] = out_packet_i[73];
  assign link_sif_o[83] = out_packet_i[72];
  assign link_sif_o[82] = out_packet_i[71];
  assign link_sif_o[81] = out_packet_i[70];
  assign link_sif_o[80] = out_packet_i[69];
  assign link_sif_o[79] = out_packet_i[68];
  assign link_sif_o[78] = out_packet_i[67];
  assign link_sif_o[77] = out_packet_i[66];
  assign link_sif_o[76] = out_packet_i[65];
  assign link_sif_o[75] = out_packet_i[64];
  assign link_sif_o[74] = out_packet_i[63];
  assign link_sif_o[73] = out_packet_i[62];
  assign link_sif_o[72] = out_packet_i[61];
  assign link_sif_o[71] = out_packet_i[60];
  assign link_sif_o[70] = out_packet_i[59];
  assign link_sif_o[69] = out_packet_i[58];
  assign link_sif_o[68] = out_packet_i[57];
  assign link_sif_o[67] = out_packet_i[56];
  assign link_sif_o[66] = out_packet_i[55];
  assign link_sif_o[65] = out_packet_i[54];
  assign link_sif_o[64] = out_packet_i[53];
  assign link_sif_o[63] = out_packet_i[52];
  assign link_sif_o[62] = out_packet_i[51];
  assign link_sif_o[61] = out_packet_i[50];
  assign link_sif_o[60] = out_packet_i[49];
  assign link_sif_o[59] = out_packet_i[48];
  assign link_sif_o[58] = out_packet_i[47];
  assign link_sif_o[57] = out_packet_i[46];
  assign link_sif_o[56] = out_packet_i[45];
  assign link_sif_o[55] = out_packet_i[44];
  assign link_sif_o[54] = out_packet_i[43];
  assign link_sif_o[53] = out_packet_i[42];
  assign link_sif_o[52] = out_packet_i[41];
  assign link_sif_o[51] = out_packet_i[40];
  assign link_sif_o[50] = out_packet_i[39];
  assign link_sif_o[49] = out_packet_i[38];
  assign link_sif_o[48] = out_packet_i[37];
  assign link_sif_o[47] = out_packet_i[36];
  assign link_sif_o[46] = out_packet_i[35];
  assign link_sif_o[45] = out_packet_i[34];
  assign link_sif_o[44] = out_packet_i[33];
  assign link_sif_o[43] = out_packet_i[32];
  assign link_sif_o[42] = out_packet_i[31];
  assign link_sif_o[41] = out_packet_i[30];
  assign link_sif_o[40] = out_packet_i[29];
  assign link_sif_o[39] = out_packet_i[28];
  assign link_sif_o[38] = out_packet_i[27];
  assign link_sif_o[37] = out_packet_i[26];
  assign link_sif_o[36] = out_packet_i[25];
  assign link_sif_o[35] = out_packet_i[24];
  assign link_sif_o[34] = out_packet_i[23];
  assign link_sif_o[33] = out_packet_i[22];
  assign link_sif_o[32] = out_packet_i[21];
  assign link_sif_o[31] = out_packet_i[20];
  assign link_sif_o[30] = out_packet_i[19];
  assign link_sif_o[29] = out_packet_i[18];
  assign link_sif_o[28] = out_packet_i[17];
  assign link_sif_o[27] = out_packet_i[16];
  assign link_sif_o[26] = out_packet_i[15];
  assign link_sif_o[25] = out_packet_i[14];
  assign link_sif_o[24] = out_packet_i[13];
  assign link_sif_o[23] = out_packet_i[12];
  assign link_sif_o[22] = out_packet_i[11];
  assign link_sif_o[21] = out_packet_i[10];
  assign link_sif_o[20] = out_packet_i[9];
  assign link_sif_o[19] = out_packet_i[8];
  assign link_sif_o[18] = out_packet_i[7];
  assign link_sif_o[17] = out_packet_i[6];
  assign link_sif_o[16] = out_packet_i[5];
  assign link_sif_o[15] = out_packet_i[4];
  assign link_sif_o[14] = out_packet_i[3];
  assign link_sif_o[13] = out_packet_i[2];
  assign link_sif_o[12] = out_packet_i[1];
  assign link_sif_o[11] = out_packet_i[0];
  assign link_sif_o[10] = fifo_yumi_i;
  assign link_sif_o[8] = fifo_data_o[17];
  assign link_sif_o[7] = fifo_data_o[16];
  assign link_sif_o[6] = fifo_data_o[15];
  assign link_sif_o[5] = fifo_data_o[14];
  assign link_sif_o[4] = fifo_data_o[13];
  assign link_sif_o[3] = fifo_data_o[12];
  assign link_sif_o[2] = fifo_data_o[11];
  assign link_sif_o[1] = fifo_data_o[10];
  assign link_sif_o[0] = fifo_data_o[9];

  bsg_fifo_1r1w_small_width_p76_els_p4
  fifo
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .v_i(link_sif_i[88]),
    .ready_o(link_sif_o[87]),
    .data_i(link_sif_i[86:11]),
    .v_o(fifo_v),
    .data_o(fifo_data_o),
    .yumi_i(fifo_yumi_i)
  );


  always @(posedge clk_i) begin
    if(1'b1) begin
      credit_v_r_o <= link_sif_i[10];
    end 
  end

  assign fifo_v_o = fifo_v & link_sif_i[9];
  assign in_fifo_full_o = ~link_sif_o[87];

endmodule



module bsg_counter_up_down_max_val_p200_init_val_p200
(
  clk_i,
  reset_i,
  up_i,
  down_i,
  count_o
);

  output [7:0] count_o;
  input clk_i;
  input reset_i;
  input up_i;
  input down_i;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,
  N22,N23,N24,N25,N26;
  reg [7:0] count_o;

  always @(posedge clk_i) begin
    if(1'b1) begin
      count_o[7] <= N26;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      count_o[6] <= N25;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      count_o[5] <= N24;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      count_o[4] <= N23;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      count_o[3] <= N22;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      count_o[2] <= N21;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      count_o[1] <= N20;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      count_o[0] <= N19;
    end 
  end

  assign { N10, N9, N8, N7, N6, N5, N4, N3 } = count_o - down_i;
  assign { N18, N17, N16, N15, N14, N13, N12, N11 } = { N10, N9, N8, N7, N6, N5, N4, N3 } + up_i;
  assign { N26, N25, N24, N23, N22, N21, N20, N19 } = (N0)? { 1'b1, 1'b1, 1'b0, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0 } : 
                                                      (N1)? { N18, N17, N16, N15, N14, N13, N12, N11 } : 1'b0;
  assign N0 = reset_i;
  assign N1 = N2;
  assign N2 = ~reset_i;

endmodule



module bsg_manycore_pkt_decode_x_cord_width_p4_y_cord_width_p5_data_width_p32_addr_width_p20
(
  v_i,
  data_i,
  pkt_freeze_o,
  pkt_unfreeze_o,
  pkt_arb_cfg_o,
  pkt_unknown_o,
  pkt_remote_store_o,
  data_o,
  addr_o,
  mask_o
);

  input [75:0] data_i;
  output [31:0] data_o;
  output [19:0] addr_o;
  output [3:0] mask_o;
  input v_i;
  output pkt_freeze_o;
  output pkt_unfreeze_o;
  output pkt_arb_cfg_o;
  output pkt_unknown_o;
  output pkt_remote_store_o;
  wire [31:0] data_o;
  wire [19:0] addr_o;
  wire [3:0] mask_o;
  wire pkt_freeze_o,pkt_unfreeze_o,pkt_arb_cfg_o,pkt_unknown_o,pkt_remote_store_o,N0,
  N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,N22,
  N23,N24,N25,N26,N27,N28,N29,N30,N31,N32,N33,N34,N35,N36,N37,N38,N39,N40,N41,N42,
  N43,N44,N45,N46,N47,N48,N49,N50,N51,N52,N53,N54,N55,N56,N57,N58,N59,N60,N61,N62,
  N63,N64,N65,N66,N67,N68,N69,N70,N71,N72,N73,N74,N75;
  assign addr_o[19] = data_i[75];
  assign addr_o[18] = data_i[74];
  assign addr_o[17] = data_i[73];
  assign addr_o[16] = data_i[72];
  assign addr_o[15] = data_i[71];
  assign addr_o[14] = data_i[70];
  assign addr_o[13] = data_i[69];
  assign addr_o[12] = data_i[68];
  assign addr_o[11] = data_i[67];
  assign addr_o[10] = data_i[66];
  assign addr_o[9] = data_i[65];
  assign addr_o[8] = data_i[64];
  assign addr_o[7] = data_i[63];
  assign addr_o[6] = data_i[62];
  assign addr_o[5] = data_i[61];
  assign addr_o[4] = data_i[60];
  assign addr_o[3] = data_i[59];
  assign addr_o[2] = data_i[58];
  assign addr_o[1] = data_i[57];
  assign addr_o[0] = data_i[56];
  assign data_o[31] = data_i[49];
  assign data_o[30] = data_i[48];
  assign data_o[29] = data_i[47];
  assign data_o[28] = data_i[46];
  assign data_o[27] = data_i[45];
  assign data_o[26] = data_i[44];
  assign data_o[25] = data_i[43];
  assign data_o[24] = data_i[42];
  assign data_o[23] = data_i[41];
  assign data_o[22] = data_i[40];
  assign data_o[21] = data_i[39];
  assign data_o[20] = data_i[38];
  assign data_o[19] = data_i[37];
  assign data_o[18] = data_i[36];
  assign data_o[17] = data_i[35];
  assign data_o[16] = data_i[34];
  assign data_o[15] = data_i[33];
  assign data_o[14] = data_i[32];
  assign data_o[13] = data_i[31];
  assign data_o[12] = data_i[30];
  assign data_o[11] = data_i[29];
  assign data_o[10] = data_i[28];
  assign data_o[9] = data_i[27];
  assign data_o[8] = data_i[26];
  assign data_o[7] = data_i[25];
  assign data_o[6] = data_i[24];
  assign data_o[5] = data_i[23];
  assign data_o[4] = data_i[22];
  assign data_o[3] = data_i[21];
  assign data_o[2] = data_i[20];
  assign data_o[1] = data_i[19];
  assign data_o[0] = data_i[18];
  assign N11 = data_i[55] | N10;
  assign N14 = N13 | data_i[54];
  assign N16 = data_i[55] & data_i[54];
  assign N17 = N13 & N10;
  assign N36 = ~data_i[56];
  assign N37 = data_i[74] | data_i[75];
  assign N38 = data_i[73] | N37;
  assign N39 = data_i[72] | N38;
  assign N40 = data_i[71] | N39;
  assign N41 = data_i[70] | N40;
  assign N42 = data_i[69] | N41;
  assign N43 = data_i[68] | N42;
  assign N44 = data_i[67] | N43;
  assign N45 = data_i[66] | N44;
  assign N46 = data_i[65] | N45;
  assign N47 = data_i[64] | N46;
  assign N48 = data_i[63] | N47;
  assign N49 = data_i[62] | N48;
  assign N50 = data_i[61] | N49;
  assign N51 = data_i[60] | N50;
  assign N52 = data_i[59] | N51;
  assign N53 = data_i[58] | N52;
  assign N54 = data_i[57] | N53;
  assign N55 = N36 | N54;
  assign N56 = ~N55;
  assign N23 = (N0)? data_i[18] : 
               (N1)? 1'b0 : 
               (N2)? 1'b0 : 1'b0;
  assign N0 = N19;
  assign N1 = N75;
  assign N2 = 1'b0;
  assign N24 = (N0)? N22 : 
               (N1)? 1'b0 : 
               (N2)? 1'b0 : 1'b0;
  assign N25 = (N0)? 1'b0 : 
               (N3)? 1'b1 : 
               (N21)? 1'b0 : 1'b0;
  assign N3 = N56;
  assign N26 = (N0)? 1'b0 : 
               (N3)? 1'b0 : 
               (N21)? 1'b1 : 1'b0;
  assign N27 = (N4)? 1'b1 : 
               (N5)? 1'b0 : 
               (N6)? 1'b0 : 1'b0;
  assign N4 = N12;
  assign N5 = N15;
  assign N6 = N18;
  assign { N31, N30, N29, N28 } = (N4)? data_i[53:50] : 
                                  (N5)? { 1'b0, 1'b0, 1'b0, 1'b0 } : 
                                  (N6)? { 1'b0, 1'b0, 1'b0, 1'b0 } : 1'b0;
  assign N32 = (N4)? 1'b0 : 
               (N5)? N26 : 
               (N6)? 1'b1 : 1'b0;
  assign N33 = (N4)? 1'b0 : 
               (N5)? N23 : 
               (N6)? 1'b0 : 1'b0;
  assign N34 = (N4)? 1'b0 : 
               (N5)? N24 : 
               (N6)? 1'b0 : 1'b0;
  assign N35 = (N4)? 1'b0 : 
               (N5)? N25 : 
               (N6)? 1'b0 : 1'b0;
  assign pkt_freeze_o = (N7)? N33 : 
                        (N8)? 1'b0 : 1'b0;
  assign N7 = v_i;
  assign N8 = N9;
  assign pkt_unfreeze_o = (N7)? N34 : 
                          (N8)? 1'b0 : 1'b0;
  assign pkt_arb_cfg_o = (N7)? N35 : 
                         (N8)? 1'b0 : 1'b0;
  assign pkt_remote_store_o = (N7)? N27 : 
                              (N8)? 1'b0 : 1'b0;
  assign mask_o = (N7)? { N31, N30, N29, N28 } : 
                  (N8)? { 1'b0, 1'b0, 1'b0, 1'b0 } : 1'b0;
  assign pkt_unknown_o = (N7)? N32 : 
                         (N8)? 1'b0 : 1'b0;
  assign N9 = ~v_i;
  assign N10 = ~data_i[54];
  assign N12 = ~N11;
  assign N13 = ~data_i[55];
  assign N15 = ~N14;
  assign N18 = N16 | N17;
  assign N19 = ~N75;
  assign N75 = N74 | data_i[56];
  assign N74 = N73 | data_i[57];
  assign N73 = N72 | data_i[58];
  assign N72 = N71 | data_i[59];
  assign N71 = N70 | data_i[60];
  assign N70 = N69 | data_i[61];
  assign N69 = N68 | data_i[62];
  assign N68 = N67 | data_i[63];
  assign N67 = N66 | data_i[64];
  assign N66 = N65 | data_i[65];
  assign N65 = N64 | data_i[66];
  assign N64 = N63 | data_i[67];
  assign N63 = N62 | data_i[68];
  assign N62 = N61 | data_i[69];
  assign N61 = N60 | data_i[70];
  assign N60 = N59 | data_i[71];
  assign N59 = N58 | data_i[72];
  assign N58 = N57 | data_i[73];
  assign N57 = data_i[75] | data_i[74];
  assign N20 = N56 | N19;
  assign N21 = ~N20;
  assign N22 = ~data_i[18];

endmodule



module bsg_manycore_endpoint_standard_x_cord_width_p4_y_cord_width_p5_fifo_els_p4_data_width_p32_addr_width_p20_max_out_credits_p200_debug_p0
(
  clk_i,
  reset_i,
  link_sif_i,
  link_sif_o,
  in_v_o,
  in_yumi_i,
  in_data_o,
  in_mask_o,
  in_addr_o,
  out_v_i,
  out_packet_i,
  out_ready_o,
  out_credits_o,
  my_x_i,
  my_y_i,
  freeze_r_o,
  reverse_arb_pr_o
);

  input [88:0] link_sif_i;
  output [88:0] link_sif_o;
  output [31:0] in_data_o;
  output [3:0] in_mask_o;
  output [19:0] in_addr_o;
  input [75:0] out_packet_i;
  output [7:0] out_credits_o;
  input [3:0] my_x_i;
  input [4:0] my_y_i;
  input clk_i;
  input reset_i;
  input in_yumi_i;
  input out_v_i;
  output in_v_o;
  output out_ready_o;
  output freeze_r_o;
  output reverse_arb_pr_o;
  wire [88:0] link_sif_o;
  wire [31:0] in_data_o;
  wire [3:0] in_mask_o;
  wire [19:0] in_addr_o;
  wire [7:0] out_credits_o;
  wire in_v_o,out_ready_o,reverse_arb_pr_o,N0,N1,cgni_v,cgni_yumi,in_fifo_full,
  credit_return_lo,launching_out,pkt_freeze,pkt_unfreeze,pkt_arb_cfg,pkt_unknown,N2,N3,N4,
  N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18;
  wire [75:0] cgni_data;
  reg freeze_r_o,arb_cfg_r;

  bsg_manycore_endpoint_x_cord_width_p4_y_cord_width_p5_fifo_els_p4_data_width_p32_addr_width_p20
  bme
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .link_sif_i(link_sif_i),
    .link_sif_o(link_sif_o),
    .fifo_data_o(cgni_data),
    .fifo_v_o(cgni_v),
    .fifo_yumi_i(cgni_yumi),
    .out_packet_i(out_packet_i),
    .out_v_i(out_v_i),
    .out_ready_o(out_ready_o),
    .credit_v_r_o(credit_return_lo),
    .in_fifo_full_o(in_fifo_full)
  );


  bsg_counter_up_down_max_val_p200_init_val_p200
  out_credit_ctr
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .up_i(credit_return_lo),
    .down_i(launching_out),
    .count_o(out_credits_o)
  );


  bsg_manycore_pkt_decode_x_cord_width_p4_y_cord_width_p5_data_width_p32_addr_width_p20
  pkt_decode
  (
    .v_i(cgni_v),
    .data_i(cgni_data),
    .pkt_freeze_o(pkt_freeze),
    .pkt_unfreeze_o(pkt_unfreeze),
    .pkt_arb_cfg_o(pkt_arb_cfg),
    .pkt_unknown_o(pkt_unknown),
    .pkt_remote_store_o(in_v_o),
    .data_o(in_data_o),
    .addr_o(in_addr_o),
    .mask_o(in_mask_o)
  );


  always @(posedge clk_i) begin
    if(N6) begin
      freeze_r_o <= N7;
    end 
  end


  always @(posedge clk_i) begin
    if(N13) begin
      arb_cfg_r <= N14;
    end 
  end

  assign N6 = (N0)? 1'b1 : 
              (N9)? 1'b1 : 
              (N5)? 1'b0 : 1'b0;
  assign N0 = N3;
  assign N7 = (N0)? 1'b1 : 
              (N9)? pkt_freeze : 1'b0;
  assign N13 = (N1)? 1'b1 : 
               (N16)? 1'b1 : 
               (N12)? 1'b0 : 1'b0;
  assign N1 = N10;
  assign N14 = (N1)? 1'b1 : 
               (N16)? in_data_o[0] : 1'b0;
  assign launching_out = out_v_i & out_ready_o;
  assign cgni_yumi = N18 | pkt_arb_cfg;
  assign N18 = N17 | pkt_unfreeze;
  assign N17 = in_yumi_i | pkt_freeze;
  assign N2 = pkt_freeze | pkt_unfreeze;
  assign N3 = reset_i;
  assign N4 = N2 | N3;
  assign N5 = ~N4;
  assign N8 = ~N3;
  assign N9 = N2 & N8;
  assign N10 = reset_i;
  assign N11 = pkt_arb_cfg | N10;
  assign N12 = ~N11;
  assign N15 = ~N10;
  assign N16 = pkt_arb_cfg & N15;
  assign reverse_arb_pr_o = arb_cfg_r & in_fifo_full;

endmodule



module bsg_mem_1rw_sync_width_p32_els_p1024
(
  clk_i,
  reset_i,
  data_i,
  addr_i,
  v_i,
  w_i,
  data_o
);

  input [31:0] data_i;
  input [9:0] addr_i;
  output [31:0] data_o;
  input clk_i;
  input reset_i;
  input v_i;
  input w_i;
  wire [31:0] data_o;
  wire n_0_net_;

  tsmc65lp_1rf_lg10_w32_all
  macro_mem
  (
    .CLK(clk_i),
    .Q(data_o),
    .CEN(n_0_net_),
    .A(addr_i),
    .D(data_i),
    .EMA({ 1'b0, 1'b1, 1'b1 }),
    .EMAW({ 1'b0, 1'b1 }),
    .RET1N(1'b1)
  );

  assign n_0_net_ = ~v_i;

endmodule



module cl_decode
(
  instruction_i,
  decode_o_op_writes_rf_,
  decode_o_is_load_op_,
  decode_o_is_store_op_,
  decode_o_is_mem_op_,
  decode_o_is_byte_op_,
  decode_o_is_hex_op_,
  decode_o_is_load_unsigned_,
  decode_o_is_branch_op_,
  decode_o_is_jump_op_,
  decode_o_op_reads_rf1_,
  decode_o_op_reads_rf2_,
  decode_o_op_is_auipc_,
  decode_o_is_md_instr_,
  decode_o_is_fence_op_,
  decode_o_is_fence_i_op_,
  decode_o_op_is_load_reservation_,
  decode_o_op_is_lr_acq_
);

  input [31:0] instruction_i;
  output decode_o_op_writes_rf_;
  output decode_o_is_load_op_;
  output decode_o_is_store_op_;
  output decode_o_is_mem_op_;
  output decode_o_is_byte_op_;
  output decode_o_is_hex_op_;
  output decode_o_is_load_unsigned_;
  output decode_o_is_branch_op_;
  output decode_o_is_jump_op_;
  output decode_o_op_reads_rf1_;
  output decode_o_op_reads_rf2_;
  output decode_o_op_is_auipc_;
  output decode_o_is_md_instr_;
  output decode_o_is_fence_op_;
  output decode_o_is_fence_i_op_;
  output decode_o_op_is_load_reservation_;
  output decode_o_op_is_lr_acq_;
  wire decode_o_op_writes_rf_,decode_o_is_load_op_,decode_o_is_store_op_,
  decode_o_is_mem_op_,decode_o_is_byte_op_,decode_o_is_hex_op_,decode_o_is_load_unsigned_,
  decode_o_is_branch_op_,decode_o_is_jump_op_,decode_o_op_reads_rf1_,
  decode_o_op_reads_rf2_,decode_o_op_is_auipc_,decode_o_is_md_instr_,decode_o_is_fence_op_,
  decode_o_is_fence_i_op_,decode_o_op_is_load_reservation_,decode_o_op_is_lr_acq_,N0,N1,N2,
  N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,N22,N23,N24,
  N25,N26,N27,N28,N29,N30,N31,N32,N33,N34,N35,N36,N37,N38,N39,N40,N41,N42,N43,N44,
  N45,N46,N47,N48,N49,N50,N51,N52,N53,N54,N55,N56,N57,N58,N59,N60,N61,N62,N63,N64,
  N65,N66,N67,N68,N69,N70,N71,N72,N73,N74,N75,N76,N77,N78,N79,N80,N81,N82,N83,N84,
  N85,N86,N87,N88,N89,N90,N91,N92,N93,N94,N95,N96,N97,N98,N99,N100,N101,N102,N103,
  N104,N105,N106,N107,N108,N109,N110,N111,N112,N113,N114,N115,N116,N117,N118,N119,
  N120,N121,N122,N123,N124,N125,N126,N127,N128,N129,N130,N131,N132,N133,N134,N135,
  N136,N137,N138,N139,N140,N141,N142,N143,N144,N145,N146,N147,N148,N149,N150,N151,
  N152,N153,N154,N155,N156,N157,N158,N159,N160,N161,N162,N163,N164,N165,N166,N167,
  N168,N169,N170,N171,N172,N173,N174,N175,N176,N177,N178,N179,N180,N181,N182,N183,
  N184,N185,N186,N187,N188,N189,N190;
  assign N9 = instruction_i[1] & instruction_i[0];
  assign N11 = instruction_i[6] | N89;
  assign N12 = N90 | instruction_i[3];
  assign N13 = N11 | N12;
  assign N14 = N13 | N106;
  assign N15 = instruction_i[6] | instruction_i[5];
  assign N16 = N15 | N12;
  assign N17 = N16 | N106;
  assign N18 = N84 | N89;
  assign N19 = instruction_i[4] | N105;
  assign N20 = N18 | N19;
  assign N21 = N20 | N106;
  assign N22 = instruction_i[4] | instruction_i[3];
  assign N23 = N18 | N22;
  assign N24 = N23 | N106;
  assign N25 = N84 & N89;
  assign N26 = N90 & N105;
  assign N27 = N25 & N26;
  assign N28 = N27 & N106;
  assign N29 = N13 | instruction_i[2];
  assign N30 = N16 | instruction_i[2];
  assign N31 = N11 | N19;
  assign N32 = N31 | N106;
  assign N34 = N84 & N90;
  assign N35 = N34 & N9;
  assign N37 = N89 & N105;
  assign N38 = N37 & N106;
  assign N39 = N89 | instruction_i[3];
  assign N40 = N39 | instruction_i[2];
  assign N41 = instruction_i[5] & instruction_i[3];
  assign N42 = N41 & instruction_i[2];
  assign N45 = N44 & N131;
  assign N47 = instruction_i[13] | N131;
  assign N51 = N11 | N22;
  assign N52 = N55 | N92;
  assign N53 = N51 | N52;
  assign N55 = instruction_i[2] | N91;
  assign N56 = N23 | N55;
  assign N58 = instruction_i[6] & instruction_i[5];
  assign N59 = N90 & instruction_i[2];
  assign N60 = N58 & N59;
  assign N61 = N60 & N9;
  assign N62 = N106 | N92;
  assign N63 = N23 | N62;
  assign N64 = N58 & N26;
  assign N65 = N64 & N106;
  assign N66 = instruction_i[2] | N92;
  assign N67 = N15 | N22;
  assign N68 = N67 | N66;
  assign N69 = N51 | N66;
  assign N70 = N13 | N66;
  assign N71 = N16 | N66;
  assign N72 = N31 | N62;
  assign N74 = instruction_i[5] & N105;
  assign N75 = N106 & instruction_i[1];
  assign N76 = N74 & N75;
  assign N78 = instruction_i[6] & N90;
  assign N79 = instruction_i[6] | instruction_i[4];
  assign N80 = N79 | N92;
  assign N81 = instruction_i[6] | N90;
  assign N82 = N81 | N92;
  assign N85 = N106 | N91;
  assign N86 = N85 | N92;
  assign N87 = N16 | N86;
  assign N89 = ~instruction_i[5];
  assign N90 = ~instruction_i[4];
  assign N91 = ~instruction_i[1];
  assign N92 = ~instruction_i[0];
  assign N93 = N89 | instruction_i[6];
  assign N94 = N90 | N93;
  assign N95 = instruction_i[3] | N94;
  assign N96 = instruction_i[2] | N95;
  assign N97 = N91 | N96;
  assign N98 = N92 | N97;
  assign N99 = ~N98;
  assign N100 = ~instruction_i[25];
  assign N101 = instruction_i[27] | N129;
  assign N102 = instruction_i[26] | N101;
  assign N103 = N100 | N102;
  assign N104 = ~N103;
  assign N105 = ~instruction_i[3];
  assign N106 = ~instruction_i[2];
  assign N107 = instruction_i[5] | instruction_i[6];
  assign N108 = instruction_i[4] | N107;
  assign N109 = N105 | N108;
  assign N110 = N106 | N109;
  assign N111 = N91 | N110;
  assign N112 = N92 | N111;
  assign N113 = ~N112;
  assign N114 = instruction_i[13] | instruction_i[14];
  assign N115 = instruction_i[12] | N114;
  assign N116 = ~N115;
  assign N117 = instruction_i[18] | instruction_i[19];
  assign N118 = instruction_i[17] | N117;
  assign N119 = instruction_i[16] | N118;
  assign N120 = instruction_i[15] | N119;
  assign N121 = ~N120;
  assign N122 = instruction_i[10] | instruction_i[11];
  assign N123 = instruction_i[9] | N122;
  assign N124 = instruction_i[8] | N123;
  assign N125 = instruction_i[7] | N124;
  assign N126 = ~N125;
  assign N127 = instruction_i[30] | instruction_i[31];
  assign N128 = instruction_i[29] | N127;
  assign N129 = instruction_i[28] | N128;
  assign N130 = ~N129;
  assign N131 = ~instruction_i[12];
  assign N132 = N131 | N114;
  assign N133 = ~N132;
  assign N134 = instruction_i[25] | N102;
  assign N135 = instruction_i[24] | N134;
  assign N136 = instruction_i[23] | N135;
  assign N137 = instruction_i[22] | N136;
  assign N138 = instruction_i[21] | N137;
  assign N139 = instruction_i[20] | N138;
  assign N140 = ~N139;
  assign decode_o_op_writes_rf_ = (N0)? N33 : 
                                  (N10)? 1'b0 : 1'b0;
  assign N0 = N9;
  assign decode_o_is_mem_op_ = (N1)? N43 : 
                               (N36)? 1'b0 : 1'b0;
  assign N1 = N35;
  assign decode_o_is_byte_op_ = (N2)? decode_o_is_mem_op_ : 
                                (N46)? 1'b0 : 1'b0;
  assign N2 = N45;
  assign decode_o_is_hex_op_ = (N3)? decode_o_is_mem_op_ : 
                               (N4)? 1'b0 : 1'b0;
  assign N3 = N48;
  assign N4 = N47;
  assign decode_o_is_load_op_ = (N1)? N49 : 
                                (N36)? 1'b0 : 1'b0;
  assign decode_o_is_load_unsigned_ = (N5)? decode_o_is_load_op_ : 
                                      (N50)? 1'b0 : 1'b0;
  assign N5 = instruction_i[14];
  assign decode_o_op_reads_rf1_ = (N6)? N73 : 
                                  (N7)? 1'b0 : 1'b0;
  assign N6 = instruction_i[1];
  assign N7 = N91;
  assign decode_o_op_reads_rf2_ = (N8)? N83 : 
                                  (N77)? 1'b0 : 1'b0;
  assign N8 = N76;
  assign N10 = ~N9;
  assign N33 = N152 | N153;
  assign N152 = N150 | N151;
  assign N150 = N148 | N149;
  assign N148 = N147 | N28;
  assign N147 = N145 | N146;
  assign N145 = N143 | N144;
  assign N143 = N141 | N142;
  assign N141 = ~N14;
  assign N142 = ~N17;
  assign N144 = ~N21;
  assign N146 = ~N24;
  assign N149 = ~N29;
  assign N151 = ~N30;
  assign N153 = ~N32;
  assign N36 = ~N35;
  assign N43 = N155 | N42;
  assign N155 = N38 | N154;
  assign N154 = ~N40;
  assign N44 = ~instruction_i[13];
  assign N46 = ~N45;
  assign N48 = ~N47;
  assign N49 = N38 | N42;
  assign N50 = ~instruction_i[14];
  assign N54 = ~N53;
  assign decode_o_is_store_op_ = N54;
  assign N57 = ~N56;
  assign decode_o_is_branch_op_ = N57;
  assign decode_o_is_jump_op_ = N61;
  assign N73 = N165 | N166;
  assign N165 = N163 | N164;
  assign N163 = N161 | N162;
  assign N161 = N159 | N160;
  assign N159 = N157 | N158;
  assign N157 = N156 | N65;
  assign N156 = ~N63;
  assign N158 = ~N68;
  assign N160 = ~N69;
  assign N162 = ~N70;
  assign N164 = ~N71;
  assign N166 = ~N72;
  assign N77 = ~N76;
  assign N83 = N168 | N169;
  assign N168 = N78 | N167;
  assign N167 = ~N80;
  assign N169 = ~N82;
  assign N84 = ~instruction_i[6];
  assign N88 = ~N87;
  assign decode_o_op_is_auipc_ = N88;
  assign decode_o_is_md_instr_ = N99 & N104;
  assign decode_o_op_is_load_reservation_ = ~N184;
  assign N184 = N183 | N92;
  assign N183 = N182 | N91;
  assign N182 = N181 | N106;
  assign N181 = N180 | N105;
  assign N180 = N179 | instruction_i[4];
  assign N179 = N178 | N89;
  assign N178 = N177 | instruction_i[6];
  assign N177 = N176 | instruction_i[12];
  assign N176 = N175 | N44;
  assign N175 = N174 | instruction_i[14];
  assign N174 = N173 | instruction_i[27];
  assign N173 = N171 | N172;
  assign N171 = N170 | instruction_i[29];
  assign N170 = instruction_i[31] | instruction_i[30];
  assign N172 = ~instruction_i[28];
  assign decode_o_op_is_lr_acq_ = decode_o_op_is_load_reservation_ & instruction_i[26];
  assign decode_o_is_fence_op_ = N187 & N130;
  assign N187 = N186 & N126;
  assign N186 = N185 & N121;
  assign N185 = N113 & N116;
  assign decode_o_is_fence_i_op_ = N190 & N140;
  assign N190 = N189 & N126;
  assign N189 = N188 & N121;
  assign N188 = N113 & N133;

endmodule



module bsg_mem_2r1w_sync_32_32_0_5_0
(
  clk_i,
  reset_i,
  w_v_i,
  w_addr_i,
  w_data_i,
  r0_v_i,
  r0_addr_i,
  r0_data_o,
  r1_v_i,
  r1_addr_i,
  r1_data_o
);

  input [4:0] w_addr_i;
  input [31:0] w_data_i;
  input [4:0] r0_addr_i;
  output [31:0] r0_data_o;
  input [4:0] r1_addr_i;
  output [31:0] r1_data_o;
  input clk_i;
  input reset_i;
  input w_v_i;
  input r0_v_i;
  input r1_v_i;
  wire [31:0] r0_data_o,r1_data_o;
  wire n_0_net_,n_1_net_,n_5_net_,n_6_net_;

  tsmc65lp_2rf_lg5_w32_all
  macro_mem0
  (
    .CLKA(clk_i),
    .AA(r0_addr_i),
    .CENA(n_0_net_),
    .QA(r0_data_o),
    .CLKB(clk_i),
    .AB(w_addr_i),
    .DB(w_data_i),
    .CENB(n_1_net_),
    .EMAA({ 1'b0, 1'b1, 1'b1 }),
    .EMAB({ 1'b0, 1'b1, 1'b1 }),
    .RET1N(1'b1)
  );


  tsmc65lp_2rf_lg5_w32_all
  macro_mem1
  (
    .CLKA(clk_i),
    .AA(r1_addr_i),
    .CENA(n_5_net_),
    .QA(r1_data_o),
    .CLKB(clk_i),
    .AB(w_addr_i),
    .DB(w_data_i),
    .CENB(n_6_net_),
    .EMAA({ 1'b0, 1'b1, 1'b1 }),
    .EMAB({ 1'b0, 1'b1, 1'b1 }),
    .RET1N(1'b1)
  );

  assign n_1_net_ = ~w_v_i;
  assign n_0_net_ = ~r0_v_i;
  assign n_6_net_ = ~w_v_i;
  assign n_5_net_ = ~r1_v_i;

endmodule



module rf_2r1w_sync_wrapper_width_p32_els_p32
(
  clk_i,
  reset_i,
  w_v_i,
  w_addr_i,
  w_data_i,
  r0_v_i,
  r0_addr_i,
  r0_data_o,
  r1_v_i,
  r1_addr_i,
  r1_data_o
);

  input [4:0] w_addr_i;
  input [31:0] w_data_i;
  input [4:0] r0_addr_i;
  output [31:0] r0_data_o;
  input [4:0] r1_addr_i;
  output [31:0] r1_data_o;
  input clk_i;
  input reset_i;
  input w_v_i;
  input r0_v_i;
  input r1_v_i;
  wire [31:0] r0_data_o,r1_data_o,r0_mem_data,r1_mem_data,r0_data_safe,r1_data_safe;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,
  r0_rw_same_addr,N20,r1_rw_same_addr,N21,r0_wrapper_v,N22,r1_wrapper_v,N23,N24,N25,N26,N27,
  N28,N29,N30,N31,N32,N33,N34,N35,N36,N37,N38,N39,N40,N41,N42,N43,N44,N45,N46,N47,
  N48,N49,N50,N51,N52,N53,N54,N55,N56,N57,N58,N59,N60,N61,N62,N63,N64,N65,N66,N67,
  N68,update_hold_reg0,N69,update_hold_reg1,N70,N71,N72,N73,N74,N75,N76,N77,N78,
  N79,N80,N81,N82,N83,N84,N85,N86,N87,N88,N89,N90,N91,N92,N93,N94,N95,N96,N97,N98,
  N99,N100,N101,N102,N103,N104,N105,N106,N107,N108,N109,N110,N111,N112,N113,N114,
  N115,N116,N117,N118,N119,N120,N121,N122,N123,N124,N125,N126,N127,N128,N129,N130,
  N131,N132,N133,N134,N135,N136,N137,N138,N139,N140,N141;
  reg r1_rw_same_addr_r,r0_rw_same_addr_r,r0_v_r,r1_v_r;
  reg [31:0] w_data_r,r0_data_r,r1_data_r;
  reg [4:0] r0_addr_r,r1_addr_r;
  assign N19 = w_addr_i == r0_addr_i;
  assign N20 = w_addr_i == r1_addr_i;

  bsg_mem_2r1w_sync_32_32_0_5_0
  rf_mem
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .w_v_i(w_v_i),
    .w_addr_i(w_addr_i),
    .w_data_i(w_data_i),
    .r0_v_i(r0_wrapper_v),
    .r0_addr_i(r0_addr_i),
    .r0_data_o(r0_mem_data),
    .r1_v_i(r1_wrapper_v),
    .r1_addr_i(r1_addr_i),
    .r1_data_o(r1_mem_data)
  );


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_rw_same_addr_r <= N26;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_rw_same_addr_r <= N25;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[31] <= N63;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[30] <= N62;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[29] <= N61;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[28] <= N60;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[27] <= N59;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[26] <= N58;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[25] <= N57;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[24] <= N56;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[23] <= N55;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[22] <= N54;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[21] <= N53;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[20] <= N52;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[19] <= N51;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[18] <= N50;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[17] <= N49;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[16] <= N48;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[15] <= N47;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[14] <= N46;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[13] <= N45;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[12] <= N44;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[11] <= N43;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[10] <= N42;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[9] <= N41;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[8] <= N40;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[7] <= N39;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[6] <= N38;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[5] <= N37;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[4] <= N36;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[3] <= N35;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[2] <= N34;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[1] <= N33;
    end 
  end


  always @(posedge clk_i) begin
    if(N31) begin
      w_data_r[0] <= N32;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_addr_r[4] <= r0_addr_i[4];
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_addr_r[3] <= r0_addr_i[3];
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_addr_r[2] <= r0_addr_i[2];
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_addr_r[1] <= r0_addr_i[1];
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_addr_r[0] <= r0_addr_i[0];
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_addr_r[4] <= r1_addr_i[4];
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_addr_r[3] <= r1_addr_i[3];
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_addr_r[2] <= r1_addr_i[2];
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_addr_r[1] <= r1_addr_i[1];
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_addr_r[0] <= r1_addr_i[0];
    end 
  end

  assign N68 = r0_addr_r == w_addr_i;
  assign N69 = r1_addr_r == w_addr_i;

  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[31] <= N102;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[30] <= N101;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[29] <= N100;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[28] <= N99;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[27] <= N98;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[26] <= N97;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[25] <= N96;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[24] <= N95;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[23] <= N94;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[22] <= N93;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[21] <= N92;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[20] <= N91;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[19] <= N90;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[18] <= N89;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[17] <= N88;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[16] <= N87;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[15] <= N86;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[14] <= N85;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[13] <= N84;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[12] <= N83;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[11] <= N82;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[10] <= N81;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[9] <= N80;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[8] <= N79;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[7] <= N78;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[6] <= N77;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[5] <= N76;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[4] <= N75;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[3] <= N74;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[2] <= N73;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[1] <= N72;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_data_r[0] <= N71;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[31] <= N135;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[30] <= N134;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[29] <= N133;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[28] <= N132;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[27] <= N131;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[26] <= N130;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[25] <= N129;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[24] <= N128;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[23] <= N127;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[22] <= N126;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[21] <= N125;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[20] <= N124;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[19] <= N123;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[18] <= N122;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[17] <= N121;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[16] <= N120;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[15] <= N119;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[14] <= N118;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[13] <= N117;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[12] <= N116;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[11] <= N115;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[10] <= N114;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[9] <= N113;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[8] <= N112;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[7] <= N111;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[6] <= N110;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[5] <= N109;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[4] <= N108;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[3] <= N107;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[2] <= N106;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[1] <= N105;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_data_r[0] <= N104;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r0_v_r <= r0_v_i;
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      r1_v_r <= r1_v_i;
    end 
  end

  assign r0_wrapper_v = (N0)? 1'b0 : 
                        (N1)? r0_v_i : 1'b0;
  assign N0 = r0_rw_same_addr;
  assign N1 = N21;
  assign r1_wrapper_v = (N2)? 1'b0 : 
                        (N3)? r1_v_i : 1'b0;
  assign N2 = r1_rw_same_addr;
  assign N3 = N22;
  assign N25 = (N4)? 1'b0 : 
               (N5)? r0_rw_same_addr : 1'b0;
  assign N4 = N24;
  assign N5 = N23;
  assign N26 = (N4)? 1'b0 : 
               (N5)? r1_rw_same_addr : 1'b0;
  assign N31 = (N6)? 1'b1 : 
               (N65)? 1'b1 : 
               (N30)? 1'b0 : 1'b0;
  assign N6 = N27;
  assign { N63, N62, N61, N60, N59, N58, N57, N56, N55, N54, N53, N52, N51, N50, N49, N48, N47, N46, N45, N44, N43, N42, N41, N40, N39, N38, N37, N36, N35, N34, N33, N32 } = (N6)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                                                                                                                                                                              (N65)? w_data_i : 1'b0;
  assign r0_data_safe = (N7)? w_data_r : 
                        (N8)? r0_mem_data : 1'b0;
  assign N7 = r0_rw_same_addr_r;
  assign N8 = N66;
  assign r1_data_safe = (N9)? w_data_r : 
                        (N10)? r1_mem_data : 1'b0;
  assign N9 = r1_rw_same_addr_r;
  assign N10 = N67;
  assign { N102, N101, N100, N99, N98, N97, N96, N95, N94, N93, N92, N91, N90, N89, N88, N87, N86, N85, N84, N83, N82, N81, N80, N79, N78, N77, N76, N75, N74, N73, N72, N71 } = (N11)? w_data_i : 
                                                                                                                                                                                 (N12)? r0_data_o : 1'b0;
  assign N11 = update_hold_reg0;
  assign N12 = N70;
  assign { N135, N134, N133, N132, N131, N130, N129, N128, N127, N126, N125, N124, N123, N122, N121, N120, N119, N118, N117, N116, N115, N114, N113, N112, N111, N110, N109, N108, N107, N106, N105, N104 } = (N13)? w_data_i : 
                                                                                                                                                                                                              (N14)? r1_data_o : 1'b0;
  assign N13 = update_hold_reg1;
  assign N14 = N103;
  assign r0_data_o = (N15)? r0_data_safe : 
                     (N16)? r0_data_r : 1'b0;
  assign N15 = r0_v_r;
  assign N16 = N136;
  assign r1_data_o = (N17)? r1_data_safe : 
                     (N18)? r1_data_r : 1'b0;
  assign N17 = r1_v_r;
  assign N18 = N137;
  assign r0_rw_same_addr = N138 & N19;
  assign N138 = w_v_i & r0_v_i;
  assign r1_rw_same_addr = N139 & N20;
  assign N139 = w_v_i & r1_v_i;
  assign N21 = ~r0_rw_same_addr;
  assign N22 = ~r1_rw_same_addr;
  assign N23 = ~reset_i;
  assign N24 = reset_i;
  assign N27 = reset_i;
  assign N28 = w_v_i;
  assign N29 = N28 | N27;
  assign N30 = ~N29;
  assign N64 = ~N27;
  assign N65 = N28 & N64;
  assign N66 = ~r0_rw_same_addr_r;
  assign N67 = ~r1_rw_same_addr_r;
  assign update_hold_reg0 = N140 & N68;
  assign N140 = r0_v_r & w_v_i;
  assign update_hold_reg1 = N141 & N69;
  assign N141 = r1_v_r & w_v_i;
  assign N70 = ~update_hold_reg0;
  assign N103 = ~update_hold_reg1;
  assign N136 = ~r0_v_r;
  assign N137 = ~r1_v_r;

endmodule



module bsg_imul_iterative_width_p32
(
  reset_i,
  clk_i,
  v_i,
  ready_o,
  opA_i,
  signed_opA_i,
  opB_i,
  signed_opB_i,
  gets_high_part_i,
  v_o,
  result_o,
  yumi_i
);

  input [31:0] opA_i;
  input [31:0] opB_i;
  output [31:0] result_o;
  input reset_i;
  input clk_i;
  input v_i;
  input signed_opA_i;
  input signed_opB_i;
  input gets_high_part_i;
  input yumi_i;
  output ready_o;
  output v_o;
  wire ready_o,v_o,N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,
  N19,N20,N21,N22,N23,N24,N25,N26,shift_counter_full,N27,N28,N29,N30,N31,N32,N33,
  N34,N35,N36,N37,N38,N39,N40,N41,N42,N43,N44,N45,N46,N47,N48,N49,N50,N51,N52,N53,
  N54,N55,N56,N57,N58,N59,N60,N61,N62,N63,N64,N65,N66,N67,N68,N69,N70,N71,N72,N73,
  N74,N75,N76,N77,N78,N79,N80,N81,N82,N83,N84,N85,N86,N87,N88,N89,N90,N91,N92,N93,
  N94,N95,N96,N97,N98,N99,N100,N101,N102,N103,N104,N105,N106,N107,N108,N109,N110,
  N111,N112,N113,N114,N115,N116,N117,N118,N119,N120,N121,N122,N123,N124,N125,N126,
  N127,N128,N129,N130,N131,N132,N133,N134,N135,N136,N137,N138,N139,N140,N141,N142,
  N143,N144,N145,N146,N147,N148,N149,N150,N151,N152,N153,N154,N155,N156,N157,N158,
  N159,N160,N161,N162,N163,N164,N165,N166,adder_neg_op,N167,latch_input,signed_opA,
  signed_opB,N168,N169,N170,N171,N172,N173,N174,N175,N176,N177,N178,N179,N180,N181,
  N182,N183,N184,N185,N186,N187,N188,N189,N190,N191,N192,N193,N194,N195,N196,N197,
  N198,N199,N200,N201,N202,N203,N204,N205,N206,N207,N208,N209,N210,N211,N212,N213,
  N214,N215,N216,N217,N218,N219,N220,N221,N222,N223,N224,N225,N226,N227,N228,N229,
  N230,N231,N232,N233,N234,N235,N236,N237,N238,N239,N240,N241,N242,N243,N244,N245,
  N246,N247,N248,N249,N250,N251,N252,N253,N254,N255,N256,N257,N258,N259,N260,N261,
  N262,N263,N264,N265,N266,N267,N268,N269,N270,N271,N272,N273,N274,N275,N276,N277,
  N278,N279,N280,N281,N282,N283,N284,N285,N286,N287,N288,N289,N290,N291,N292,N293,
  N294,N295,N296,N297,N298,N299,N300,N301,N302,N303,N304,N305,N306,N307,N308,N309,
  shifted_lsb,N310,N311,N312,N313,N314,N315,N316,N317,N318,N319,N320,N321,N322,N323,
  N324,N325,N326,N327,N328,N329,N330,N331,N332,N333,N334,N335,N336,N337,N338,N339,
  N340,N341,N342,N343,N344,N345,N346,N347,N348,N349,N350,N351,N352,N353,N354,N355,
  N356,N357,N358,N359,N360,N361,N362,N363,N364,N365,N366,N367,N368,N369,N370,N371,
  N372,N373,N374,N375,N376,N377,N378,N379,N380,N381,N382,N383,N384,N385,N386,N387,
  N388,N389,N390,N391,N392,N393,N394,N395,N396,N397,N398,N399,N400,N401,N402,N403,
  N404,N405,N406,N407,N408,N409,N410,N411,N412,N413,N414,N415,N416,N417,N418,N419,
  N420,N421,N422,N423,N424,N425,N426,N427,N428,N429,N430,N431,N432,N433,N434,N435,
  N436,N437,N438,N439,N440,N441,N442,N443,N444,N445,N446,N447,N448,N449,N450,N451,
  N453,N454,N455,N456,N457,N458,N459,N460,N461,N462,N463,N464,N465,N466,N467,N468,
  N469,N470,N471,N472,N473,N474,N475,N476,N477,N478,N479,N480,N481,N482,N483,N484,
  N485,N486,N487,N488,N489,N490,N491,N492,N493,N494,N495,N496,N497,N498,N499,N500,
  N501,N502,N503,N504,N505,N506,N507,N509,N510,N511,N512,N513,N514,N515,N516,N517,
  N518,N519,N520,N521,N522,N523,N524,N525,N526,N527,N528,N529;
  wire [2:0] next_state;
  wire [31:0] adder_a,adder_b;
  wire [32:0] adder_result;
  reg [2:0] curr_state_r;
  reg [5:0] shift_counter_r;
  reg signed_opA_r,signed_opB_r,need_neg_result_r,gets_high_part_r,all_sh_lsb_zero_r;
  reg [31:0] opA_r,opB_r,result_o;

  always @(posedge clk_i) begin
    if(reset_i) begin
      curr_state_r[2] <= 1'b0;
    end else if(1'b1) begin
      curr_state_r[2] <= next_state[2];
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      curr_state_r[1] <= 1'b0;
    end else if(1'b1) begin
      curr_state_r[1] <= next_state[1];
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      curr_state_r[0] <= 1'b0;
    end else if(1'b1) begin
      curr_state_r[0] <= next_state[0];
    end 
  end

  assign N27 = N448 & N453;
  assign N28 = N27 & N449;
  assign N29 = curr_state_r[2] | curr_state_r[1];
  assign N30 = N29 | N449;
  assign N32 = curr_state_r[2] | N453;
  assign N33 = N32 | curr_state_r[0];
  assign N35 = curr_state_r[2] | N453;
  assign N36 = N35 | N449;
  assign N38 = N448 | curr_state_r[1];
  assign N39 = N38 | curr_state_r[0];
  assign N41 = N448 | curr_state_r[1];
  assign N42 = N41 | N449;
  assign N44 = curr_state_r[2] & curr_state_r[1];

  always @(posedge clk_i) begin
    if(reset_i) begin
      shift_counter_r[5] <= 1'b0;
    end else if(N59) begin
      shift_counter_r[5] <= N65;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      shift_counter_r[4] <= 1'b0;
    end else if(N59) begin
      shift_counter_r[4] <= N64;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      shift_counter_r[3] <= 1'b0;
    end else if(N59) begin
      shift_counter_r[3] <= N63;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      shift_counter_r[2] <= 1'b0;
    end else if(N59) begin
      shift_counter_r[2] <= N62;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      shift_counter_r[1] <= 1'b0;
    end else if(N59) begin
      shift_counter_r[1] <= N61;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      shift_counter_r[0] <= 1'b0;
    end else if(N59) begin
      shift_counter_r[0] <= N60;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      signed_opA_r <= 1'b0;
    end else if(latch_input) begin
      signed_opA_r <= signed_opA;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      signed_opB_r <= 1'b0;
    end else if(latch_input) begin
      signed_opB_r <= signed_opB;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      need_neg_result_r <= 1'b0;
    end else if(latch_input) begin
      need_neg_result_r <= N168;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      gets_high_part_r <= 1'b0;
    end else if(latch_input) begin
      gets_high_part_r <= gets_high_part_i;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[31] <= 1'b0;
    end else if(N207) begin
      opA_r[31] <= N239;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[30] <= 1'b0;
    end else if(N207) begin
      opA_r[30] <= N238;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[29] <= 1'b0;
    end else if(N207) begin
      opA_r[29] <= N237;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[28] <= 1'b0;
    end else if(N207) begin
      opA_r[28] <= N236;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[27] <= 1'b0;
    end else if(N207) begin
      opA_r[27] <= N235;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[26] <= 1'b0;
    end else if(N207) begin
      opA_r[26] <= N234;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[25] <= 1'b0;
    end else if(N207) begin
      opA_r[25] <= N233;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[24] <= 1'b0;
    end else if(N207) begin
      opA_r[24] <= N232;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[23] <= 1'b0;
    end else if(N207) begin
      opA_r[23] <= N231;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[22] <= 1'b0;
    end else if(N207) begin
      opA_r[22] <= N230;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[21] <= 1'b0;
    end else if(N207) begin
      opA_r[21] <= N229;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[20] <= 1'b0;
    end else if(N207) begin
      opA_r[20] <= N228;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[19] <= 1'b0;
    end else if(N207) begin
      opA_r[19] <= N227;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[18] <= 1'b0;
    end else if(N207) begin
      opA_r[18] <= N226;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[17] <= 1'b0;
    end else if(N207) begin
      opA_r[17] <= N225;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[16] <= 1'b0;
    end else if(N207) begin
      opA_r[16] <= N224;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[15] <= 1'b0;
    end else if(N207) begin
      opA_r[15] <= N223;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[14] <= 1'b0;
    end else if(N207) begin
      opA_r[14] <= N222;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[13] <= 1'b0;
    end else if(N207) begin
      opA_r[13] <= N221;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[12] <= 1'b0;
    end else if(N207) begin
      opA_r[12] <= N220;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[11] <= 1'b0;
    end else if(N207) begin
      opA_r[11] <= N219;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[10] <= 1'b0;
    end else if(N207) begin
      opA_r[10] <= N218;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[9] <= 1'b0;
    end else if(N207) begin
      opA_r[9] <= N217;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[8] <= 1'b0;
    end else if(N207) begin
      opA_r[8] <= N216;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[7] <= 1'b0;
    end else if(N207) begin
      opA_r[7] <= N215;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[6] <= 1'b0;
    end else if(N207) begin
      opA_r[6] <= N214;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[5] <= 1'b0;
    end else if(N207) begin
      opA_r[5] <= N213;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[4] <= 1'b0;
    end else if(N207) begin
      opA_r[4] <= N212;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[3] <= 1'b0;
    end else if(N207) begin
      opA_r[3] <= N211;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[2] <= 1'b0;
    end else if(N207) begin
      opA_r[2] <= N210;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[1] <= 1'b0;
    end else if(N207) begin
      opA_r[1] <= N209;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opA_r[0] <= 1'b0;
    end else if(N207) begin
      opA_r[0] <= N208;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[31] <= 1'b0;
    end else if(N276) begin
      opB_r[31] <= N308;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[30] <= 1'b0;
    end else if(N276) begin
      opB_r[30] <= N307;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[29] <= 1'b0;
    end else if(N276) begin
      opB_r[29] <= N306;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[28] <= 1'b0;
    end else if(N276) begin
      opB_r[28] <= N305;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[27] <= 1'b0;
    end else if(N276) begin
      opB_r[27] <= N304;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[26] <= 1'b0;
    end else if(N276) begin
      opB_r[26] <= N303;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[25] <= 1'b0;
    end else if(N276) begin
      opB_r[25] <= N302;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[24] <= 1'b0;
    end else if(N276) begin
      opB_r[24] <= N301;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[23] <= 1'b0;
    end else if(N276) begin
      opB_r[23] <= N300;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[22] <= 1'b0;
    end else if(N276) begin
      opB_r[22] <= N299;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[21] <= 1'b0;
    end else if(N276) begin
      opB_r[21] <= N298;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[20] <= 1'b0;
    end else if(N276) begin
      opB_r[20] <= N297;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[19] <= 1'b0;
    end else if(N276) begin
      opB_r[19] <= N296;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[18] <= 1'b0;
    end else if(N276) begin
      opB_r[18] <= N295;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[17] <= 1'b0;
    end else if(N276) begin
      opB_r[17] <= N294;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[16] <= 1'b0;
    end else if(N276) begin
      opB_r[16] <= N293;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[15] <= 1'b0;
    end else if(N276) begin
      opB_r[15] <= N292;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[14] <= 1'b0;
    end else if(N276) begin
      opB_r[14] <= N291;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[13] <= 1'b0;
    end else if(N276) begin
      opB_r[13] <= N290;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[12] <= 1'b0;
    end else if(N276) begin
      opB_r[12] <= N289;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[11] <= 1'b0;
    end else if(N276) begin
      opB_r[11] <= N288;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[10] <= 1'b0;
    end else if(N276) begin
      opB_r[10] <= N287;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[9] <= 1'b0;
    end else if(N276) begin
      opB_r[9] <= N286;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[8] <= 1'b0;
    end else if(N276) begin
      opB_r[8] <= N285;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[7] <= 1'b0;
    end else if(N276) begin
      opB_r[7] <= N284;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[6] <= 1'b0;
    end else if(N276) begin
      opB_r[6] <= N283;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[5] <= 1'b0;
    end else if(N276) begin
      opB_r[5] <= N282;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[4] <= 1'b0;
    end else if(N276) begin
      opB_r[4] <= N281;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[3] <= 1'b0;
    end else if(N276) begin
      opB_r[3] <= N280;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[2] <= 1'b0;
    end else if(N276) begin
      opB_r[2] <= N279;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[1] <= 1'b0;
    end else if(N276) begin
      opB_r[1] <= N278;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      opB_r[0] <= 1'b0;
    end else if(N276) begin
      opB_r[0] <= N277;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      all_sh_lsb_zero_r <= 1'b0;
    end else if(latch_input) begin
      all_sh_lsb_zero_r <= 1'b1;
    end else if(N456) begin
      all_sh_lsb_zero_r <= N310;
    end 
  end


  always @(posedge clk_i) begin
    if(N416) begin
      result_o[31] <= 1'b0;
    end else if(N383) begin
      result_o[31] <= N415;
    end 
  end


  always @(posedge clk_i) begin
    if(N447) begin
      result_o[30] <= 1'b0;
    end else if(N383) begin
      result_o[30] <= N414;
    end 
  end


  always @(posedge clk_i) begin
    if(N446) begin
      result_o[29] <= 1'b0;
    end else if(N383) begin
      result_o[29] <= N413;
    end 
  end


  always @(posedge clk_i) begin
    if(N445) begin
      result_o[28] <= 1'b0;
    end else if(N383) begin
      result_o[28] <= N412;
    end 
  end


  always @(posedge clk_i) begin
    if(N444) begin
      result_o[27] <= 1'b0;
    end else if(N383) begin
      result_o[27] <= N411;
    end 
  end


  always @(posedge clk_i) begin
    if(N443) begin
      result_o[26] <= 1'b0;
    end else if(N383) begin
      result_o[26] <= N410;
    end 
  end


  always @(posedge clk_i) begin
    if(N442) begin
      result_o[25] <= 1'b0;
    end else if(N383) begin
      result_o[25] <= N409;
    end 
  end


  always @(posedge clk_i) begin
    if(N441) begin
      result_o[24] <= 1'b0;
    end else if(N383) begin
      result_o[24] <= N408;
    end 
  end


  always @(posedge clk_i) begin
    if(N440) begin
      result_o[23] <= 1'b0;
    end else if(N383) begin
      result_o[23] <= N407;
    end 
  end


  always @(posedge clk_i) begin
    if(N439) begin
      result_o[22] <= 1'b0;
    end else if(N383) begin
      result_o[22] <= N406;
    end 
  end


  always @(posedge clk_i) begin
    if(N438) begin
      result_o[21] <= 1'b0;
    end else if(N383) begin
      result_o[21] <= N405;
    end 
  end


  always @(posedge clk_i) begin
    if(N437) begin
      result_o[20] <= 1'b0;
    end else if(N383) begin
      result_o[20] <= N404;
    end 
  end


  always @(posedge clk_i) begin
    if(N436) begin
      result_o[19] <= 1'b0;
    end else if(N383) begin
      result_o[19] <= N403;
    end 
  end


  always @(posedge clk_i) begin
    if(N435) begin
      result_o[18] <= 1'b0;
    end else if(N383) begin
      result_o[18] <= N402;
    end 
  end


  always @(posedge clk_i) begin
    if(N434) begin
      result_o[17] <= 1'b0;
    end else if(N383) begin
      result_o[17] <= N401;
    end 
  end


  always @(posedge clk_i) begin
    if(N433) begin
      result_o[16] <= 1'b0;
    end else if(N383) begin
      result_o[16] <= N400;
    end 
  end


  always @(posedge clk_i) begin
    if(N432) begin
      result_o[15] <= 1'b0;
    end else if(N383) begin
      result_o[15] <= N399;
    end 
  end


  always @(posedge clk_i) begin
    if(N431) begin
      result_o[14] <= 1'b0;
    end else if(N383) begin
      result_o[14] <= N398;
    end 
  end


  always @(posedge clk_i) begin
    if(N430) begin
      result_o[13] <= 1'b0;
    end else if(N383) begin
      result_o[13] <= N397;
    end 
  end


  always @(posedge clk_i) begin
    if(N429) begin
      result_o[12] <= 1'b0;
    end else if(N383) begin
      result_o[12] <= N396;
    end 
  end


  always @(posedge clk_i) begin
    if(N428) begin
      result_o[11] <= 1'b0;
    end else if(N383) begin
      result_o[11] <= N395;
    end 
  end


  always @(posedge clk_i) begin
    if(N427) begin
      result_o[10] <= 1'b0;
    end else if(N383) begin
      result_o[10] <= N394;
    end 
  end


  always @(posedge clk_i) begin
    if(N426) begin
      result_o[9] <= 1'b0;
    end else if(N383) begin
      result_o[9] <= N393;
    end 
  end


  always @(posedge clk_i) begin
    if(N425) begin
      result_o[8] <= 1'b0;
    end else if(N383) begin
      result_o[8] <= N392;
    end 
  end


  always @(posedge clk_i) begin
    if(N424) begin
      result_o[7] <= 1'b0;
    end else if(N383) begin
      result_o[7] <= N391;
    end 
  end


  always @(posedge clk_i) begin
    if(N423) begin
      result_o[6] <= 1'b0;
    end else if(N383) begin
      result_o[6] <= N390;
    end 
  end


  always @(posedge clk_i) begin
    if(N422) begin
      result_o[5] <= 1'b0;
    end else if(N383) begin
      result_o[5] <= N389;
    end 
  end


  always @(posedge clk_i) begin
    if(N421) begin
      result_o[4] <= 1'b0;
    end else if(N383) begin
      result_o[4] <= N388;
    end 
  end


  always @(posedge clk_i) begin
    if(N420) begin
      result_o[3] <= 1'b0;
    end else if(N383) begin
      result_o[3] <= N387;
    end 
  end


  always @(posedge clk_i) begin
    if(N419) begin
      result_o[2] <= 1'b0;
    end else if(N383) begin
      result_o[2] <= N386;
    end 
  end


  always @(posedge clk_i) begin
    if(N418) begin
      result_o[1] <= 1'b0;
    end else if(N383) begin
      result_o[1] <= N385;
    end 
  end


  always @(posedge clk_i) begin
    if(N417) begin
      result_o[0] <= 1'b0;
    end else if(N383) begin
      result_o[0] <= N384;
    end 
  end

  assign N416 = reset_i | latch_input;
  assign N417 = reset_i | latch_input;
  assign N418 = reset_i | latch_input;
  assign N419 = reset_i | latch_input;
  assign N420 = reset_i | latch_input;
  assign N421 = reset_i | latch_input;
  assign N422 = reset_i | latch_input;
  assign N423 = reset_i | latch_input;
  assign N424 = reset_i | latch_input;
  assign N425 = reset_i | latch_input;
  assign N426 = reset_i | latch_input;
  assign N427 = reset_i | latch_input;
  assign N428 = reset_i | latch_input;
  assign N429 = reset_i | latch_input;
  assign N430 = reset_i | latch_input;
  assign N431 = reset_i | latch_input;
  assign N432 = reset_i | latch_input;
  assign N433 = reset_i | latch_input;
  assign N434 = reset_i | latch_input;
  assign N435 = reset_i | latch_input;
  assign N436 = reset_i | latch_input;
  assign N437 = reset_i | latch_input;
  assign N438 = reset_i | latch_input;
  assign N439 = reset_i | latch_input;
  assign N440 = reset_i | latch_input;
  assign N441 = reset_i | latch_input;
  assign N442 = reset_i | latch_input;
  assign N443 = reset_i | latch_input;
  assign N444 = reset_i | latch_input;
  assign N445 = reset_i | latch_input;
  assign N446 = reset_i | latch_input;
  assign N447 = reset_i | latch_input;
  assign N448 = ~curr_state_r[2];
  assign N449 = ~curr_state_r[0];
  assign N450 = curr_state_r[1] | N448;
  assign N451 = N449 | N450;
  assign v_o = ~N451;
  assign N453 = ~curr_state_r[1];
  assign N454 = N453 | curr_state_r[2];
  assign N455 = N449 | N454;
  assign N456 = ~N455;
  assign N457 = N453 | curr_state_r[2];
  assign N458 = N449 | N457;
  assign N459 = ~N458;
  assign N460 = N453 | curr_state_r[2];
  assign N461 = N449 | N460;
  assign N462 = ~N461;
  assign N463 = N453 | curr_state_r[2];
  assign N464 = N449 | N463;
  assign N465 = ~N464;
  assign N466 = curr_state_r[1] | curr_state_r[2];
  assign N467 = N449 | N466;
  assign N468 = ~N467;
  assign N469 = N453 | curr_state_r[2];
  assign N470 = N449 | N469;
  assign N471 = ~N470;
  assign N472 = N453 | curr_state_r[2];
  assign N473 = curr_state_r[0] | N472;
  assign N474 = ~N473;
  assign N475 = N453 | curr_state_r[2];
  assign N476 = N449 | N475;
  assign N477 = ~N476;
  assign N478 = curr_state_r[1] | N448;
  assign N479 = curr_state_r[0] | N478;
  assign N480 = ~N479;
  assign N481 = N453 | curr_state_r[2];
  assign N482 = N449 | N481;
  assign N483 = ~next_state[1];
  assign N484 = ~next_state[0];
  assign N485 = N483 | next_state[2];
  assign N486 = N484 | N485;
  assign N487 = ~N486;
  assign N488 = curr_state_r[1] | N448;
  assign N489 = curr_state_r[0] | N488;
  assign N490 = ~N489;
  assign N491 = curr_state_r[1] | curr_state_r[2];
  assign N492 = N449 | N491;
  assign N493 = ~N492;
  assign N494 = N453 | curr_state_r[2];
  assign N495 = curr_state_r[0] | N494;
  assign N496 = ~N495;
  assign N497 = curr_state_r[1] | N448;
  assign N498 = curr_state_r[0] | N497;
  assign N499 = ~N498;
  assign N500 = N453 | curr_state_r[2];
  assign N501 = curr_state_r[0] | N500;
  assign N502 = ~N501;
  assign N503 = curr_state_r[1] | curr_state_r[2];
  assign N504 = N449 | N503;
  assign N505 = ~N504;
  assign N506 = curr_state_r[1] | curr_state_r[2];
  assign N507 = curr_state_r[0] | N506;
  assign ready_o = ~N507;
  assign N509 = ~shift_counter_r[4];
  assign N510 = ~shift_counter_r[3];
  assign N511 = ~shift_counter_r[2];
  assign N512 = ~shift_counter_r[1];
  assign N513 = ~shift_counter_r[0];
  assign N514 = N509 | shift_counter_r[5];
  assign N515 = N510 | N514;
  assign N516 = N511 | N515;
  assign N517 = N512 | N516;
  assign N518 = N513 | N517;
  assign N519 = ~N518;
  assign N520 = ~shift_counter_r[5];
  assign N521 = shift_counter_r[4] | N520;
  assign N522 = shift_counter_r[3] | N521;
  assign N523 = shift_counter_r[2] | N522;
  assign N524 = shift_counter_r[1] | N523;
  assign N525 = shift_counter_r[0] | N524;
  assign N526 = ~N525;
  assign adder_result = adder_a + adder_b;
  assign { N58, N57, N56, N55, N54, N53 } = shift_counter_r + 1'b1;
  assign shift_counter_full = (N0)? N519 : 
                              (N1)? N526 : 1'b0;
  assign N0 = gets_high_part_r;
  assign N1 = N26;
  assign next_state = (N2)? { 1'b0, 1'b0, v_i } : 
                      (N3)? { 1'b0, 1'b1, 1'b0 } : 
                      (N4)? { 1'b0, 1'b1, 1'b1 } : 
                      (N5)? { shift_counter_full, N45, N45 } : 
                      (N6)? { 1'b1, 1'b0, 1'b1 } : 
                      (N7)? { N46, 1'b0, N46 } : 
                      (N8)? { 1'b0, 1'b0, 1'b0 } : 1'b0;
  assign N2 = N28;
  assign N3 = N31;
  assign N4 = N34;
  assign N5 = N37;
  assign N6 = N40;
  assign N7 = N43;
  assign N8 = N44;
  assign N59 = (N9)? 1'b1 : 
               (N67)? 1'b1 : 
               (N51)? 1'b0 : 1'b0;
  assign N9 = N49;
  assign { N65, N64, N63, N62, N61, N60 } = (N9)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                                            (N67)? { N58, N57, N56, N55, N54, N53 } : 1'b0;
  assign adder_a = (N10)? { N71, N72, N73, N74, N75, N76, N77, N78, N79, N80, N81, N82, N83, N84, N85, N86, N87, N88, N89, N90, N91, N92, N93, N94, N95, N96, N97, N98, N99, N100, N101, N102 } : 
                   (N11)? { N103, N104, N105, N106, N107, N108, N109, N110, N111, N112, N113, N114, N115, N116, N117, N118, N119, N120, N121, N122, N123, N124, N125, N126, N127, N128, N129, N130, N131, N132, N133, N134 } : 
                   (N12)? { N135, N136, N137, N138, N139, N140, N141, N142, N143, N144, N145, N146, N147, N148, N149, N150, N151, N152, N153, N154, N155, N156, N157, N158, N159, N160, N161, N162, N163, N164, N165, N166 } : 
                   (N70)? result_o : 1'b0;
  assign N10 = N505;
  assign N11 = N502;
  assign N12 = N490;
  assign adder_b = (N13)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b1 } : 
                   (N14)? opA_r : 1'b0;
  assign N13 = adder_neg_op;
  assign N14 = N167;
  assign N174 = (N15)? 1'b1 : 
                (N16)? 1'b1 : 
                (N173)? 1'b0 : 1'b0;
  assign N15 = N170;
  assign N16 = N171;
  assign { N206, N205, N204, N203, N202, N201, N200, N199, N198, N197, N196, N195, N194, N193, N192, N191, N190, N189, N188, N187, N186, N185, N184, N183, N182, N181, N180, N179, N178, N177, N176, N175 } = (N15)? { opA_r[30:0], 1'b0 } : 
                                                                                                                                                                                                              (N16)? adder_result[31:0] : 1'b0;
  assign N207 = (N17)? 1'b1 : 
                (N18)? N174 : 1'b0;
  assign N17 = latch_input;
  assign N18 = N169;
  assign { N239, N238, N237, N236, N235, N234, N233, N232, N231, N230, N229, N228, N227, N226, N225, N224, N223, N222, N221, N220, N219, N218, N217, N216, N215, N214, N213, N212, N211, N210, N209, N208 } = (N17)? opA_i : 
                                                                                                                                                                                                              (N18)? { N206, N205, N204, N203, N202, N201, N200, N199, N198, N197, N196, N195, N194, N193, N192, N191, N190, N189, N188, N187, N186, N185, N184, N183, N182, N181, N180, N179, N178, N177, N176, N175 } : 1'b0;
  assign N243 = (N19)? 1'b1 : 
                (N20)? 1'b1 : 
                (N242)? 1'b0 : 1'b0;
  assign N19 = N459;
  assign N20 = N240;
  assign { N275, N274, N273, N272, N271, N270, N269, N268, N267, N266, N265, N264, N263, N262, N261, N260, N259, N258, N257, N256, N255, N254, N253, N252, N251, N250, N249, N248, N247, N246, N245, N244 } = (N19)? { 1'b0, opB_r[31:1] } : 
                                                                                                                                                                                                              (N20)? adder_result[31:0] : 1'b0;
  assign N276 = (N17)? 1'b1 : 
                (N18)? N243 : 1'b0;
  assign { N308, N307, N306, N305, N304, N303, N302, N301, N300, N299, N298, N297, N296, N295, N294, N293, N292, N291, N290, N289, N288, N287, N286, N285, N284, N283, N282, N281, N280, N279, N278, N277 } = (N17)? opB_i : 
                                                                                                                                                                                                              (N18)? { N275, N274, N273, N272, N271, N270, N269, N268, N267, N266, N265, N264, N263, N262, N261, N260, N259, N258, N257, N256, N255, N254, N253, N252, N251, N250, N249, N248, N247, N246, N245, N244 } : 1'b0;
  assign shifted_lsb = (N21)? adder_result[0] : 
                       (N309)? result_o[0] : 1'b0;
  assign N21 = opB_r[0];
  assign { N350, N349, N348, N347, N346, N345, N344, N343, N342, N341, N340, N339, N338, N337, N336, N335, N334, N333, N332, N331, N330, N329, N328, N327, N326, N325, N324, N323, N322, N321, N320, N319 } = (N22)? { N135, N136, N137, N138, N139, N140, N141, N142, N143, N144, N145, N146, N147, N148, N149, N150, N151, N152, N153, N154, N155, N156, N157, N158, N159, N160, N161, N162, N163, N164, N165, N166 } : 
                                                                                                                                                                                                              (N318)? adder_result[31:0] : 1'b0;
  assign N22 = N317;
  assign { N382, N381, N380, N379, N378, N377, N376, N375, N374, N373, N372, N371, N370, N369, N368, N367, N366, N365, N364, N363, N362, N361, N360, N359, N358, N357, N356, N355, N354, N353, N352, N351 } = (N0)? adder_result[32:1] : 
                                                                                                                                                                                                              (N1)? adder_result[31:0] : 1'b0;
  assign N383 = (N23)? 1'b1 : 
                (N24)? 1'b1 : 
                (N25)? gets_high_part_r : 
                (N316)? 1'b0 : 1'b0;
  assign N23 = N311;
  assign N24 = N312;
  assign N25 = N313;
  assign { N415, N414, N413, N412, N411, N410, N409, N408, N407, N406, N405, N404, N403, N402, N401, N400, N399, N398, N397, N396, N395, N394, N393, N392, N391, N390, N389, N388, N387, N386, N385, N384 } = (N23)? { N350, N349, N348, N347, N346, N345, N344, N343, N342, N341, N340, N339, N338, N337, N336, N335, N334, N333, N332, N331, N330, N329, N328, N327, N326, N325, N324, N323, N322, N321, N320, N319 } : 
                                                                                                                                                                                                              (N24)? { N382, N381, N380, N379, N378, N377, N376, N375, N374, N373, N372, N371, N370, N369, N368, N367, N366, N365, N364, N363, N362, N361, N360, N359, N358, N357, N356, N355, N354, N353, N352, N351 } : 
                                                                                                                                                                                                              (N25)? { 1'b0, result_o[31:1] } : 1'b0;
  assign N26 = ~gets_high_part_r;
  assign N31 = ~N30;
  assign N34 = ~N33;
  assign N37 = ~N36;
  assign N40 = ~N39;
  assign N43 = ~N42;
  assign N45 = ~shift_counter_full;
  assign N46 = ~yumi_i;
  assign N47 = ~reset_i;
  assign N48 = N47;
  assign N49 = N482 & N487;
  assign N50 = N465 | N49;
  assign N51 = ~N50;
  assign N52 = N48 & N67;
  assign N66 = ~N49;
  assign N67 = N465 & N66;
  assign N68 = N502 | N505;
  assign N69 = N490 | N68;
  assign N70 = ~N69;
  assign N71 = ~opA_r[31];
  assign N72 = ~opA_r[30];
  assign N73 = ~opA_r[29];
  assign N74 = ~opA_r[28];
  assign N75 = ~opA_r[27];
  assign N76 = ~opA_r[26];
  assign N77 = ~opA_r[25];
  assign N78 = ~opA_r[24];
  assign N79 = ~opA_r[23];
  assign N80 = ~opA_r[22];
  assign N81 = ~opA_r[21];
  assign N82 = ~opA_r[20];
  assign N83 = ~opA_r[19];
  assign N84 = ~opA_r[18];
  assign N85 = ~opA_r[17];
  assign N86 = ~opA_r[16];
  assign N87 = ~opA_r[15];
  assign N88 = ~opA_r[14];
  assign N89 = ~opA_r[13];
  assign N90 = ~opA_r[12];
  assign N91 = ~opA_r[11];
  assign N92 = ~opA_r[10];
  assign N93 = ~opA_r[9];
  assign N94 = ~opA_r[8];
  assign N95 = ~opA_r[7];
  assign N96 = ~opA_r[6];
  assign N97 = ~opA_r[5];
  assign N98 = ~opA_r[4];
  assign N99 = ~opA_r[3];
  assign N100 = ~opA_r[2];
  assign N101 = ~opA_r[1];
  assign N102 = ~opA_r[0];
  assign N103 = ~opB_r[31];
  assign N104 = ~opB_r[30];
  assign N105 = ~opB_r[29];
  assign N106 = ~opB_r[28];
  assign N107 = ~opB_r[27];
  assign N108 = ~opB_r[26];
  assign N109 = ~opB_r[25];
  assign N110 = ~opB_r[24];
  assign N111 = ~opB_r[23];
  assign N112 = ~opB_r[22];
  assign N113 = ~opB_r[21];
  assign N114 = ~opB_r[20];
  assign N115 = ~opB_r[19];
  assign N116 = ~opB_r[18];
  assign N117 = ~opB_r[17];
  assign N118 = ~opB_r[16];
  assign N119 = ~opB_r[15];
  assign N120 = ~opB_r[14];
  assign N121 = ~opB_r[13];
  assign N122 = ~opB_r[12];
  assign N123 = ~opB_r[11];
  assign N124 = ~opB_r[10];
  assign N125 = ~opB_r[9];
  assign N126 = ~opB_r[8];
  assign N127 = ~opB_r[7];
  assign N128 = ~opB_r[6];
  assign N129 = ~opB_r[5];
  assign N130 = ~opB_r[4];
  assign N131 = ~opB_r[3];
  assign N132 = ~opB_r[2];
  assign N133 = ~opB_r[1];
  assign N134 = ~opB_r[0];
  assign N135 = ~result_o[31];
  assign N136 = ~result_o[30];
  assign N137 = ~result_o[29];
  assign N138 = ~result_o[28];
  assign N139 = ~result_o[27];
  assign N140 = ~result_o[26];
  assign N141 = ~result_o[25];
  assign N142 = ~result_o[24];
  assign N143 = ~result_o[23];
  assign N144 = ~result_o[22];
  assign N145 = ~result_o[21];
  assign N146 = ~result_o[20];
  assign N147 = ~result_o[19];
  assign N148 = ~result_o[18];
  assign N149 = ~result_o[17];
  assign N150 = ~result_o[16];
  assign N151 = ~result_o[15];
  assign N152 = ~result_o[14];
  assign N153 = ~result_o[13];
  assign N154 = ~result_o[12];
  assign N155 = ~result_o[11];
  assign N156 = ~result_o[10];
  assign N157 = ~result_o[9];
  assign N158 = ~result_o[8];
  assign N159 = ~result_o[7];
  assign N160 = ~result_o[6];
  assign N161 = ~result_o[5];
  assign N162 = ~result_o[4];
  assign N163 = ~result_o[3];
  assign N164 = ~result_o[2];
  assign N165 = ~result_o[1];
  assign N166 = ~result_o[0];
  assign adder_neg_op = N527 | N499;
  assign N527 = N493 | N496;
  assign N167 = ~adder_neg_op;
  assign latch_input = v_i & ready_o;
  assign signed_opA = signed_opA_i & opA_i[31];
  assign signed_opB = signed_opB_i & opB_i[31];
  assign N168 = signed_opA ^ signed_opB;
  assign N169 = ~latch_input;
  assign N170 = N471 & N26;
  assign N171 = N468 & signed_opA_r;
  assign N172 = N171 | N170;
  assign N173 = ~N172;
  assign N240 = N474 & signed_opB_r;
  assign N241 = N240 | N459;
  assign N242 = ~N241;
  assign N309 = ~opB_r[0];
  assign N310 = all_sh_lsb_zero_r & N528;
  assign N528 = ~shifted_lsb;
  assign N311 = N480 & need_neg_result_r;
  assign N312 = N477 & opB_r[0];
  assign N313 = N462 & N134;
  assign N314 = N312 | N311;
  assign N315 = N313 | N314;
  assign N316 = ~N315;
  assign N317 = gets_high_part_r & N529;
  assign N529 = ~all_sh_lsb_zero_r;
  assign N318 = ~N317;

endmodule



module bsg_buf_width_p32
(
  i,
  o
);

  input [31:0] i;
  output [31:0] o;
  wire [31:0] o;
  assign o[31] = i[31];
  assign o[30] = i[30];
  assign o[29] = i[29];
  assign o[28] = i[28];
  assign o[27] = i[27];
  assign o[26] = i[26];
  assign o[25] = i[25];
  assign o[24] = i[24];
  assign o[23] = i[23];
  assign o[22] = i[22];
  assign o[21] = i[21];
  assign o[20] = i[20];
  assign o[19] = i[19];
  assign o[18] = i[18];
  assign o[17] = i[17];
  assign o[16] = i[16];
  assign o[15] = i[15];
  assign o[14] = i[14];
  assign o[13] = i[13];
  assign o[12] = i[12];
  assign o[11] = i[11];
  assign o[10] = i[10];
  assign o[9] = i[9];
  assign o[8] = i[8];
  assign o[7] = i[7];
  assign o[6] = i[6];
  assign o[5] = i[5];
  assign o[4] = i[4];
  assign o[3] = i[3];
  assign o[2] = i[2];
  assign o[1] = i[1];
  assign o[0] = i[0];

endmodule



module bsg_dff_en_width_p1
(
  clock_i,
  data_i,
  en_i,
  data_o
);

  input [0:0] data_i;
  output [0:0] data_o;
  input clock_i;
  input en_i;
  reg [0:0] data_o;

  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[0] <= data_i[0];
    end 
  end


endmodule



module bsg_dff_en_width_p32
(
  clock_i,
  data_i,
  en_i,
  data_o
);

  input [31:0] data_i;
  output [31:0] data_o;
  input clock_i;
  input en_i;
  reg [31:0] data_o;

  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[31] <= data_i[31];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[30] <= data_i[30];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[29] <= data_i[29];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[28] <= data_i[28];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[27] <= data_i[27];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[26] <= data_i[26];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[25] <= data_i[25];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[24] <= data_i[24];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[23] <= data_i[23];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[22] <= data_i[22];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[21] <= data_i[21];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[20] <= data_i[20];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[19] <= data_i[19];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[18] <= data_i[18];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[17] <= data_i[17];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[16] <= data_i[16];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[15] <= data_i[15];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[14] <= data_i[14];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[13] <= data_i[13];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[12] <= data_i[12];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[11] <= data_i[11];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[10] <= data_i[10];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[9] <= data_i[9];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[8] <= data_i[8];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[7] <= data_i[7];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[6] <= data_i[6];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[5] <= data_i[5];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[4] <= data_i[4];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[3] <= data_i[3];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[2] <= data_i[2];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[1] <= data_i[1];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[0] <= data_i[0];
    end 
  end


endmodule



module bsg_mux_width_p33_els_p2
(
  data_i,
  sel_i,
  data_o
);

  input [65:0] data_i;
  input [0:0] sel_i;
  output [32:0] data_o;
  wire [32:0] data_o;
  wire N0,N1;
  assign data_o[32] = (N1)? data_i[32] : 
                      (N0)? data_i[65] : 1'b0;
  assign N0 = sel_i[0];
  assign data_o[31] = (N1)? data_i[31] : 
                      (N0)? data_i[64] : 1'b0;
  assign data_o[30] = (N1)? data_i[30] : 
                      (N0)? data_i[63] : 1'b0;
  assign data_o[29] = (N1)? data_i[29] : 
                      (N0)? data_i[62] : 1'b0;
  assign data_o[28] = (N1)? data_i[28] : 
                      (N0)? data_i[61] : 1'b0;
  assign data_o[27] = (N1)? data_i[27] : 
                      (N0)? data_i[60] : 1'b0;
  assign data_o[26] = (N1)? data_i[26] : 
                      (N0)? data_i[59] : 1'b0;
  assign data_o[25] = (N1)? data_i[25] : 
                      (N0)? data_i[58] : 1'b0;
  assign data_o[24] = (N1)? data_i[24] : 
                      (N0)? data_i[57] : 1'b0;
  assign data_o[23] = (N1)? data_i[23] : 
                      (N0)? data_i[56] : 1'b0;
  assign data_o[22] = (N1)? data_i[22] : 
                      (N0)? data_i[55] : 1'b0;
  assign data_o[21] = (N1)? data_i[21] : 
                      (N0)? data_i[54] : 1'b0;
  assign data_o[20] = (N1)? data_i[20] : 
                      (N0)? data_i[53] : 1'b0;
  assign data_o[19] = (N1)? data_i[19] : 
                      (N0)? data_i[52] : 1'b0;
  assign data_o[18] = (N1)? data_i[18] : 
                      (N0)? data_i[51] : 1'b0;
  assign data_o[17] = (N1)? data_i[17] : 
                      (N0)? data_i[50] : 1'b0;
  assign data_o[16] = (N1)? data_i[16] : 
                      (N0)? data_i[49] : 1'b0;
  assign data_o[15] = (N1)? data_i[15] : 
                      (N0)? data_i[48] : 1'b0;
  assign data_o[14] = (N1)? data_i[14] : 
                      (N0)? data_i[47] : 1'b0;
  assign data_o[13] = (N1)? data_i[13] : 
                      (N0)? data_i[46] : 1'b0;
  assign data_o[12] = (N1)? data_i[12] : 
                      (N0)? data_i[45] : 1'b0;
  assign data_o[11] = (N1)? data_i[11] : 
                      (N0)? data_i[44] : 1'b0;
  assign data_o[10] = (N1)? data_i[10] : 
                      (N0)? data_i[43] : 1'b0;
  assign data_o[9] = (N1)? data_i[9] : 
                     (N0)? data_i[42] : 1'b0;
  assign data_o[8] = (N1)? data_i[8] : 
                     (N0)? data_i[41] : 1'b0;
  assign data_o[7] = (N1)? data_i[7] : 
                     (N0)? data_i[40] : 1'b0;
  assign data_o[6] = (N1)? data_i[6] : 
                     (N0)? data_i[39] : 1'b0;
  assign data_o[5] = (N1)? data_i[5] : 
                     (N0)? data_i[38] : 1'b0;
  assign data_o[4] = (N1)? data_i[4] : 
                     (N0)? data_i[37] : 1'b0;
  assign data_o[3] = (N1)? data_i[3] : 
                     (N0)? data_i[36] : 1'b0;
  assign data_o[2] = (N1)? data_i[2] : 
                     (N0)? data_i[35] : 1'b0;
  assign data_o[1] = (N1)? data_i[1] : 
                     (N0)? data_i[34] : 1'b0;
  assign data_o[0] = (N1)? data_i[0] : 
                     (N0)? data_i[33] : 1'b0;
  assign N1 = ~sel_i[0];

endmodule



module bsg_mux_one_hot_width_p33_els_p3
(
  data_i,
  sel_one_hot_i,
  data_o
);

  input [98:0] data_i;
  input [2:0] sel_one_hot_i;
  output [32:0] data_o;
  wire [32:0] data_o;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,
  N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32;
  wire [98:0] data_masked;
  assign data_masked[32] = data_i[32] & sel_one_hot_i[0];
  assign data_masked[31] = data_i[31] & sel_one_hot_i[0];
  assign data_masked[30] = data_i[30] & sel_one_hot_i[0];
  assign data_masked[29] = data_i[29] & sel_one_hot_i[0];
  assign data_masked[28] = data_i[28] & sel_one_hot_i[0];
  assign data_masked[27] = data_i[27] & sel_one_hot_i[0];
  assign data_masked[26] = data_i[26] & sel_one_hot_i[0];
  assign data_masked[25] = data_i[25] & sel_one_hot_i[0];
  assign data_masked[24] = data_i[24] & sel_one_hot_i[0];
  assign data_masked[23] = data_i[23] & sel_one_hot_i[0];
  assign data_masked[22] = data_i[22] & sel_one_hot_i[0];
  assign data_masked[21] = data_i[21] & sel_one_hot_i[0];
  assign data_masked[20] = data_i[20] & sel_one_hot_i[0];
  assign data_masked[19] = data_i[19] & sel_one_hot_i[0];
  assign data_masked[18] = data_i[18] & sel_one_hot_i[0];
  assign data_masked[17] = data_i[17] & sel_one_hot_i[0];
  assign data_masked[16] = data_i[16] & sel_one_hot_i[0];
  assign data_masked[15] = data_i[15] & sel_one_hot_i[0];
  assign data_masked[14] = data_i[14] & sel_one_hot_i[0];
  assign data_masked[13] = data_i[13] & sel_one_hot_i[0];
  assign data_masked[12] = data_i[12] & sel_one_hot_i[0];
  assign data_masked[11] = data_i[11] & sel_one_hot_i[0];
  assign data_masked[10] = data_i[10] & sel_one_hot_i[0];
  assign data_masked[9] = data_i[9] & sel_one_hot_i[0];
  assign data_masked[8] = data_i[8] & sel_one_hot_i[0];
  assign data_masked[7] = data_i[7] & sel_one_hot_i[0];
  assign data_masked[6] = data_i[6] & sel_one_hot_i[0];
  assign data_masked[5] = data_i[5] & sel_one_hot_i[0];
  assign data_masked[4] = data_i[4] & sel_one_hot_i[0];
  assign data_masked[3] = data_i[3] & sel_one_hot_i[0];
  assign data_masked[2] = data_i[2] & sel_one_hot_i[0];
  assign data_masked[1] = data_i[1] & sel_one_hot_i[0];
  assign data_masked[0] = data_i[0] & sel_one_hot_i[0];
  assign data_masked[65] = data_i[65] & sel_one_hot_i[1];
  assign data_masked[64] = data_i[64] & sel_one_hot_i[1];
  assign data_masked[63] = data_i[63] & sel_one_hot_i[1];
  assign data_masked[62] = data_i[62] & sel_one_hot_i[1];
  assign data_masked[61] = data_i[61] & sel_one_hot_i[1];
  assign data_masked[60] = data_i[60] & sel_one_hot_i[1];
  assign data_masked[59] = data_i[59] & sel_one_hot_i[1];
  assign data_masked[58] = data_i[58] & sel_one_hot_i[1];
  assign data_masked[57] = data_i[57] & sel_one_hot_i[1];
  assign data_masked[56] = data_i[56] & sel_one_hot_i[1];
  assign data_masked[55] = data_i[55] & sel_one_hot_i[1];
  assign data_masked[54] = data_i[54] & sel_one_hot_i[1];
  assign data_masked[53] = data_i[53] & sel_one_hot_i[1];
  assign data_masked[52] = data_i[52] & sel_one_hot_i[1];
  assign data_masked[51] = data_i[51] & sel_one_hot_i[1];
  assign data_masked[50] = data_i[50] & sel_one_hot_i[1];
  assign data_masked[49] = data_i[49] & sel_one_hot_i[1];
  assign data_masked[48] = data_i[48] & sel_one_hot_i[1];
  assign data_masked[47] = data_i[47] & sel_one_hot_i[1];
  assign data_masked[46] = data_i[46] & sel_one_hot_i[1];
  assign data_masked[45] = data_i[45] & sel_one_hot_i[1];
  assign data_masked[44] = data_i[44] & sel_one_hot_i[1];
  assign data_masked[43] = data_i[43] & sel_one_hot_i[1];
  assign data_masked[42] = data_i[42] & sel_one_hot_i[1];
  assign data_masked[41] = data_i[41] & sel_one_hot_i[1];
  assign data_masked[40] = data_i[40] & sel_one_hot_i[1];
  assign data_masked[39] = data_i[39] & sel_one_hot_i[1];
  assign data_masked[38] = data_i[38] & sel_one_hot_i[1];
  assign data_masked[37] = data_i[37] & sel_one_hot_i[1];
  assign data_masked[36] = data_i[36] & sel_one_hot_i[1];
  assign data_masked[35] = data_i[35] & sel_one_hot_i[1];
  assign data_masked[34] = data_i[34] & sel_one_hot_i[1];
  assign data_masked[33] = data_i[33] & sel_one_hot_i[1];
  assign data_masked[98] = data_i[98] & sel_one_hot_i[2];
  assign data_masked[97] = data_i[97] & sel_one_hot_i[2];
  assign data_masked[96] = data_i[96] & sel_one_hot_i[2];
  assign data_masked[95] = data_i[95] & sel_one_hot_i[2];
  assign data_masked[94] = data_i[94] & sel_one_hot_i[2];
  assign data_masked[93] = data_i[93] & sel_one_hot_i[2];
  assign data_masked[92] = data_i[92] & sel_one_hot_i[2];
  assign data_masked[91] = data_i[91] & sel_one_hot_i[2];
  assign data_masked[90] = data_i[90] & sel_one_hot_i[2];
  assign data_masked[89] = data_i[89] & sel_one_hot_i[2];
  assign data_masked[88] = data_i[88] & sel_one_hot_i[2];
  assign data_masked[87] = data_i[87] & sel_one_hot_i[2];
  assign data_masked[86] = data_i[86] & sel_one_hot_i[2];
  assign data_masked[85] = data_i[85] & sel_one_hot_i[2];
  assign data_masked[84] = data_i[84] & sel_one_hot_i[2];
  assign data_masked[83] = data_i[83] & sel_one_hot_i[2];
  assign data_masked[82] = data_i[82] & sel_one_hot_i[2];
  assign data_masked[81] = data_i[81] & sel_one_hot_i[2];
  assign data_masked[80] = data_i[80] & sel_one_hot_i[2];
  assign data_masked[79] = data_i[79] & sel_one_hot_i[2];
  assign data_masked[78] = data_i[78] & sel_one_hot_i[2];
  assign data_masked[77] = data_i[77] & sel_one_hot_i[2];
  assign data_masked[76] = data_i[76] & sel_one_hot_i[2];
  assign data_masked[75] = data_i[75] & sel_one_hot_i[2];
  assign data_masked[74] = data_i[74] & sel_one_hot_i[2];
  assign data_masked[73] = data_i[73] & sel_one_hot_i[2];
  assign data_masked[72] = data_i[72] & sel_one_hot_i[2];
  assign data_masked[71] = data_i[71] & sel_one_hot_i[2];
  assign data_masked[70] = data_i[70] & sel_one_hot_i[2];
  assign data_masked[69] = data_i[69] & sel_one_hot_i[2];
  assign data_masked[68] = data_i[68] & sel_one_hot_i[2];
  assign data_masked[67] = data_i[67] & sel_one_hot_i[2];
  assign data_masked[66] = data_i[66] & sel_one_hot_i[2];
  assign data_o[0] = N0 | data_masked[0];
  assign N0 = data_masked[66] | data_masked[33];
  assign data_o[1] = N1 | data_masked[1];
  assign N1 = data_masked[67] | data_masked[34];
  assign data_o[2] = N2 | data_masked[2];
  assign N2 = data_masked[68] | data_masked[35];
  assign data_o[3] = N3 | data_masked[3];
  assign N3 = data_masked[69] | data_masked[36];
  assign data_o[4] = N4 | data_masked[4];
  assign N4 = data_masked[70] | data_masked[37];
  assign data_o[5] = N5 | data_masked[5];
  assign N5 = data_masked[71] | data_masked[38];
  assign data_o[6] = N6 | data_masked[6];
  assign N6 = data_masked[72] | data_masked[39];
  assign data_o[7] = N7 | data_masked[7];
  assign N7 = data_masked[73] | data_masked[40];
  assign data_o[8] = N8 | data_masked[8];
  assign N8 = data_masked[74] | data_masked[41];
  assign data_o[9] = N9 | data_masked[9];
  assign N9 = data_masked[75] | data_masked[42];
  assign data_o[10] = N10 | data_masked[10];
  assign N10 = data_masked[76] | data_masked[43];
  assign data_o[11] = N11 | data_masked[11];
  assign N11 = data_masked[77] | data_masked[44];
  assign data_o[12] = N12 | data_masked[12];
  assign N12 = data_masked[78] | data_masked[45];
  assign data_o[13] = N13 | data_masked[13];
  assign N13 = data_masked[79] | data_masked[46];
  assign data_o[14] = N14 | data_masked[14];
  assign N14 = data_masked[80] | data_masked[47];
  assign data_o[15] = N15 | data_masked[15];
  assign N15 = data_masked[81] | data_masked[48];
  assign data_o[16] = N16 | data_masked[16];
  assign N16 = data_masked[82] | data_masked[49];
  assign data_o[17] = N17 | data_masked[17];
  assign N17 = data_masked[83] | data_masked[50];
  assign data_o[18] = N18 | data_masked[18];
  assign N18 = data_masked[84] | data_masked[51];
  assign data_o[19] = N19 | data_masked[19];
  assign N19 = data_masked[85] | data_masked[52];
  assign data_o[20] = N20 | data_masked[20];
  assign N20 = data_masked[86] | data_masked[53];
  assign data_o[21] = N21 | data_masked[21];
  assign N21 = data_masked[87] | data_masked[54];
  assign data_o[22] = N22 | data_masked[22];
  assign N22 = data_masked[88] | data_masked[55];
  assign data_o[23] = N23 | data_masked[23];
  assign N23 = data_masked[89] | data_masked[56];
  assign data_o[24] = N24 | data_masked[24];
  assign N24 = data_masked[90] | data_masked[57];
  assign data_o[25] = N25 | data_masked[25];
  assign N25 = data_masked[91] | data_masked[58];
  assign data_o[26] = N26 | data_masked[26];
  assign N26 = data_masked[92] | data_masked[59];
  assign data_o[27] = N27 | data_masked[27];
  assign N27 = data_masked[93] | data_masked[60];
  assign data_o[28] = N28 | data_masked[28];
  assign N28 = data_masked[94] | data_masked[61];
  assign data_o[29] = N29 | data_masked[29];
  assign N29 = data_masked[95] | data_masked[62];
  assign data_o[30] = N30 | data_masked[30];
  assign N30 = data_masked[96] | data_masked[63];
  assign data_o[31] = N31 | data_masked[31];
  assign N31 = data_masked[97] | data_masked[64];
  assign data_o[32] = N32 | data_masked[32];
  assign N32 = data_masked[98] | data_masked[65];

endmodule



module bsg_dff_en_width_p33
(
  clock_i,
  data_i,
  en_i,
  data_o
);

  input [32:0] data_i;
  output [32:0] data_o;
  input clock_i;
  input en_i;
  reg [32:0] data_o;

  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[32] <= data_i[32];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[31] <= data_i[31];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[30] <= data_i[30];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[29] <= data_i[29];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[28] <= data_i[28];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[27] <= data_i[27];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[26] <= data_i[26];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[25] <= data_i[25];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[24] <= data_i[24];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[23] <= data_i[23];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[22] <= data_i[22];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[21] <= data_i[21];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[20] <= data_i[20];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[19] <= data_i[19];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[18] <= data_i[18];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[17] <= data_i[17];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[16] <= data_i[16];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[15] <= data_i[15];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[14] <= data_i[14];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[13] <= data_i[13];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[12] <= data_i[12];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[11] <= data_i[11];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[10] <= data_i[10];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[9] <= data_i[9];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[8] <= data_i[8];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[7] <= data_i[7];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[6] <= data_i[6];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[5] <= data_i[5];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[4] <= data_i[4];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[3] <= data_i[3];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[2] <= data_i[2];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[1] <= data_i[1];
    end 
  end


  always @(posedge clock_i) begin
    if(en_i) begin
      data_o[0] <= data_i[0];
    end 
  end


endmodule



module bsg_buf_ctrl_width_p33
(
  i,
  o
);

  output [32:0] o;
  input i;
  wire [32:0] o;
  wire i;
  assign o[0] = i;
  assign o[1] = i;
  assign o[2] = i;
  assign o[3] = i;
  assign o[4] = i;
  assign o[5] = i;
  assign o[6] = i;
  assign o[7] = i;
  assign o[8] = i;
  assign o[9] = i;
  assign o[10] = i;
  assign o[11] = i;
  assign o[12] = i;
  assign o[13] = i;
  assign o[14] = i;
  assign o[15] = i;
  assign o[16] = i;
  assign o[17] = i;
  assign o[18] = i;
  assign o[19] = i;
  assign o[20] = i;
  assign o[21] = i;
  assign o[22] = i;
  assign o[23] = i;
  assign o[24] = i;
  assign o[25] = i;
  assign o[26] = i;
  assign o[27] = i;
  assign o[28] = i;
  assign o[29] = i;
  assign o[30] = i;
  assign o[31] = i;
  assign o[32] = i;

endmodule



module bsg_xnor_width_p33
(
  a_i,
  b_i,
  o
);

  input [32:0] a_i;
  input [32:0] b_i;
  output [32:0] o;
  wire [32:0] o;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,
  N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32;
  assign o[32] = ~N0;
  assign N0 = a_i[32] ^ b_i[32];
  assign o[31] = ~N1;
  assign N1 = a_i[31] ^ b_i[31];
  assign o[30] = ~N2;
  assign N2 = a_i[30] ^ b_i[30];
  assign o[29] = ~N3;
  assign N3 = a_i[29] ^ b_i[29];
  assign o[28] = ~N4;
  assign N4 = a_i[28] ^ b_i[28];
  assign o[27] = ~N5;
  assign N5 = a_i[27] ^ b_i[27];
  assign o[26] = ~N6;
  assign N6 = a_i[26] ^ b_i[26];
  assign o[25] = ~N7;
  assign N7 = a_i[25] ^ b_i[25];
  assign o[24] = ~N8;
  assign N8 = a_i[24] ^ b_i[24];
  assign o[23] = ~N9;
  assign N9 = a_i[23] ^ b_i[23];
  assign o[22] = ~N10;
  assign N10 = a_i[22] ^ b_i[22];
  assign o[21] = ~N11;
  assign N11 = a_i[21] ^ b_i[21];
  assign o[20] = ~N12;
  assign N12 = a_i[20] ^ b_i[20];
  assign o[19] = ~N13;
  assign N13 = a_i[19] ^ b_i[19];
  assign o[18] = ~N14;
  assign N14 = a_i[18] ^ b_i[18];
  assign o[17] = ~N15;
  assign N15 = a_i[17] ^ b_i[17];
  assign o[16] = ~N16;
  assign N16 = a_i[16] ^ b_i[16];
  assign o[15] = ~N17;
  assign N17 = a_i[15] ^ b_i[15];
  assign o[14] = ~N18;
  assign N18 = a_i[14] ^ b_i[14];
  assign o[13] = ~N19;
  assign N19 = a_i[13] ^ b_i[13];
  assign o[12] = ~N20;
  assign N20 = a_i[12] ^ b_i[12];
  assign o[11] = ~N21;
  assign N21 = a_i[11] ^ b_i[11];
  assign o[10] = ~N22;
  assign N22 = a_i[10] ^ b_i[10];
  assign o[9] = ~N23;
  assign N23 = a_i[9] ^ b_i[9];
  assign o[8] = ~N24;
  assign N24 = a_i[8] ^ b_i[8];
  assign o[7] = ~N25;
  assign N25 = a_i[7] ^ b_i[7];
  assign o[6] = ~N26;
  assign N26 = a_i[6] ^ b_i[6];
  assign o[5] = ~N27;
  assign N27 = a_i[5] ^ b_i[5];
  assign o[4] = ~N28;
  assign N28 = a_i[4] ^ b_i[4];
  assign o[3] = ~N29;
  assign N29 = a_i[3] ^ b_i[3];
  assign o[2] = ~N30;
  assign N30 = a_i[2] ^ b_i[2];
  assign o[1] = ~N31;
  assign N31 = a_i[1] ^ b_i[1];
  assign o[0] = ~N32;
  assign N32 = a_i[0] ^ b_i[0];

endmodule



module bsg_nor2_width_p33
(
  a_i,
  b_i,
  o
);

  input [32:0] a_i;
  input [32:0] b_i;
  output [32:0] o;
  wire [32:0] o;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,
  N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32;
  assign o[32] = ~N0;
  assign N0 = a_i[32] | b_i[32];
  assign o[31] = ~N1;
  assign N1 = a_i[31] | b_i[31];
  assign o[30] = ~N2;
  assign N2 = a_i[30] | b_i[30];
  assign o[29] = ~N3;
  assign N3 = a_i[29] | b_i[29];
  assign o[28] = ~N4;
  assign N4 = a_i[28] | b_i[28];
  assign o[27] = ~N5;
  assign N5 = a_i[27] | b_i[27];
  assign o[26] = ~N6;
  assign N6 = a_i[26] | b_i[26];
  assign o[25] = ~N7;
  assign N7 = a_i[25] | b_i[25];
  assign o[24] = ~N8;
  assign N8 = a_i[24] | b_i[24];
  assign o[23] = ~N9;
  assign N9 = a_i[23] | b_i[23];
  assign o[22] = ~N10;
  assign N10 = a_i[22] | b_i[22];
  assign o[21] = ~N11;
  assign N11 = a_i[21] | b_i[21];
  assign o[20] = ~N12;
  assign N12 = a_i[20] | b_i[20];
  assign o[19] = ~N13;
  assign N13 = a_i[19] | b_i[19];
  assign o[18] = ~N14;
  assign N14 = a_i[18] | b_i[18];
  assign o[17] = ~N15;
  assign N15 = a_i[17] | b_i[17];
  assign o[16] = ~N16;
  assign N16 = a_i[16] | b_i[16];
  assign o[15] = ~N17;
  assign N17 = a_i[15] | b_i[15];
  assign o[14] = ~N18;
  assign N18 = a_i[14] | b_i[14];
  assign o[13] = ~N19;
  assign N19 = a_i[13] | b_i[13];
  assign o[12] = ~N20;
  assign N20 = a_i[12] | b_i[12];
  assign o[11] = ~N21;
  assign N21 = a_i[11] | b_i[11];
  assign o[10] = ~N22;
  assign N22 = a_i[10] | b_i[10];
  assign o[9] = ~N23;
  assign N23 = a_i[9] | b_i[9];
  assign o[8] = ~N24;
  assign N24 = a_i[8] | b_i[8];
  assign o[7] = ~N25;
  assign N25 = a_i[7] | b_i[7];
  assign o[6] = ~N26;
  assign N26 = a_i[6] | b_i[6];
  assign o[5] = ~N27;
  assign N27 = a_i[5] | b_i[5];
  assign o[4] = ~N28;
  assign N28 = a_i[4] | b_i[4];
  assign o[3] = ~N29;
  assign N29 = a_i[3] | b_i[3];
  assign o[2] = ~N30;
  assign N30 = a_i[2] | b_i[2];
  assign o[1] = ~N31;
  assign N31 = a_i[1] | b_i[1];
  assign o[0] = ~N32;
  assign N32 = a_i[0] | b_i[0];

endmodule



module bsg_adder_cin_width_p33
(
  a_i,
  b_i,
  cin_i,
  o
);

  input [32:0] a_i;
  input [32:0] b_i;
  output [32:0] o;
  input cin_i;
  wire [32:0] o;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,
  N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32;
  assign { N32, N31, N30, N29, N28, N27, N26, N25, N24, N23, N22, N21, N20, N19, N18, N17, N16, N15, N14, N13, N12, N11, N10, N9, N8, N7, N6, N5, N4, N3, N2, N1, N0 } = a_i + b_i;
  assign o = { N32, N31, N30, N29, N28, N27, N26, N25, N24, N23, N22, N21, N20, N19, N18, N17, N16, N15, N14, N13, N12, N11, N10, N9, N8, N7, N6, N5, N4, N3, N2, N1, N0 } + cin_i;

endmodule



module bsg_idiv_iterative_controller
(
  clk_i,
  reset_i,
  v_i,
  ready_o,
  signed_div_r_i,
  adder_result_is_neg_i,
  opA_is_neg_i,
  opC_is_neg_i,
  opA_sel_o,
  opA_ld_o,
  opA_inv_o,
  opA_clr_l_o,
  opB_sel_o,
  opB_ld_o,
  opB_inv_o,
  opB_clr_l_o,
  opC_sel_o,
  opC_ld_o,
  latch_inputs_o,
  adder_cin_o,
  v_o,
  yumi_i
);

  output [2:0] opB_sel_o;
  output [2:0] opC_sel_o;
  input clk_i;
  input reset_i;
  input v_i;
  input signed_div_r_i;
  input adder_result_is_neg_i;
  input opA_is_neg_i;
  input opC_is_neg_i;
  input yumi_i;
  output ready_o;
  output opA_sel_o;
  output opA_ld_o;
  output opA_inv_o;
  output opA_clr_l_o;
  output opB_ld_o;
  output opB_inv_o;
  output opB_clr_l_o;
  output opC_ld_o;
  output latch_inputs_o;
  output adder_cin_o;
  output v_o;
  wire [2:0] opB_sel_o,opC_sel_o;
  wire ready_o,opA_sel_o,opA_ld_o,opA_inv_o,opA_clr_l_o,opB_ld_o,opB_inv_o,opB_clr_l_o,
  opC_ld_o,latch_inputs_o,adder_cin_o,v_o,N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,
  N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,
  N32,N33,N34,N35,N36,N37,N38,N39,N40,N41,neg_ld,N42,N43,N44,N45,N46,N47,N48,N49,
  N50,N51,N52,N53,N54,N55,N56,N57,N58,N59,N60,N61,N62,N63,N64,N65,N66,N67,N68,N69,
  N70,N71,N72,N73,N74,N75,N76,N77,N78,N79,N80,N81,N82,N83,N84,N85,N86,N87,N88,N89,
  N90,N91,N92,N93,N94,N95,N96,N97,N98,N99,N100,N101,N102,N103,N104,N105,N106,N107,
  N108,N109,N110,N111,N112,N113,N114,N115,N116,N117,N118,N119,N120,N121,N122,N123,
  N124,N125,N126,N127,N128,N129,N130,N131,N132,N133,N134,N135,N136,N137,N138,N139,
  N140,N141,N142,N143,N144,N145,N146,N147,N148,N149,N150,N151,N152,N153,N154,N155,
  N156,N157,N158,N159,N160,N161,N162,N163,N164,N165,N166,N167,N168,N169,N170,N171,
  N172,N173,N174,N175,N176,N177,N178,N179,N180,N181,N182,N183,N184,N185,N186,N187,
  N188,N189,N190,N191,N192,N193,N194,N195,N196,N197,N198,N199,N200,N201,N202,N203,
  N204,N205,N206,N207,N208,N209,N210,N211,N212,N213,N214,N215,N216,N217,N218,N219,
  N220,N221,N222,N223,N224,N225,N226,N227,N228,N229,N230,N231,N232,N233,N234,N235,
  N236,N237,N238,N239,N240,N241,N242,N243,N244,N245,N246,N247,N248,N249,N250,N251,
  N252,N253,N254,N255,N256,N257,N258,N259,N260,N261,N262,N263,N264,N265,N266,N267,
  N268,N269,N270,N271,N272,N273,N274,N275,N276,N277,N278,N279,N280,N281,N282,N283,
  N284,N285,N286,N287,N288,N289,N290,N291,N292,N293,N294,N295,N296,N297,N298,N299,
  N300,N301,N302,N303,N304,N305,N306,N307,N308,N309,N310,N311,N312,N313,N314,N315,
  N316,N317,N318,N319,N320,N321,N322,N323,N324,N325,N326,N327,N328,N329,N330,N331,
  N332,N333,N334,N335,N336,N337,N338,N339,N340,N341,N342,N343,N344,N345,N346,N347,
  N349,N350,N351,N352,N353,N354,N355,N356,N358;
  wire [5:0] next_state;
  reg add_neg_last,r_neg,q_neg;
  reg [5:0] state;

  always @(posedge clk_i) begin
    if(1'b1) begin
      add_neg_last <= adder_result_is_neg_i;
    end 
  end


  always @(posedge clk_i) begin
    if(neg_ld) begin
      r_neg <= N299;
    end 
  end


  always @(posedge clk_i) begin
    if(neg_ld) begin
      q_neg <= N42;
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      state[5] <= 1'b0;
    end else if(1'b1) begin
      state[5] <= next_state[5];
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      state[4] <= 1'b0;
    end else if(1'b1) begin
      state[4] <= next_state[4];
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      state[3] <= 1'b0;
    end else if(1'b1) begin
      state[3] <= next_state[3];
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      state[2] <= 1'b0;
    end else if(1'b1) begin
      state[2] <= next_state[2];
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      state[1] <= 1'b0;
    end else if(1'b1) begin
      state[1] <= next_state[1];
    end 
  end


  always @(posedge clk_i) begin
    if(reset_i) begin
      state[0] <= 1'b0;
    end else if(1'b1) begin
      state[0] <= next_state[0];
    end 
  end

  assign N47 = N349 & N44;
  assign N48 = N350 & N45;
  assign N49 = N46 & N351;
  assign N50 = N47 & N48;
  assign N51 = N50 & N49;
  assign N52 = state[5] | state[4];
  assign N53 = state[3] | state[2];
  assign N54 = state[1] | N351;
  assign N55 = N52 | N53;
  assign N56 = N55 | N54;
  assign N58 = state[5] | state[4];
  assign N59 = state[3] | state[2];
  assign N60 = N46 | state[0];
  assign N61 = N58 | N59;
  assign N62 = N61 | N60;
  assign N64 = state[5] | state[4];
  assign N65 = state[3] | state[2];
  assign N66 = N46 | N351;
  assign N67 = N64 | N65;
  assign N68 = N67 | N66;
  assign N70 = state[5] | state[4];
  assign N71 = state[3] | N45;
  assign N72 = state[1] | state[0];
  assign N73 = N70 | N71;
  assign N74 = N73 | N72;
  assign N76 = state[5] | state[4];
  assign N77 = state[3] | N45;
  assign N78 = state[1] | N351;
  assign N79 = N76 | N77;
  assign N80 = N79 | N78;
  assign N82 = state[5] | state[4];
  assign N83 = state[3] | N45;
  assign N84 = N46 | state[0];
  assign N85 = N82 | N83;
  assign N86 = N85 | N84;
  assign N88 = state[5] | state[4];
  assign N89 = state[3] | N45;
  assign N90 = N46 | N351;
  assign N91 = N88 | N89;
  assign N92 = N91 | N90;
  assign N94 = state[5] | state[4];
  assign N95 = N350 | state[2];
  assign N96 = state[1] | state[0];
  assign N97 = N94 | N95;
  assign N98 = N97 | N96;
  assign N100 = state[5] | state[4];
  assign N101 = N350 | state[2];
  assign N102 = state[1] | N351;
  assign N103 = N100 | N101;
  assign N104 = N103 | N102;
  assign N106 = state[5] | state[4];
  assign N107 = N350 | state[2];
  assign N108 = N46 | state[0];
  assign N109 = N106 | N107;
  assign N110 = N109 | N108;
  assign N112 = state[5] | state[4];
  assign N113 = N350 | state[2];
  assign N114 = N46 | N351;
  assign N115 = N112 | N113;
  assign N116 = N115 | N114;
  assign N118 = state[5] | state[4];
  assign N119 = N350 | N45;
  assign N120 = state[1] | state[0];
  assign N121 = N118 | N119;
  assign N122 = N121 | N120;
  assign N124 = state[5] | state[4];
  assign N125 = N350 | N45;
  assign N126 = state[1] | N351;
  assign N127 = N124 | N125;
  assign N128 = N127 | N126;
  assign N130 = state[5] | state[4];
  assign N131 = N350 | N45;
  assign N132 = N46 | state[0];
  assign N133 = N130 | N131;
  assign N134 = N133 | N132;
  assign N136 = state[5] | state[4];
  assign N137 = N350 | N45;
  assign N138 = N46 | N351;
  assign N139 = N136 | N137;
  assign N140 = N139 | N138;
  assign N142 = state[5] | N44;
  assign N143 = state[3] | state[2];
  assign N144 = state[1] | state[0];
  assign N145 = N142 | N143;
  assign N146 = N145 | N144;
  assign N148 = state[5] | N44;
  assign N149 = state[3] | state[2];
  assign N150 = state[1] | N351;
  assign N151 = N148 | N149;
  assign N152 = N151 | N150;
  assign N154 = state[5] | N44;
  assign N155 = state[3] | state[2];
  assign N156 = N46 | state[0];
  assign N157 = N154 | N155;
  assign N158 = N157 | N156;
  assign N160 = state[5] | N44;
  assign N161 = state[3] | state[2];
  assign N162 = N46 | N351;
  assign N163 = N160 | N161;
  assign N164 = N163 | N162;
  assign N166 = state[5] | N44;
  assign N167 = state[3] | N45;
  assign N168 = state[1] | state[0];
  assign N169 = N166 | N167;
  assign N170 = N169 | N168;
  assign N172 = state[5] | N44;
  assign N173 = state[3] | N45;
  assign N174 = state[1] | N351;
  assign N175 = N172 | N173;
  assign N176 = N175 | N174;
  assign N178 = state[5] | N44;
  assign N179 = state[3] | N45;
  assign N180 = N46 | state[0];
  assign N181 = N178 | N179;
  assign N182 = N181 | N180;
  assign N184 = state[5] | N44;
  assign N185 = state[3] | N45;
  assign N186 = N46 | N351;
  assign N187 = N184 | N185;
  assign N188 = N187 | N186;
  assign N190 = state[5] | N44;
  assign N191 = N350 | state[2];
  assign N192 = state[1] | state[0];
  assign N193 = N190 | N191;
  assign N194 = N193 | N192;
  assign N196 = state[5] | N44;
  assign N197 = N350 | state[2];
  assign N198 = state[1] | N351;
  assign N199 = N196 | N197;
  assign N200 = N199 | N198;
  assign N202 = state[5] | N44;
  assign N203 = N350 | state[2];
  assign N204 = N46 | state[0];
  assign N205 = N202 | N203;
  assign N206 = N205 | N204;
  assign N208 = state[5] | N44;
  assign N209 = N350 | state[2];
  assign N210 = N46 | N351;
  assign N211 = N208 | N209;
  assign N212 = N211 | N210;
  assign N214 = state[5] | N44;
  assign N215 = N350 | N45;
  assign N216 = state[1] | state[0];
  assign N217 = N214 | N215;
  assign N218 = N217 | N216;
  assign N220 = state[5] | N44;
  assign N221 = N350 | N45;
  assign N222 = state[1] | N351;
  assign N223 = N220 | N221;
  assign N224 = N223 | N222;
  assign N226 = state[5] | N44;
  assign N227 = N350 | N45;
  assign N228 = N46 | state[0];
  assign N229 = N226 | N227;
  assign N230 = N229 | N228;
  assign N232 = state[5] | N44;
  assign N233 = N350 | N45;
  assign N234 = N46 | N351;
  assign N235 = N232 | N233;
  assign N236 = N235 | N234;
  assign N238 = N349 | state[4];
  assign N239 = state[3] | state[2];
  assign N240 = state[1] | state[0];
  assign N241 = N238 | N239;
  assign N242 = N241 | N240;
  assign N244 = N349 | state[4];
  assign N245 = state[3] | state[2];
  assign N246 = state[1] | N351;
  assign N247 = N244 | N245;
  assign N248 = N247 | N246;
  assign N250 = N349 | state[4];
  assign N251 = state[3] | state[2];
  assign N252 = N46 | state[0];
  assign N253 = N250 | N251;
  assign N254 = N253 | N252;
  assign N256 = N349 | state[4];
  assign N257 = state[3] | state[2];
  assign N258 = N46 | N351;
  assign N259 = N256 | N257;
  assign N260 = N259 | N258;
  assign N262 = N349 | state[4];
  assign N263 = state[3] | N45;
  assign N264 = state[1] | state[0];
  assign N265 = N262 | N263;
  assign N266 = N265 | N264;
  assign N268 = N349 | state[4];
  assign N269 = state[3] | N45;
  assign N270 = state[1] | N351;
  assign N271 = N268 | N269;
  assign N272 = N271 | N270;
  assign N274 = N349 | state[4];
  assign N275 = state[3] | N45;
  assign N276 = N46 | state[0];
  assign N277 = N274 | N275;
  assign N278 = N277 | N276;
  assign N280 = N349 | state[4];
  assign N281 = state[3] | N45;
  assign N282 = N46 | N351;
  assign N283 = N280 | N281;
  assign N284 = N283 | N282;
  assign N286 = N349 | state[4];
  assign N287 = N350 | state[2];
  assign N288 = state[1] | state[0];
  assign N289 = N286 | N287;
  assign N290 = N289 | N288;
  assign N292 = N349 | state[4];
  assign N293 = N350 | state[2];
  assign N294 = state[1] | N351;
  assign N295 = N292 | N293;
  assign N296 = N295 | N294;
  assign N343 = state[4] | state[5];
  assign N344 = state[3] | N343;
  assign N345 = state[2] | N344;
  assign N346 = state[1] | N345;
  assign N347 = state[0] | N346;
  assign ready_o = ~N347;
  assign N349 = ~state[5];
  assign N350 = ~state[3];
  assign N351 = ~state[0];
  assign N352 = state[4] | N349;
  assign N353 = N350 | N352;
  assign N354 = state[2] | N353;
  assign N355 = state[1] | N354;
  assign N356 = N351 | N355;
  assign v_o = ~N356;
  assign next_state = (N0)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, v_i } : 
                      (N1)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b1, 1'b0 } : 
                      (N2)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b1, 1'b1 } : 
                      (N3)? { 1'b0, 1'b0, 1'b0, 1'b1, 1'b0, 1'b0 } : 
                      (N4)? { 1'b0, 1'b0, 1'b0, 1'b1, 1'b0, 1'b1 } : 
                      (N5)? { 1'b0, 1'b0, 1'b0, 1'b1, 1'b1, 1'b0 } : 
                      (N6)? { 1'b0, 1'b0, 1'b0, 1'b1, 1'b1, 1'b1 } : 
                      (N7)? { 1'b0, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0 } : 
                      (N8)? { 1'b0, 1'b0, 1'b1, 1'b0, 1'b0, 1'b1 } : 
                      (N9)? { 1'b0, 1'b0, 1'b1, 1'b0, 1'b1, 1'b0 } : 
                      (N10)? { 1'b0, 1'b0, 1'b1, 1'b0, 1'b1, 1'b1 } : 
                      (N11)? { 1'b0, 1'b0, 1'b1, 1'b1, 1'b0, 1'b0 } : 
                      (N12)? { 1'b0, 1'b0, 1'b1, 1'b1, 1'b0, 1'b1 } : 
                      (N13)? { 1'b0, 1'b0, 1'b1, 1'b1, 1'b1, 1'b0 } : 
                      (N14)? { 1'b0, 1'b0, 1'b1, 1'b1, 1'b1, 1'b1 } : 
                      (N15)? { 1'b0, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                      (N16)? { 1'b0, 1'b1, 1'b0, 1'b0, 1'b0, 1'b1 } : 
                      (N17)? { 1'b0, 1'b1, 1'b0, 1'b0, 1'b1, 1'b0 } : 
                      (N18)? { 1'b0, 1'b1, 1'b0, 1'b0, 1'b1, 1'b1 } : 
                      (N19)? { 1'b0, 1'b1, 1'b0, 1'b1, 1'b0, 1'b0 } : 
                      (N20)? { 1'b0, 1'b1, 1'b0, 1'b1, 1'b0, 1'b1 } : 
                      (N21)? { 1'b0, 1'b1, 1'b0, 1'b1, 1'b1, 1'b0 } : 
                      (N22)? { 1'b0, 1'b1, 1'b0, 1'b1, 1'b1, 1'b1 } : 
                      (N23)? { 1'b0, 1'b1, 1'b1, 1'b0, 1'b0, 1'b0 } : 
                      (N24)? { 1'b0, 1'b1, 1'b1, 1'b0, 1'b0, 1'b1 } : 
                      (N25)? { 1'b0, 1'b1, 1'b1, 1'b0, 1'b1, 1'b0 } : 
                      (N26)? { 1'b0, 1'b1, 1'b1, 1'b0, 1'b1, 1'b1 } : 
                      (N27)? { 1'b0, 1'b1, 1'b1, 1'b1, 1'b0, 1'b0 } : 
                      (N28)? { 1'b0, 1'b1, 1'b1, 1'b1, 1'b0, 1'b1 } : 
                      (N29)? { 1'b0, 1'b1, 1'b1, 1'b1, 1'b1, 1'b0 } : 
                      (N30)? { 1'b0, 1'b1, 1'b1, 1'b1, 1'b1, 1'b1 } : 
                      (N31)? { 1'b1, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                      (N32)? { 1'b1, 1'b0, 1'b0, 1'b0, 1'b0, 1'b1 } : 
                      (N33)? { 1'b1, 1'b0, 1'b0, 1'b0, 1'b1, 1'b0 } : 
                      (N34)? { 1'b1, 1'b0, 1'b0, 1'b0, 1'b1, 1'b1 } : 
                      (N35)? { 1'b1, 1'b0, 1'b0, 1'b1, 1'b0, 1'b0 } : 
                      (N36)? { 1'b1, 1'b0, 1'b0, 1'b1, 1'b0, 1'b1 } : 
                      (N37)? { 1'b1, 1'b0, 1'b0, 1'b1, 1'b1, 1'b0 } : 
                      (N38)? { 1'b1, 1'b0, 1'b0, 1'b1, 1'b1, 1'b1 } : 
                      (N39)? { 1'b1, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0 } : 
                      (N40)? { N300, 1'b0, N300, 1'b0, 1'b0, N300 } : 
                      (N41)? { N300, 1'b0, N300, 1'b0, 1'b0, N300 } : 
                      (N342)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 1'b0;
  assign N0 = N51;
  assign N1 = opC_sel_o[2];
  assign N2 = N63;
  assign N3 = N69;
  assign N4 = N75;
  assign N5 = N81;
  assign N6 = N87;
  assign N7 = N93;
  assign N8 = N99;
  assign N9 = N105;
  assign N10 = N111;
  assign N11 = N117;
  assign N12 = N123;
  assign N13 = N129;
  assign N14 = N135;
  assign N15 = N141;
  assign N16 = N147;
  assign N17 = N153;
  assign N18 = N159;
  assign N19 = N165;
  assign N20 = N171;
  assign N21 = N177;
  assign N22 = N183;
  assign N23 = N189;
  assign N24 = N195;
  assign N25 = N201;
  assign N26 = N207;
  assign N27 = N213;
  assign N28 = N219;
  assign N29 = N225;
  assign N30 = N231;
  assign N31 = N237;
  assign N32 = N243;
  assign N33 = N249;
  assign N34 = N255;
  assign N35 = N261;
  assign N36 = N267;
  assign N37 = N273;
  assign N38 = N279;
  assign N39 = N285;
  assign N40 = N291;
  assign N41 = N297;
  assign latch_inputs_o = (N0)? 1'b1 : 
                          (N1)? 1'b0 : 
                          (N2)? 1'b0 : 
                          (N3)? 1'b0 : 
                          (N4)? 1'b0 : 
                          (N5)? 1'b0 : 
                          (N6)? 1'b0 : 
                          (N7)? 1'b0 : 
                          (N8)? 1'b0 : 
                          (N9)? 1'b0 : 
                          (N10)? 1'b0 : 
                          (N11)? 1'b0 : 
                          (N12)? 1'b0 : 
                          (N13)? 1'b0 : 
                          (N14)? 1'b0 : 
                          (N15)? 1'b0 : 
                          (N16)? 1'b0 : 
                          (N17)? 1'b0 : 
                          (N18)? 1'b0 : 
                          (N19)? 1'b0 : 
                          (N20)? 1'b0 : 
                          (N21)? 1'b0 : 
                          (N22)? 1'b0 : 
                          (N23)? 1'b0 : 
                          (N24)? 1'b0 : 
                          (N25)? 1'b0 : 
                          (N26)? 1'b0 : 
                          (N27)? 1'b0 : 
                          (N28)? 1'b0 : 
                          (N29)? 1'b0 : 
                          (N30)? 1'b0 : 
                          (N31)? 1'b0 : 
                          (N32)? 1'b0 : 
                          (N33)? 1'b0 : 
                          (N34)? 1'b0 : 
                          (N35)? 1'b0 : 
                          (N36)? 1'b0 : 
                          (N37)? 1'b0 : 
                          (N38)? 1'b0 : 
                          (N39)? 1'b0 : 
                          (N40)? 1'b0 : 
                          (N41)? 1'b0 : 
                          (N342)? 1'b0 : 1'b0;
  assign opA_ld_o = (N0)? 1'b0 : 
                    (N1)? 1'b1 : 
                    (N2)? N298 : 
                    (N3)? 1'b0 : 
                    (N4)? 1'b0 : 
                    (N5)? 1'b0 : 
                    (N6)? 1'b0 : 
                    (N7)? 1'b0 : 
                    (N8)? 1'b0 : 
                    (N9)? 1'b0 : 
                    (N10)? 1'b0 : 
                    (N11)? 1'b0 : 
                    (N12)? 1'b0 : 
                    (N13)? 1'b0 : 
                    (N14)? 1'b0 : 
                    (N15)? 1'b0 : 
                    (N16)? 1'b0 : 
                    (N17)? 1'b0 : 
                    (N18)? 1'b0 : 
                    (N19)? 1'b0 : 
                    (N20)? 1'b0 : 
                    (N21)? 1'b0 : 
                    (N22)? 1'b0 : 
                    (N23)? 1'b0 : 
                    (N24)? 1'b0 : 
                    (N25)? 1'b0 : 
                    (N26)? 1'b0 : 
                    (N27)? 1'b0 : 
                    (N28)? 1'b0 : 
                    (N29)? 1'b0 : 
                    (N30)? 1'b0 : 
                    (N31)? 1'b0 : 
                    (N32)? 1'b0 : 
                    (N33)? 1'b0 : 
                    (N34)? 1'b0 : 
                    (N35)? 1'b0 : 
                    (N36)? 1'b0 : 
                    (N37)? 1'b0 : 
                    (N38)? 1'b0 : 
                    (N39)? 1'b1 : 
                    (N40)? 1'b0 : 
                    (N41)? 1'b0 : 
                    (N342)? 1'b0 : 1'b0;
  assign opC_ld_o = (N0)? 1'b1 : 
                    (N1)? 1'b1 : 
                    (N2)? 1'b0 : 
                    (N3)? N299 : 
                    (N4)? 1'b1 : 
                    (N5)? 1'b1 : 
                    (N6)? 1'b1 : 
                    (N7)? 1'b1 : 
                    (N8)? 1'b1 : 
                    (N9)? 1'b1 : 
                    (N10)? 1'b1 : 
                    (N11)? 1'b1 : 
                    (N12)? 1'b1 : 
                    (N13)? 1'b1 : 
                    (N14)? 1'b1 : 
                    (N15)? 1'b1 : 
                    (N16)? 1'b1 : 
                    (N17)? 1'b1 : 
                    (N18)? 1'b1 : 
                    (N19)? 1'b1 : 
                    (N20)? 1'b1 : 
                    (N21)? 1'b1 : 
                    (N22)? 1'b1 : 
                    (N23)? 1'b1 : 
                    (N24)? 1'b1 : 
                    (N25)? 1'b1 : 
                    (N26)? 1'b1 : 
                    (N27)? 1'b1 : 
                    (N28)? 1'b1 : 
                    (N29)? 1'b1 : 
                    (N30)? 1'b1 : 
                    (N31)? 1'b1 : 
                    (N32)? 1'b1 : 
                    (N33)? 1'b1 : 
                    (N34)? 1'b1 : 
                    (N35)? 1'b1 : 
                    (N36)? 1'b1 : 
                    (N37)? 1'b1 : 
                    (N38)? 1'b0 : 
                    (N39)? 1'b0 : 
                    (N40)? q_neg : 
                    (N41)? 1'b0 : 
                    (N342)? 1'b1 : 1'b0;
  assign opA_sel_o = (N0)? 1'b0 : 
                     (N1)? 1'b1 : 
                     (N2)? 1'b0 : 
                     (N3)? 1'b0 : 
                     (N4)? 1'b0 : 
                     (N5)? 1'b0 : 
                     (N6)? 1'b0 : 
                     (N7)? 1'b0 : 
                     (N8)? 1'b0 : 
                     (N9)? 1'b0 : 
                     (N10)? 1'b0 : 
                     (N11)? 1'b0 : 
                     (N12)? 1'b0 : 
                     (N13)? 1'b0 : 
                     (N14)? 1'b0 : 
                     (N15)? 1'b0 : 
                     (N16)? 1'b0 : 
                     (N17)? 1'b0 : 
                     (N18)? 1'b0 : 
                     (N19)? 1'b0 : 
                     (N20)? 1'b0 : 
                     (N21)? 1'b0 : 
                     (N22)? 1'b0 : 
                     (N23)? 1'b0 : 
                     (N24)? 1'b0 : 
                     (N25)? 1'b0 : 
                     (N26)? 1'b0 : 
                     (N27)? 1'b0 : 
                     (N28)? 1'b0 : 
                     (N29)? 1'b0 : 
                     (N30)? 1'b0 : 
                     (N31)? 1'b0 : 
                     (N32)? 1'b0 : 
                     (N33)? 1'b0 : 
                     (N34)? 1'b0 : 
                     (N35)? 1'b0 : 
                     (N36)? 1'b0 : 
                     (N37)? 1'b0 : 
                     (N38)? 1'b0 : 
                     (N39)? 1'b0 : 
                     (N40)? 1'b0 : 
                     (N41)? 1'b0 : 
                     (N342)? 1'b0 : 1'b0;
  assign opC_sel_o[1:0] = (N0)? { 1'b0, 1'b1 } : 
                          (N1)? { 1'b0, 1'b0 } : 
                          (N2)? { 1'b0, 1'b1 } : 
                          (N3)? { 1'b1, 1'b0 } : 
                          (N4)? { 1'b0, 1'b1 } : 
                          (N5)? { 1'b0, 1'b1 } : 
                          (N6)? { 1'b0, 1'b1 } : 
                          (N7)? { 1'b0, 1'b1 } : 
                          (N8)? { 1'b0, 1'b1 } : 
                          (N9)? { 1'b0, 1'b1 } : 
                          (N10)? { 1'b0, 1'b1 } : 
                          (N11)? { 1'b0, 1'b1 } : 
                          (N12)? { 1'b0, 1'b1 } : 
                          (N13)? { 1'b0, 1'b1 } : 
                          (N14)? { 1'b0, 1'b1 } : 
                          (N15)? { 1'b0, 1'b1 } : 
                          (N16)? { 1'b0, 1'b1 } : 
                          (N17)? { 1'b0, 1'b1 } : 
                          (N18)? { 1'b0, 1'b1 } : 
                          (N19)? { 1'b0, 1'b1 } : 
                          (N20)? { 1'b0, 1'b1 } : 
                          (N21)? { 1'b0, 1'b1 } : 
                          (N22)? { 1'b0, 1'b1 } : 
                          (N23)? { 1'b0, 1'b1 } : 
                          (N24)? { 1'b0, 1'b1 } : 
                          (N25)? { 1'b0, 1'b1 } : 
                          (N26)? { 1'b0, 1'b1 } : 
                          (N27)? { 1'b0, 1'b1 } : 
                          (N28)? { 1'b0, 1'b1 } : 
                          (N29)? { 1'b0, 1'b1 } : 
                          (N30)? { 1'b0, 1'b1 } : 
                          (N31)? { 1'b0, 1'b1 } : 
                          (N32)? { 1'b0, 1'b1 } : 
                          (N33)? { 1'b0, 1'b1 } : 
                          (N34)? { 1'b0, 1'b1 } : 
                          (N35)? { 1'b0, 1'b1 } : 
                          (N36)? { 1'b0, 1'b1 } : 
                          (N37)? { 1'b0, 1'b1 } : 
                          (N38)? { 1'b0, 1'b1 } : 
                          (N39)? { 1'b0, 1'b1 } : 
                          (N40)? { 1'b1, 1'b0 } : 
                          (N41)? { 1'b0, 1'b1 } : 
                          (N342)? { 1'b0, 1'b1 } : 1'b0;
  assign opB_ld_o = (N0)? 1'b1 : 
                    (N1)? 1'b0 : 
                    (N2)? 1'b1 : 
                    (N3)? 1'b0 : 
                    (N4)? 1'b1 : 
                    (N5)? 1'b1 : 
                    (N6)? 1'b1 : 
                    (N7)? 1'b1 : 
                    (N8)? 1'b1 : 
                    (N9)? 1'b1 : 
                    (N10)? 1'b1 : 
                    (N11)? 1'b1 : 
                    (N12)? 1'b1 : 
                    (N13)? 1'b1 : 
                    (N14)? 1'b1 : 
                    (N15)? 1'b1 : 
                    (N16)? 1'b1 : 
                    (N17)? 1'b1 : 
                    (N18)? 1'b1 : 
                    (N19)? 1'b1 : 
                    (N20)? 1'b1 : 
                    (N21)? 1'b1 : 
                    (N22)? 1'b1 : 
                    (N23)? 1'b1 : 
                    (N24)? 1'b1 : 
                    (N25)? 1'b1 : 
                    (N26)? 1'b1 : 
                    (N27)? 1'b1 : 
                    (N28)? 1'b1 : 
                    (N29)? 1'b1 : 
                    (N30)? 1'b1 : 
                    (N31)? 1'b1 : 
                    (N32)? 1'b1 : 
                    (N33)? 1'b1 : 
                    (N34)? 1'b1 : 
                    (N35)? 1'b1 : 
                    (N36)? 1'b1 : 
                    (N37)? 1'b1 : 
                    (N38)? add_neg_last : 
                    (N39)? 1'b1 : 
                    (N40)? 1'b0 : 
                    (N41)? 1'b0 : 
                    (N342)? 1'b1 : 1'b0;
  assign opA_inv_o = (N0)? N43 : 
                     (N1)? N43 : 
                     (N2)? 1'b1 : 
                     (N3)? N43 : 
                     (N4)? N43 : 
                     (N5)? N43 : 
                     (N6)? N43 : 
                     (N7)? N43 : 
                     (N8)? N43 : 
                     (N9)? N43 : 
                     (N10)? N43 : 
                     (N11)? N43 : 
                     (N12)? N43 : 
                     (N13)? N43 : 
                     (N14)? N43 : 
                     (N15)? N43 : 
                     (N16)? N43 : 
                     (N17)? N43 : 
                     (N18)? N43 : 
                     (N19)? N43 : 
                     (N20)? N43 : 
                     (N21)? N43 : 
                     (N22)? N43 : 
                     (N23)? N43 : 
                     (N24)? N43 : 
                     (N25)? N43 : 
                     (N26)? N43 : 
                     (N27)? N43 : 
                     (N28)? N43 : 
                     (N29)? N43 : 
                     (N30)? N43 : 
                     (N31)? N43 : 
                     (N32)? N43 : 
                     (N33)? N43 : 
                     (N34)? N43 : 
                     (N35)? N43 : 
                     (N36)? N43 : 
                     (N37)? N43 : 
                     (N38)? 1'b0 : 
                     (N39)? N43 : 
                     (N40)? N43 : 
                     (N41)? N43 : 
                     (N342)? N43 : 1'b0;
  assign opB_clr_l_o = (N0)? 1'b1 : 
                       (N1)? 1'b1 : 
                       (N2)? 1'b0 : 
                       (N3)? 1'b1 : 
                       (N4)? 1'b0 : 
                       (N5)? 1'b1 : 
                       (N6)? 1'b1 : 
                       (N7)? 1'b1 : 
                       (N8)? 1'b1 : 
                       (N9)? 1'b1 : 
                       (N10)? 1'b1 : 
                       (N11)? 1'b1 : 
                       (N12)? 1'b1 : 
                       (N13)? 1'b1 : 
                       (N14)? 1'b1 : 
                       (N15)? 1'b1 : 
                       (N16)? 1'b1 : 
                       (N17)? 1'b1 : 
                       (N18)? 1'b1 : 
                       (N19)? 1'b1 : 
                       (N20)? 1'b1 : 
                       (N21)? 1'b1 : 
                       (N22)? 1'b1 : 
                       (N23)? 1'b1 : 
                       (N24)? 1'b1 : 
                       (N25)? 1'b1 : 
                       (N26)? 1'b1 : 
                       (N27)? 1'b1 : 
                       (N28)? 1'b1 : 
                       (N29)? 1'b1 : 
                       (N30)? 1'b1 : 
                       (N31)? 1'b1 : 
                       (N32)? 1'b1 : 
                       (N33)? 1'b1 : 
                       (N34)? 1'b1 : 
                       (N35)? 1'b1 : 
                       (N36)? 1'b1 : 
                       (N37)? 1'b1 : 
                       (N38)? 1'b1 : 
                       (N39)? 1'b1 : 
                       (N40)? 1'b1 : 
                       (N41)? 1'b1 : 
                       (N342)? 1'b1 : 1'b0;
  assign opB_sel_o = (N0)? { 1'b0, 1'b0, 1'b1 } : 
                     (N1)? { 1'b0, 1'b0, 1'b1 } : 
                     (N2)? { 1'b1, 1'b0, 1'b0 } : 
                     (N3)? { 1'b0, 1'b0, 1'b1 } : 
                     (N4)? { 1'b0, 1'b0, 1'b1 } : 
                     (N5)? { 1'b0, 1'b0, 1'b1 } : 
                     (N6)? { 1'b0, 1'b0, 1'b1 } : 
                     (N7)? { 1'b0, 1'b0, 1'b1 } : 
                     (N8)? { 1'b0, 1'b0, 1'b1 } : 
                     (N9)? { 1'b0, 1'b0, 1'b1 } : 
                     (N10)? { 1'b0, 1'b0, 1'b1 } : 
                     (N11)? { 1'b0, 1'b0, 1'b1 } : 
                     (N12)? { 1'b0, 1'b0, 1'b1 } : 
                     (N13)? { 1'b0, 1'b0, 1'b1 } : 
                     (N14)? { 1'b0, 1'b0, 1'b1 } : 
                     (N15)? { 1'b0, 1'b0, 1'b1 } : 
                     (N16)? { 1'b0, 1'b0, 1'b1 } : 
                     (N17)? { 1'b0, 1'b0, 1'b1 } : 
                     (N18)? { 1'b0, 1'b0, 1'b1 } : 
                     (N19)? { 1'b0, 1'b0, 1'b1 } : 
                     (N20)? { 1'b0, 1'b0, 1'b1 } : 
                     (N21)? { 1'b0, 1'b0, 1'b1 } : 
                     (N22)? { 1'b0, 1'b0, 1'b1 } : 
                     (N23)? { 1'b0, 1'b0, 1'b1 } : 
                     (N24)? { 1'b0, 1'b0, 1'b1 } : 
                     (N25)? { 1'b0, 1'b0, 1'b1 } : 
                     (N26)? { 1'b0, 1'b0, 1'b1 } : 
                     (N27)? { 1'b0, 1'b0, 1'b1 } : 
                     (N28)? { 1'b0, 1'b0, 1'b1 } : 
                     (N29)? { 1'b0, 1'b0, 1'b1 } : 
                     (N30)? { 1'b0, 1'b0, 1'b1 } : 
                     (N31)? { 1'b0, 1'b0, 1'b1 } : 
                     (N32)? { 1'b0, 1'b0, 1'b1 } : 
                     (N33)? { 1'b0, 1'b0, 1'b1 } : 
                     (N34)? { 1'b0, 1'b0, 1'b1 } : 
                     (N35)? { 1'b0, 1'b0, 1'b1 } : 
                     (N36)? { 1'b0, 1'b0, 1'b1 } : 
                     (N37)? { 1'b0, 1'b1, 1'b0 } : 
                     (N38)? { 1'b0, 1'b1, 1'b0 } : 
                     (N39)? { 1'b1, 1'b0, 1'b0 } : 
                     (N40)? { 1'b0, 1'b0, 1'b1 } : 
                     (N41)? { 1'b0, 1'b0, 1'b1 } : 
                     (N342)? { 1'b0, 1'b0, 1'b1 } : 1'b0;
  assign neg_ld = (N0)? 1'b0 : 
                  (N1)? 1'b0 : 
                  (N2)? 1'b1 : 
                  (N3)? 1'b0 : 
                  (N4)? 1'b0 : 
                  (N5)? 1'b0 : 
                  (N6)? 1'b0 : 
                  (N7)? 1'b0 : 
                  (N8)? 1'b0 : 
                  (N9)? 1'b0 : 
                  (N10)? 1'b0 : 
                  (N11)? 1'b0 : 
                  (N12)? 1'b0 : 
                  (N13)? 1'b0 : 
                  (N14)? 1'b0 : 
                  (N15)? 1'b0 : 
                  (N16)? 1'b0 : 
                  (N17)? 1'b0 : 
                  (N18)? 1'b0 : 
                  (N19)? 1'b0 : 
                  (N20)? 1'b0 : 
                  (N21)? 1'b0 : 
                  (N22)? 1'b0 : 
                  (N23)? 1'b0 : 
                  (N24)? 1'b0 : 
                  (N25)? 1'b0 : 
                  (N26)? 1'b0 : 
                  (N27)? 1'b0 : 
                  (N28)? 1'b0 : 
                  (N29)? 1'b0 : 
                  (N30)? 1'b0 : 
                  (N31)? 1'b0 : 
                  (N32)? 1'b0 : 
                  (N33)? 1'b0 : 
                  (N34)? 1'b0 : 
                  (N35)? 1'b0 : 
                  (N36)? 1'b0 : 
                  (N37)? 1'b0 : 
                  (N38)? 1'b0 : 
                  (N39)? 1'b0 : 
                  (N40)? 1'b0 : 
                  (N41)? 1'b0 : 
                  (N342)? 1'b0 : 1'b0;
  assign adder_cin_o = (N0)? N43 : 
                       (N1)? N43 : 
                       (N2)? 1'b1 : 
                       (N3)? 1'b1 : 
                       (N4)? 1'b0 : 
                       (N5)? N43 : 
                       (N6)? N43 : 
                       (N7)? N43 : 
                       (N8)? N43 : 
                       (N9)? N43 : 
                       (N10)? N43 : 
                       (N11)? N43 : 
                       (N12)? N43 : 
                       (N13)? N43 : 
                       (N14)? N43 : 
                       (N15)? N43 : 
                       (N16)? N43 : 
                       (N17)? N43 : 
                       (N18)? N43 : 
                       (N19)? N43 : 
                       (N20)? N43 : 
                       (N21)? N43 : 
                       (N22)? N43 : 
                       (N23)? N43 : 
                       (N24)? N43 : 
                       (N25)? N43 : 
                       (N26)? N43 : 
                       (N27)? N43 : 
                       (N28)? N43 : 
                       (N29)? N43 : 
                       (N30)? N43 : 
                       (N31)? N43 : 
                       (N32)? N43 : 
                       (N33)? N43 : 
                       (N34)? N43 : 
                       (N35)? N43 : 
                       (N36)? N43 : 
                       (N37)? N43 : 
                       (N38)? 1'b0 : 
                       (N39)? r_neg : 
                       (N40)? 1'b1 : 
                       (N41)? N43 : 
                       (N342)? N43 : 1'b0;
  assign opA_clr_l_o = (N0)? 1'b1 : 
                       (N1)? 1'b1 : 
                       (N2)? 1'b1 : 
                       (N3)? 1'b0 : 
                       (N4)? 1'b0 : 
                       (N5)? 1'b1 : 
                       (N6)? 1'b1 : 
                       (N7)? 1'b1 : 
                       (N8)? 1'b1 : 
                       (N9)? 1'b1 : 
                       (N10)? 1'b1 : 
                       (N11)? 1'b1 : 
                       (N12)? 1'b1 : 
                       (N13)? 1'b1 : 
                       (N14)? 1'b1 : 
                       (N15)? 1'b1 : 
                       (N16)? 1'b1 : 
                       (N17)? 1'b1 : 
                       (N18)? 1'b1 : 
                       (N19)? 1'b1 : 
                       (N20)? 1'b1 : 
                       (N21)? 1'b1 : 
                       (N22)? 1'b1 : 
                       (N23)? 1'b1 : 
                       (N24)? 1'b1 : 
                       (N25)? 1'b1 : 
                       (N26)? 1'b1 : 
                       (N27)? 1'b1 : 
                       (N28)? 1'b1 : 
                       (N29)? 1'b1 : 
                       (N30)? 1'b1 : 
                       (N31)? 1'b1 : 
                       (N32)? 1'b1 : 
                       (N33)? 1'b1 : 
                       (N34)? 1'b1 : 
                       (N35)? 1'b1 : 
                       (N36)? 1'b1 : 
                       (N37)? 1'b1 : 
                       (N38)? 1'b1 : 
                       (N39)? 1'b0 : 
                       (N40)? 1'b0 : 
                       (N41)? 1'b1 : 
                       (N342)? 1'b1 : 1'b0;
  assign opB_inv_o = (N0)? 1'b0 : 
                     (N1)? 1'b0 : 
                     (N2)? 1'b0 : 
                     (N3)? 1'b1 : 
                     (N4)? 1'b0 : 
                     (N5)? 1'b0 : 
                     (N6)? 1'b0 : 
                     (N7)? 1'b0 : 
                     (N8)? 1'b0 : 
                     (N9)? 1'b0 : 
                     (N10)? 1'b0 : 
                     (N11)? 1'b0 : 
                     (N12)? 1'b0 : 
                     (N13)? 1'b0 : 
                     (N14)? 1'b0 : 
                     (N15)? 1'b0 : 
                     (N16)? 1'b0 : 
                     (N17)? 1'b0 : 
                     (N18)? 1'b0 : 
                     (N19)? 1'b0 : 
                     (N20)? 1'b0 : 
                     (N21)? 1'b0 : 
                     (N22)? 1'b0 : 
                     (N23)? 1'b0 : 
                     (N24)? 1'b0 : 
                     (N25)? 1'b0 : 
                     (N26)? 1'b0 : 
                     (N27)? 1'b0 : 
                     (N28)? 1'b0 : 
                     (N29)? 1'b0 : 
                     (N30)? 1'b0 : 
                     (N31)? 1'b0 : 
                     (N32)? 1'b0 : 
                     (N33)? 1'b0 : 
                     (N34)? 1'b0 : 
                     (N35)? 1'b0 : 
                     (N36)? 1'b0 : 
                     (N37)? 1'b0 : 
                     (N38)? 1'b0 : 
                     (N39)? r_neg : 
                     (N40)? 1'b1 : 
                     (N41)? 1'b0 : 
                     (N342)? 1'b0 : 1'b0;
  assign N42 = N358 & signed_div_r_i;
  assign N358 = opA_is_neg_i ^ opC_is_neg_i;
  assign N43 = ~add_neg_last;
  assign N44 = ~state[4];
  assign N45 = ~state[2];
  assign N46 = ~state[1];
  assign N57 = ~N56;
  assign N63 = ~N62;
  assign N69 = ~N68;
  assign N75 = ~N74;
  assign N81 = ~N80;
  assign N87 = ~N86;
  assign N93 = ~N92;
  assign N99 = ~N98;
  assign N105 = ~N104;
  assign N111 = ~N110;
  assign N117 = ~N116;
  assign N123 = ~N122;
  assign N129 = ~N128;
  assign N135 = ~N134;
  assign N141 = ~N140;
  assign N147 = ~N146;
  assign N153 = ~N152;
  assign N159 = ~N158;
  assign N165 = ~N164;
  assign N171 = ~N170;
  assign N177 = ~N176;
  assign N183 = ~N182;
  assign N189 = ~N188;
  assign N195 = ~N194;
  assign N201 = ~N200;
  assign N207 = ~N206;
  assign N213 = ~N212;
  assign N219 = ~N218;
  assign N225 = ~N224;
  assign N231 = ~N230;
  assign N237 = ~N236;
  assign N243 = ~N242;
  assign N249 = ~N248;
  assign N255 = ~N254;
  assign N261 = ~N260;
  assign N267 = ~N266;
  assign N273 = ~N272;
  assign N279 = ~N278;
  assign N285 = ~N284;
  assign N291 = ~N290;
  assign N297 = ~N296;
  assign opC_sel_o[2] = N57;
  assign N298 = opA_is_neg_i & signed_div_r_i;
  assign N299 = opC_is_neg_i & signed_div_r_i;
  assign N300 = ~yumi_i;
  assign N301 = opC_sel_o[2] | N51;
  assign N302 = N63 | N301;
  assign N303 = N69 | N302;
  assign N304 = N75 | N303;
  assign N305 = N81 | N304;
  assign N306 = N87 | N305;
  assign N307 = N93 | N306;
  assign N308 = N99 | N307;
  assign N309 = N105 | N308;
  assign N310 = N111 | N309;
  assign N311 = N117 | N310;
  assign N312 = N123 | N311;
  assign N313 = N129 | N312;
  assign N314 = N135 | N313;
  assign N315 = N141 | N314;
  assign N316 = N147 | N315;
  assign N317 = N153 | N316;
  assign N318 = N159 | N317;
  assign N319 = N165 | N318;
  assign N320 = N171 | N319;
  assign N321 = N177 | N320;
  assign N322 = N183 | N321;
  assign N323 = N189 | N322;
  assign N324 = N195 | N323;
  assign N325 = N201 | N324;
  assign N326 = N207 | N325;
  assign N327 = N213 | N326;
  assign N328 = N219 | N327;
  assign N329 = N225 | N328;
  assign N330 = N231 | N329;
  assign N331 = N237 | N330;
  assign N332 = N243 | N331;
  assign N333 = N249 | N332;
  assign N334 = N255 | N333;
  assign N335 = N261 | N334;
  assign N336 = N267 | N335;
  assign N337 = N273 | N336;
  assign N338 = N279 | N337;
  assign N339 = N285 | N338;
  assign N340 = N291 | N339;
  assign N341 = N297 | N340;
  assign N342 = ~N341;

endmodule



module bsg_idiv_iterative
(
  reset_i,
  clk_i,
  v_i,
  ready_o,
  dividend_i,
  divisor_i,
  signed_div_i,
  v_o,
  quotient_o,
  remainder_o,
  yumi_i
);

  input [31:0] dividend_i;
  input [31:0] divisor_i;
  output [31:0] quotient_o;
  output [31:0] remainder_o;
  input reset_i;
  input clk_i;
  input v_i;
  input signed_div_i;
  input yumi_i;
  output ready_o;
  output v_o;
  wire [31:0] quotient_o,remainder_o,divisor_r,dividend_r;
  wire ready_o,v_o,signed_div_r,divisor_msb,dividend_msb,latch_inputs,opA_sel,
  n_2_net__0_,opA_ld,opB_ld,opC_ld,opA_inv,opB_inv,n_3_net_,opA_clr_l,n_4_net_,opB_clr_l,
  adder_cin;
  wire [32:0] opA,opC,opA_mux,add_out,opB_mux,opC_mux,opB,opA_inv_buf,opB_inv_buf,opA_clr_buf,
  opB_clr_buf,opA_xnor,opB_xnor,add_in0,add_in1;
  wire [2:0] opB_sel,opC_sel;

  bsg_buf_width_p32
  remainder_buf
  (
    .i(opA[31:0]),
    .o(remainder_o)
  );


  bsg_buf_width_p32
  quotient_buf
  (
    .i(opC[31:0]),
    .o(quotient_o)
  );


  bsg_dff_en_width_p1
  req_reg
  (
    .clock_i(clk_i),
    .data_i(signed_div_i),
    .en_i(latch_inputs),
    .data_o(signed_div_r)
  );


  bsg_dff_en_width_p32
  dividend_reg
  (
    .clock_i(clk_i),
    .data_i(dividend_i),
    .en_i(latch_inputs),
    .data_o(dividend_r)
  );


  bsg_dff_en_width_p32
  divisor_reg
  (
    .clock_i(clk_i),
    .data_i(divisor_i),
    .en_i(latch_inputs),
    .data_o(divisor_r)
  );


  bsg_mux_width_p33_els_p2
  muxA
  (
    .data_i({ divisor_msb, divisor_r, add_out }),
    .sel_i(opA_sel),
    .data_o(opA_mux)
  );


  bsg_mux_one_hot_width_p33_els_p3
  muxB
  (
    .data_i({ opC, add_out, add_out[31:0], opC[32:32] }),
    .sel_one_hot_i(opB_sel),
    .data_o(opB_mux)
  );


  bsg_mux_one_hot_width_p33_els_p3
  muxC
  (
    .data_i({ dividend_msb, dividend_r, add_out, opC[31:0], n_2_net__0_ }),
    .sel_one_hot_i(opC_sel),
    .data_o(opC_mux)
  );


  bsg_dff_en_width_p33
  opA_reg
  (
    .clock_i(clk_i),
    .data_i(opA_mux),
    .en_i(opA_ld),
    .data_o(opA)
  );


  bsg_dff_en_width_p33
  opB_reg
  (
    .clock_i(clk_i),
    .data_i(opB_mux),
    .en_i(opB_ld),
    .data_o(opB)
  );


  bsg_dff_en_width_p33
  opC_reg
  (
    .clock_i(clk_i),
    .data_i(opC_mux),
    .en_i(opC_ld),
    .data_o(opC)
  );


  bsg_buf_ctrl_width_p33
  buf_opA_inv
  (
    .i(opA_inv),
    .o(opA_inv_buf)
  );


  bsg_buf_ctrl_width_p33
  buf_opB_inv
  (
    .i(opB_inv),
    .o(opB_inv_buf)
  );


  bsg_buf_ctrl_width_p33
  buf_opA_clr
  (
    .i(n_3_net_),
    .o(opA_clr_buf)
  );


  bsg_buf_ctrl_width_p33
  buf_opB_clr
  (
    .i(n_4_net_),
    .o(opB_clr_buf)
  );


  bsg_xnor_width_p33
  xnor_opA
  (
    .a_i(opA_inv_buf),
    .b_i(opA),
    .o(opA_xnor)
  );


  bsg_xnor_width_p33
  xnor_opB
  (
    .a_i(opB_inv_buf),
    .b_i(opB),
    .o(opB_xnor)
  );


  bsg_nor2_width_p33
  nor_opA
  (
    .a_i(opA_xnor),
    .b_i(opA_clr_buf),
    .o(add_in0)
  );


  bsg_nor2_width_p33
  nor_opB
  (
    .a_i(opB_xnor),
    .b_i(opB_clr_buf),
    .o(add_in1)
  );


  bsg_adder_cin_width_p33
  adder
  (
    .a_i(add_in0),
    .b_i(add_in1),
    .cin_i(adder_cin),
    .o(add_out)
  );


  bsg_idiv_iterative_controller
  control
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .v_i(v_i),
    .ready_o(ready_o),
    .signed_div_r_i(signed_div_r),
    .adder_result_is_neg_i(add_out[32]),
    .opA_is_neg_i(opA[32]),
    .opC_is_neg_i(opC[32]),
    .opA_sel_o(opA_sel),
    .opA_ld_o(opA_ld),
    .opA_inv_o(opA_inv),
    .opA_clr_l_o(opA_clr_l),
    .opB_sel_o(opB_sel),
    .opB_ld_o(opB_ld),
    .opB_inv_o(opB_inv),
    .opB_clr_l_o(opB_clr_l),
    .opC_sel_o(opC_sel),
    .opC_ld_o(opC_ld),
    .latch_inputs_o(latch_inputs),
    .adder_cin_o(adder_cin),
    .v_o(v_o),
    .yumi_i(yumi_i)
  );

  assign divisor_msb = signed_div_r & divisor_r[31];
  assign dividend_msb = signed_div_r & dividend_r[31];
  assign n_2_net__0_ = ~add_out[32];
  assign n_3_net_ = ~opA_clr_l;
  assign n_4_net_ = ~opB_clr_l;

endmodule



module imul_idiv_iterative
(
  reset_i,
  clk_i,
  v_i,
  ready_o,
  opA_i,
  opB_i,
  funct3,
  v_o,
  result_o,
  yumi_i
);

  input [31:0] opA_i;
  input [31:0] opB_i;
  input [2:0] funct3;
  output [31:0] result_o;
  input reset_i;
  input clk_i;
  input v_i;
  input yumi_i;
  output ready_o;
  output v_o;
  wire [31:0] result_o,imul_result,quotient,remainder;
  wire ready_o,v_o,N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,imul_v,signed_opA,signed_opB,
  gets_high_part,idiv_v,signed_div,gets_quotient,N11,N12,N13,N14,N15,N16,N17,N18,N19,
  N20,N21,N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32,N33,imul_ready,imul_v_o,
  idiv_ready,idiv_v_o,N34,N35,N36,N37,N38,N39,N40,N41,N42,N43,N44;
  reg gets_quotient_r;
  assign N14 = N11 & N12;
  assign N15 = N14 & N13;
  assign N16 = funct3[2] | funct3[1];
  assign N17 = N16 | N13;
  assign N19 = funct3[2] | N12;
  assign N20 = N19 | funct3[0];
  assign N22 = N19 | N13;
  assign N24 = N11 | funct3[1];
  assign N25 = N24 | funct3[0];
  assign N27 = N24 | N13;
  assign N29 = N11 | N12;
  assign N30 = N29 | funct3[0];
  assign N32 = funct3[2] & funct3[1];
  assign N33 = N32 & funct3[0];

  bsg_imul_iterative_width_p32
  imul
  (
    .reset_i(reset_i),
    .clk_i(clk_i),
    .v_i(imul_v),
    .ready_o(imul_ready),
    .opA_i(opA_i),
    .signed_opA_i(signed_opA),
    .opB_i(opB_i),
    .signed_opB_i(signed_opB),
    .gets_high_part_i(gets_high_part),
    .v_o(imul_v_o),
    .result_o(imul_result),
    .yumi_i(yumi_i)
  );


  bsg_idiv_iterative
  idiv
  (
    .reset_i(reset_i),
    .clk_i(clk_i),
    .v_i(idiv_v),
    .ready_o(idiv_ready),
    .dividend_i(opA_i),
    .divisor_i(opB_i),
    .signed_div_i(signed_div),
    .v_o(idiv_v_o),
    .quotient_o(quotient),
    .remainder_o(remainder),
    .yumi_i(yumi_i)
  );


  always @(posedge clk_i) begin
    if(N38) begin
      gets_quotient_r <= N39;
    end 
  end

  assign imul_v = (N0)? v_i : 
                  (N1)? v_i : 
                  (N2)? v_i : 
                  (N3)? v_i : 
                  (N4)? 1'b0 : 
                  (N5)? 1'b0 : 
                  (N6)? 1'b0 : 
                  (N7)? 1'b0 : 1'b0;
  assign N0 = N15;
  assign N1 = N18;
  assign N2 = N21;
  assign N3 = N23;
  assign N4 = N26;
  assign N5 = N28;
  assign N6 = N31;
  assign N7 = N33;
  assign signed_opA = (N0)? 1'b1 : 
                      (N1)? 1'b1 : 
                      (N2)? 1'b1 : 
                      (N3)? 1'b0 : 
                      (N4)? 1'b0 : 
                      (N5)? 1'b0 : 
                      (N6)? 1'b0 : 
                      (N7)? 1'b0 : 1'b0;
  assign signed_opB = (N0)? 1'b1 : 
                      (N1)? 1'b1 : 
                      (N2)? 1'b0 : 
                      (N3)? 1'b0 : 
                      (N4)? 1'b0 : 
                      (N5)? 1'b0 : 
                      (N6)? 1'b0 : 
                      (N7)? 1'b0 : 1'b0;
  assign gets_high_part = (N0)? 1'b0 : 
                          (N1)? 1'b1 : 
                          (N2)? 1'b1 : 
                          (N3)? 1'b1 : 
                          (N4)? 1'b0 : 
                          (N5)? 1'b0 : 
                          (N6)? 1'b0 : 
                          (N7)? 1'b0 : 1'b0;
  assign idiv_v = (N0)? 1'b0 : 
                  (N1)? 1'b0 : 
                  (N2)? 1'b0 : 
                  (N3)? 1'b0 : 
                  (N4)? v_i : 
                  (N5)? v_i : 
                  (N6)? v_i : 
                  (N7)? v_i : 1'b0;
  assign signed_div = (N0)? 1'b0 : 
                      (N1)? 1'b0 : 
                      (N2)? 1'b0 : 
                      (N3)? 1'b0 : 
                      (N4)? 1'b1 : 
                      (N5)? 1'b0 : 
                      (N6)? 1'b1 : 
                      (N7)? 1'b0 : 1'b0;
  assign gets_quotient = (N0)? 1'b0 : 
                         (N1)? 1'b0 : 
                         (N2)? 1'b0 : 
                         (N3)? 1'b0 : 
                         (N4)? 1'b1 : 
                         (N5)? 1'b1 : 
                         (N6)? 1'b0 : 
                         (N7)? 1'b0 : 1'b0;
  assign N38 = (N8)? 1'b1 : 
               (N41)? 1'b1 : 
               (N37)? 1'b0 : 1'b0;
  assign N8 = N35;
  assign N39 = (N8)? 1'b0 : 
               (N41)? gets_quotient : 1'b0;
  assign result_o = (N9)? imul_result : 
                    (N10)? quotient : 
                    (N44)? remainder : 1'b0;
  assign N9 = imul_v_o;
  assign N10 = N42;
  assign N11 = ~funct3[2];
  assign N12 = ~funct3[1];
  assign N13 = ~funct3[0];
  assign N18 = ~N17;
  assign N21 = ~N20;
  assign N23 = ~N22;
  assign N26 = ~N25;
  assign N28 = ~N27;
  assign N31 = ~N30;
  assign N34 = idiv_v & idiv_ready;
  assign N35 = reset_i;
  assign N36 = N34 | N35;
  assign N37 = ~N36;
  assign N40 = ~N35;
  assign N41 = N34 & N40;
  assign N42 = idiv_v_o & gets_quotient_r;
  assign N43 = N42 | imul_v_o;
  assign N44 = ~N43;
  assign v_o = idiv_v_o | imul_v_o;
  assign ready_o = idiv_ready & imul_ready;

endmodule



module bsg_mux_width_p32_els_p2
(
  data_i,
  sel_i,
  data_o
);

  input [63:0] data_i;
  input [0:0] sel_i;
  output [31:0] data_o;
  wire [31:0] data_o;
  wire N0,N1;
  assign data_o[31] = (N1)? data_i[31] : 
                      (N0)? data_i[63] : 1'b0;
  assign N0 = sel_i[0];
  assign data_o[30] = (N1)? data_i[30] : 
                      (N0)? data_i[62] : 1'b0;
  assign data_o[29] = (N1)? data_i[29] : 
                      (N0)? data_i[61] : 1'b0;
  assign data_o[28] = (N1)? data_i[28] : 
                      (N0)? data_i[60] : 1'b0;
  assign data_o[27] = (N1)? data_i[27] : 
                      (N0)? data_i[59] : 1'b0;
  assign data_o[26] = (N1)? data_i[26] : 
                      (N0)? data_i[58] : 1'b0;
  assign data_o[25] = (N1)? data_i[25] : 
                      (N0)? data_i[57] : 1'b0;
  assign data_o[24] = (N1)? data_i[24] : 
                      (N0)? data_i[56] : 1'b0;
  assign data_o[23] = (N1)? data_i[23] : 
                      (N0)? data_i[55] : 1'b0;
  assign data_o[22] = (N1)? data_i[22] : 
                      (N0)? data_i[54] : 1'b0;
  assign data_o[21] = (N1)? data_i[21] : 
                      (N0)? data_i[53] : 1'b0;
  assign data_o[20] = (N1)? data_i[20] : 
                      (N0)? data_i[52] : 1'b0;
  assign data_o[19] = (N1)? data_i[19] : 
                      (N0)? data_i[51] : 1'b0;
  assign data_o[18] = (N1)? data_i[18] : 
                      (N0)? data_i[50] : 1'b0;
  assign data_o[17] = (N1)? data_i[17] : 
                      (N0)? data_i[49] : 1'b0;
  assign data_o[16] = (N1)? data_i[16] : 
                      (N0)? data_i[48] : 1'b0;
  assign data_o[15] = (N1)? data_i[15] : 
                      (N0)? data_i[47] : 1'b0;
  assign data_o[14] = (N1)? data_i[14] : 
                      (N0)? data_i[46] : 1'b0;
  assign data_o[13] = (N1)? data_i[13] : 
                      (N0)? data_i[45] : 1'b0;
  assign data_o[12] = (N1)? data_i[12] : 
                      (N0)? data_i[44] : 1'b0;
  assign data_o[11] = (N1)? data_i[11] : 
                      (N0)? data_i[43] : 1'b0;
  assign data_o[10] = (N1)? data_i[10] : 
                      (N0)? data_i[42] : 1'b0;
  assign data_o[9] = (N1)? data_i[9] : 
                     (N0)? data_i[41] : 1'b0;
  assign data_o[8] = (N1)? data_i[8] : 
                     (N0)? data_i[40] : 1'b0;
  assign data_o[7] = (N1)? data_i[7] : 
                     (N0)? data_i[39] : 1'b0;
  assign data_o[6] = (N1)? data_i[6] : 
                     (N0)? data_i[38] : 1'b0;
  assign data_o[5] = (N1)? data_i[5] : 
                     (N0)? data_i[37] : 1'b0;
  assign data_o[4] = (N1)? data_i[4] : 
                     (N0)? data_i[36] : 1'b0;
  assign data_o[3] = (N1)? data_i[3] : 
                     (N0)? data_i[35] : 1'b0;
  assign data_o[2] = (N1)? data_i[2] : 
                     (N0)? data_i[34] : 1'b0;
  assign data_o[1] = (N1)? data_i[1] : 
                     (N0)? data_i[33] : 1'b0;
  assign data_o[0] = (N1)? data_i[0] : 
                     (N0)? data_i[32] : 1'b0;
  assign N1 = ~sel_i[0];

endmodule



module alu_imem_addr_width_p10
(
  rs1_i,
  rs2_i,
  pc_plus4_i,
  op_i,
  result_o,
  jalr_addr_o,
  jump_now_o
);

  input [31:0] rs1_i;
  input [31:0] rs2_i;
  input [31:0] pc_plus4_i;
  input [31:0] op_i;
  output [31:0] result_o;
  output [9:0] jalr_addr_o;
  output jump_now_o;
  wire [31:0] result_o,op2,adder_input,shr_out,shl_out,xor_out,and_out,or_out;
  wire [9:0] jalr_addr_o;
  wire jump_now_o,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,N22,N23,N24,N25,N26,
  N27,N28,N29,N30,N31,N32,N33,N34,N35,N36,is_imm_op,N37,sub_not_add,N38,N39,N40,
  N41,N42,N43,N44,N45,N46,N47,N48,N49,N50,N51,N52,N53,N54,N55,N56,N57,N58,N59,N60,
  N61,N62,N63,N64,N65,N66,N67,N68,N69,N70,N71,N72,N73,N74,N75,N76,N77,N78,N79,N80,
  N81,N82,N83,N84,N85,N86,N87,N88,N89,N90,N91,N92,N93,N94,N95,N96,N97,N98,N99,N100,
  N101,N102,N103,N104,carry,sign_ex_or_zero,N105,N106,N107,N108,N109,N110,N111,N112,
  N113,N114,N115,N116,N117,N118,N119,N120,N121,N122,N123,N124,N125,N126,N127,N128,
  N129,N130,N131,N132,N133,N134,N135,N136,N137,N138,N139,N140,N141,N142,N143,N144,
  N145,N146,N147,N148,N149,N150,N151,N152,N153,N154,N155,N156,N157,N158,N159,N160,
  N161,N162,N163,N164,N165,N166,N167,N168,N169,N170,N171,N172,N173,N174,N175,N176,
  N177,N178,N179,N180,N181,N182,N183,N184,N185,N186,N187,N188,N189,N190,N191,N192,
  N193,N194,N195,N196,N197,N198,N199,N200,N201,N202,N203,N204,N205,N206,N207,N208,
  N209,N210,N211,N212,N213,N214,N215,N216,N217,N218,N219,N220,N221,N222,N223,N224,
  N225,N226,N227,N228,N229,N230,N231,N232,N233,N234,N235,N236,N237,N238,N239,N240,
  N241,N242,N243,N244,N245,N246,N247,N248,N249,N250,N251,N252,N253,N254,N255,N256,
  N257,N258,N259,N260,N261,N262,N263,N264,N265,N266,N267,N268,N269,N270,N271,N272,
  N273,N274,N275,N276,N277,N278,N279,N280,N281,N282,N283,N284,N285,N286,N287,N288,
  N289,N290,N291,N292,N293,rs1_eq_rs2,rs1_lt_rs2_unsigned,rs1_lt_rs2_signed,N294,
  N295,N296,N297,N298,N299,N300,N301,N302,N303,N304,N305,N306,N307,N308,N309,N310,
  N311,N312,N313,N314,N315,N316,N317,N318,N319,N320,N321,N322,N323,N324,N325,N326,
  N327,N328,N329,N330,N331,N332,N333,N334,N335,SV2V_UNCONNECTED_1;
  wire [4:0] sh_amount;
  wire [32:0] sum;
  assign { SV2V_UNCONNECTED_1, shr_out } = $signed({ sign_ex_or_zero, rs1_i }) >>> sh_amount;
  assign shl_out = rs1_i << sh_amount;
  assign N106 = N326 & op_i[5];
  assign N107 = op_i[4] & N105;
  assign N108 = op_i[2] & op_i[1];
  assign N109 = N106 & N107;
  assign N110 = N108 & op_i[0];
  assign N111 = N109 & N110;
  assign N112 = N326 & N327;
  assign N113 = N112 & N107;
  assign N114 = N113 & N110;
  assign N115 = N301 & N147;
  assign N116 = N115 & N152;
  assign N117 = N116 & N150;
  assign N118 = N193 & N167;
  assign N119 = N118 & op_i[0];
  assign N125 = N121 & N122;
  assign N126 = N123 & op_i[28];
  assign N127 = N124 & N310;
  assign N128 = op_i[13] & N300;
  assign N129 = N125 & N126;
  assign N130 = N127 & N128;
  assign N131 = N106 & N226;
  assign N132 = N129 & N130;
  assign N133 = N131 & N110;
  assign N134 = N132 & N133;
  assign N135 = N311 & N147;
  assign N136 = N135 & N152;
  assign N137 = N136 & N150;
  assign N138 = N193 & N175;
  assign N139 = N138 & op_i[0];
  assign N141 = N311 & N179;
  assign N142 = N141 & N152;
  assign N143 = N142 & N150;
  assign N144 = N193 & N185;
  assign N145 = N144 & op_i[0];
  assign N147 = N300 & N326;
  assign N148 = N327 & op_i[4];
  assign N149 = N105 & N331;
  assign N150 = op_i[1] & op_i[0];
  assign N151 = N304 & N147;
  assign N152 = N148 & N149;
  assign N153 = N151 & N152;
  assign N154 = N153 & N150;
  assign N158 = N123 & N155;
  assign N159 = N124 & N156;
  assign N160 = N157 & op_i[14];
  assign N161 = N299 & N300;
  assign N162 = N125 & N158;
  assign N163 = N159 & N160;
  assign N164 = N161 & N106;
  assign N165 = N107 & N295;
  assign N166 = N162 & N163;
  assign N167 = N164 & N165;
  assign N168 = N166 & N167;
  assign N169 = N168 & op_i[0];
  assign N171 = N307 & N147;
  assign N172 = N171 & N152;
  assign N173 = N172 & N150;
  assign N174 = N128 & N106;
  assign N175 = N174 & N165;
  assign N176 = N166 & N175;
  assign N177 = N176 & op_i[0];
  assign N179 = op_i[12] & N326;
  assign N180 = N307 & N179;
  assign N181 = N180 & N152;
  assign N182 = N181 & N150;
  assign N183 = op_i[13] & op_i[12];
  assign N184 = N183 & N106;
  assign N185 = N184 & N165;
  assign N186 = N166 & N185;
  assign N187 = N186 & op_i[0];
  assign N189 = N157 & N310;
  assign N190 = N299 & op_i[12];
  assign N191 = N159 & N189;
  assign N192 = N190 & N112;
  assign N193 = N162 & N191;
  assign N194 = N192 & N165;
  assign N195 = N193 & N194;
  assign N196 = N195 & op_i[0];
  assign N197 = N190 & N106;
  assign N198 = N197 & N165;
  assign N199 = N193 & N198;
  assign N200 = N199 & op_i[0];
  assign N202 = N166 & N194;
  assign N203 = N202 & op_i[0];
  assign N204 = N166 & N198;
  assign N205 = N204 & op_i[0];
  assign N207 = N121 & op_i[30];
  assign N208 = N207 & N158;
  assign N209 = N208 & N163;
  assign N210 = N209 & N194;
  assign N211 = N210 & op_i[0];
  assign N212 = N209 & N198;
  assign N213 = N212 & op_i[0];
  assign N215 = N208 & N191;
  assign N216 = N215 & N167;
  assign N217 = N216 & op_i[0];
  assign N218 = N300 & op_i[6];
  assign N219 = op_i[5] & N317;
  assign N220 = N105 & op_i[2];
  assign N221 = N301 & N218;
  assign N222 = N219 & N220;
  assign N223 = N221 & N222;
  assign N224 = N223 & N150;
  assign N225 = op_i[6] & op_i[5];
  assign N226 = N317 & op_i[3];
  assign N227 = N225 & N226;
  assign N228 = N227 & N110;
  assign rs1_eq_rs2 = rs1_i == rs2_i;
  assign rs1_lt_rs2_unsigned = rs1_i < rs2_i;
  assign rs1_lt_rs2_signed = $signed(rs1_i) < $signed(rs2_i);
  assign N294 = N317 & N105;
  assign N295 = N331 & op_i[1];
  assign N296 = N225 & N294;
  assign N297 = N296 & N295;
  assign N301 = N310 & N299;
  assign N302 = N301 & N300;
  assign N303 = N301 & op_i[12];
  assign N304 = op_i[14] & N299;
  assign N305 = N304 & N300;
  assign N306 = N304 & op_i[12];
  assign N307 = op_i[14] & op_i[13];
  assign N308 = N307 & N300;
  assign N309 = N307 & op_i[12];
  assign N311 = N310 & op_i[13];
  assign { N260, N259, N258, N257, N256, N255, N254, N253, N252, N251, N250, N249, N248, N247, N246, N245, N244, N243, N242, N241, N240, N239, N238, N237, N236, N235, N234, N233, N232, N231, N230, N229 } = { op_i[31:12], 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } + pc_plus4_i;
  assign { N292, N291, N290, N289, N288, N287, N286, N285, N284, N283, N282, N281, N280, N279, N278, N277, N276, N275, N274, N273, N272, N271, N270, N269, N268, N267, N266, N265, N264, N263, N262, N261 } = { N260, N259, N258, N257, N256, N255, N254, N253, N252, N251, N250, N249, N248, N247, N246, N245, N244, N243, N242, N241, N240, N239, N238, N237, N236, N235, N234, N233, N232, N231, N230, N229 } - { 1'b1, 1'b0, 1'b0 };
  assign { N104, N103, N102, N101, N100, N99, N98, N97, N96, N95, N94, N93, N92, N91, N90, N89, N88, N87, N86, N85, N84, N83, N82, N81, N80, N79, N78, N77, N76, N75, N74, N73, N72, N71 } = { rs1_i[31:31], rs1_i } + { adder_input[31:31], adder_input };
  assign { carry, sum } = { N104, N103, N102, N101, N100, N99, N98, N97, N96, N95, N94, N93, N92, N91, N90, N89, N88, N87, N86, N85, N84, N83, N82, N81, N80, N79, N78, N77, N76, N75, N74, N73, N72, N71 } + sub_not_add;
  assign jalr_addr_o[0] = sum[2];
  assign jalr_addr_o[1] = sum[3];
  assign jalr_addr_o[2] = sum[4];
  assign jalr_addr_o[3] = sum[5];
  assign jalr_addr_o[4] = sum[6];
  assign jalr_addr_o[5] = sum[7];
  assign jalr_addr_o[6] = sum[8];
  assign jalr_addr_o[7] = sum[9];
  assign jalr_addr_o[8] = sum[10];
  assign jalr_addr_o[9] = sum[11];
  assign op2 = (N10)? { op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:31], op_i[31:20] } : 
               (N11)? rs2_i : 1'b0;
  assign N10 = is_imm_op;
  assign N11 = N37;
  assign adder_input = (N12)? { N39, N40, N41, N42, N43, N44, N45, N46, N47, N48, N49, N50, N51, N52, N53, N54, N55, N56, N57, N58, N59, N60, N61, N62, N63, N64, N65, N66, N67, N68, N69, N70 } : 
                       (N13)? op2 : 1'b0;
  assign N12 = sub_not_add;
  assign N13 = N38;
  assign sh_amount = (N10)? op_i[24:20] : 
                     (N11)? rs2_i[4:0] : 1'b0;
  assign result_o = (N14)? { op_i[31:12], 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                    (N15)? { N292, N291, N290, N289, N288, N287, N286, N285, N284, N283, N282, N281, N280, N279, N278, N277, N276, N275, N274, N273, N272, N271, N270, N269, N268, N267, N266, N265, N264, N263, N262, N261 } : 
                    (N16)? sum[31:0] : 
                    (N17)? rs1_i : 
                    (N18)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, sum[32:32] } : 
                    (N19)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, N293 } : 
                    (N20)? xor_out : 
                    (N21)? or_out : 
                    (N22)? and_out : 
                    (N23)? shl_out : 
                    (N24)? shr_out : 
                    (N25)? shr_out : 
                    (N26)? sum[31:0] : 
                    (N27)? pc_plus4_i : 
                    (N28)? pc_plus4_i : 1'b0;
  assign N14 = N111;
  assign N15 = N114;
  assign N16 = N120;
  assign N17 = N134;
  assign N18 = N140;
  assign N19 = N146;
  assign N20 = N170;
  assign N21 = N178;
  assign N22 = N188;
  assign N23 = N201;
  assign N24 = N206;
  assign N25 = N214;
  assign N26 = N217;
  assign N27 = N224;
  assign N28 = N228;
  assign sub_not_add = (N16)? 1'b0 : 
                       (N18)? 1'b1 : 
                       (N19)? 1'b1 : 
                       (N26)? 1'b1 : 
                       (N27)? 1'b0 : 1'b0;
  assign sign_ex_or_zero = (N24)? 1'b0 : 
                           (N25)? rs1_i[31] : 1'b0;
  assign N315 = (N29)? rs1_eq_rs2 : 
                (N30)? N312 : 
                (N31)? rs1_lt_rs2_signed : 
                (N32)? N313 : 
                (N33)? rs1_lt_rs2_unsigned : 
                (N34)? N314 : 
                (N35)? 1'b0 : 1'b0;
  assign N29 = N302;
  assign N30 = N303;
  assign N31 = N305;
  assign N32 = N306;
  assign N33 = N308;
  assign N34 = N309;
  assign N35 = N311;
  assign jump_now_o = (N36)? N315 : 
                      (N298)? 1'b0 : 1'b0;
  assign N36 = N297;
  assign is_imm_op = N325 | N335;
  assign N325 = ~N324;
  assign N324 = N322 | N323;
  assign N322 = N320 | N321;
  assign N320 = N319 | op_i[2];
  assign N319 = N318 | op_i[3];
  assign N318 = N316 | N317;
  assign N316 = op_i[6] | op_i[5];
  assign N317 = ~op_i[4];
  assign N321 = ~op_i[1];
  assign N323 = ~op_i[0];
  assign N335 = ~N334;
  assign N334 = N333 | N323;
  assign N333 = N332 | N321;
  assign N332 = N330 | N331;
  assign N330 = N329 | op_i[3];
  assign N329 = N328 | op_i[4];
  assign N328 = N326 | N327;
  assign N326 = ~op_i[6];
  assign N327 = ~op_i[5];
  assign N331 = ~op_i[2];
  assign N37 = ~is_imm_op;
  assign N38 = ~sub_not_add;
  assign N39 = ~op2[31];
  assign N40 = ~op2[30];
  assign N41 = ~op2[29];
  assign N42 = ~op2[28];
  assign N43 = ~op2[27];
  assign N44 = ~op2[26];
  assign N45 = ~op2[25];
  assign N46 = ~op2[24];
  assign N47 = ~op2[23];
  assign N48 = ~op2[22];
  assign N49 = ~op2[21];
  assign N50 = ~op2[20];
  assign N51 = ~op2[19];
  assign N52 = ~op2[18];
  assign N53 = ~op2[17];
  assign N54 = ~op2[16];
  assign N55 = ~op2[15];
  assign N56 = ~op2[14];
  assign N57 = ~op2[13];
  assign N58 = ~op2[12];
  assign N59 = ~op2[11];
  assign N60 = ~op2[10];
  assign N61 = ~op2[9];
  assign N62 = ~op2[8];
  assign N63 = ~op2[7];
  assign N64 = ~op2[6];
  assign N65 = ~op2[5];
  assign N66 = ~op2[4];
  assign N67 = ~op2[3];
  assign N68 = ~op2[2];
  assign N69 = ~op2[1];
  assign N70 = ~op2[0];
  assign xor_out[31] = rs1_i[31] ^ op2[31];
  assign xor_out[30] = rs1_i[30] ^ op2[30];
  assign xor_out[29] = rs1_i[29] ^ op2[29];
  assign xor_out[28] = rs1_i[28] ^ op2[28];
  assign xor_out[27] = rs1_i[27] ^ op2[27];
  assign xor_out[26] = rs1_i[26] ^ op2[26];
  assign xor_out[25] = rs1_i[25] ^ op2[25];
  assign xor_out[24] = rs1_i[24] ^ op2[24];
  assign xor_out[23] = rs1_i[23] ^ op2[23];
  assign xor_out[22] = rs1_i[22] ^ op2[22];
  assign xor_out[21] = rs1_i[21] ^ op2[21];
  assign xor_out[20] = rs1_i[20] ^ op2[20];
  assign xor_out[19] = rs1_i[19] ^ op2[19];
  assign xor_out[18] = rs1_i[18] ^ op2[18];
  assign xor_out[17] = rs1_i[17] ^ op2[17];
  assign xor_out[16] = rs1_i[16] ^ op2[16];
  assign xor_out[15] = rs1_i[15] ^ op2[15];
  assign xor_out[14] = rs1_i[14] ^ op2[14];
  assign xor_out[13] = rs1_i[13] ^ op2[13];
  assign xor_out[12] = rs1_i[12] ^ op2[12];
  assign xor_out[11] = rs1_i[11] ^ op2[11];
  assign xor_out[10] = rs1_i[10] ^ op2[10];
  assign xor_out[9] = rs1_i[9] ^ op2[9];
  assign xor_out[8] = rs1_i[8] ^ op2[8];
  assign xor_out[7] = rs1_i[7] ^ op2[7];
  assign xor_out[6] = rs1_i[6] ^ op2[6];
  assign xor_out[5] = rs1_i[5] ^ op2[5];
  assign xor_out[4] = rs1_i[4] ^ op2[4];
  assign xor_out[3] = rs1_i[3] ^ op2[3];
  assign xor_out[2] = rs1_i[2] ^ op2[2];
  assign xor_out[1] = rs1_i[1] ^ op2[1];
  assign xor_out[0] = rs1_i[0] ^ op2[0];
  assign and_out[31] = rs1_i[31] & op2[31];
  assign and_out[30] = rs1_i[30] & op2[30];
  assign and_out[29] = rs1_i[29] & op2[29];
  assign and_out[28] = rs1_i[28] & op2[28];
  assign and_out[27] = rs1_i[27] & op2[27];
  assign and_out[26] = rs1_i[26] & op2[26];
  assign and_out[25] = rs1_i[25] & op2[25];
  assign and_out[24] = rs1_i[24] & op2[24];
  assign and_out[23] = rs1_i[23] & op2[23];
  assign and_out[22] = rs1_i[22] & op2[22];
  assign and_out[21] = rs1_i[21] & op2[21];
  assign and_out[20] = rs1_i[20] & op2[20];
  assign and_out[19] = rs1_i[19] & op2[19];
  assign and_out[18] = rs1_i[18] & op2[18];
  assign and_out[17] = rs1_i[17] & op2[17];
  assign and_out[16] = rs1_i[16] & op2[16];
  assign and_out[15] = rs1_i[15] & op2[15];
  assign and_out[14] = rs1_i[14] & op2[14];
  assign and_out[13] = rs1_i[13] & op2[13];
  assign and_out[12] = rs1_i[12] & op2[12];
  assign and_out[11] = rs1_i[11] & op2[11];
  assign and_out[10] = rs1_i[10] & op2[10];
  assign and_out[9] = rs1_i[9] & op2[9];
  assign and_out[8] = rs1_i[8] & op2[8];
  assign and_out[7] = rs1_i[7] & op2[7];
  assign and_out[6] = rs1_i[6] & op2[6];
  assign and_out[5] = rs1_i[5] & op2[5];
  assign and_out[4] = rs1_i[4] & op2[4];
  assign and_out[3] = rs1_i[3] & op2[3];
  assign and_out[2] = rs1_i[2] & op2[2];
  assign and_out[1] = rs1_i[1] & op2[1];
  assign and_out[0] = rs1_i[0] & op2[0];
  assign or_out[31] = rs1_i[31] | op2[31];
  assign or_out[30] = rs1_i[30] | op2[30];
  assign or_out[29] = rs1_i[29] | op2[29];
  assign or_out[28] = rs1_i[28] | op2[28];
  assign or_out[27] = rs1_i[27] | op2[27];
  assign or_out[26] = rs1_i[26] | op2[26];
  assign or_out[25] = rs1_i[25] | op2[25];
  assign or_out[24] = rs1_i[24] | op2[24];
  assign or_out[23] = rs1_i[23] | op2[23];
  assign or_out[22] = rs1_i[22] | op2[22];
  assign or_out[21] = rs1_i[21] | op2[21];
  assign or_out[20] = rs1_i[20] | op2[20];
  assign or_out[19] = rs1_i[19] | op2[19];
  assign or_out[18] = rs1_i[18] | op2[18];
  assign or_out[17] = rs1_i[17] | op2[17];
  assign or_out[16] = rs1_i[16] | op2[16];
  assign or_out[15] = rs1_i[15] | op2[15];
  assign or_out[14] = rs1_i[14] | op2[14];
  assign or_out[13] = rs1_i[13] | op2[13];
  assign or_out[12] = rs1_i[12] | op2[12];
  assign or_out[11] = rs1_i[11] | op2[11];
  assign or_out[10] = rs1_i[10] | op2[10];
  assign or_out[9] = rs1_i[9] | op2[9];
  assign or_out[8] = rs1_i[8] | op2[8];
  assign or_out[7] = rs1_i[7] | op2[7];
  assign or_out[6] = rs1_i[6] | op2[6];
  assign or_out[5] = rs1_i[5] | op2[5];
  assign or_out[4] = rs1_i[4] | op2[4];
  assign or_out[3] = rs1_i[3] | op2[3];
  assign or_out[2] = rs1_i[2] | op2[2];
  assign or_out[1] = rs1_i[1] | op2[1];
  assign or_out[0] = rs1_i[0] | op2[0];
  assign N105 = ~op_i[3];
  assign N120 = N117 | N119;
  assign N121 = ~op_i[31];
  assign N122 = ~op_i[30];
  assign N123 = ~op_i[29];
  assign N124 = ~op_i[27];
  assign N140 = N137 | N139;
  assign N146 = N143 | N145;
  assign N155 = ~op_i[28];
  assign N156 = ~op_i[26];
  assign N157 = ~op_i[25];
  assign N170 = N154 | N169;
  assign N178 = N173 | N177;
  assign N188 = N182 | N187;
  assign N201 = N196 | N200;
  assign N206 = N203 | N205;
  assign N214 = N211 | N213;
  assign N293 = ~carry;
  assign N298 = ~N297;
  assign N299 = ~op_i[13];
  assign N300 = ~op_i[12];
  assign N310 = ~op_i[14];
  assign N312 = ~rs1_eq_rs2;
  assign N313 = ~rs1_lt_rs2_signed;
  assign N314 = ~rs1_lt_rs2_unsigned;

endmodule



module cl_state_machine
(
  instruction_i,
  state_i,
  net_pc_write_cmd_idle_i,
  stall_i,
  state_o
);

  input [31:0] instruction_i;
  input [1:0] state_i;
  output [1:0] state_o;
  input net_pc_write_cmd_idle_i;
  input stall_i;
  wire [1:0] state_o;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11;
  assign N6 = N4 & N5;
  assign N7 = state_i[1] | N5;
  assign N9 = state_i[1] & state_i[0];
  assign N10 = N4 | state_i[0];
  assign state_o = (N0)? { 1'b0, net_pc_write_cmd_idle_i } : 
                   (N1)? { 1'b0, 1'b1 } : 
                   (N2)? { 1'b1, 1'b1 } : 
                   (N3)? { 1'b1, 1'b1 } : 1'b0;
  assign N0 = N6;
  assign N1 = N8;
  assign N2 = N9;
  assign N3 = N11;
  assign N4 = ~state_i[1];
  assign N5 = ~state_i[0];
  assign N8 = ~N7;
  assign N11 = ~N10;

endmodule



module bsg_dff_reset_width_p32_harden_p1
(
  clock_i,
  data_i,
  reset_i,
  data_o
);

  input [31:0] data_i;
  output [31:0] data_o;
  input clock_i;
  input reset_i;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,
  N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32,N33,N34;
  reg [31:0] data_o;

  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[31] <= N34;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[30] <= N33;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[29] <= N32;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[28] <= N31;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[27] <= N30;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[26] <= N29;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[25] <= N28;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[24] <= N27;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[23] <= N26;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[22] <= N25;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[21] <= N24;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[20] <= N23;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[19] <= N22;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[18] <= N21;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[17] <= N20;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[16] <= N19;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[15] <= N18;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[14] <= N17;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[13] <= N16;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[12] <= N15;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[11] <= N14;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[10] <= N13;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[9] <= N12;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[8] <= N11;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[7] <= N10;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[6] <= N9;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[5] <= N8;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[4] <= N7;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[3] <= N6;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[2] <= N5;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[1] <= N4;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[0] <= N3;
    end 
  end

  assign { N34, N33, N32, N31, N30, N29, N28, N27, N26, N25, N24, N23, N22, N21, N20, N19, N18, N17, N16, N15, N14, N13, N12, N11, N10, N9, N8, N7, N6, N5, N4, N3 } = (N0)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                                                                                                                                                                       (N1)? data_i : 1'b0;
  assign N0 = reset_i;
  assign N1 = N2;
  assign N2 = ~reset_i;

endmodule



module bsg_dff_reset_width_p65_harden_p0
(
  clock_i,
  data_i,
  reset_i,
  data_o
);

  input [64:0] data_i;
  output [64:0] data_o;
  input clock_i;
  input reset_i;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,
  N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32,N33,N34,N35,N36,N37,N38,N39,N40,N41,
  N42,N43,N44,N45,N46,N47,N48,N49,N50,N51,N52,N53,N54,N55,N56,N57,N58,N59,N60,N61,
  N62,N63,N64,N65,N66,N67;
  reg [64:0] data_o;

  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[64] <= N67;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[63] <= N66;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[62] <= N65;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[61] <= N64;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[60] <= N63;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[59] <= N62;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[58] <= N61;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[57] <= N60;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[56] <= N59;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[55] <= N58;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[54] <= N57;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[53] <= N56;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[52] <= N55;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[51] <= N54;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[50] <= N53;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[49] <= N52;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[48] <= N51;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[47] <= N50;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[46] <= N49;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[45] <= N48;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[44] <= N47;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[43] <= N46;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[42] <= N45;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[41] <= N44;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[40] <= N43;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[39] <= N42;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[38] <= N41;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[37] <= N40;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[36] <= N39;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[35] <= N38;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[34] <= N37;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[33] <= N36;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[32] <= N35;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[31] <= N34;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[30] <= N33;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[29] <= N32;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[28] <= N31;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[27] <= N30;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[26] <= N29;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[25] <= N28;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[24] <= N27;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[23] <= N26;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[22] <= N25;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[21] <= N24;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[20] <= N23;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[19] <= N22;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[18] <= N21;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[17] <= N20;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[16] <= N19;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[15] <= N18;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[14] <= N17;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[13] <= N16;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[12] <= N15;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[11] <= N14;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[10] <= N13;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[9] <= N12;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[8] <= N11;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[7] <= N10;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[6] <= N9;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[5] <= N8;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[4] <= N7;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[3] <= N6;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[2] <= N5;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[1] <= N4;
    end 
  end


  always @(posedge clock_i) begin
    if(1'b1) begin
      data_o[0] <= N3;
    end 
  end

  assign { N67, N66, N65, N64, N63, N62, N61, N60, N59, N58, N57, N56, N55, N54, N53, N52, N51, N50, N49, N48, N47, N46, N45, N44, N43, N42, N41, N40, N39, N38, N37, N36, N35, N34, N33, N32, N31, N30, N29, N28, N27, N26, N25, N24, N23, N22, N21, N20, N19, N18, N17, N16, N15, N14, N13, N12, N11, N10, N9, N8, N7, N6, N5, N4, N3 } = (N0)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                                                                                                                                                                                                                                                                                                                                            (N1)? data_i : 1'b0;
  assign N0 = reset_i;
  assign N1 = N2;
  assign N2 = ~reset_i;

endmodule



module bsg_dff_reset_en_width_p10_harden_p1
(
  clock_i,
  reset_i,
  en_i,
  data_i,
  data_o
);

  input [9:0] data_i;
  output [9:0] data_o;
  input clock_i;
  input reset_i;
  input en_i;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15;
  reg [9:0] data_o;

  always @(posedge clock_i) begin
    if(N3) begin
      data_o[9] <= N13;
    end 
  end


  always @(posedge clock_i) begin
    if(N3) begin
      data_o[8] <= N12;
    end 
  end


  always @(posedge clock_i) begin
    if(N3) begin
      data_o[7] <= N11;
    end 
  end


  always @(posedge clock_i) begin
    if(N3) begin
      data_o[6] <= N10;
    end 
  end


  always @(posedge clock_i) begin
    if(N3) begin
      data_o[5] <= N9;
    end 
  end


  always @(posedge clock_i) begin
    if(N3) begin
      data_o[4] <= N8;
    end 
  end


  always @(posedge clock_i) begin
    if(N3) begin
      data_o[3] <= N7;
    end 
  end


  always @(posedge clock_i) begin
    if(N3) begin
      data_o[2] <= N6;
    end 
  end


  always @(posedge clock_i) begin
    if(N3) begin
      data_o[1] <= N5;
    end 
  end


  always @(posedge clock_i) begin
    if(N3) begin
      data_o[0] <= N4;
    end 
  end

  assign N3 = (N0)? 1'b1 : 
              (N15)? 1'b1 : 
              (N2)? 1'b0 : 1'b0;
  assign N0 = reset_i;
  assign { N13, N12, N11, N10, N9, N8, N7, N6, N5, N4 } = (N0)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                                                          (N15)? data_i : 1'b0;
  assign N1 = en_i | reset_i;
  assign N2 = ~N1;
  assign N14 = ~reset_i;
  assign N15 = en_i & N14;

endmodule



module hobbit_imem_addr_width_p10_gw_ID_p0_ring_ID_p0_x_cord_width_p4_y_cord_width_p5
(
  clk,
  reset,
  net_packet_i,
  from_mem_i,
  to_mem_o,
  reservation_i,
  reserve_1_o,
  my_x_i,
  my_y_i,
  outstanding_stores_i
);

  input [64:0] net_packet_i;
  input [33:0] from_mem_i;
  output [70:0] to_mem_o;
  input [3:0] my_x_i;
  input [4:0] my_y_i;
  input clk;
  input reset;
  input reservation_i;
  input outstanding_stores_i;
  output reserve_1_o;
  wire reserve_1_o,N0,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,
  N19,N20,N21,N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32,N33,N34,N35,N36,N37,N38,
  N39,N40,N41,N42,net_packet_r_valid_,net_packet_r_header__bc_,
  net_packet_r_header__external_,net_packet_r_header__gw_ID__2_,net_packet_r_header__gw_ID__1_,
  net_packet_r_header__gw_ID__0_,net_packet_r_header__ring_ID__4_,
  net_packet_r_header__ring_ID__3_,net_packet_r_header__ring_ID__2_,net_packet_r_header__ring_ID__1_,
  net_packet_r_header__ring_ID__0_,net_packet_r_header__net_op__1_,
  net_packet_r_header__net_op__0_,net_packet_r_header__mask__3_,net_packet_r_header__mask__2_,
  net_packet_r_header__mask__1_,net_packet_r_header__mask__0_,
  net_packet_r_header__reserved__1_,net_packet_r_header__reserved__0_,net_packet_r_header__addr__13_,
  net_packet_r_header__addr__12_,net_packet_r_header__addr__11_,
  net_packet_r_header__addr__10_,net_packet_r_header__addr__9_,net_packet_r_header__addr__8_,
  net_packet_r_header__addr__7_,net_packet_r_header__addr__6_,net_packet_r_header__addr__5_,
  net_packet_r_header__addr__4_,net_packet_r_header__addr__3_,
  net_packet_r_header__addr__2_,net_packet_r_header__addr__1_,net_packet_r_header__addr__0_,
  net_id_match_valid,exec_net_packet,net_pc_write_cmd,net_imem_write_cmd,net_reg_write_cmd,
  net_pc_write_cmd_idle,data_mem_valid,stall_md,stall_non_mem,stall_fence,stall_lrw,
  stall_mem,stall,N43,id_exe_rs1_match,N44,id_exe_rs2_match,depend_stall,N45,N46,N47,
  N48,N49,N50,N51,N52,N53,N54,N55,N56,N57,N58,N59,N60,N61,N62,N63,N64,N65,N66,N67,
  N68,N69,N70,N71,N72,N73,N74,N75,N76,N77,N78,N79,N80,N81,N82,N83,N84,N85,N86,N87,
  N88,N89,N90,N91,N92,N93,N94,N95,N96,N97,N98,N99,N100,N101,N102,N103,N104,N105,
  N106,N107,N108,N109,N110,N111,N112,N113,N114,N115,N116,N117,N118,N119,N120,N121,
  N122,N123,N124,N125,jump_now,branch_under_predict,branch_over_predict,
  branch_mispredict,N126,jalr_mispredict,flush,pc_wen,instruction_rs1__4_,instruction_rs1__3_,
  instruction_rs1__2_,instruction_rs1__1_,instruction_rs1__0_,
  instruction_funct3__2_,instruction_funct3__1_,instruction_op__6_,instruction_op__5_,
  instruction_op__4_,instruction_op__3_,instruction_op__2_,instruction_op__1_,instruction_op__0_,
  JImm_extract_11,JImm_extract_10,decode_op_writes_rf_,decode_is_load_op_,
  decode_is_store_op_,decode_is_mem_op_,decode_is_byte_op_,decode_is_hex_op_,
  decode_is_load_unsigned_,decode_is_branch_op_,decode_is_jump_op_,decode_op_reads_rf1_,
  decode_op_reads_rf2_,decode_op_is_auipc_,decode_is_md_instr_,decode_is_fence_op_,
  decode_is_fence_i_op_,decode_op_is_load_reservation_,decode_op_is_lr_acq_,N127,N128,N129,
  N130,N131,N132,N133,N134,N135,N136,N137,N138,N139,N140,N141,N142,N143,N144,N145,
  N146,N147,N148,N149,N150,N151,N152,N153,N154,N155,N156,N157,N158,N159,N160,N161,
  N162,N163,N164,N165,N166,imem_cen,BImm_sign_ext_31,JImm_sign_ext_4,
  JImm_sign_ext_3,JImm_sign_ext_2,JImm_sign_ext_1,instr_cast_op__6_,instr_cast_op__5_,
  instr_cast_op__4_,instr_cast_op__3_,instr_cast_op__2_,instr_cast_op__1_,
  instr_cast_op__0_,write_branch_instr,write_jal_instr,N167,inject_pc_rel_9,N168,N169,
  imem_w_data_0,N170,N171,N172,rf_wen,N173,rf_cen,md_ready,md_valid,md_resp_valid,n_3_net_,
  rs1_is_forward,rs2_is_forward,N174,n_cse_43,N175,N176,N177,id_wb_rs1_forward,N178,
  id_wb_rs2_forward,N179,N180,N181,N182,N183,exe_rs1_in_mem,N184,exe_rs1_in_wb,N185,
  exe_rs2_in_mem,N186,exe_rs2_in_wb,n_cse_62,N187,N188,N189,N190,N191,N192,N193,
  N194,N195,N196,N197,N198,N199,N200,N201,N202,N203,N204,N205,N206,N207,N208,N209,
  N210,N211,N212,N213,N214,N215,N216,N217,N218,N219,N220,N221,N222,N223,N224,N225,
  N226,N227,N228,N229,N230,N231,N232,N233,N234,N235,N236,N237,N238,N239,N240,N241,
  N242,N243,N244,N245,N246,N247,N248,N249,N250,N251,N252,N253,N254,N255,N256,N257,
  N258,N259,N260,N261,N262,N263,N264,N265,N266,N267,N268,N269,N270,N271,N272,N273,
  N274,N275,N276,N277,N278,N279,N280,N281,N282,N283,N284,N285,N286,N287,N288,N289,
  N290,N291,N292,N293,N294,N295,N296,N297,N298,N299,N300,N301,N302,N303,N304,N305,
  N306,N307,N308,N309,N310,N311,N312,N313,N314,N315,N316,N317,N318,N319,N320,N321,
  N322,N323,N324,N325,N326,N327,N328,N329,N330,N331,N332,N333,N334,N335,N336,N337,
  N338,N339,N340,N341,N342,N343,N344,N345,N346,N347,N348,N349,N350,N351,N352,N353,
  N354,N355,N356,N357,N358,N359,N360,N361,N362,N363,N364,N365,N366,N367,N368,N369,
  N370,N371,N372,N373,N374,N375,N376,N377,N378,N379,N380,N381,N382,N383,N384,N385,
  N386,N387,N388,N389,N390,N391,N392,N393,N394,N395,N396,N397,N398,N399,N400,N401,
  N402,N403,N404,N405,N406,N407,N408,N409,N410,N411,N412,N413,N414,N415,N416,N417,
  N418,N419,N420,N421,N422,N423,N424,N425,N426,N427,N428,N429,N430,N431,N432,N433,
  N434,N435,N436,N437,N438,N439,N440,N441,N442;
  wire [31:0] rs2_to_alu,mem_addr_op2,rs1_to_alu,jalr_prediction_rr,jalr_prediction_n,
  jalr_prediction_r,imem_out,instruction_r,rf_wd,rf_rs1_val,rf_rs2_val,md_result,
  rs1_forward_val,rs2_forward_val,basic_comp_result,alu_result,rf_rs1_index0_fix,
  rf_rs2_index0_fix,rs1_to_exe,rs2_to_exe,loaded_data,mem_loaded_data,rf_data;
  wire [9:0] jalr_addr,pc_r,pc_plus4,pc_n,imem_addr,inject_pc_value;
  wire [11:0] BImm_extract;
  wire [3:0] JImm_extract,pc_jump_addr;
  wire [11:1] BImm_sign_ext;
  wire [19:11] JImm_sign_ext;
  wire [2:0] inject_pc_rel;
  wire [31:7] imem_w_data;
  wire [4:0] rf_wa;
  wire [1:0] state_n;
  wire [7:0] loaded_byte;
  wire [15:0] loaded_hex;
  reg pc_wen_r,id_pc_plus4__31_,id_pc_plus4__30_,id_pc_plus4__29_,id_pc_plus4__28_,
  id_pc_plus4__27_,id_pc_plus4__26_,id_pc_plus4__25_,id_pc_plus4__24_,
  id_pc_plus4__23_,id_pc_plus4__22_,id_pc_plus4__21_,id_pc_plus4__20_,id_pc_plus4__19_,
  id_pc_plus4__18_,id_pc_plus4__17_,id_pc_plus4__16_,id_pc_plus4__15_,id_pc_plus4__14_,
  id_pc_plus4__13_,id_pc_plus4__12_,id_pc_plus4__11_,id_pc_plus4__10_,id_pc_plus4__9_,
  id_pc_plus4__8_,id_pc_plus4__7_,id_pc_plus4__6_,id_pc_plus4__5_,id_pc_plus4__4_,
  id_pc_plus4__3_,id_pc_plus4__2_,id_pc_plus4__1_,id_pc_plus4__0_,
  id_pc_jump_addr__11_,id_pc_jump_addr__10_,id_pc_jump_addr__9_,id_pc_jump_addr__8_,
  id_pc_jump_addr__7_,id_pc_jump_addr__6_,id_pc_jump_addr__5_,id_pc_jump_addr__4_,
  id_pc_jump_addr__3_,id_pc_jump_addr__2_,id_instruction__funct7__6_,id_instruction__funct7__5_,
  id_instruction__funct7__4_,id_instruction__funct7__3_,id_instruction__funct7__2_,
  id_instruction__funct7__1_,id_instruction__funct7__0_,id_instruction__rs2__4_,
  id_instruction__rs2__3_,id_instruction__rs2__2_,id_instruction__rs2__1_,
  id_instruction__rs2__0_,id_instruction__rs1__4_,id_instruction__rs1__3_,
  id_instruction__rs1__2_,id_instruction__rs1__1_,id_instruction__rs1__0_,
  id_instruction__funct3__2_,id_instruction__funct3__1_,id_instruction__funct3__0_,id_instruction__rd__4_,
  id_instruction__rd__3_,id_instruction__rd__2_,id_instruction__rd__1_,
  id_instruction__rd__0_,id_instruction__op__6_,id_instruction__op__5_,id_instruction__op__4_,
  id_instruction__op__3_,id_instruction__op__2_,id_instruction__op__1_,
  id_instruction__op__0_,id_decode__op_writes_rf_,id_decode__is_load_op_,
  id_decode__is_store_op_,id_decode__is_mem_op_,id_decode__is_byte_op_,id_decode__is_hex_op_,
  id_decode__is_load_unsigned_,id_decode__is_branch_op_,id_decode__is_jump_op_,
  id_decode__op_reads_rf1_,id_decode__op_reads_rf2_,id_decode__is_md_instr_,
  id_decode__is_fence_op_,id_decode__op_is_load_reservation_,id_decode__op_is_lr_acq_,
  exe_pc_plus4__31_,exe_pc_plus4__30_,exe_pc_plus4__29_,exe_pc_plus4__28_,exe_pc_plus4__27_,
  exe_pc_plus4__26_,exe_pc_plus4__25_,exe_pc_plus4__24_,exe_pc_plus4__23_,
  exe_pc_plus4__22_,exe_pc_plus4__21_,exe_pc_plus4__20_,exe_pc_plus4__19_,exe_pc_plus4__18_,
  exe_pc_plus4__17_,exe_pc_plus4__16_,exe_pc_plus4__15_,exe_pc_plus4__14_,
  exe_pc_plus4__13_,exe_pc_plus4__12_,exe_pc_plus4__11_,exe_pc_plus4__10_,exe_pc_plus4__9_,
  exe_pc_plus4__8_,exe_pc_plus4__7_,exe_pc_plus4__6_,exe_pc_plus4__5_,
  exe_pc_plus4__4_,exe_pc_plus4__3_,exe_pc_plus4__2_,exe_pc_plus4__1_,exe_pc_plus4__0_,
  exe_pc_jump_addr__11_,exe_pc_jump_addr__10_,exe_pc_jump_addr__9_,exe_pc_jump_addr__8_,
  exe_pc_jump_addr__7_,exe_pc_jump_addr__6_,exe_pc_jump_addr__5_,
  exe_pc_jump_addr__4_,exe_pc_jump_addr__3_,exe_pc_jump_addr__2_,exe_instruction__funct7__6_,
  exe_instruction__funct7__5_,exe_instruction__funct7__4_,exe_instruction__funct7__3_,
  exe_instruction__funct7__2_,exe_instruction__funct7__1_,exe_instruction__funct7__0_,
  exe_instruction__rs2__4_,exe_instruction__rs2__3_,exe_instruction__rs2__2_,
  exe_instruction__rs2__1_,exe_instruction__rs2__0_,exe_instruction__rs1__4_,
  exe_instruction__rs1__3_,exe_instruction__rs1__2_,exe_instruction__rs1__1_,
  exe_instruction__rs1__0_,exe_instruction__funct3__2_,exe_instruction__funct3__1_,
  exe_instruction__funct3__0_,exe_instruction__rd__4_,exe_instruction__rd__3_,
  exe_instruction__rd__2_,exe_instruction__rd__1_,exe_instruction__rd__0_,exe_instruction__op__6_,
  exe_instruction__op__5_,exe_instruction__op__4_,exe_instruction__op__3_,
  exe_instruction__op__2_,exe_instruction__op__1_,exe_instruction__op__0_,
  exe_decode__op_writes_rf_,exe_decode__is_load_op_,exe_decode__is_mem_op_,exe_decode__is_byte_op_,
  exe_decode__is_hex_op_,exe_decode__is_load_unsigned_,exe_decode__is_branch_op_,
  exe_decode__is_jump_op_,exe_decode__is_md_instr_,exe_decode__is_fence_op_,
  exe_decode__op_is_load_reservation_,exe_decode__op_is_lr_acq_,exe_rs1_val__31_,
  exe_rs1_val__30_,exe_rs1_val__29_,exe_rs1_val__28_,exe_rs1_val__27_,exe_rs1_val__26_,
  exe_rs1_val__25_,exe_rs1_val__24_,exe_rs1_val__23_,exe_rs1_val__22_,exe_rs1_val__21_,
  exe_rs1_val__20_,exe_rs1_val__19_,exe_rs1_val__18_,exe_rs1_val__17_,
  exe_rs1_val__16_,exe_rs1_val__15_,exe_rs1_val__14_,exe_rs1_val__13_,exe_rs1_val__12_,
  exe_rs1_val__11_,exe_rs1_val__10_,exe_rs1_val__9_,exe_rs1_val__8_,exe_rs1_val__7_,
  exe_rs1_val__6_,exe_rs1_val__5_,exe_rs1_val__4_,exe_rs1_val__3_,exe_rs1_val__2_,
  exe_rs1_val__1_,exe_rs1_val__0_,exe_rs2_val__31_,exe_rs2_val__30_,exe_rs2_val__29_,
  exe_rs2_val__28_,exe_rs2_val__27_,exe_rs2_val__26_,exe_rs2_val__25_,
  exe_rs2_val__24_,exe_rs2_val__23_,exe_rs2_val__22_,exe_rs2_val__21_,exe_rs2_val__20_,
  exe_rs2_val__19_,exe_rs2_val__18_,exe_rs2_val__17_,exe_rs2_val__16_,exe_rs2_val__15_,
  exe_rs2_val__14_,exe_rs2_val__13_,exe_rs2_val__12_,exe_rs2_val__11_,
  exe_rs2_val__10_,exe_rs2_val__9_,exe_rs2_val__8_,exe_rs2_val__7_,exe_rs2_val__6_,
  exe_rs2_val__5_,exe_rs2_val__4_,exe_rs2_val__3_,exe_rs2_val__2_,exe_rs2_val__1_,
  exe_rs2_val__0_,exe_mem_addr_op2__31_,exe_mem_addr_op2__30_,exe_mem_addr_op2__29_,
  exe_mem_addr_op2__28_,exe_mem_addr_op2__27_,exe_mem_addr_op2__26_,exe_mem_addr_op2__25_,
  exe_mem_addr_op2__24_,exe_mem_addr_op2__23_,exe_mem_addr_op2__22_,
  exe_mem_addr_op2__21_,exe_mem_addr_op2__20_,exe_mem_addr_op2__19_,exe_mem_addr_op2__18_,
  exe_mem_addr_op2__17_,exe_mem_addr_op2__16_,exe_mem_addr_op2__15_,exe_mem_addr_op2__14_,
  exe_mem_addr_op2__13_,exe_mem_addr_op2__12_,exe_mem_addr_op2__11_,
  exe_mem_addr_op2__10_,exe_mem_addr_op2__9_,exe_mem_addr_op2__8_,exe_mem_addr_op2__7_,
  exe_mem_addr_op2__6_,exe_mem_addr_op2__5_,exe_mem_addr_op2__4_,exe_mem_addr_op2__3_,
  exe_mem_addr_op2__2_,exe_mem_addr_op2__1_,exe_mem_addr_op2__0_,exe_rs1_in_mem_,
  exe_rs1_in_wb_,exe_rs2_in_mem_,exe_rs2_in_wb_,mem_rd_addr__4_,mem_rd_addr__3_,
  mem_rd_addr__2_,mem_rd_addr__1_,mem_rd_addr__0_,mem_decode__op_writes_rf_,
  mem_decode__is_load_op_,mem_decode__is_mem_op_,mem_decode__is_byte_op_,mem_decode__is_hex_op_,
  mem_decode__is_load_unsigned_,mem_alu_result__31_,mem_alu_result__30_,
  mem_alu_result__29_,mem_alu_result__28_,mem_alu_result__27_,mem_alu_result__26_,
  mem_alu_result__25_,mem_alu_result__24_,mem_alu_result__23_,mem_alu_result__22_,
  mem_alu_result__21_,mem_alu_result__20_,mem_alu_result__19_,mem_alu_result__18_,
  mem_alu_result__17_,mem_alu_result__16_,mem_alu_result__15_,mem_alu_result__14_,
  mem_alu_result__13_,mem_alu_result__12_,mem_alu_result__11_,mem_alu_result__10_,
  mem_alu_result__9_,mem_alu_result__8_,mem_alu_result__7_,mem_alu_result__6_,
  mem_alu_result__5_,mem_alu_result__4_,mem_alu_result__3_,mem_alu_result__2_,mem_alu_result__1_,
  mem_alu_result__0_,mem_mem_addr_send__1_,mem_mem_addr_send__0_,
  is_load_buffer_valid;
  reg [1:0] state_r;
  reg [70:0] to_mem_o;
  reg [31:0] load_buffer_data;
  reg [37:0] wb;
  assign N43 = { id_instruction__rs1__4_, id_instruction__rs1__3_, id_instruction__rs1__2_, id_instruction__rs1__1_, id_instruction__rs1__0_ } == { exe_instruction__rd__4_, exe_instruction__rd__3_, exe_instruction__rd__2_, exe_instruction__rd__1_, exe_instruction__rd__0_ };
  assign N44 = { id_instruction__rs2__4_, id_instruction__rs2__3_, id_instruction__rs2__2_, id_instruction__rs2__1_, id_instruction__rs2__0_ } == { exe_instruction__rd__4_, exe_instruction__rd__3_, exe_instruction__rd__2_, exe_instruction__rd__1_, exe_instruction__rd__0_ };
  assign { N78, N77, N76, N75, N74, N73, N72, N71, N70, N69, N68, N67, N66, N65, N64, N63, N62, N61, N60, N59, N58, N57, N56, N55, N54, N53, N52, N51, N50, N49, N48, N47 } = { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, rs2_to_alu[7:0] } << { to_mem_o[34:33], 1'b0, 1'b0, 1'b0 };
  assign { N82, N81, N80, N79 } = { 1'b0, 1'b0, 1'b0, 1'b1 } << to_mem_o[34:33];
  assign { N115, N114, N113, N112, N111, N110, N109, N108, N107, N106, N105, N104, N103, N102, N101, N100, N99, N98, N97, N96, N95, N94, N93, N92, N91, N90, N89, N88, N87, N86, N85, N84 } = { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, rs2_to_alu[15:0] } << { to_mem_o[34:33], 1'b0, 1'b0, 1'b0 };
  assign { N119, N118, N117, N116 } = { 1'b0, 1'b0, 1'b1, 1'b1 } << to_mem_o[34:33];
  assign N126 = jalr_addr != jalr_prediction_rr;

  bsg_mem_1rw_sync_width_p32_els_p1024
  imem_0
  (
    .clk_i(clk),
    .reset_i(reset),
    .data_i({ imem_w_data, instr_cast_op__6_, instr_cast_op__5_, instr_cast_op__4_, instr_cast_op__3_, instr_cast_op__2_, instr_cast_op__1_, imem_w_data_0 }),
    .addr_i(imem_addr),
    .v_i(imem_cen),
    .w_i(net_imem_write_cmd),
    .data_o(imem_out)
  );


  cl_decode
  cl_decode_0
  (
    .instruction_i({ BImm_extract[11:11], BImm_extract[9:4], JImm_extract, JImm_extract_10, instruction_rs1__4_, instruction_rs1__3_, instruction_rs1__2_, instruction_rs1__1_, instruction_rs1__0_, instruction_funct3__2_, instruction_funct3__1_, JImm_extract_11, BImm_extract[3:0], BImm_extract[10:10], instruction_op__6_, instruction_op__5_, instruction_op__4_, instruction_op__3_, instruction_op__2_, instruction_op__1_, instruction_op__0_ }),
    .decode_o_op_writes_rf_(decode_op_writes_rf_),
    .decode_o_is_load_op_(decode_is_load_op_),
    .decode_o_is_store_op_(decode_is_store_op_),
    .decode_o_is_mem_op_(decode_is_mem_op_),
    .decode_o_is_byte_op_(decode_is_byte_op_),
    .decode_o_is_hex_op_(decode_is_hex_op_),
    .decode_o_is_load_unsigned_(decode_is_load_unsigned_),
    .decode_o_is_branch_op_(decode_is_branch_op_),
    .decode_o_is_jump_op_(decode_is_jump_op_),
    .decode_o_op_reads_rf1_(decode_op_reads_rf1_),
    .decode_o_op_reads_rf2_(decode_op_reads_rf2_),
    .decode_o_op_is_auipc_(decode_op_is_auipc_),
    .decode_o_is_md_instr_(decode_is_md_instr_),
    .decode_o_is_fence_op_(decode_is_fence_op_),
    .decode_o_is_fence_i_op_(decode_is_fence_i_op_),
    .decode_o_op_is_load_reservation_(decode_op_is_load_reservation_),
    .decode_o_op_is_lr_acq_(decode_op_is_lr_acq_)
  );


  rf_2r1w_sync_wrapper_width_p32_els_p32
  rf_0
  (
    .clk_i(clk),
    .reset_i(reset),
    .w_v_i(rf_wen),
    .w_addr_i(rf_wa),
    .w_data_i(rf_wd),
    .r0_v_i(rf_cen),
    .r0_addr_i({ instruction_rs1__4_, instruction_rs1__3_, instruction_rs1__2_, instruction_rs1__1_, instruction_rs1__0_ }),
    .r0_data_o(rf_rs1_val),
    .r1_v_i(rf_cen),
    .r1_addr_i({ JImm_extract, JImm_extract_10 }),
    .r1_data_o(rf_rs2_val)
  );


  imul_idiv_iterative
  md_0
  (
    .reset_i(reset),
    .clk_i(clk),
    .v_i(md_valid),
    .ready_o(md_ready),
    .opA_i(rs1_to_alu),
    .opB_i(rs2_to_alu),
    .funct3({ exe_instruction__funct3__2_, exe_instruction__funct3__1_, exe_instruction__funct3__0_ }),
    .v_o(md_resp_valid),
    .result_o(md_result),
    .yumi_i(n_3_net_)
  );


  bsg_mux_width_p32_els_p2
  rs1_forward_mux
  (
    .data_i({ mem_alu_result__31_, mem_alu_result__30_, mem_alu_result__29_, mem_alu_result__28_, mem_alu_result__27_, mem_alu_result__26_, mem_alu_result__25_, mem_alu_result__24_, mem_alu_result__23_, mem_alu_result__22_, mem_alu_result__21_, mem_alu_result__20_, mem_alu_result__19_, mem_alu_result__18_, mem_alu_result__17_, mem_alu_result__16_, mem_alu_result__15_, mem_alu_result__14_, mem_alu_result__13_, mem_alu_result__12_, mem_alu_result__11_, mem_alu_result__10_, mem_alu_result__9_, mem_alu_result__8_, mem_alu_result__7_, mem_alu_result__6_, mem_alu_result__5_, mem_alu_result__4_, mem_alu_result__3_, mem_alu_result__2_, mem_alu_result__1_, mem_alu_result__0_, wb[31:0] }),
    .sel_i(exe_rs1_in_mem_),
    .data_o(rs1_forward_val)
  );


  bsg_mux_width_p32_els_p2
  rs2_forward_mux
  (
    .data_i({ mem_alu_result__31_, mem_alu_result__30_, mem_alu_result__29_, mem_alu_result__28_, mem_alu_result__27_, mem_alu_result__26_, mem_alu_result__25_, mem_alu_result__24_, mem_alu_result__23_, mem_alu_result__22_, mem_alu_result__21_, mem_alu_result__20_, mem_alu_result__19_, mem_alu_result__18_, mem_alu_result__17_, mem_alu_result__16_, mem_alu_result__15_, mem_alu_result__14_, mem_alu_result__13_, mem_alu_result__12_, mem_alu_result__11_, mem_alu_result__10_, mem_alu_result__9_, mem_alu_result__8_, mem_alu_result__7_, mem_alu_result__6_, mem_alu_result__5_, mem_alu_result__4_, mem_alu_result__3_, mem_alu_result__2_, mem_alu_result__1_, mem_alu_result__0_, wb[31:0] }),
    .sel_i(exe_rs2_in_mem_),
    .data_o(rs2_forward_val)
  );


  bsg_mux_width_p32_els_p2
  rs1_alu_mux
  (
    .data_i({ rs1_forward_val, exe_rs1_val__31_, exe_rs1_val__30_, exe_rs1_val__29_, exe_rs1_val__28_, exe_rs1_val__27_, exe_rs1_val__26_, exe_rs1_val__25_, exe_rs1_val__24_, exe_rs1_val__23_, exe_rs1_val__22_, exe_rs1_val__21_, exe_rs1_val__20_, exe_rs1_val__19_, exe_rs1_val__18_, exe_rs1_val__17_, exe_rs1_val__16_, exe_rs1_val__15_, exe_rs1_val__14_, exe_rs1_val__13_, exe_rs1_val__12_, exe_rs1_val__11_, exe_rs1_val__10_, exe_rs1_val__9_, exe_rs1_val__8_, exe_rs1_val__7_, exe_rs1_val__6_, exe_rs1_val__5_, exe_rs1_val__4_, exe_rs1_val__3_, exe_rs1_val__2_, exe_rs1_val__1_, exe_rs1_val__0_ }),
    .sel_i(rs1_is_forward),
    .data_o(rs1_to_alu)
  );


  bsg_mux_width_p32_els_p2
  rs2_alu_mux
  (
    .data_i({ rs2_forward_val, exe_rs2_val__31_, exe_rs2_val__30_, exe_rs2_val__29_, exe_rs2_val__28_, exe_rs2_val__27_, exe_rs2_val__26_, exe_rs2_val__25_, exe_rs2_val__24_, exe_rs2_val__23_, exe_rs2_val__22_, exe_rs2_val__21_, exe_rs2_val__20_, exe_rs2_val__19_, exe_rs2_val__18_, exe_rs2_val__17_, exe_rs2_val__16_, exe_rs2_val__15_, exe_rs2_val__14_, exe_rs2_val__13_, exe_rs2_val__12_, exe_rs2_val__11_, exe_rs2_val__10_, exe_rs2_val__9_, exe_rs2_val__8_, exe_rs2_val__7_, exe_rs2_val__6_, exe_rs2_val__5_, exe_rs2_val__4_, exe_rs2_val__3_, exe_rs2_val__2_, exe_rs2_val__1_, exe_rs2_val__0_ }),
    .sel_i(rs2_is_forward),
    .data_o(rs2_to_alu)
  );


  alu_imem_addr_width_p10
  alu_0
  (
    .rs1_i(rs1_to_alu),
    .rs2_i(rs2_to_alu),
    .pc_plus4_i({ exe_pc_plus4__31_, exe_pc_plus4__30_, exe_pc_plus4__29_, exe_pc_plus4__28_, exe_pc_plus4__27_, exe_pc_plus4__26_, exe_pc_plus4__25_, exe_pc_plus4__24_, exe_pc_plus4__23_, exe_pc_plus4__22_, exe_pc_plus4__21_, exe_pc_plus4__20_, exe_pc_plus4__19_, exe_pc_plus4__18_, exe_pc_plus4__17_, exe_pc_plus4__16_, exe_pc_plus4__15_, exe_pc_plus4__14_, exe_pc_plus4__13_, exe_pc_plus4__12_, exe_pc_plus4__11_, exe_pc_plus4__10_, exe_pc_plus4__9_, exe_pc_plus4__8_, exe_pc_plus4__7_, exe_pc_plus4__6_, exe_pc_plus4__5_, exe_pc_plus4__4_, exe_pc_plus4__3_, exe_pc_plus4__2_, exe_pc_plus4__1_, exe_pc_plus4__0_ }),
    .op_i({ exe_instruction__funct7__6_, exe_instruction__funct7__5_, exe_instruction__funct7__4_, exe_instruction__funct7__3_, exe_instruction__funct7__2_, exe_instruction__funct7__1_, exe_instruction__funct7__0_, exe_instruction__rs2__4_, exe_instruction__rs2__3_, exe_instruction__rs2__2_, exe_instruction__rs2__1_, exe_instruction__rs2__0_, exe_instruction__rs1__4_, exe_instruction__rs1__3_, exe_instruction__rs1__2_, exe_instruction__rs1__1_, exe_instruction__rs1__0_, exe_instruction__funct3__2_, exe_instruction__funct3__1_, exe_instruction__funct3__0_, exe_instruction__rd__4_, exe_instruction__rd__3_, exe_instruction__rd__2_, exe_instruction__rd__1_, exe_instruction__rd__0_, exe_instruction__op__6_, exe_instruction__op__5_, exe_instruction__op__4_, exe_instruction__op__3_, exe_instruction__op__2_, exe_instruction__op__1_, exe_instruction__op__0_ }),
    .result_o(basic_comp_result),
    .jalr_addr_o(jalr_addr),
    .jump_now_o(jump_now)
  );


  cl_state_machine
  state_machine
  (
    .instruction_i({ exe_instruction__funct7__6_, exe_instruction__funct7__5_, exe_instruction__funct7__4_, exe_instruction__funct7__3_, exe_instruction__funct7__2_, exe_instruction__funct7__1_, exe_instruction__funct7__0_, exe_instruction__rs2__4_, exe_instruction__rs2__3_, exe_instruction__rs2__2_, exe_instruction__rs2__1_, exe_instruction__rs2__0_, exe_instruction__rs1__4_, exe_instruction__rs1__3_, exe_instruction__rs1__2_, exe_instruction__rs1__1_, exe_instruction__rs1__0_, exe_instruction__funct3__2_, exe_instruction__funct3__1_, exe_instruction__funct3__0_, exe_instruction__rd__4_, exe_instruction__rd__3_, exe_instruction__rd__2_, exe_instruction__rd__1_, exe_instruction__rd__0_, exe_instruction__op__6_, exe_instruction__op__5_, exe_instruction__op__4_, exe_instruction__op__3_, exe_instruction__op__2_, exe_instruction__op__1_, exe_instruction__op__0_ }),
    .state_i(state_r),
    .net_pc_write_cmd_idle_i(net_pc_write_cmd_idle),
    .stall_i(stall),
    .state_o(state_n)
  );


  always @(posedge clk) begin
    if(reset) begin
      pc_wen_r <= 1'b0;
    end else if(1'b1) begin
      pc_wen_r <= pc_wen;
    end 
  end


  always @(posedge clk) begin
    if(reset) begin
      state_r[1] <= 1'b0;
    end else if(1'b1) begin
      state_r[1] <= state_n[1];
    end 
  end


  always @(posedge clk) begin
    if(reset) begin
      state_r[0] <= 1'b0;
    end else if(1'b1) begin
      state_r[0] <= state_n[0];
    end 
  end


  bsg_dff_reset_width_p32_harden_p1
  jalr_prediction_r_reg
  (
    .clock_i(clk),
    .data_i(jalr_prediction_n),
    .reset_i(reset),
    .data_o(jalr_prediction_r)
  );


  bsg_dff_reset_width_p32_harden_p1
  jalr_prediction_rr_reg
  (
    .clock_i(clk),
    .data_i(jalr_prediction_r),
    .reset_i(reset),
    .data_o(jalr_prediction_rr)
  );


  bsg_dff_reset_width_p65_harden_p0
  net_packet_r_reg
  (
    .clock_i(clk),
    .data_i(net_packet_i),
    .reset_i(reset),
    .data_o({ net_packet_r_valid_, net_packet_r_header__bc_, net_packet_r_header__external_, net_packet_r_header__gw_ID__2_, net_packet_r_header__gw_ID__1_, net_packet_r_header__gw_ID__0_, net_packet_r_header__ring_ID__4_, net_packet_r_header__ring_ID__3_, net_packet_r_header__ring_ID__2_, net_packet_r_header__ring_ID__1_, net_packet_r_header__ring_ID__0_, net_packet_r_header__net_op__1_, net_packet_r_header__net_op__0_, net_packet_r_header__mask__3_, net_packet_r_header__mask__2_, net_packet_r_header__mask__1_, net_packet_r_header__mask__0_, net_packet_r_header__reserved__1_, net_packet_r_header__reserved__0_, net_packet_r_header__addr__13_, net_packet_r_header__addr__12_, net_packet_r_header__addr__11_, net_packet_r_header__addr__10_, net_packet_r_header__addr__9_, net_packet_r_header__addr__8_, net_packet_r_header__addr__7_, net_packet_r_header__addr__6_, net_packet_r_header__addr__5_, net_packet_r_header__addr__4_, net_packet_r_header__addr__3_, net_packet_r_header__addr__2_, net_packet_r_header__addr__1_, net_packet_r_header__addr__0_, BImm_sign_ext_31, BImm_sign_ext[10:5], JImm_sign_ext_4, JImm_sign_ext_3, JImm_sign_ext_2, JImm_sign_ext_1, JImm_sign_ext[11:11], JImm_sign_ext[19:12], BImm_sign_ext[4:1], BImm_sign_ext[11:11], instr_cast_op__6_, instr_cast_op__5_, instr_cast_op__4_, instr_cast_op__3_, instr_cast_op__2_, instr_cast_op__1_, instr_cast_op__0_ })
  );


  bsg_dff_reset_width_p32_harden_p1
  instruction_r_reg
  (
    .clock_i(clk),
    .data_i({ BImm_extract[11:11], BImm_extract[9:4], JImm_extract, JImm_extract_10, instruction_rs1__4_, instruction_rs1__3_, instruction_rs1__2_, instruction_rs1__1_, instruction_rs1__0_, instruction_funct3__2_, instruction_funct3__1_, JImm_extract_11, BImm_extract[3:0], BImm_extract[10:10], instruction_op__6_, instruction_op__5_, instruction_op__4_, instruction_op__3_, instruction_op__2_, instruction_op__1_, instruction_op__0_ }),
    .reset_i(reset),
    .data_o(instruction_r)
  );


  bsg_dff_reset_en_width_p10_harden_p1
  pc_r_reg
  (
    .clock_i(clk),
    .reset_i(reset),
    .en_i(pc_wen),
    .data_i(pc_n),
    .data_o(pc_r)
  );


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__31_ <= 1'b0;
    end else begin
      id_pc_plus4__31_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__30_ <= 1'b0;
    end else begin
      id_pc_plus4__30_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__29_ <= 1'b0;
    end else begin
      id_pc_plus4__29_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__28_ <= 1'b0;
    end else begin
      id_pc_plus4__28_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__27_ <= 1'b0;
    end else begin
      id_pc_plus4__27_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__26_ <= 1'b0;
    end else begin
      id_pc_plus4__26_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__25_ <= 1'b0;
    end else begin
      id_pc_plus4__25_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__24_ <= 1'b0;
    end else begin
      id_pc_plus4__24_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__23_ <= 1'b0;
    end else begin
      id_pc_plus4__23_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__22_ <= 1'b0;
    end else begin
      id_pc_plus4__22_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__21_ <= 1'b0;
    end else begin
      id_pc_plus4__21_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__20_ <= 1'b0;
    end else begin
      id_pc_plus4__20_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__19_ <= 1'b0;
    end else begin
      id_pc_plus4__19_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__18_ <= 1'b0;
    end else begin
      id_pc_plus4__18_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__17_ <= 1'b0;
    end else begin
      id_pc_plus4__17_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__16_ <= 1'b0;
    end else begin
      id_pc_plus4__16_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__15_ <= 1'b0;
    end else begin
      id_pc_plus4__15_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__14_ <= 1'b0;
    end else begin
      id_pc_plus4__14_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__13_ <= 1'b0;
    end else begin
      id_pc_plus4__13_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__12_ <= 1'b0;
    end else begin
      id_pc_plus4__12_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_plus4__11_ <= 1'b0;
    end else if(N176) begin
      id_pc_plus4__11_ <= pc_plus4[9];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_plus4__10_ <= 1'b0;
    end else if(N176) begin
      id_pc_plus4__10_ <= pc_plus4[8];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_plus4__9_ <= 1'b0;
    end else if(N176) begin
      id_pc_plus4__9_ <= pc_plus4[7];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_plus4__8_ <= 1'b0;
    end else if(N176) begin
      id_pc_plus4__8_ <= pc_plus4[6];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_plus4__7_ <= 1'b0;
    end else if(N176) begin
      id_pc_plus4__7_ <= pc_plus4[5];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_plus4__6_ <= 1'b0;
    end else if(N176) begin
      id_pc_plus4__6_ <= pc_plus4[4];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_plus4__5_ <= 1'b0;
    end else if(N176) begin
      id_pc_plus4__5_ <= pc_plus4[3];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_plus4__4_ <= 1'b0;
    end else if(N176) begin
      id_pc_plus4__4_ <= pc_plus4[2];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_plus4__3_ <= 1'b0;
    end else if(N176) begin
      id_pc_plus4__3_ <= pc_plus4[1];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_plus4__2_ <= 1'b0;
    end else if(N176) begin
      id_pc_plus4__2_ <= pc_plus4[0];
    end 
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__1_ <= 1'b0;
    end else begin
      id_pc_plus4__1_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N261) begin
      id_pc_plus4__0_ <= 1'b0;
    end else begin
      id_pc_plus4__0_ <= N42;
    end
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_jump_addr__11_ <= 1'b0;
    end else if(N176) begin
      id_pc_jump_addr__11_ <= BImm_extract[9];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_jump_addr__10_ <= 1'b0;
    end else if(N176) begin
      id_pc_jump_addr__10_ <= BImm_extract[8];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_jump_addr__9_ <= 1'b0;
    end else if(N176) begin
      id_pc_jump_addr__9_ <= BImm_extract[7];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_jump_addr__8_ <= 1'b0;
    end else if(N176) begin
      id_pc_jump_addr__8_ <= BImm_extract[6];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_jump_addr__7_ <= 1'b0;
    end else if(N176) begin
      id_pc_jump_addr__7_ <= BImm_extract[5];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_jump_addr__6_ <= 1'b0;
    end else if(N176) begin
      id_pc_jump_addr__6_ <= BImm_extract[4];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_jump_addr__5_ <= 1'b0;
    end else if(N176) begin
      id_pc_jump_addr__5_ <= pc_jump_addr[3];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_jump_addr__4_ <= 1'b0;
    end else if(N176) begin
      id_pc_jump_addr__4_ <= pc_jump_addr[2];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_jump_addr__3_ <= 1'b0;
    end else if(N176) begin
      id_pc_jump_addr__3_ <= pc_jump_addr[1];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_pc_jump_addr__2_ <= 1'b0;
    end else if(N176) begin
      id_pc_jump_addr__2_ <= pc_jump_addr[0];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__funct7__6_ <= 1'b0;
    end else if(N176) begin
      id_instruction__funct7__6_ <= BImm_extract[11];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__funct7__5_ <= 1'b0;
    end else if(N176) begin
      id_instruction__funct7__5_ <= BImm_extract[9];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__funct7__4_ <= 1'b0;
    end else if(N176) begin
      id_instruction__funct7__4_ <= BImm_extract[8];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__funct7__3_ <= 1'b0;
    end else if(N176) begin
      id_instruction__funct7__3_ <= BImm_extract[7];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__funct7__2_ <= 1'b0;
    end else if(N176) begin
      id_instruction__funct7__2_ <= BImm_extract[6];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__funct7__1_ <= 1'b0;
    end else if(N176) begin
      id_instruction__funct7__1_ <= BImm_extract[5];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__funct7__0_ <= 1'b0;
    end else if(N176) begin
      id_instruction__funct7__0_ <= BImm_extract[4];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__rs2__4_ <= 1'b0;
    end else if(N176) begin
      id_instruction__rs2__4_ <= JImm_extract[3];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__rs2__3_ <= 1'b0;
    end else if(N176) begin
      id_instruction__rs2__3_ <= JImm_extract[2];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__rs2__2_ <= 1'b0;
    end else if(N176) begin
      id_instruction__rs2__2_ <= JImm_extract[1];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__rs2__1_ <= 1'b0;
    end else if(N176) begin
      id_instruction__rs2__1_ <= JImm_extract[0];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__rs2__0_ <= 1'b0;
    end else if(N176) begin
      id_instruction__rs2__0_ <= JImm_extract_10;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__rs1__4_ <= 1'b0;
    end else if(N176) begin
      id_instruction__rs1__4_ <= instruction_rs1__4_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__rs1__3_ <= 1'b0;
    end else if(N176) begin
      id_instruction__rs1__3_ <= instruction_rs1__3_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__rs1__2_ <= 1'b0;
    end else if(N176) begin
      id_instruction__rs1__2_ <= instruction_rs1__2_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__rs1__1_ <= 1'b0;
    end else if(N176) begin
      id_instruction__rs1__1_ <= instruction_rs1__1_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__rs1__0_ <= 1'b0;
    end else if(N176) begin
      id_instruction__rs1__0_ <= instruction_rs1__0_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__funct3__2_ <= 1'b0;
    end else if(N176) begin
      id_instruction__funct3__2_ <= instruction_funct3__2_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__funct3__1_ <= 1'b0;
    end else if(N176) begin
      id_instruction__funct3__1_ <= instruction_funct3__1_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__funct3__0_ <= 1'b0;
    end else if(N176) begin
      id_instruction__funct3__0_ <= JImm_extract_11;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__rd__4_ <= 1'b0;
    end else if(N176) begin
      id_instruction__rd__4_ <= BImm_extract[3];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__rd__3_ <= 1'b0;
    end else if(N176) begin
      id_instruction__rd__3_ <= BImm_extract[2];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__rd__2_ <= 1'b0;
    end else if(N176) begin
      id_instruction__rd__2_ <= BImm_extract[1];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__rd__1_ <= 1'b0;
    end else if(N176) begin
      id_instruction__rd__1_ <= BImm_extract[0];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__rd__0_ <= 1'b0;
    end else if(N176) begin
      id_instruction__rd__0_ <= BImm_extract[10];
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__op__6_ <= 1'b0;
    end else if(N176) begin
      id_instruction__op__6_ <= instruction_op__6_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__op__5_ <= 1'b0;
    end else if(N176) begin
      id_instruction__op__5_ <= instruction_op__5_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__op__4_ <= 1'b0;
    end else if(N176) begin
      id_instruction__op__4_ <= instruction_op__4_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__op__3_ <= 1'b0;
    end else if(N176) begin
      id_instruction__op__3_ <= instruction_op__3_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__op__2_ <= 1'b0;
    end else if(N176) begin
      id_instruction__op__2_ <= instruction_op__2_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__op__1_ <= 1'b0;
    end else if(N176) begin
      id_instruction__op__1_ <= instruction_op__1_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_instruction__op__0_ <= 1'b0;
    end else if(N176) begin
      id_instruction__op__0_ <= instruction_op__0_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_decode__op_writes_rf_ <= 1'b0;
    end else if(N176) begin
      id_decode__op_writes_rf_ <= decode_op_writes_rf_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_decode__is_load_op_ <= 1'b0;
    end else if(N176) begin
      id_decode__is_load_op_ <= decode_is_load_op_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_decode__is_store_op_ <= 1'b0;
    end else if(N176) begin
      id_decode__is_store_op_ <= decode_is_store_op_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_decode__is_mem_op_ <= 1'b0;
    end else if(N176) begin
      id_decode__is_mem_op_ <= decode_is_mem_op_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_decode__is_byte_op_ <= 1'b0;
    end else if(N176) begin
      id_decode__is_byte_op_ <= decode_is_byte_op_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_decode__is_hex_op_ <= 1'b0;
    end else if(N176) begin
      id_decode__is_hex_op_ <= decode_is_hex_op_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_decode__is_load_unsigned_ <= 1'b0;
    end else if(N176) begin
      id_decode__is_load_unsigned_ <= decode_is_load_unsigned_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_decode__is_branch_op_ <= 1'b0;
    end else if(N176) begin
      id_decode__is_branch_op_ <= decode_is_branch_op_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_decode__is_jump_op_ <= 1'b0;
    end else if(N176) begin
      id_decode__is_jump_op_ <= decode_is_jump_op_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_decode__op_reads_rf1_ <= 1'b0;
    end else if(N176) begin
      id_decode__op_reads_rf1_ <= decode_op_reads_rf1_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_decode__op_reads_rf2_ <= 1'b0;
    end else if(N176) begin
      id_decode__op_reads_rf2_ <= decode_op_reads_rf2_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_decode__is_md_instr_ <= 1'b0;
    end else if(N176) begin
      id_decode__is_md_instr_ <= decode_is_md_instr_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_decode__is_fence_op_ <= 1'b0;
    end else if(N176) begin
      id_decode__is_fence_op_ <= decode_is_fence_op_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_decode__op_is_load_reservation_ <= 1'b0;
    end else if(N176) begin
      id_decode__op_is_load_reservation_ <= decode_op_is_load_reservation_;
    end 
  end


  always @(posedge clk) begin
    if(N175) begin
      id_decode__op_is_lr_acq_ <= 1'b0;
    end else if(N176) begin
      id_decode__op_is_lr_acq_ <= decode_op_is_lr_acq_;
    end 
  end

  assign N177 = { id_instruction__rs1__4_, id_instruction__rs1__3_, id_instruction__rs1__2_, id_instruction__rs1__1_, id_instruction__rs1__0_ } == wb[36:32];
  assign N178 = { id_instruction__rs2__4_, id_instruction__rs2__3_, id_instruction__rs2__2_, id_instruction__rs2__1_, id_instruction__rs2__0_ } == wb[36:32];
  assign N183 = { id_instruction__rs1__4_, id_instruction__rs1__3_, id_instruction__rs1__2_, id_instruction__rs1__1_, id_instruction__rs1__0_ } == { exe_instruction__rd__4_, exe_instruction__rd__3_, exe_instruction__rd__2_, exe_instruction__rd__1_, exe_instruction__rd__0_ };
  assign N184 = { id_instruction__rs1__4_, id_instruction__rs1__3_, id_instruction__rs1__2_, id_instruction__rs1__1_, id_instruction__rs1__0_ } == { mem_rd_addr__4_, mem_rd_addr__3_, mem_rd_addr__2_, mem_rd_addr__1_, mem_rd_addr__0_ };
  assign N185 = { id_instruction__rs2__4_, id_instruction__rs2__3_, id_instruction__rs2__2_, id_instruction__rs2__1_, id_instruction__rs2__0_ } == { exe_instruction__rd__4_, exe_instruction__rd__3_, exe_instruction__rd__2_, exe_instruction__rd__1_, exe_instruction__rd__0_ };
  assign N186 = { id_instruction__rs2__4_, id_instruction__rs2__3_, id_instruction__rs2__2_, id_instruction__rs2__1_, id_instruction__rs2__0_ } == { mem_rd_addr__4_, mem_rd_addr__3_, mem_rd_addr__2_, mem_rd_addr__1_, mem_rd_addr__0_ };

  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__31_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__31_ <= id_pc_plus4__31_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__30_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__30_ <= id_pc_plus4__30_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__29_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__29_ <= id_pc_plus4__29_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__28_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__28_ <= id_pc_plus4__28_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__27_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__27_ <= id_pc_plus4__27_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__26_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__26_ <= id_pc_plus4__26_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__25_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__25_ <= id_pc_plus4__25_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__24_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__24_ <= id_pc_plus4__24_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__23_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__23_ <= id_pc_plus4__23_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__22_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__22_ <= id_pc_plus4__22_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__21_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__21_ <= id_pc_plus4__21_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__20_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__20_ <= id_pc_plus4__20_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__19_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__19_ <= id_pc_plus4__19_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__18_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__18_ <= id_pc_plus4__18_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__17_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__17_ <= id_pc_plus4__17_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__16_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__16_ <= id_pc_plus4__16_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__15_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__15_ <= id_pc_plus4__15_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__14_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__14_ <= id_pc_plus4__14_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__13_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__13_ <= id_pc_plus4__13_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__12_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__12_ <= id_pc_plus4__12_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__11_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__11_ <= id_pc_plus4__11_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__10_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__10_ <= id_pc_plus4__10_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__9_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__9_ <= id_pc_plus4__9_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__8_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__8_ <= id_pc_plus4__8_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__7_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__7_ <= id_pc_plus4__7_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__6_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__6_ <= id_pc_plus4__6_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__5_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__5_ <= id_pc_plus4__5_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__4_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__4_ <= id_pc_plus4__4_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__3_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__3_ <= id_pc_plus4__3_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__2_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__2_ <= id_pc_plus4__2_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__1_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__1_ <= id_pc_plus4__1_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_plus4__0_ <= 1'b0;
    end else if(N190) begin
      exe_pc_plus4__0_ <= id_pc_plus4__0_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_jump_addr__11_ <= 1'b0;
    end else if(N190) begin
      exe_pc_jump_addr__11_ <= id_pc_jump_addr__11_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_jump_addr__10_ <= 1'b0;
    end else if(N190) begin
      exe_pc_jump_addr__10_ <= id_pc_jump_addr__10_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_jump_addr__9_ <= 1'b0;
    end else if(N190) begin
      exe_pc_jump_addr__9_ <= id_pc_jump_addr__9_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_jump_addr__8_ <= 1'b0;
    end else if(N190) begin
      exe_pc_jump_addr__8_ <= id_pc_jump_addr__8_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_jump_addr__7_ <= 1'b0;
    end else if(N190) begin
      exe_pc_jump_addr__7_ <= id_pc_jump_addr__7_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_jump_addr__6_ <= 1'b0;
    end else if(N190) begin
      exe_pc_jump_addr__6_ <= id_pc_jump_addr__6_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_jump_addr__5_ <= 1'b0;
    end else if(N190) begin
      exe_pc_jump_addr__5_ <= id_pc_jump_addr__5_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_jump_addr__4_ <= 1'b0;
    end else if(N190) begin
      exe_pc_jump_addr__4_ <= id_pc_jump_addr__4_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_jump_addr__3_ <= 1'b0;
    end else if(N190) begin
      exe_pc_jump_addr__3_ <= id_pc_jump_addr__3_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_pc_jump_addr__2_ <= 1'b0;
    end else if(N190) begin
      exe_pc_jump_addr__2_ <= id_pc_jump_addr__2_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__funct7__6_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__funct7__6_ <= id_instruction__funct7__6_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__funct7__5_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__funct7__5_ <= id_instruction__funct7__5_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__funct7__4_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__funct7__4_ <= id_instruction__funct7__4_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__funct7__3_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__funct7__3_ <= id_instruction__funct7__3_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__funct7__2_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__funct7__2_ <= id_instruction__funct7__2_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__funct7__1_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__funct7__1_ <= id_instruction__funct7__1_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__funct7__0_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__funct7__0_ <= id_instruction__funct7__0_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__rs2__4_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__rs2__4_ <= id_instruction__rs2__4_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__rs2__3_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__rs2__3_ <= id_instruction__rs2__3_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__rs2__2_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__rs2__2_ <= id_instruction__rs2__2_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__rs2__1_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__rs2__1_ <= id_instruction__rs2__1_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__rs2__0_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__rs2__0_ <= id_instruction__rs2__0_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__rs1__4_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__rs1__4_ <= id_instruction__rs1__4_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__rs1__3_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__rs1__3_ <= id_instruction__rs1__3_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__rs1__2_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__rs1__2_ <= id_instruction__rs1__2_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__rs1__1_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__rs1__1_ <= id_instruction__rs1__1_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__rs1__0_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__rs1__0_ <= id_instruction__rs1__0_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__funct3__2_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__funct3__2_ <= id_instruction__funct3__2_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__funct3__1_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__funct3__1_ <= id_instruction__funct3__1_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__funct3__0_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__funct3__0_ <= id_instruction__funct3__0_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__rd__4_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__rd__4_ <= id_instruction__rd__4_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__rd__3_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__rd__3_ <= id_instruction__rd__3_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__rd__2_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__rd__2_ <= id_instruction__rd__2_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__rd__1_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__rd__1_ <= id_instruction__rd__1_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__rd__0_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__rd__0_ <= id_instruction__rd__0_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__op__6_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__op__6_ <= id_instruction__op__6_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__op__5_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__op__5_ <= id_instruction__op__5_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__op__4_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__op__4_ <= id_instruction__op__4_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__op__3_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__op__3_ <= id_instruction__op__3_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__op__2_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__op__2_ <= id_instruction__op__2_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__op__1_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__op__1_ <= id_instruction__op__1_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_instruction__op__0_ <= 1'b0;
    end else if(N190) begin
      exe_instruction__op__0_ <= id_instruction__op__0_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_decode__op_writes_rf_ <= 1'b0;
    end else if(N190) begin
      exe_decode__op_writes_rf_ <= id_decode__op_writes_rf_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_decode__is_load_op_ <= 1'b0;
    end else if(N190) begin
      exe_decode__is_load_op_ <= id_decode__is_load_op_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      to_mem_o[69] <= 1'b0;
    end else if(N190) begin
      to_mem_o[69] <= id_decode__is_store_op_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_decode__is_mem_op_ <= 1'b0;
    end else if(N190) begin
      exe_decode__is_mem_op_ <= id_decode__is_mem_op_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_decode__is_byte_op_ <= 1'b0;
    end else if(N190) begin
      exe_decode__is_byte_op_ <= id_decode__is_byte_op_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_decode__is_hex_op_ <= 1'b0;
    end else if(N190) begin
      exe_decode__is_hex_op_ <= id_decode__is_hex_op_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_decode__is_load_unsigned_ <= 1'b0;
    end else if(N190) begin
      exe_decode__is_load_unsigned_ <= id_decode__is_load_unsigned_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_decode__is_branch_op_ <= 1'b0;
    end else if(N190) begin
      exe_decode__is_branch_op_ <= id_decode__is_branch_op_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_decode__is_jump_op_ <= 1'b0;
    end else if(N190) begin
      exe_decode__is_jump_op_ <= id_decode__is_jump_op_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_decode__is_md_instr_ <= 1'b0;
    end else if(N190) begin
      exe_decode__is_md_instr_ <= id_decode__is_md_instr_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_decode__is_fence_op_ <= 1'b0;
    end else if(N190) begin
      exe_decode__is_fence_op_ <= id_decode__is_fence_op_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_decode__op_is_load_reservation_ <= 1'b0;
    end else if(N190) begin
      exe_decode__op_is_load_reservation_ <= id_decode__op_is_load_reservation_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_decode__op_is_lr_acq_ <= 1'b0;
    end else if(N190) begin
      exe_decode__op_is_lr_acq_ <= id_decode__op_is_lr_acq_;
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_rs1_val__31_ <= 1'b0;
    end else if(N190) begin
      exe_rs1_val__31_ <= rs1_to_exe[31];
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_rs1_val__30_ <= 1'b0;
    end else if(N190) begin
      exe_rs1_val__30_ <= rs1_to_exe[30];
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_rs1_val__29_ <= 1'b0;
    end else if(N190) begin
      exe_rs1_val__29_ <= rs1_to_exe[29];
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_rs1_val__28_ <= 1'b0;
    end else if(N190) begin
      exe_rs1_val__28_ <= rs1_to_exe[28];
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_rs1_val__27_ <= 1'b0;
    end else if(N190) begin
      exe_rs1_val__27_ <= rs1_to_exe[27];
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_rs1_val__26_ <= 1'b0;
    end else if(N190) begin
      exe_rs1_val__26_ <= rs1_to_exe[26];
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_rs1_val__25_ <= 1'b0;
    end else if(N190) begin
      exe_rs1_val__25_ <= rs1_to_exe[25];
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_rs1_val__24_ <= 1'b0;
    end else if(N190) begin
      exe_rs1_val__24_ <= rs1_to_exe[24];
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_rs1_val__23_ <= 1'b0;
    end else if(N190) begin
      exe_rs1_val__23_ <= rs1_to_exe[23];
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_rs1_val__22_ <= 1'b0;
    end else if(N190) begin
      exe_rs1_val__22_ <= rs1_to_exe[22];
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_rs1_val__21_ <= 1'b0;
    end else if(N190) begin
      exe_rs1_val__21_ <= rs1_to_exe[21];
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_rs1_val__20_ <= 1'b0;
    end else if(N190) begin
      exe_rs1_val__20_ <= rs1_to_exe[20];
    end 
  end


  always @(posedge clk) begin
    if(N262) begin
      exe_rs1_val__19_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__19_ <= rs1_to_exe[19];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__18_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__18_ <= rs1_to_exe[18];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__17_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__17_ <= rs1_to_exe[17];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__16_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__16_ <= rs1_to_exe[16];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__15_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__15_ <= rs1_to_exe[15];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__14_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__14_ <= rs1_to_exe[14];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__13_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__13_ <= rs1_to_exe[13];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__12_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__12_ <= rs1_to_exe[12];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__11_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__11_ <= rs1_to_exe[11];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__10_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__10_ <= rs1_to_exe[10];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__9_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__9_ <= rs1_to_exe[9];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__8_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__8_ <= rs1_to_exe[8];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__7_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__7_ <= rs1_to_exe[7];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__6_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__6_ <= rs1_to_exe[6];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__5_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__5_ <= rs1_to_exe[5];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__4_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__4_ <= rs1_to_exe[4];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__3_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__3_ <= rs1_to_exe[3];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__2_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__2_ <= rs1_to_exe[2];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__1_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__1_ <= rs1_to_exe[1];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_val__0_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_val__0_ <= rs1_to_exe[0];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__31_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__31_ <= rs2_to_exe[31];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__30_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__30_ <= rs2_to_exe[30];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__29_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__29_ <= rs2_to_exe[29];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__28_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__28_ <= rs2_to_exe[28];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__27_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__27_ <= rs2_to_exe[27];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__26_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__26_ <= rs2_to_exe[26];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__25_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__25_ <= rs2_to_exe[25];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__24_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__24_ <= rs2_to_exe[24];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__23_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__23_ <= rs2_to_exe[23];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__22_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__22_ <= rs2_to_exe[22];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__21_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__21_ <= rs2_to_exe[21];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__20_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__20_ <= rs2_to_exe[20];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__19_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__19_ <= rs2_to_exe[19];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__18_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__18_ <= rs2_to_exe[18];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__17_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__17_ <= rs2_to_exe[17];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__16_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__16_ <= rs2_to_exe[16];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__15_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__15_ <= rs2_to_exe[15];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__14_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__14_ <= rs2_to_exe[14];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__13_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__13_ <= rs2_to_exe[13];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__12_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__12_ <= rs2_to_exe[12];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__11_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__11_ <= rs2_to_exe[11];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__10_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__10_ <= rs2_to_exe[10];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__9_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__9_ <= rs2_to_exe[9];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__8_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__8_ <= rs2_to_exe[8];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__7_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__7_ <= rs2_to_exe[7];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__6_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__6_ <= rs2_to_exe[6];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__5_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__5_ <= rs2_to_exe[5];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__4_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__4_ <= rs2_to_exe[4];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__3_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__3_ <= rs2_to_exe[3];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__2_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__2_ <= rs2_to_exe[2];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__1_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__1_ <= rs2_to_exe[1];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_val__0_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_val__0_ <= rs2_to_exe[0];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__31_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__31_ <= mem_addr_op2[31];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__30_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__30_ <= mem_addr_op2[30];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__29_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__29_ <= mem_addr_op2[29];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__28_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__28_ <= mem_addr_op2[28];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__27_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__27_ <= mem_addr_op2[27];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__26_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__26_ <= mem_addr_op2[26];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__25_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__25_ <= mem_addr_op2[25];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__24_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__24_ <= mem_addr_op2[24];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__23_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__23_ <= mem_addr_op2[23];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__22_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__22_ <= mem_addr_op2[22];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__21_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__21_ <= mem_addr_op2[21];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__20_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__20_ <= mem_addr_op2[20];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__19_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__19_ <= mem_addr_op2[19];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__18_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__18_ <= mem_addr_op2[18];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__17_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__17_ <= mem_addr_op2[17];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__16_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__16_ <= mem_addr_op2[16];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__15_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__15_ <= mem_addr_op2[15];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__14_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__14_ <= mem_addr_op2[14];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__13_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__13_ <= mem_addr_op2[13];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__12_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__12_ <= mem_addr_op2[12];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__11_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__11_ <= mem_addr_op2[11];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__10_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__10_ <= mem_addr_op2[10];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__9_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__9_ <= mem_addr_op2[9];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__8_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__8_ <= mem_addr_op2[8];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__7_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__7_ <= mem_addr_op2[7];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__6_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__6_ <= mem_addr_op2[6];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__5_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__5_ <= mem_addr_op2[5];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__4_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__4_ <= mem_addr_op2[4];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__3_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__3_ <= mem_addr_op2[3];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__2_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__2_ <= mem_addr_op2[2];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__1_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__1_ <= mem_addr_op2[1];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_mem_addr_op2__0_ <= 1'b0;
    end else if(N191) begin
      exe_mem_addr_op2__0_ <= mem_addr_op2[0];
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_in_mem_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_in_mem_ <= exe_rs1_in_mem;
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs1_in_wb_ <= 1'b0;
    end else if(N191) begin
      exe_rs1_in_wb_ <= exe_rs1_in_wb;
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_in_mem_ <= 1'b0;
    end else if(N191) begin
      exe_rs2_in_mem_ <= exe_rs2_in_mem;
    end 
  end


  always @(posedge clk) begin
    if(N263) begin
      exe_rs2_in_wb_ <= 1'b0;
    end else if(N190) begin
      exe_rs2_in_wb_ <= exe_rs2_in_wb;
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_rd_addr__4_ <= 1'b0;
    end else if(N195) begin
      mem_rd_addr__4_ <= exe_instruction__rd__4_;
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_rd_addr__3_ <= 1'b0;
    end else if(N195) begin
      mem_rd_addr__3_ <= exe_instruction__rd__3_;
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_rd_addr__2_ <= 1'b0;
    end else if(N195) begin
      mem_rd_addr__2_ <= exe_instruction__rd__2_;
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_rd_addr__1_ <= 1'b0;
    end else if(N195) begin
      mem_rd_addr__1_ <= exe_instruction__rd__1_;
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_rd_addr__0_ <= 1'b0;
    end else if(N195) begin
      mem_rd_addr__0_ <= exe_instruction__rd__0_;
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_decode__op_writes_rf_ <= 1'b0;
    end else if(N195) begin
      mem_decode__op_writes_rf_ <= exe_decode__op_writes_rf_;
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_decode__is_load_op_ <= 1'b0;
    end else if(N195) begin
      mem_decode__is_load_op_ <= exe_decode__is_load_op_;
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_decode__is_mem_op_ <= 1'b0;
    end else if(N195) begin
      mem_decode__is_mem_op_ <= exe_decode__is_mem_op_;
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_decode__is_byte_op_ <= 1'b0;
    end else if(N195) begin
      mem_decode__is_byte_op_ <= exe_decode__is_byte_op_;
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_decode__is_hex_op_ <= 1'b0;
    end else if(N195) begin
      mem_decode__is_hex_op_ <= exe_decode__is_hex_op_;
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_decode__is_load_unsigned_ <= 1'b0;
    end else if(N195) begin
      mem_decode__is_load_unsigned_ <= exe_decode__is_load_unsigned_;
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__31_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__31_ <= alu_result[31];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__30_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__30_ <= alu_result[30];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__29_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__29_ <= alu_result[29];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__28_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__28_ <= alu_result[28];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__27_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__27_ <= alu_result[27];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__26_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__26_ <= alu_result[26];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__25_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__25_ <= alu_result[25];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__24_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__24_ <= alu_result[24];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__23_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__23_ <= alu_result[23];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__22_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__22_ <= alu_result[22];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__21_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__21_ <= alu_result[21];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__20_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__20_ <= alu_result[20];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__19_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__19_ <= alu_result[19];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__18_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__18_ <= alu_result[18];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__17_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__17_ <= alu_result[17];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__16_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__16_ <= alu_result[16];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__15_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__15_ <= alu_result[15];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__14_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__14_ <= alu_result[14];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__13_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__13_ <= alu_result[13];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__12_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__12_ <= alu_result[12];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__11_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__11_ <= alu_result[11];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__10_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__10_ <= alu_result[10];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__9_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__9_ <= alu_result[9];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__8_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__8_ <= alu_result[8];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__7_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__7_ <= alu_result[7];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__6_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__6_ <= alu_result[6];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__5_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__5_ <= alu_result[5];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__4_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__4_ <= alu_result[4];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__3_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__3_ <= alu_result[3];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__2_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__2_ <= alu_result[2];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__1_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__1_ <= alu_result[1];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_alu_result__0_ <= 1'b0;
    end else if(N195) begin
      mem_alu_result__0_ <= alu_result[0];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_mem_addr_send__1_ <= 1'b0;
    end else if(N195) begin
      mem_mem_addr_send__1_ <= to_mem_o[34];
    end 
  end


  always @(posedge clk) begin
    if(N192) begin
      mem_mem_addr_send__0_ <= 1'b0;
    end else if(N195) begin
      mem_mem_addr_send__0_ <= to_mem_o[33];
    end 
  end


  always @(posedge clk) begin
    if(N264) begin
      load_buffer_data[31] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[31] <= from_mem_i[32];
    end 
  end


  always @(posedge clk) begin
    if(N296) begin
      load_buffer_data[30] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[30] <= from_mem_i[31];
    end 
  end


  always @(posedge clk) begin
    if(N295) begin
      load_buffer_data[29] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[29] <= from_mem_i[30];
    end 
  end


  always @(posedge clk) begin
    if(N294) begin
      load_buffer_data[28] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[28] <= from_mem_i[29];
    end 
  end


  always @(posedge clk) begin
    if(N293) begin
      load_buffer_data[27] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[27] <= from_mem_i[28];
    end 
  end


  always @(posedge clk) begin
    if(N292) begin
      load_buffer_data[26] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[26] <= from_mem_i[27];
    end 
  end


  always @(posedge clk) begin
    if(N291) begin
      load_buffer_data[25] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[25] <= from_mem_i[26];
    end 
  end


  always @(posedge clk) begin
    if(N290) begin
      load_buffer_data[24] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[24] <= from_mem_i[25];
    end 
  end


  always @(posedge clk) begin
    if(N289) begin
      load_buffer_data[23] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[23] <= from_mem_i[24];
    end 
  end


  always @(posedge clk) begin
    if(N288) begin
      load_buffer_data[22] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[22] <= from_mem_i[23];
    end 
  end


  always @(posedge clk) begin
    if(N287) begin
      load_buffer_data[21] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[21] <= from_mem_i[22];
    end 
  end


  always @(posedge clk) begin
    if(N286) begin
      load_buffer_data[20] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[20] <= from_mem_i[21];
    end 
  end


  always @(posedge clk) begin
    if(N285) begin
      load_buffer_data[19] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[19] <= from_mem_i[20];
    end 
  end


  always @(posedge clk) begin
    if(N284) begin
      load_buffer_data[18] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[18] <= from_mem_i[19];
    end 
  end


  always @(posedge clk) begin
    if(N283) begin
      load_buffer_data[17] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[17] <= from_mem_i[18];
    end 
  end


  always @(posedge clk) begin
    if(N282) begin
      load_buffer_data[16] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[16] <= from_mem_i[17];
    end 
  end


  always @(posedge clk) begin
    if(N281) begin
      load_buffer_data[15] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[15] <= from_mem_i[16];
    end 
  end


  always @(posedge clk) begin
    if(N280) begin
      load_buffer_data[14] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[14] <= from_mem_i[15];
    end 
  end


  always @(posedge clk) begin
    if(N279) begin
      load_buffer_data[13] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[13] <= from_mem_i[14];
    end 
  end


  always @(posedge clk) begin
    if(N278) begin
      load_buffer_data[12] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[12] <= from_mem_i[13];
    end 
  end


  always @(posedge clk) begin
    if(N277) begin
      load_buffer_data[11] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[11] <= from_mem_i[12];
    end 
  end


  always @(posedge clk) begin
    if(N276) begin
      load_buffer_data[10] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[10] <= from_mem_i[11];
    end 
  end


  always @(posedge clk) begin
    if(N275) begin
      load_buffer_data[9] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[9] <= from_mem_i[10];
    end 
  end


  always @(posedge clk) begin
    if(N274) begin
      load_buffer_data[8] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[8] <= from_mem_i[9];
    end 
  end


  always @(posedge clk) begin
    if(N273) begin
      load_buffer_data[7] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[7] <= from_mem_i[8];
    end 
  end


  always @(posedge clk) begin
    if(N272) begin
      load_buffer_data[6] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[6] <= from_mem_i[7];
    end 
  end


  always @(posedge clk) begin
    if(N271) begin
      load_buffer_data[5] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[5] <= from_mem_i[6];
    end 
  end


  always @(posedge clk) begin
    if(N270) begin
      load_buffer_data[4] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[4] <= from_mem_i[5];
    end 
  end


  always @(posedge clk) begin
    if(N269) begin
      load_buffer_data[3] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[3] <= from_mem_i[4];
    end 
  end


  always @(posedge clk) begin
    if(N268) begin
      load_buffer_data[2] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[2] <= from_mem_i[3];
    end 
  end


  always @(posedge clk) begin
    if(N267) begin
      load_buffer_data[1] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[1] <= from_mem_i[2];
    end 
  end


  always @(posedge clk) begin
    if(N266) begin
      load_buffer_data[0] <= 1'b0;
    end else if(N199) begin
      load_buffer_data[0] <= from_mem_i[1];
    end 
  end


  always @(posedge clk) begin
    if(N265) begin
      is_load_buffer_valid <= 1'b0;
    end else if(N199) begin
      is_load_buffer_valid <= 1'b1;
    end 
  end

  assign N203 = N201 & N202;
  assign N204 = mem_mem_addr_send__1_ | N202;
  assign N206 = N201 | mem_mem_addr_send__0_;
  assign N208 = mem_mem_addr_send__1_ & mem_mem_addr_send__0_;

  always @(posedge clk) begin
    if(N257) begin
      wb[37] <= 1'b0;
    end else if(N260) begin
      wb[37] <= mem_decode__op_writes_rf_;
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[36] <= 1'b0;
    end else if(N260) begin
      wb[36] <= mem_rd_addr__4_;
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[35] <= 1'b0;
    end else if(N260) begin
      wb[35] <= mem_rd_addr__3_;
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[34] <= 1'b0;
    end else if(N260) begin
      wb[34] <= mem_rd_addr__2_;
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[33] <= 1'b0;
    end else if(N260) begin
      wb[33] <= mem_rd_addr__1_;
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[32] <= 1'b0;
    end else if(N260) begin
      wb[32] <= mem_rd_addr__0_;
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[31] <= 1'b0;
    end else if(N260) begin
      wb[31] <= rf_data[31];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[30] <= 1'b0;
    end else if(N260) begin
      wb[30] <= rf_data[30];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[29] <= 1'b0;
    end else if(N260) begin
      wb[29] <= rf_data[29];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[28] <= 1'b0;
    end else if(N260) begin
      wb[28] <= rf_data[28];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[27] <= 1'b0;
    end else if(N260) begin
      wb[27] <= rf_data[27];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[26] <= 1'b0;
    end else if(N260) begin
      wb[26] <= rf_data[26];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[25] <= 1'b0;
    end else if(N260) begin
      wb[25] <= rf_data[25];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[24] <= 1'b0;
    end else if(N260) begin
      wb[24] <= rf_data[24];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[23] <= 1'b0;
    end else if(N260) begin
      wb[23] <= rf_data[23];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[22] <= 1'b0;
    end else if(N260) begin
      wb[22] <= rf_data[22];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[21] <= 1'b0;
    end else if(N260) begin
      wb[21] <= rf_data[21];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[20] <= 1'b0;
    end else if(N260) begin
      wb[20] <= rf_data[20];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[19] <= 1'b0;
    end else if(N260) begin
      wb[19] <= rf_data[19];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[18] <= 1'b0;
    end else if(N260) begin
      wb[18] <= rf_data[18];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[17] <= 1'b0;
    end else if(N260) begin
      wb[17] <= rf_data[17];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[16] <= 1'b0;
    end else if(N260) begin
      wb[16] <= rf_data[16];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[15] <= 1'b0;
    end else if(N260) begin
      wb[15] <= rf_data[15];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[14] <= 1'b0;
    end else if(N260) begin
      wb[14] <= rf_data[14];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[13] <= 1'b0;
    end else if(N260) begin
      wb[13] <= rf_data[13];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[12] <= 1'b0;
    end else if(N260) begin
      wb[12] <= rf_data[12];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[11] <= 1'b0;
    end else if(N260) begin
      wb[11] <= rf_data[11];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[10] <= 1'b0;
    end else if(N260) begin
      wb[10] <= rf_data[10];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[9] <= 1'b0;
    end else if(N260) begin
      wb[9] <= rf_data[9];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[8] <= 1'b0;
    end else if(N260) begin
      wb[8] <= rf_data[8];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[7] <= 1'b0;
    end else if(N260) begin
      wb[7] <= rf_data[7];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[6] <= 1'b0;
    end else if(N260) begin
      wb[6] <= rf_data[6];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[5] <= 1'b0;
    end else if(N260) begin
      wb[5] <= rf_data[5];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[4] <= 1'b0;
    end else if(N260) begin
      wb[4] <= rf_data[4];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[3] <= 1'b0;
    end else if(N260) begin
      wb[3] <= rf_data[3];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[2] <= 1'b0;
    end else if(N260) begin
      wb[2] <= rf_data[2];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[1] <= 1'b0;
    end else if(N260) begin
      wb[1] <= rf_data[1];
    end 
  end


  always @(posedge clk) begin
    if(N257) begin
      wb[0] <= 1'b0;
    end else if(N260) begin
      wb[0] <= rf_data[0];
    end 
  end

  assign N261 = N175 | n_cse_43;
  assign N262 = N187 | N188;
  assign N263 = N187 | N188;
  assign N264 = reset | N197;
  assign N265 = reset | N197;
  assign N266 = reset | N197;
  assign N267 = reset | N197;
  assign N268 = reset | N197;
  assign N269 = reset | N197;
  assign N270 = reset | N197;
  assign N271 = reset | N197;
  assign N272 = reset | N197;
  assign N273 = reset | N197;
  assign N274 = reset | N197;
  assign N275 = reset | N197;
  assign N276 = reset | N197;
  assign N277 = reset | N197;
  assign N278 = reset | N197;
  assign N279 = reset | N197;
  assign N280 = reset | N197;
  assign N281 = reset | N197;
  assign N282 = reset | N197;
  assign N283 = reset | N197;
  assign N284 = reset | N197;
  assign N285 = reset | N197;
  assign N286 = reset | N197;
  assign N287 = reset | N197;
  assign N288 = reset | N197;
  assign N289 = reset | N197;
  assign N290 = reset | N197;
  assign N291 = reset | N197;
  assign N292 = reset | N197;
  assign N293 = reset | N197;
  assign N294 = reset | N197;
  assign N295 = reset | N197;
  assign N296 = reset | N197;
  assign N297 = ~state_r[0];
  assign N298 = N297 | state_r[1];
  assign N299 = ~instruction_op__6_;
  assign N300 = ~instruction_op__5_;
  assign N301 = ~instruction_op__3_;
  assign N302 = ~instruction_op__2_;
  assign N303 = ~instruction_op__1_;
  assign N304 = ~instruction_op__0_;
  assign N305 = N300 | N299;
  assign N306 = instruction_op__4_ | N305;
  assign N307 = N301 | N306;
  assign N308 = N302 | N307;
  assign N309 = N303 | N308;
  assign N310 = N304 | N309;
  assign N311 = ~N310;
  assign N312 = ~net_packet_r_header__net_op__0_;
  assign N313 = N312 | net_packet_r_header__net_op__1_;
  assign N314 = ~N313;
  assign N315 = ~net_packet_r_header__net_op__1_;
  assign N316 = net_packet_r_header__net_op__0_ | N315;
  assign N317 = ~N316;
  assign N318 = state_r[0] | state_r[1];
  assign N319 = ~N318;
  assign N320 = net_packet_r_header__net_op__0_ & net_packet_r_header__net_op__1_;
  assign N321 = net_packet_r_header__ring_ID__3_ | net_packet_r_header__ring_ID__4_;
  assign N322 = net_packet_r_header__ring_ID__2_ | N321;
  assign N323 = net_packet_r_header__ring_ID__1_ | N322;
  assign N324 = net_packet_r_header__ring_ID__0_ | N323;
  assign N325 = ~N324;
  assign to_mem_o[64:33] = rs1_to_alu + { exe_mem_addr_op2__31_, exe_mem_addr_op2__30_, exe_mem_addr_op2__29_, exe_mem_addr_op2__28_, exe_mem_addr_op2__27_, exe_mem_addr_op2__26_, exe_mem_addr_op2__25_, exe_mem_addr_op2__24_, exe_mem_addr_op2__23_, exe_mem_addr_op2__22_, exe_mem_addr_op2__21_, exe_mem_addr_op2__20_, exe_mem_addr_op2__19_, exe_mem_addr_op2__18_, exe_mem_addr_op2__17_, exe_mem_addr_op2__16_, exe_mem_addr_op2__15_, exe_mem_addr_op2__14_, exe_mem_addr_op2__13_, exe_mem_addr_op2__12_, exe_mem_addr_op2__11_, exe_mem_addr_op2__10_, exe_mem_addr_op2__9_, exe_mem_addr_op2__8_, exe_mem_addr_op2__7_, exe_mem_addr_op2__6_, exe_mem_addr_op2__5_, exe_mem_addr_op2__4_, exe_mem_addr_op2__3_, exe_mem_addr_op2__2_, exe_mem_addr_op2__1_, exe_mem_addr_op2__0_ };
  assign pc_plus4 = pc_r + 1'b1;
  assign inject_pc_value = $signed({ net_packet_r_header__addr__11_, net_packet_r_header__addr__10_, net_packet_r_header__addr__9_, net_packet_r_header__addr__8_, net_packet_r_header__addr__7_, net_packet_r_header__addr__6_, net_packet_r_header__addr__5_, net_packet_r_header__addr__4_, net_packet_r_header__addr__3_, net_packet_r_header__addr__2_ }) + $signed({ inject_pc_rel_9, BImm_sign_ext[10:5], inject_pc_rel });
  assign to_mem_o[32:1] = (N0)? { N78, N77, N76, N75, N74, N73, N72, N71, N70, N69, N68, N67, N66, N65, N64, N63, N62, N61, N60, N59, N58, N57, N56, N55, N54, N53, N52, N51, N50, N49, N48, N47 } : 
                          (N121)? { N115, N114, N113, N112, N111, N110, N109, N108, N107, N106, N105, N104, N103, N102, N101, N100, N99, N98, N97, N96, N95, N94, N93, N92, N91, N90, N89, N88, N87, N86, N85, N84 } : 
                          (N46)? rs2_to_alu : 1'b0;
  assign N0 = exe_decode__is_byte_op_;
  assign to_mem_o[68:65] = (N0)? { N82, N81, N80, N79 } : 
                           (N121)? { N119, N118, N117, N116 } : 
                           (N46)? { 1'b1, 1'b1, 1'b1, 1'b1 } : 1'b0;
  assign mem_addr_op2 = (N1)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                        (N125)? { id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__5_, id_instruction__funct7__4_, id_instruction__funct7__3_, id_instruction__funct7__2_, id_instruction__funct7__1_, id_instruction__funct7__0_, id_instruction__rd__4_, id_instruction__rd__3_, id_instruction__rd__2_, id_instruction__rd__1_, id_instruction__rd__0_ } : 
                        (N123)? { id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__6_, id_instruction__funct7__5_, id_instruction__funct7__4_, id_instruction__funct7__3_, id_instruction__funct7__2_, id_instruction__funct7__1_, id_instruction__funct7__0_, id_instruction__rs2__4_, id_instruction__rs2__3_, id_instruction__rs2__2_, id_instruction__rs2__1_, id_instruction__rs2__0_ } : 1'b0;
  assign N1 = id_decode__op_is_load_reservation_;
  assign pc_jump_addr = (N2)? BImm_extract[3:0] : 
                        (N127)? JImm_extract : 1'b0;
  assign N2 = decode_is_branch_op_;
  assign jalr_prediction_n = (N3)? { exe_pc_plus4__31_, exe_pc_plus4__30_, exe_pc_plus4__29_, exe_pc_plus4__28_, exe_pc_plus4__27_, exe_pc_plus4__26_, exe_pc_plus4__25_, exe_pc_plus4__24_, exe_pc_plus4__23_, exe_pc_plus4__22_, exe_pc_plus4__21_, exe_pc_plus4__20_, exe_pc_plus4__19_, exe_pc_plus4__18_, exe_pc_plus4__17_, exe_pc_plus4__16_, exe_pc_plus4__15_, exe_pc_plus4__14_, exe_pc_plus4__13_, exe_pc_plus4__12_, exe_pc_plus4__11_, exe_pc_plus4__10_, exe_pc_plus4__9_, exe_pc_plus4__8_, exe_pc_plus4__7_, exe_pc_plus4__6_, exe_pc_plus4__5_, exe_pc_plus4__4_, exe_pc_plus4__3_, exe_pc_plus4__2_, exe_pc_plus4__1_, exe_pc_plus4__0_ } : 
                             (N128)? jalr_prediction_r : 1'b0;
  assign N3 = exe_decode__is_jump_op_;
  assign { N146, N145, N144, N143, N142, N141, N140, N139, N138, N137 } = (N4)? { exe_pc_jump_addr__11_, exe_pc_jump_addr__10_, exe_pc_jump_addr__9_, exe_pc_jump_addr__8_, exe_pc_jump_addr__7_, exe_pc_jump_addr__6_, exe_pc_jump_addr__5_, exe_pc_jump_addr__4_, exe_pc_jump_addr__3_, exe_pc_jump_addr__2_ } : 
                                                                          (N5)? { exe_pc_plus4__11_, exe_pc_plus4__10_, exe_pc_plus4__9_, exe_pc_plus4__8_, exe_pc_plus4__7_, exe_pc_plus4__6_, exe_pc_plus4__5_, exe_pc_plus4__4_, exe_pc_plus4__3_, exe_pc_plus4__2_ } : 1'b0;
  assign N4 = branch_under_predict;
  assign N5 = N136;
  assign { N156, N155, N154, N153, N152, N151, N150, N149, N148, N147 } = (N6)? { N146, N145, N144, N143, N142, N141, N140, N139, N138, N137 } : 
                                                                          (N158)? jalr_addr : 
                                                                          (N161)? { BImm_extract[9:4], pc_jump_addr } : 
                                                                          (N164)? jalr_prediction_n[9:0] : 
                                                                          (N135)? pc_plus4 : 1'b0;
  assign N6 = branch_mispredict;
  assign pc_n = (N7)? { net_packet_r_header__addr__11_, net_packet_r_header__addr__10_, net_packet_r_header__addr__9_, net_packet_r_header__addr__8_, net_packet_r_header__addr__7_, net_packet_r_header__addr__6_, net_packet_r_header__addr__5_, net_packet_r_header__addr__4_, net_packet_r_header__addr__3_, net_packet_r_header__addr__2_ } : 
                (N8)? { N156, N155, N154, N153, N152, N151, N150, N149, N148, N147 } : 1'b0;
  assign N7 = N130;
  assign N8 = N129;
  assign imem_addr = (N9)? { net_packet_r_header__addr__11_, net_packet_r_header__addr__10_, net_packet_r_header__addr__9_, net_packet_r_header__addr__8_, net_packet_r_header__addr__7_, net_packet_r_header__addr__6_, net_packet_r_header__addr__5_, net_packet_r_header__addr__4_, net_packet_r_header__addr__3_, net_packet_r_header__addr__2_ } : 
                     (N10)? pc_n : 1'b0;
  assign N9 = N166;
  assign N10 = N165;
  assign { inject_pc_rel_9, inject_pc_rel } = (N11)? { BImm_sign_ext[11:11], BImm_sign_ext[4:2] } : 
                                              (N12)? { JImm_sign_ext[11:11], JImm_sign_ext_4, JImm_sign_ext_3, JImm_sign_ext_2 } : 1'b0;
  assign N11 = write_branch_instr;
  assign N12 = N167;
  assign { imem_w_data, imem_w_data_0 } = (N11)? { 1'b0, inject_pc_value[9:4], JImm_sign_ext_4, JImm_sign_ext_3, JImm_sign_ext_2, JImm_sign_ext_1, JImm_sign_ext[11:11], JImm_sign_ext[19:12], inject_pc_value[3:0], 1'b0, BImm_sign_ext_31 } : 
                                          (N171)? { 1'b0, inject_pc_value, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, BImm_sign_ext[4:1], BImm_sign_ext[11:11], instr_cast_op__0_ } : 
                                          (N169)? { BImm_sign_ext_31, BImm_sign_ext[10:5], JImm_sign_ext_4, JImm_sign_ext_3, JImm_sign_ext_2, JImm_sign_ext_1, JImm_sign_ext[11:11], JImm_sign_ext[19:12], BImm_sign_ext[4:1], BImm_sign_ext[11:11], instr_cast_op__0_ } : 1'b0;
  assign { BImm_extract[11:11], BImm_extract[9:4], JImm_extract, JImm_extract_10, instruction_rs1__4_, instruction_rs1__3_, instruction_rs1__2_, instruction_rs1__1_, instruction_rs1__0_, instruction_funct3__2_, instruction_funct3__1_, JImm_extract_11, BImm_extract[3:0], BImm_extract[10:10], instruction_op__6_, instruction_op__5_, instruction_op__4_, instruction_op__3_, instruction_op__2_, instruction_op__1_, instruction_op__0_ } = (N13)? imem_out : 
                                                                                                                                                                                                                                                                                                                                                                                                                                                   (N14)? instruction_r : 1'b0;
  assign N13 = pc_wen_r;
  assign N14 = N172;
  assign rf_wa = (N15)? { net_packet_r_header__addr__4_, net_packet_r_header__addr__3_, net_packet_r_header__addr__2_, net_packet_r_header__addr__1_, net_packet_r_header__addr__0_ } : 
                 (N16)? wb[36:32] : 1'b0;
  assign N15 = net_reg_write_cmd;
  assign N16 = N173;
  assign rf_wd = (N15)? { BImm_sign_ext_31, BImm_sign_ext[10:5], JImm_sign_ext_4, JImm_sign_ext_3, JImm_sign_ext_2, JImm_sign_ext_1, JImm_sign_ext[11:11], JImm_sign_ext[19:12], BImm_sign_ext[4:1], BImm_sign_ext[11:11], instr_cast_op__6_, instr_cast_op__5_, instr_cast_op__4_, instr_cast_op__3_, instr_cast_op__2_, instr_cast_op__1_, instr_cast_op__0_ } : 
                 (N16)? wb[31:0] : 1'b0;
  assign alu_result = (N17)? md_result : 
                      (N174)? basic_comp_result : 1'b0;
  assign N17 = exe_decode__is_md_instr_;
  assign N176 = (N18)? 1'b1 : 
                (N19)? 1'b0 : 1'b0;
  assign N18 = n_cse_43;
  assign N19 = N395;
  assign rf_rs1_index0_fix = (N20)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                             (N21)? rf_rs1_val : 1'b0;
  assign N20 = N179;
  assign N21 = N413;
  assign rf_rs2_index0_fix = (N22)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                             (N23)? rf_rs2_val : 1'b0;
  assign N22 = N180;
  assign N23 = N417;
  assign rs1_to_exe = (N24)? wb[31:0] : 
                      (N25)? rf_rs1_index0_fix : 1'b0;
  assign N24 = id_wb_rs1_forward;
  assign N25 = N181;
  assign rs2_to_exe = (N26)? wb[31:0] : 
                      (N27)? rf_rs2_index0_fix : 1'b0;
  assign N26 = id_wb_rs2_forward;
  assign N27 = N182;
  assign { N191, N190 } = (N28)? { 1'b1, 1'b1 } : 
                          (N189)? { 1'b0, 1'b0 } : 1'b0;
  assign N28 = n_cse_62;
  assign N195 = (N29)? 1'b1 : 
                (N194)? 1'b0 : 1'b0;
  assign N29 = N193;
  assign N199 = (N30)? 1'b1 : 
                (N198)? 1'b0 : 1'b0;
  assign N30 = N196;
  assign loaded_data = (N31)? load_buffer_data : 
                       (N32)? from_mem_i[32:1] : 1'b0;
  assign N31 = is_load_buffer_valid;
  assign N32 = N200;
  assign loaded_byte = (N33)? loaded_data[7:0] : 
                       (N34)? loaded_data[15:8] : 
                       (N35)? loaded_data[23:16] : 
                       (N36)? loaded_data[31:24] : 1'b0;
  assign N33 = N203;
  assign N34 = N205;
  assign N35 = N207;
  assign N36 = N208;
  assign loaded_hex = (N37)? loaded_data[31:16] : 
                      (N210)? loaded_data[15:0] : 1'b0;
  assign N37 = N209;
  assign { N237, N236, N235, N234, N233, N232, N231, N230, N229, N228, N227, N226, N225, N224, N223, N222, N221, N220, N219, N218, N217, N216, N215, N214 } = (N38)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                                                                                                                                                              (N213)? { loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7], loaded_byte[7:7] } : 1'b0;
  assign N38 = mem_decode__is_load_unsigned_;
  assign { N253, N252, N251, N250, N249, N248, N247, N246, N245, N244, N243, N242, N241, N240, N239, N238 } = (N38)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 
                                                                                                              (N213)? { loaded_hex[15:15], loaded_hex[15:15], loaded_hex[15:15], loaded_hex[15:15], loaded_hex[15:15], loaded_hex[15:15], loaded_hex[15:15], loaded_hex[15:15], loaded_hex[15:15], loaded_hex[15:15], loaded_hex[15:15], loaded_hex[15:15], loaded_hex[15:15], loaded_hex[15:15], loaded_hex[15:15], loaded_hex[15:15] } : 1'b0;
  assign mem_loaded_data = (N39)? { N237, N236, N235, N234, N233, N232, N231, N230, N229, N228, N227, N226, N225, N224, N223, N222, N221, N220, N219, N218, N217, N216, N215, N214, loaded_byte } : 
                           (N255)? { N253, N252, N251, N250, N249, N248, N247, N246, N245, N244, N243, N242, N241, N240, N239, N238, loaded_hex } : 
                           (N212)? loaded_data : 1'b0;
  assign N39 = mem_decode__is_byte_op_;
  assign rf_data = (N40)? mem_loaded_data : 
                   (N256)? { mem_alu_result__31_, mem_alu_result__30_, mem_alu_result__29_, mem_alu_result__28_, mem_alu_result__27_, mem_alu_result__26_, mem_alu_result__25_, mem_alu_result__24_, mem_alu_result__23_, mem_alu_result__22_, mem_alu_result__21_, mem_alu_result__20_, mem_alu_result__19_, mem_alu_result__18_, mem_alu_result__17_, mem_alu_result__16_, mem_alu_result__15_, mem_alu_result__14_, mem_alu_result__13_, mem_alu_result__12_, mem_alu_result__11_, mem_alu_result__10_, mem_alu_result__9_, mem_alu_result__8_, mem_alu_result__7_, mem_alu_result__6_, mem_alu_result__5_, mem_alu_result__4_, mem_alu_result__3_, mem_alu_result__2_, mem_alu_result__1_, mem_alu_result__0_ } : 1'b0;
  assign N40 = mem_decode__is_load_op_;
  assign N260 = (N41)? 1'b1 : 
                (N259)? 1'b0 : 1'b0;
  assign N41 = N258;
  assign N42 = 1'b0;
  assign net_id_match_valid = N327 & net_packet_r_valid_;
  assign N327 = N325 & N326;
  assign N326 = ~net_packet_r_header__external_;
  assign exec_net_packet = N329 | N333;
  assign N329 = net_id_match_valid & N328;
  assign N328 = ~net_packet_r_header__bc_;
  assign N333 = N332 & N326;
  assign N332 = N331 & net_packet_r_valid_;
  assign N331 = N330 & net_packet_r_header__bc_;
  assign N330 = ~net_id_match_valid;
  assign net_pc_write_cmd = exec_net_packet & N320;
  assign net_imem_write_cmd = exec_net_packet & N314;
  assign net_reg_write_cmd = exec_net_packet & N317;
  assign net_pc_write_cmd_idle = net_pc_write_cmd & N319;
  assign data_mem_valid = is_load_buffer_valid | from_mem_i[33];
  assign stall_non_mem = N337 | stall_md;
  assign N337 = N336 | N298;
  assign N336 = N335 | net_reg_write_cmd;
  assign N335 = net_imem_write_cmd | N334;
  assign N334 = net_reg_write_cmd & wb[37];
  assign stall_fence = exe_decode__is_fence_op_ & outstanding_stores_i;
  assign stall_mem = N343 | stall_lrw;
  assign N343 = N342 | stall_fence;
  assign N342 = N339 | N341;
  assign N339 = exe_decode__is_mem_op_ & N338;
  assign N338 = ~from_mem_i[0];
  assign N341 = mem_decode__is_load_op_ & N340;
  assign N340 = ~data_mem_valid;
  assign stall = stall_non_mem | stall_mem;
  assign id_exe_rs1_match = id_decode__op_reads_rf1_ & N43;
  assign id_exe_rs2_match = id_decode__op_reads_rf2_ & N44;
  assign depend_stall = N345 & exe_decode__op_writes_rf_;
  assign N345 = N344 & exe_decode__is_load_op_;
  assign N344 = id_exe_rs1_match | id_exe_rs2_match;
  assign N45 = exe_decode__is_hex_op_ | exe_decode__is_byte_op_;
  assign N46 = ~N45;
  assign N83 = N121;
  assign N120 = ~exe_decode__is_byte_op_;
  assign N121 = exe_decode__is_hex_op_ & N120;
  assign N122 = id_decode__is_store_op_ | id_decode__op_is_load_reservation_;
  assign N123 = ~N122;
  assign N124 = ~id_decode__op_is_load_reservation_;
  assign N125 = id_decode__is_store_op_ & N124;
  assign branch_under_predict = N346 & jump_now;
  assign N346 = ~exe_instruction__op__0_;
  assign branch_over_predict = exe_instruction__op__0_ & N347;
  assign N347 = ~jump_now;
  assign branch_mispredict = exe_decode__is_branch_op_ & N348;
  assign N348 = branch_under_predict | branch_over_predict;
  assign jalr_mispredict = N360 & N126;
  assign N360 = ~N359;
  assign N359 = N357 | N358;
  assign N357 = N355 | N356;
  assign N355 = N353 | N354;
  assign N353 = N352 | exe_instruction__op__3_;
  assign N352 = N351 | exe_instruction__op__4_;
  assign N351 = N349 | N350;
  assign N349 = ~exe_instruction__op__6_;
  assign N350 = ~exe_instruction__op__5_;
  assign N354 = ~exe_instruction__op__2_;
  assign N356 = ~exe_instruction__op__1_;
  assign N358 = ~exe_instruction__op__0_;
  assign flush = branch_mispredict | jalr_mispredict;
  assign pc_wen = net_pc_write_cmd_idle | N362;
  assign N362 = ~N361;
  assign N361 = stall | depend_stall;
  assign N127 = ~decode_is_branch_op_;
  assign N128 = ~exe_decode__is_jump_op_;
  assign N129 = ~net_pc_write_cmd_idle;
  assign N130 = net_pc_write_cmd_idle;
  assign N131 = N363 | N311;
  assign N363 = decode_is_branch_op_ & instruction_op__0_;
  assign N132 = jalr_mispredict | branch_mispredict;
  assign N133 = N131 | N132;
  assign N134 = decode_is_jump_op_ | N133;
  assign N135 = ~N134;
  assign N136 = ~branch_under_predict;
  assign N157 = ~branch_mispredict;
  assign N158 = jalr_mispredict & N157;
  assign N159 = ~jalr_mispredict;
  assign N160 = N157 & N159;
  assign N161 = N131 & N160;
  assign N162 = ~N131;
  assign N163 = N160 & N162;
  assign N164 = decode_is_jump_op_ & N163;
  assign N165 = ~net_imem_write_cmd;
  assign N166 = net_imem_write_cmd;
  assign imem_cen = N365 | N366;
  assign N365 = ~N364;
  assign N364 = stall | depend_stall;
  assign N366 = net_imem_write_cmd | net_pc_write_cmd_idle;
  assign write_branch_instr = ~N374;
  assign N374 = N372 | N373;
  assign N372 = N371 | instr_cast_op__2_;
  assign N371 = N370 | instr_cast_op__3_;
  assign N370 = N369 | instr_cast_op__4_;
  assign N369 = N367 | N368;
  assign N367 = ~instr_cast_op__6_;
  assign N368 = ~instr_cast_op__5_;
  assign N373 = ~instr_cast_op__1_;
  assign write_jal_instr = ~N386;
  assign N386 = N384 | N385;
  assign N384 = N382 | N383;
  assign N382 = N380 | N381;
  assign N380 = N378 | N379;
  assign N378 = N377 | instr_cast_op__4_;
  assign N377 = N375 | N376;
  assign N375 = ~instr_cast_op__6_;
  assign N376 = ~instr_cast_op__5_;
  assign N379 = ~instr_cast_op__3_;
  assign N381 = ~instr_cast_op__2_;
  assign N383 = ~instr_cast_op__1_;
  assign N385 = ~instr_cast_op__0_;
  assign N167 = ~write_branch_instr;
  assign N168 = write_jal_instr | write_branch_instr;
  assign N169 = ~N168;
  assign N170 = ~write_branch_instr;
  assign N171 = write_jal_instr & N170;
  assign N172 = ~pc_wen_r;
  assign rf_wen = net_reg_write_cmd | N388;
  assign N388 = wb[37] & N387;
  assign N387 = ~stall;
  assign N173 = ~net_reg_write_cmd;
  assign rf_cen = ~N389;
  assign N389 = stall | depend_stall;
  assign md_valid = exe_decode__is_md_instr_ & md_ready;
  assign stall_md = exe_decode__is_md_instr_ & N390;
  assign N390 = ~md_resp_valid;
  assign n_3_net_ = ~stall_non_mem;
  assign rs1_is_forward = exe_rs1_in_mem_ | exe_rs1_in_wb_;
  assign rs2_is_forward = exe_rs2_in_mem_ | exe_rs2_in_wb_;
  assign N174 = ~exe_decode__is_md_instr_;
  assign to_mem_o[70] = N392 & N393;
  assign N392 = exe_decode__is_mem_op_ & N391;
  assign N391 = ~stall_non_mem;
  assign N393 = ~stall_lrw;
  assign to_mem_o[0] = mem_decode__is_mem_op_ & from_mem_i[33];
  assign stall_lrw = exe_decode__op_is_lr_acq_ & reservation_i;
  assign reserve_1_o = exe_decode__op_is_load_reservation_ & N394;
  assign N394 = ~exe_decode__op_is_lr_acq_;
  assign n_cse_43 = ~N395;
  assign N395 = stall | depend_stall;
  assign N175 = N396 | N397;
  assign N396 = reset | net_pc_write_cmd_idle;
  assign N397 = flush & n_cse_43;
  assign id_wb_rs1_forward = N399 & N403;
  assign N399 = N398 & wb[37];
  assign N398 = id_decode__op_reads_rf1_ & N177;
  assign N403 = N402 | id_instruction__rs1__0_;
  assign N402 = N401 | id_instruction__rs1__1_;
  assign N401 = N400 | id_instruction__rs1__2_;
  assign N400 = id_instruction__rs1__4_ | id_instruction__rs1__3_;
  assign id_wb_rs2_forward = N405 & N409;
  assign N405 = N404 & wb[37];
  assign N404 = id_decode__op_reads_rf2_ & N178;
  assign N409 = N408 | id_instruction__rs2__0_;
  assign N408 = N407 | id_instruction__rs2__1_;
  assign N407 = N406 | id_instruction__rs2__2_;
  assign N406 = id_instruction__rs2__4_ | id_instruction__rs2__3_;
  assign N179 = ~N413;
  assign N413 = N412 | id_instruction__rs1__0_;
  assign N412 = N411 | id_instruction__rs1__1_;
  assign N411 = N410 | id_instruction__rs1__2_;
  assign N410 = id_instruction__rs1__4_ | id_instruction__rs1__3_;
  assign N180 = ~N417;
  assign N417 = N416 | id_instruction__rs2__0_;
  assign N416 = N415 | id_instruction__rs2__1_;
  assign N415 = N414 | id_instruction__rs2__2_;
  assign N414 = id_instruction__rs2__4_ | id_instruction__rs2__3_;
  assign N181 = ~id_wb_rs1_forward;
  assign N182 = ~id_wb_rs2_forward;
  assign exe_rs1_in_mem = N418 & N422;
  assign N418 = exe_decode__op_writes_rf_ & N183;
  assign N422 = N421 | id_instruction__rs1__0_;
  assign N421 = N420 | id_instruction__rs1__1_;
  assign N420 = N419 | id_instruction__rs1__2_;
  assign N419 = id_instruction__rs1__4_ | id_instruction__rs1__3_;
  assign exe_rs1_in_wb = N423 & N427;
  assign N423 = mem_decode__op_writes_rf_ & N184;
  assign N427 = N426 | id_instruction__rs1__0_;
  assign N426 = N425 | id_instruction__rs1__1_;
  assign N425 = N424 | id_instruction__rs1__2_;
  assign N424 = id_instruction__rs1__4_ | id_instruction__rs1__3_;
  assign exe_rs2_in_mem = N428 & N432;
  assign N428 = exe_decode__op_writes_rf_ & N185;
  assign N432 = N431 | id_instruction__rs2__0_;
  assign N431 = N430 | id_instruction__rs2__1_;
  assign N430 = N429 | id_instruction__rs2__2_;
  assign N429 = id_instruction__rs2__4_ | id_instruction__rs2__3_;
  assign exe_rs2_in_wb = N433 & N437;
  assign N433 = mem_decode__op_writes_rf_ & N186;
  assign N437 = N436 | id_instruction__rs2__0_;
  assign N436 = N435 | id_instruction__rs2__1_;
  assign N435 = N434 | id_instruction__rs2__2_;
  assign N434 = id_instruction__rs2__4_ | id_instruction__rs2__3_;
  assign n_cse_62 = ~stall;
  assign N187 = N438 | N441;
  assign N438 = reset | net_pc_write_cmd_idle;
  assign N441 = flush & N440;
  assign N440 = ~N439;
  assign N439 = stall | depend_stall;
  assign N188 = depend_stall & n_cse_62;
  assign N189 = ~n_cse_62;
  assign N192 = reset | net_pc_write_cmd_idle;
  assign N193 = ~stall;
  assign N194 = ~N193;
  assign N196 = N442 & from_mem_i[33];
  assign N442 = stall & mem_decode__is_load_op_;
  assign N197 = ~stall;
  assign N198 = ~N196;
  assign N200 = ~is_load_buffer_valid;
  assign N201 = ~mem_mem_addr_send__1_;
  assign N202 = ~mem_mem_addr_send__0_;
  assign N205 = ~N204;
  assign N207 = ~N206;
  assign N209 = mem_mem_addr_send__1_ | mem_mem_addr_send__0_;
  assign N210 = ~N209;
  assign N211 = mem_decode__is_hex_op_ | mem_decode__is_byte_op_;
  assign N212 = ~N211;
  assign N213 = ~mem_decode__is_load_unsigned_;
  assign N254 = ~mem_decode__is_byte_op_;
  assign N255 = mem_decode__is_hex_op_ & N254;
  assign N256 = ~mem_decode__is_load_op_;
  assign N257 = reset | net_pc_write_cmd_idle;
  assign N258 = ~stall;
  assign N259 = ~N258;

endmodule



module bsg_manycore_pkt_encode_x_cord_width_p4_y_cord_width_p5_data_width_p32_addr_width_p20
(
  clk_i,
  v_i,
  addr_i,
  data_i,
  mask_i,
  we_i,
  my_x_i,
  my_y_i,
  v_o,
  data_o
);

  input [31:0] addr_i;
  input [31:0] data_i;
  input [3:0] mask_i;
  input [3:0] my_x_i;
  input [4:0] my_y_i;
  output [75:0] data_o;
  input clk_i;
  input v_i;
  input we_i;
  output v_o;
  wire [75:0] data_o;
  wire v_o,N0;
  assign data_o[75] = 1'b0;
  assign data_o[74] = addr_i[20];
  assign data_o[73] = addr_i[19];
  assign data_o[72] = addr_i[18];
  assign data_o[71] = addr_i[17];
  assign data_o[70] = addr_i[16];
  assign data_o[69] = addr_i[15];
  assign data_o[68] = addr_i[14];
  assign data_o[67] = addr_i[13];
  assign data_o[66] = addr_i[12];
  assign data_o[65] = addr_i[11];
  assign data_o[64] = addr_i[10];
  assign data_o[63] = addr_i[9];
  assign data_o[62] = addr_i[8];
  assign data_o[61] = addr_i[7];
  assign data_o[60] = addr_i[6];
  assign data_o[59] = addr_i[5];
  assign data_o[58] = addr_i[4];
  assign data_o[57] = addr_i[3];
  assign data_o[56] = addr_i[2];
  assign data_o[8] = addr_i[30];
  assign data_o[7] = addr_i[29];
  assign data_o[6] = addr_i[28];
  assign data_o[5] = addr_i[27];
  assign data_o[4] = addr_i[26];
  assign data_o[3] = addr_i[25];
  assign data_o[2] = addr_i[24];
  assign data_o[1] = addr_i[23];
  assign data_o[0] = addr_i[22];
  assign data_o[53] = mask_i[3];
  assign data_o[52] = mask_i[2];
  assign data_o[51] = mask_i[1];
  assign data_o[50] = mask_i[0];
  assign data_o[49] = data_i[31];
  assign data_o[48] = data_i[30];
  assign data_o[47] = data_i[29];
  assign data_o[46] = data_i[28];
  assign data_o[45] = data_i[27];
  assign data_o[44] = data_i[26];
  assign data_o[43] = data_i[25];
  assign data_o[42] = data_i[24];
  assign data_o[41] = data_i[23];
  assign data_o[40] = data_i[22];
  assign data_o[39] = data_i[21];
  assign data_o[38] = data_i[20];
  assign data_o[37] = data_i[19];
  assign data_o[36] = data_i[18];
  assign data_o[35] = data_i[17];
  assign data_o[34] = data_i[16];
  assign data_o[33] = data_i[15];
  assign data_o[32] = data_i[14];
  assign data_o[31] = data_i[13];
  assign data_o[30] = data_i[12];
  assign data_o[29] = data_i[11];
  assign data_o[28] = data_i[10];
  assign data_o[27] = data_i[9];
  assign data_o[26] = data_i[8];
  assign data_o[25] = data_i[7];
  assign data_o[24] = data_i[6];
  assign data_o[23] = data_i[5];
  assign data_o[22] = data_i[4];
  assign data_o[21] = data_i[3];
  assign data_o[20] = data_i[2];
  assign data_o[19] = data_i[1];
  assign data_o[18] = data_i[0];
  assign data_o[17] = my_y_i[4];
  assign data_o[16] = my_y_i[3];
  assign data_o[15] = my_y_i[2];
  assign data_o[14] = my_y_i[1];
  assign data_o[13] = my_y_i[0];
  assign data_o[12] = my_x_i[3];
  assign data_o[11] = my_x_i[2];
  assign data_o[10] = my_x_i[1];
  assign data_o[9] = my_x_i[0];
  assign data_o[54] = ~data_o[55];
  assign data_o[55] = addr_i[21];
  assign v_o = N0 & v_i;
  assign N0 = addr_i[31] & we_i;

endmodule



module bsg_transpose_width_p1_els_p2
(
  i,
  o
);

  input [1:0] i;
  output [1:0] o;
  wire [1:0] o;
  assign o[1] = i[1];
  assign o[0] = i[0];

endmodule



module bsg_scan_2_1_0
(
  i,
  o
);

  input [1:0] i;
  output [1:0] o;
  wire [1:0] o;
  assign o[1] = i[1] | 1'b0;
  assign o[0] = i[0] | i[1];

endmodule



module bsg_priority_encode_one_hot_out_2_0
(
  i,
  o
);

  input [1:0] i;
  output [1:0] o;
  wire [1:0] o;
  wire N0;
  wire [0:0] scan_lo;

  bsg_scan_2_1_0
  scan
  (
    .i(i),
    .o({ o[1:1], scan_lo[0:0] })
  );

  assign o[0] = scan_lo[0] & N0;
  assign N0 = ~o[1];

endmodule



module bsg_arb_fixed_2_0
(
  ready_i,
  reqs_i,
  grants_o
);

  input [1:0] reqs_i;
  output [1:0] grants_o;
  input ready_i;
  wire [1:0] grants_o,grants_unmasked_lo;

  bsg_priority_encode_one_hot_out_2_0
  enc
  (
    .i(reqs_i),
    .o(grants_unmasked_lo)
  );

  assign grants_o[1] = grants_unmasked_lo[1] & ready_i;
  assign grants_o[0] = grants_unmasked_lo[0] & ready_i;

endmodule



module bsg_scan_2_1_1
(
  i,
  o
);

  input [1:0] i;
  output [1:0] o;
  wire [1:0] o;
  assign o[0] = i[0] | 1'b0;
  assign o[1] = i[1] | i[0];

endmodule



module bsg_priority_encode_one_hot_out_2_1
(
  i,
  o
);

  input [1:0] i;
  output [1:0] o;
  wire [1:0] o;
  wire N0;
  wire [1:1] scan_lo;

  bsg_scan_2_1_1
  scan
  (
    .i(i),
    .o({ scan_lo[1:1], o[0:0] })
  );

  assign o[1] = scan_lo[1] & N0;
  assign N0 = ~o[0];

endmodule



module bsg_arb_fixed_2_1
(
  ready_i,
  reqs_i,
  grants_o
);

  input [1:0] reqs_i;
  output [1:0] grants_o;
  input ready_i;
  wire [1:0] grants_o,grants_unmasked_lo;

  bsg_priority_encode_one_hot_out_2_1
  enc
  (
    .i(reqs_i),
    .o(grants_unmasked_lo)
  );

  assign grants_o[1] = grants_unmasked_lo[1] & ready_i;
  assign grants_o[0] = grants_unmasked_lo[0] & ready_i;

endmodule



module bsg_transpose_width_p2_els_p1
(
  i,
  o
);

  input [1:0] i;
  output [1:0] o;
  wire [1:0] o;
  assign o[1] = i[1];
  assign o[0] = i[0];

endmodule



module bsg_crossbar_control_o_by_i_i_els_p2_o_els_p1_rr_lo_hi_p5
(
  clk_i,
  reset_i,
  reverse_pr_i,
  valid_i,
  sel_io_i,
  yumi_o,
  ready_i,
  valid_o,
  grants_oi_one_hot_o
);

  input [1:0] valid_i;
  input [1:0] sel_io_i;
  output [1:0] yumi_o;
  input [0:0] ready_i;
  output [0:0] valid_o;
  output [1:0] grants_oi_one_hot_o;
  input clk_i;
  input reset_i;
  input reverse_pr_i;
  wire [1:0] yumi_o,grants_oi_one_hot_o,sel_io_one_hot,sel_oi_one_hot,grants_io_one_hot;
  wire [0:0] valid_o;
  wire N0,N1,N2,N3,N4,N5,N6,N7,N8;
  wire [3:0] arb_0__dynamic_grants_oi_one_hot;

  bsg_transpose_width_p1_els_p2
  transpose0
  (
    .i(sel_io_one_hot),
    .o(sel_oi_one_hot)
  );


  bsg_arb_fixed_2_0
  arb_0__dynamic_fixed_arb_low
  (
    .ready_i(ready_i[0]),
    .reqs_i(sel_oi_one_hot),
    .grants_o(arb_0__dynamic_grants_oi_one_hot[1:0])
  );


  bsg_arb_fixed_2_1
  arb_0__dynamic_fixed_arb_high
  (
    .ready_i(ready_i[0]),
    .reqs_i(sel_oi_one_hot),
    .grants_o(arb_0__dynamic_grants_oi_one_hot[3:2])
  );


  bsg_transpose_width_p2_els_p1
  transpose1
  (
    .i(grants_oi_one_hot_o),
    .o(grants_io_one_hot)
  );

  assign sel_io_one_hot[0] = (N0)? N5 : 
                             (N4)? 1'b0 : 1'b0;
  assign N0 = valid_i[0];
  assign sel_io_one_hot[1] = (N1)? N7 : 
                             (N6)? 1'b0 : 1'b0;
  assign N1 = valid_i[1];
  assign grants_oi_one_hot_o = (N2)? arb_0__dynamic_grants_oi_one_hot[3:2] : 
                               (N3)? arb_0__dynamic_grants_oi_one_hot[1:0] : 1'b0;
  assign N2 = reverse_pr_i;
  assign N3 = N8;
  assign N4 = ~valid_i[0];
  assign N6 = ~valid_i[1];
  assign N8 = ~reverse_pr_i;
  assign valid_o[0] = grants_oi_one_hot_o[1] | grants_oi_one_hot_o[0];
  assign yumi_o[0] = valid_i[0] & grants_io_one_hot[0];
  assign yumi_o[1] = valid_i[1] & grants_io_one_hot[1];
  assign N7 = ~sel_io_i[1];
  assign N5 = ~sel_io_i[0];

endmodule



module bsg_mux_one_hot_width_p32_els_p2
(
  data_i,
  sel_one_hot_i,
  data_o
);

  input [63:0] data_i;
  input [1:0] sel_one_hot_i;
  output [31:0] data_o;
  wire [31:0] data_o;
  wire [63:0] data_masked;
  assign data_masked[31] = data_i[31] & sel_one_hot_i[0];
  assign data_masked[30] = data_i[30] & sel_one_hot_i[0];
  assign data_masked[29] = data_i[29] & sel_one_hot_i[0];
  assign data_masked[28] = data_i[28] & sel_one_hot_i[0];
  assign data_masked[27] = data_i[27] & sel_one_hot_i[0];
  assign data_masked[26] = data_i[26] & sel_one_hot_i[0];
  assign data_masked[25] = data_i[25] & sel_one_hot_i[0];
  assign data_masked[24] = data_i[24] & sel_one_hot_i[0];
  assign data_masked[23] = data_i[23] & sel_one_hot_i[0];
  assign data_masked[22] = data_i[22] & sel_one_hot_i[0];
  assign data_masked[21] = data_i[21] & sel_one_hot_i[0];
  assign data_masked[20] = data_i[20] & sel_one_hot_i[0];
  assign data_masked[19] = data_i[19] & sel_one_hot_i[0];
  assign data_masked[18] = data_i[18] & sel_one_hot_i[0];
  assign data_masked[17] = data_i[17] & sel_one_hot_i[0];
  assign data_masked[16] = data_i[16] & sel_one_hot_i[0];
  assign data_masked[15] = data_i[15] & sel_one_hot_i[0];
  assign data_masked[14] = data_i[14] & sel_one_hot_i[0];
  assign data_masked[13] = data_i[13] & sel_one_hot_i[0];
  assign data_masked[12] = data_i[12] & sel_one_hot_i[0];
  assign data_masked[11] = data_i[11] & sel_one_hot_i[0];
  assign data_masked[10] = data_i[10] & sel_one_hot_i[0];
  assign data_masked[9] = data_i[9] & sel_one_hot_i[0];
  assign data_masked[8] = data_i[8] & sel_one_hot_i[0];
  assign data_masked[7] = data_i[7] & sel_one_hot_i[0];
  assign data_masked[6] = data_i[6] & sel_one_hot_i[0];
  assign data_masked[5] = data_i[5] & sel_one_hot_i[0];
  assign data_masked[4] = data_i[4] & sel_one_hot_i[0];
  assign data_masked[3] = data_i[3] & sel_one_hot_i[0];
  assign data_masked[2] = data_i[2] & sel_one_hot_i[0];
  assign data_masked[1] = data_i[1] & sel_one_hot_i[0];
  assign data_masked[0] = data_i[0] & sel_one_hot_i[0];
  assign data_masked[63] = data_i[63] & sel_one_hot_i[1];
  assign data_masked[62] = data_i[62] & sel_one_hot_i[1];
  assign data_masked[61] = data_i[61] & sel_one_hot_i[1];
  assign data_masked[60] = data_i[60] & sel_one_hot_i[1];
  assign data_masked[59] = data_i[59] & sel_one_hot_i[1];
  assign data_masked[58] = data_i[58] & sel_one_hot_i[1];
  assign data_masked[57] = data_i[57] & sel_one_hot_i[1];
  assign data_masked[56] = data_i[56] & sel_one_hot_i[1];
  assign data_masked[55] = data_i[55] & sel_one_hot_i[1];
  assign data_masked[54] = data_i[54] & sel_one_hot_i[1];
  assign data_masked[53] = data_i[53] & sel_one_hot_i[1];
  assign data_masked[52] = data_i[52] & sel_one_hot_i[1];
  assign data_masked[51] = data_i[51] & sel_one_hot_i[1];
  assign data_masked[50] = data_i[50] & sel_one_hot_i[1];
  assign data_masked[49] = data_i[49] & sel_one_hot_i[1];
  assign data_masked[48] = data_i[48] & sel_one_hot_i[1];
  assign data_masked[47] = data_i[47] & sel_one_hot_i[1];
  assign data_masked[46] = data_i[46] & sel_one_hot_i[1];
  assign data_masked[45] = data_i[45] & sel_one_hot_i[1];
  assign data_masked[44] = data_i[44] & sel_one_hot_i[1];
  assign data_masked[43] = data_i[43] & sel_one_hot_i[1];
  assign data_masked[42] = data_i[42] & sel_one_hot_i[1];
  assign data_masked[41] = data_i[41] & sel_one_hot_i[1];
  assign data_masked[40] = data_i[40] & sel_one_hot_i[1];
  assign data_masked[39] = data_i[39] & sel_one_hot_i[1];
  assign data_masked[38] = data_i[38] & sel_one_hot_i[1];
  assign data_masked[37] = data_i[37] & sel_one_hot_i[1];
  assign data_masked[36] = data_i[36] & sel_one_hot_i[1];
  assign data_masked[35] = data_i[35] & sel_one_hot_i[1];
  assign data_masked[34] = data_i[34] & sel_one_hot_i[1];
  assign data_masked[33] = data_i[33] & sel_one_hot_i[1];
  assign data_masked[32] = data_i[32] & sel_one_hot_i[1];
  assign data_o[0] = data_masked[32] | data_masked[0];
  assign data_o[1] = data_masked[33] | data_masked[1];
  assign data_o[2] = data_masked[34] | data_masked[2];
  assign data_o[3] = data_masked[35] | data_masked[3];
  assign data_o[4] = data_masked[36] | data_masked[4];
  assign data_o[5] = data_masked[37] | data_masked[5];
  assign data_o[6] = data_masked[38] | data_masked[6];
  assign data_o[7] = data_masked[39] | data_masked[7];
  assign data_o[8] = data_masked[40] | data_masked[8];
  assign data_o[9] = data_masked[41] | data_masked[9];
  assign data_o[10] = data_masked[42] | data_masked[10];
  assign data_o[11] = data_masked[43] | data_masked[11];
  assign data_o[12] = data_masked[44] | data_masked[12];
  assign data_o[13] = data_masked[45] | data_masked[13];
  assign data_o[14] = data_masked[46] | data_masked[14];
  assign data_o[15] = data_masked[47] | data_masked[15];
  assign data_o[16] = data_masked[48] | data_masked[16];
  assign data_o[17] = data_masked[49] | data_masked[17];
  assign data_o[18] = data_masked[50] | data_masked[18];
  assign data_o[19] = data_masked[51] | data_masked[19];
  assign data_o[20] = data_masked[52] | data_masked[20];
  assign data_o[21] = data_masked[53] | data_masked[21];
  assign data_o[22] = data_masked[54] | data_masked[22];
  assign data_o[23] = data_masked[55] | data_masked[23];
  assign data_o[24] = data_masked[56] | data_masked[24];
  assign data_o[25] = data_masked[57] | data_masked[25];
  assign data_o[26] = data_masked[58] | data_masked[26];
  assign data_o[27] = data_masked[59] | data_masked[27];
  assign data_o[28] = data_masked[60] | data_masked[28];
  assign data_o[29] = data_masked[61] | data_masked[29];
  assign data_o[30] = data_masked[62] | data_masked[30];
  assign data_o[31] = data_masked[63] | data_masked[31];

endmodule



module bsg_crossbar_o_by_i_i_els_p2_o_els_p1_width_p32
(
  i,
  sel_oi_one_hot_i,
  o
);

  input [63:0] i;
  input [1:0] sel_oi_one_hot_i;
  output [31:0] o;
  wire [31:0] o;

  bsg_mux_one_hot_width_p32_els_p2
  genblk1_0__mux_one_hot
  (
    .data_i(i),
    .sel_one_hot_i(sel_oi_one_hot_i),
    .data_o(o)
  );


endmodule



module bsg_mux_one_hot_width_p10_els_p2
(
  data_i,
  sel_one_hot_i,
  data_o
);

  input [19:0] data_i;
  input [1:0] sel_one_hot_i;
  output [9:0] data_o;
  wire [9:0] data_o;
  wire [19:0] data_masked;
  assign data_masked[9] = data_i[9] & sel_one_hot_i[0];
  assign data_masked[8] = data_i[8] & sel_one_hot_i[0];
  assign data_masked[7] = data_i[7] & sel_one_hot_i[0];
  assign data_masked[6] = data_i[6] & sel_one_hot_i[0];
  assign data_masked[5] = data_i[5] & sel_one_hot_i[0];
  assign data_masked[4] = data_i[4] & sel_one_hot_i[0];
  assign data_masked[3] = data_i[3] & sel_one_hot_i[0];
  assign data_masked[2] = data_i[2] & sel_one_hot_i[0];
  assign data_masked[1] = data_i[1] & sel_one_hot_i[0];
  assign data_masked[0] = data_i[0] & sel_one_hot_i[0];
  assign data_masked[19] = data_i[19] & sel_one_hot_i[1];
  assign data_masked[18] = data_i[18] & sel_one_hot_i[1];
  assign data_masked[17] = data_i[17] & sel_one_hot_i[1];
  assign data_masked[16] = data_i[16] & sel_one_hot_i[1];
  assign data_masked[15] = data_i[15] & sel_one_hot_i[1];
  assign data_masked[14] = data_i[14] & sel_one_hot_i[1];
  assign data_masked[13] = data_i[13] & sel_one_hot_i[1];
  assign data_masked[12] = data_i[12] & sel_one_hot_i[1];
  assign data_masked[11] = data_i[11] & sel_one_hot_i[1];
  assign data_masked[10] = data_i[10] & sel_one_hot_i[1];
  assign data_o[0] = data_masked[10] | data_masked[0];
  assign data_o[1] = data_masked[11] | data_masked[1];
  assign data_o[2] = data_masked[12] | data_masked[2];
  assign data_o[3] = data_masked[13] | data_masked[3];
  assign data_o[4] = data_masked[14] | data_masked[4];
  assign data_o[5] = data_masked[15] | data_masked[5];
  assign data_o[6] = data_masked[16] | data_masked[6];
  assign data_o[7] = data_masked[17] | data_masked[7];
  assign data_o[8] = data_masked[18] | data_masked[8];
  assign data_o[9] = data_masked[19] | data_masked[9];

endmodule



module bsg_crossbar_o_by_i_i_els_p2_o_els_p1_width_p10
(
  i,
  sel_oi_one_hot_i,
  o
);

  input [19:0] i;
  input [1:0] sel_oi_one_hot_i;
  output [9:0] o;
  wire [9:0] o;

  bsg_mux_one_hot_width_p10_els_p2
  genblk1_0__mux_one_hot
  (
    .data_i(i),
    .sel_one_hot_i(sel_oi_one_hot_i),
    .data_o(o)
  );


endmodule



module bsg_mux_one_hot_width_p1_els_p2
(
  data_i,
  sel_one_hot_i,
  data_o
);

  input [1:0] data_i;
  input [1:0] sel_one_hot_i;
  output [0:0] data_o;
  wire [0:0] data_o;
  wire [1:0] data_masked;
  assign data_masked[0] = data_i[0] & sel_one_hot_i[0];
  assign data_masked[1] = data_i[1] & sel_one_hot_i[1];
  assign data_o[0] = data_masked[1] | data_masked[0];

endmodule



module bsg_crossbar_o_by_i_i_els_p2_o_els_p1_width_p1
(
  i,
  sel_oi_one_hot_i,
  o
);

  input [1:0] i;
  input [1:0] sel_oi_one_hot_i;
  output [0:0] o;
  wire [0:0] o;

  bsg_mux_one_hot_width_p1_els_p2
  genblk1_0__mux_one_hot
  (
    .data_i(i),
    .sel_one_hot_i(sel_oi_one_hot_i),
    .data_o(o[0])
  );


endmodule



module bsg_mux_one_hot_width_p4_els_p2
(
  data_i,
  sel_one_hot_i,
  data_o
);

  input [7:0] data_i;
  input [1:0] sel_one_hot_i;
  output [3:0] data_o;
  wire [3:0] data_o;
  wire [7:0] data_masked;
  assign data_masked[3] = data_i[3] & sel_one_hot_i[0];
  assign data_masked[2] = data_i[2] & sel_one_hot_i[0];
  assign data_masked[1] = data_i[1] & sel_one_hot_i[0];
  assign data_masked[0] = data_i[0] & sel_one_hot_i[0];
  assign data_masked[7] = data_i[7] & sel_one_hot_i[1];
  assign data_masked[6] = data_i[6] & sel_one_hot_i[1];
  assign data_masked[5] = data_i[5] & sel_one_hot_i[1];
  assign data_masked[4] = data_i[4] & sel_one_hot_i[1];
  assign data_o[0] = data_masked[4] | data_masked[0];
  assign data_o[1] = data_masked[5] | data_masked[1];
  assign data_o[2] = data_masked[6] | data_masked[2];
  assign data_o[3] = data_masked[7] | data_masked[3];

endmodule



module bsg_crossbar_o_by_i_i_els_p2_o_els_p1_width_p4
(
  i,
  sel_oi_one_hot_i,
  o
);

  input [7:0] i;
  input [1:0] sel_oi_one_hot_i;
  output [3:0] o;
  wire [3:0] o;

  bsg_mux_one_hot_width_p4_els_p2
  genblk1_0__mux_one_hot
  (
    .data_i(i),
    .sel_one_hot_i(sel_oi_one_hot_i),
    .data_o(o)
  );


endmodule



module bsg_mem_1rw_sync_mask_write_byte_els_p1024_data_width_p32
(
  clk_i,
  reset_i,
  v_i,
  w_i,
  addr_i,
  data_i,
  write_mask_i,
  data_o
);

  input [9:0] addr_i;
  input [31:0] data_i;
  input [3:0] write_mask_i;
  output [31:0] data_o;
  input clk_i;
  input reset_i;
  input v_i;
  input w_i;
  wire [31:0] data_o,macro_wen;
  wire n_0_net_,n_1_net_;

  tsmc65lp_1rf_lg10_w32_byte
  macro_mem
  (
    .CLK(clk_i),
    .Q(data_o),
    .CEN(n_0_net_),
    .WEN(macro_wen),
    .GWEN(n_1_net_),
    .A(addr_i),
    .D(data_i),
    .EMA({ 1'b0, 1'b1, 1'b1 }),
    .EMAW({ 1'b0, 1'b1 }),
    .RET1N(1'b1)
  );

  assign macro_wen[31] = ~write_mask_i[3];
  assign macro_wen[30] = ~write_mask_i[3];
  assign macro_wen[29] = ~write_mask_i[3];
  assign macro_wen[28] = ~write_mask_i[3];
  assign macro_wen[27] = ~write_mask_i[3];
  assign macro_wen[26] = ~write_mask_i[3];
  assign macro_wen[25] = ~write_mask_i[3];
  assign macro_wen[24] = ~write_mask_i[3];
  assign macro_wen[23] = ~write_mask_i[2];
  assign macro_wen[22] = ~write_mask_i[2];
  assign macro_wen[21] = ~write_mask_i[2];
  assign macro_wen[20] = ~write_mask_i[2];
  assign macro_wen[19] = ~write_mask_i[2];
  assign macro_wen[18] = ~write_mask_i[2];
  assign macro_wen[17] = ~write_mask_i[2];
  assign macro_wen[16] = ~write_mask_i[2];
  assign macro_wen[15] = ~write_mask_i[1];
  assign macro_wen[14] = ~write_mask_i[1];
  assign macro_wen[13] = ~write_mask_i[1];
  assign macro_wen[12] = ~write_mask_i[1];
  assign macro_wen[11] = ~write_mask_i[1];
  assign macro_wen[10] = ~write_mask_i[1];
  assign macro_wen[9] = ~write_mask_i[1];
  assign macro_wen[8] = ~write_mask_i[1];
  assign macro_wen[7] = ~write_mask_i[0];
  assign macro_wen[6] = ~write_mask_i[0];
  assign macro_wen[5] = ~write_mask_i[0];
  assign macro_wen[4] = ~write_mask_i[0];
  assign macro_wen[3] = ~write_mask_i[0];
  assign macro_wen[2] = ~write_mask_i[0];
  assign macro_wen[1] = ~write_mask_i[0];
  assign macro_wen[0] = ~write_mask_i[0];
  assign n_1_net_ = ~w_i;
  assign n_0_net_ = ~v_i;

endmodule



module bsg_mux_one_hot_width_p32_els_p1
(
  data_i,
  sel_one_hot_i,
  data_o
);

  input [31:0] data_i;
  input [0:0] sel_one_hot_i;
  output [31:0] data_o;
  wire [31:0] data_o;
  assign data_o[31] = data_i[31] & sel_one_hot_i[0];
  assign data_o[30] = data_i[30] & sel_one_hot_i[0];
  assign data_o[29] = data_i[29] & sel_one_hot_i[0];
  assign data_o[28] = data_i[28] & sel_one_hot_i[0];
  assign data_o[27] = data_i[27] & sel_one_hot_i[0];
  assign data_o[26] = data_i[26] & sel_one_hot_i[0];
  assign data_o[25] = data_i[25] & sel_one_hot_i[0];
  assign data_o[24] = data_i[24] & sel_one_hot_i[0];
  assign data_o[23] = data_i[23] & sel_one_hot_i[0];
  assign data_o[22] = data_i[22] & sel_one_hot_i[0];
  assign data_o[21] = data_i[21] & sel_one_hot_i[0];
  assign data_o[20] = data_i[20] & sel_one_hot_i[0];
  assign data_o[19] = data_i[19] & sel_one_hot_i[0];
  assign data_o[18] = data_i[18] & sel_one_hot_i[0];
  assign data_o[17] = data_i[17] & sel_one_hot_i[0];
  assign data_o[16] = data_i[16] & sel_one_hot_i[0];
  assign data_o[15] = data_i[15] & sel_one_hot_i[0];
  assign data_o[14] = data_i[14] & sel_one_hot_i[0];
  assign data_o[13] = data_i[13] & sel_one_hot_i[0];
  assign data_o[12] = data_i[12] & sel_one_hot_i[0];
  assign data_o[11] = data_i[11] & sel_one_hot_i[0];
  assign data_o[10] = data_i[10] & sel_one_hot_i[0];
  assign data_o[9] = data_i[9] & sel_one_hot_i[0];
  assign data_o[8] = data_i[8] & sel_one_hot_i[0];
  assign data_o[7] = data_i[7] & sel_one_hot_i[0];
  assign data_o[6] = data_i[6] & sel_one_hot_i[0];
  assign data_o[5] = data_i[5] & sel_one_hot_i[0];
  assign data_o[4] = data_i[4] & sel_one_hot_i[0];
  assign data_o[3] = data_i[3] & sel_one_hot_i[0];
  assign data_o[2] = data_i[2] & sel_one_hot_i[0];
  assign data_o[1] = data_i[1] & sel_one_hot_i[0];
  assign data_o[0] = data_i[0] & sel_one_hot_i[0];

endmodule



module bsg_crossbar_o_by_i_i_els_p1_o_els_p2_width_p32
(
  i,
  sel_oi_one_hot_i,
  o
);

  input [31:0] i;
  input [1:0] sel_oi_one_hot_i;
  output [63:0] o;
  wire [63:0] o;

  bsg_mux_one_hot_width_p32_els_p1
  genblk1_0__mux_one_hot
  (
    .data_i(i),
    .sel_one_hot_i(sel_oi_one_hot_i[0]),
    .data_o(o[31:0])
  );


  bsg_mux_one_hot_width_p32_els_p1
  genblk1_1__mux_one_hot
  (
    .data_i(i),
    .sel_one_hot_i(sel_oi_one_hot_i[1]),
    .data_o(o[63:32])
  );


endmodule



module bsg_mux_one_hot_width_p1_els_p1
(
  data_i,
  sel_one_hot_i,
  data_o
);

  input [0:0] data_i;
  input [0:0] sel_one_hot_i;
  output [0:0] data_o;
  wire [0:0] data_o;
  assign data_o[0] = data_i[0] & sel_one_hot_i[0];

endmodule



module bsg_crossbar_o_by_i_i_els_p1_o_els_p2_width_p1
(
  i,
  sel_oi_one_hot_i,
  o
);

  input [0:0] i;
  input [1:0] sel_oi_one_hot_i;
  output [1:0] o;
  wire [1:0] o;

  bsg_mux_one_hot_width_p1_els_p1
  genblk1_0__mux_one_hot
  (
    .data_i(i[0]),
    .sel_one_hot_i(sel_oi_one_hot_i[0]),
    .data_o(o[0])
  );


  bsg_mux_one_hot_width_p1_els_p1
  genblk1_1__mux_one_hot
  (
    .data_i(i[0]),
    .sel_one_hot_i(sel_oi_one_hot_i[1]),
    .data_o(o[1])
  );


endmodule



module bsg_mem_banked_crossbar_num_ports_p2_num_banks_p1_bank_size_p1024_rr_lo_hi_p5_data_width_p32
(
  clk_i,
  reset_i,
  reverse_pr_i,
  v_i,
  w_i,
  addr_i,
  data_i,
  mask_i,
  yumi_o,
  v_o,
  data_o
);

  input [1:0] v_i;
  input [1:0] w_i;
  input [19:0] addr_i;
  input [63:0] data_i;
  input [7:0] mask_i;
  output [1:0] yumi_o;
  output [1:0] v_o;
  output [63:0] data_o;
  input clk_i;
  input reset_i;
  input reverse_pr_i;
  wire [1:0] yumi_o,v_o,bank_port_grants_one_hot,port_bank_grants_one_hot;
  wire [63:0] data_o;
  wire n_1_net__0_,N0;
  wire [0:0] bank_v,bank_w;
  wire [31:0] bank_data,bank_data_out;
  wire [9:0] bank_addr;
  wire [3:0] bank_mask;
  reg [1:0] bank_port_grants_one_hot_r;
  reg [0:0] bank_w_r,bank_v_r;

  bsg_crossbar_control_o_by_i_i_els_p2_o_els_p1_rr_lo_hi_p5
  crossbar_control
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .reverse_pr_i(reverse_pr_i),
    .valid_i(v_i),
    .sel_io_i({ 1'b0, 1'b0 }),
    .yumi_o(yumi_o),
    .ready_i(1'b1),
    .valid_o(bank_v[0]),
    .grants_oi_one_hot_o(bank_port_grants_one_hot)
  );


  bsg_crossbar_o_by_i_i_els_p2_o_els_p1_width_p32
  port_bank_data_crossbar
  (
    .i(data_i),
    .sel_oi_one_hot_i(bank_port_grants_one_hot),
    .o(bank_data)
  );


  bsg_crossbar_o_by_i_i_els_p2_o_els_p1_width_p10
  port_bank_addr_crossbar
  (
    .i(addr_i),
    .sel_oi_one_hot_i(bank_port_grants_one_hot),
    .o(bank_addr)
  );


  bsg_crossbar_o_by_i_i_els_p2_o_els_p1_width_p1
  port_bank_w_crossbar
  (
    .i(w_i),
    .sel_oi_one_hot_i(bank_port_grants_one_hot),
    .o(bank_w[0])
  );


  bsg_crossbar_o_by_i_i_els_p2_o_els_p1_width_p4
  port_bank_mask_crossbar
  (
    .i(mask_i),
    .sel_oi_one_hot_i(bank_port_grants_one_hot),
    .o(bank_mask)
  );


  bsg_mem_1rw_sync_mask_write_byte_els_p1024_data_width_p32
  z_0__m1rw_mask
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .v_i(bank_v[0]),
    .w_i(bank_w[0]),
    .addr_i(bank_addr),
    .data_i(bank_data),
    .write_mask_i(bank_mask),
    .data_o(bank_data_out)
  );


  always @(posedge clk_i) begin
    if(1'b1) begin
      bank_port_grants_one_hot_r[1] <= bank_port_grants_one_hot[1];
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      bank_port_grants_one_hot_r[0] <= bank_port_grants_one_hot[0];
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      bank_w_r[0] <= bank_w[0];
    end 
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      bank_v_r[0] <= bank_v[0];
    end 
  end


  bsg_transpose_width_p2_els_p1
  grants_transpose
  (
    .i(bank_port_grants_one_hot_r),
    .o(port_bank_grants_one_hot)
  );


  bsg_crossbar_o_by_i_i_els_p1_o_els_p2_width_p32
  bank_port_data_crossbar
  (
    .i(bank_data_out),
    .sel_oi_one_hot_i(port_bank_grants_one_hot),
    .o(data_o)
  );


  bsg_crossbar_o_by_i_i_els_p1_o_els_p2_width_p1
  bank_port_v_crossbar
  (
    .i(n_1_net__0_),
    .sel_oi_one_hot_i(port_bank_grants_one_hot),
    .o(v_o)
  );

  assign n_1_net__0_ = bank_v_r[0] & N0;
  assign N0 = ~bank_w_r[0];

endmodule



module bsg_manycore_proc_vanilla_x_cord_width_p4_y_cord_width_p5_data_width_p32_addr_width_p20_debug_p0_bank_size_p1024_num_banks_p1_imem_size_p1024_max_out_credits_p200_hetero_type_p0
(
  clk_i,
  reset_i,
  link_sif_i,
  link_sif_o,
  my_x_i,
  my_y_i,
  freeze_o
);

  input [88:0] link_sif_i;
  output [88:0] link_sif_o;
  input [3:0] my_x_i;
  input [4:0] my_y_i;
  input clk_i;
  input reset_i;
  output freeze_o;
  wire [88:0] link_sif_o;
  wire freeze_o,N0,N1,N2,N3,N4,N5,N6,in_v_lo,in_yumi_li,out_v_li,out_ready_lo,
  reverse_arb_pr,core_mem_reserve_1,N7,N8,N9,N10,N11,N12,N13,N14,launching_out,
  non_imem_bits_set,remote_store_imem_not_dmem,N15,N16,N17,pkt_unfreeze,pkt_freeze,n_0_net_,
  core_net_pkt_valid_,core_net_pkt_header__net_op__1_,core_net_pkt_header__mask__3_,
  core_net_pkt_header__mask__2_,core_net_pkt_header__mask__1_,
  core_net_pkt_header__mask__0_,core_net_pkt_header__addr__13_,core_net_pkt_header__addr__12_,
  core_net_pkt_header__addr__11_,core_net_pkt_header__addr__10_,
  core_net_pkt_header__addr__9_,core_net_pkt_header__addr__8_,core_net_pkt_header__addr__7_,
  core_net_pkt_header__addr__6_,core_net_pkt_header__addr__5_,core_net_pkt_header__addr__4_,
  core_net_pkt_header__addr__3_,core_net_pkt_header__addr__2_,core_net_pkt_data__31_,
  core_net_pkt_data__30_,core_net_pkt_data__29_,core_net_pkt_data__28_,
  core_net_pkt_data__27_,core_net_pkt_data__26_,core_net_pkt_data__25_,core_net_pkt_data__24_,
  core_net_pkt_data__23_,core_net_pkt_data__22_,core_net_pkt_data__21_,
  core_net_pkt_data__20_,core_net_pkt_data__19_,core_net_pkt_data__18_,core_net_pkt_data__17_,
  core_net_pkt_data__16_,core_net_pkt_data__15_,core_net_pkt_data__14_,
  core_net_pkt_data__13_,core_net_pkt_data__12_,core_net_pkt_data__11_,core_net_pkt_data__10_,
  core_net_pkt_data__9_,core_net_pkt_data__8_,core_net_pkt_data__7_,
  core_net_pkt_data__6_,core_net_pkt_data__5_,core_net_pkt_data__4_,core_net_pkt_data__3_,
  core_net_pkt_data__2_,core_net_pkt_data__1_,core_net_pkt_data__0_,N18,out_request,
  unused_valid,N19,N20,N21,N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32,N33,N34,N35,
  N36,N37,N38,N39,N40,N41,N42,N43,N44,N45,N46,N47,N48,N49;
  wire [31:0] in_data_lo,unused_data;
  wire [3:0] in_mask_lo;
  wire [19:0] in_addr_lo;
  wire [75:0] out_packet_li;
  wire [7:0] out_credits_lo;
  wire [33:0] mem_to_core;
  wire [70:0] core_to_mem;
  wire [1:0] xbar_port_v_in,xbar_port_yumi_out;
  reg [19:0] core_mem_reserve_addr_r;
  reg core_mem_reservation_r,freeze_r_r;

  bsg_manycore_endpoint_standard_x_cord_width_p4_y_cord_width_p5_fifo_els_p4_data_width_p32_addr_width_p20_max_out_credits_p200_debug_p0
  endp
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .link_sif_i(link_sif_i),
    .link_sif_o(link_sif_o),
    .in_v_o(in_v_lo),
    .in_yumi_i(in_yumi_li),
    .in_data_o(in_data_lo),
    .in_mask_o(in_mask_lo),
    .in_addr_o(in_addr_lo),
    .out_v_i(out_v_li),
    .out_packet_i(out_packet_li),
    .out_ready_o(out_ready_lo),
    .out_credits_o(out_credits_lo),
    .my_x_i(my_x_i),
    .my_y_i(my_y_i),
    .freeze_r_o(freeze_o),
    .reverse_arb_pr_o(reverse_arb_pr)
  );

  assign N8 = core_mem_reserve_addr_r == in_addr_lo;

  always @(posedge clk_i) begin
    if(N7) begin
      core_mem_reserve_addr_r[19] <= 1'b0;
    end else begin
      core_mem_reserve_addr_r[19] <= 1'b0;
    end
  end


  always @(posedge clk_i) begin
    if(N7) begin
      core_mem_reserve_addr_r[18] <= 1'b0;
    end else begin
      core_mem_reserve_addr_r[18] <= 1'b0;
    end
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[17] <= core_to_mem[52];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[16] <= core_to_mem[51];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[15] <= core_to_mem[50];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[14] <= core_to_mem[49];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[13] <= core_to_mem[48];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[12] <= core_to_mem[47];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[11] <= core_to_mem[46];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[10] <= core_to_mem[45];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[9] <= core_to_mem[44];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[8] <= core_to_mem[43];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[7] <= core_to_mem[42];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[6] <= core_to_mem[41];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[5] <= core_to_mem[40];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[4] <= core_to_mem[39];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[3] <= core_to_mem[38];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[2] <= core_to_mem[37];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[1] <= core_to_mem[36];
    end 
  end


  always @(posedge clk_i) begin
    if(N12) begin
      core_mem_reserve_addr_r[0] <= core_to_mem[35];
    end 
  end


  always @(posedge clk_i) begin
    if(N9) begin
      core_mem_reservation_r <= 1'b0;
    end else if(N7) begin
      core_mem_reservation_r <= 1'b1;
    end else begin
      core_mem_reservation_r <= N6;
    end
  end


  always @(posedge clk_i) begin
    if(1'b1) begin
      freeze_r_r <= N17;
    end 
  end


  hobbit_imem_addr_width_p10_gw_ID_p0_ring_ID_p0_x_cord_width_p4_y_cord_width_p5
  vanilla_core
  (
    .clk(clk_i),
    .reset(n_0_net_),
    .net_packet_i({ core_net_pkt_valid_, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, core_net_pkt_header__net_op__1_, 1'b1, core_net_pkt_header__mask__3_, core_net_pkt_header__mask__2_, core_net_pkt_header__mask__1_, core_net_pkt_header__mask__0_, 1'b0, 1'b0, core_net_pkt_header__addr__13_, core_net_pkt_header__addr__12_, core_net_pkt_header__addr__11_, core_net_pkt_header__addr__10_, core_net_pkt_header__addr__9_, core_net_pkt_header__addr__8_, core_net_pkt_header__addr__7_, core_net_pkt_header__addr__6_, core_net_pkt_header__addr__5_, core_net_pkt_header__addr__4_, core_net_pkt_header__addr__3_, core_net_pkt_header__addr__2_, 1'b0, 1'b0, core_net_pkt_data__31_, core_net_pkt_data__30_, core_net_pkt_data__29_, core_net_pkt_data__28_, core_net_pkt_data__27_, core_net_pkt_data__26_, core_net_pkt_data__25_, core_net_pkt_data__24_, core_net_pkt_data__23_, core_net_pkt_data__22_, core_net_pkt_data__21_, core_net_pkt_data__20_, core_net_pkt_data__19_, core_net_pkt_data__18_, core_net_pkt_data__17_, core_net_pkt_data__16_, core_net_pkt_data__15_, core_net_pkt_data__14_, core_net_pkt_data__13_, core_net_pkt_data__12_, core_net_pkt_data__11_, core_net_pkt_data__10_, core_net_pkt_data__9_, core_net_pkt_data__8_, core_net_pkt_data__7_, core_net_pkt_data__6_, core_net_pkt_data__5_, core_net_pkt_data__4_, core_net_pkt_data__3_, core_net_pkt_data__2_, core_net_pkt_data__1_, core_net_pkt_data__0_ }),
    .from_mem_i(mem_to_core),
    .to_mem_o(core_to_mem),
    .reservation_i(core_mem_reservation_r),
    .reserve_1_o(core_mem_reserve_1),
    .my_x_i(my_x_i),
    .my_y_i(my_y_i),
    .outstanding_stores_i(N28)
  );


  bsg_manycore_pkt_encode_x_cord_width_p4_y_cord_width_p5_data_width_p32_addr_width_p20
  pkt_encode
  (
    .clk_i(clk_i),
    .v_i(core_to_mem[70]),
    .addr_i(core_to_mem[64:33]),
    .data_i(core_to_mem[32:1]),
    .mask_i(core_to_mem[68:65]),
    .we_i(core_to_mem[69]),
    .my_x_i(my_x_i),
    .my_y_i(my_y_i),
    .v_o(out_request),
    .data_o(out_packet_li)
  );


  bsg_mem_banked_crossbar_num_ports_p2_num_banks_p1_bank_size_p1024_rr_lo_hi_p5_data_width_p32
  bnkd_xbar
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .reverse_pr_i(reverse_arb_pr),
    .v_i(xbar_port_v_in),
    .w_i({ core_to_mem[69:69], 1'b1 }),
    .addr_i({ core_to_mem[44:35], in_addr_lo[9:0] }),
    .data_i({ core_to_mem[32:1], in_data_lo }),
    .mask_i({ core_to_mem[68:65], in_mask_lo }),
    .yumi_o(xbar_port_yumi_out),
    .v_o({ mem_to_core[33:33], unused_valid }),
    .data_o({ mem_to_core[32:1], unused_data })
  );

  assign N19 = ~out_credits_lo[7];
  assign N20 = ~out_credits_lo[6];
  assign N21 = ~out_credits_lo[3];
  assign N22 = N20 | N19;
  assign N23 = out_credits_lo[5] | N22;
  assign N24 = out_credits_lo[4] | N23;
  assign N25 = N21 | N24;
  assign N26 = out_credits_lo[2] | N25;
  assign N27 = out_credits_lo[1] | N26;
  assign N28 = out_credits_lo[0] | N27;
  assign N29 = ~freeze_r_r;
  assign N30 = ~freeze_o;
  assign N12 = (N0)? 1'b1 : 
               (N14)? 1'b0 : 
               (N11)? 1'b0 : 1'b0;
  assign N0 = N7;
  assign N17 = (N1)? 1'b0 : 
               (N2)? freeze_o : 1'b0;
  assign N1 = N16;
  assign N2 = N15;
  assign { core_net_pkt_header__mask__3_, core_net_pkt_header__mask__2_, core_net_pkt_header__mask__1_, core_net_pkt_header__mask__0_, core_net_pkt_header__addr__13_, core_net_pkt_header__addr__12_, core_net_pkt_header__addr__11_, core_net_pkt_header__addr__10_, core_net_pkt_header__addr__9_, core_net_pkt_header__addr__8_, core_net_pkt_header__addr__7_, core_net_pkt_header__addr__6_, core_net_pkt_header__addr__5_, core_net_pkt_header__addr__4_, core_net_pkt_header__addr__3_, core_net_pkt_header__addr__2_ } = (N3)? { in_mask_lo, in_addr_lo[11:0] } : 
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  (N4)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 1'b0;
  assign N3 = remote_store_imem_not_dmem;
  assign N4 = core_net_pkt_header__net_op__1_;
  assign { core_net_pkt_data__31_, core_net_pkt_data__30_, core_net_pkt_data__29_, core_net_pkt_data__28_, core_net_pkt_data__27_, core_net_pkt_data__26_, core_net_pkt_data__25_, core_net_pkt_data__24_, core_net_pkt_data__23_, core_net_pkt_data__22_, core_net_pkt_data__21_, core_net_pkt_data__20_, core_net_pkt_data__19_, core_net_pkt_data__18_, core_net_pkt_data__17_, core_net_pkt_data__16_, core_net_pkt_data__15_, core_net_pkt_data__14_, core_net_pkt_data__13_, core_net_pkt_data__12_, core_net_pkt_data__11_, core_net_pkt_data__10_, core_net_pkt_data__9_, core_net_pkt_data__8_, core_net_pkt_data__7_, core_net_pkt_data__6_, core_net_pkt_data__5_, core_net_pkt_data__4_, core_net_pkt_data__3_, core_net_pkt_data__2_, core_net_pkt_data__1_, core_net_pkt_data__0_ } = (N3)? in_data_lo : 
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    (N5)? { 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0 } : 1'b0;
  assign N5 = N18;
  assign N6 = 1'b0;
  assign N7 = N31 & xbar_port_yumi_out[1];
  assign N31 = core_to_mem[70] & core_mem_reserve_1;
  assign N9 = N32 & in_yumi_li;
  assign N32 = in_v_lo & N8;
  assign N10 = N9 | N7;
  assign N11 = ~N10;
  assign N13 = ~N7;
  assign N14 = N9 & N13;
  assign launching_out = out_v_li & out_ready_lo;
  assign non_imem_bits_set = N40 | in_addr_lo[10];
  assign N40 = N39 | in_addr_lo[11];
  assign N39 = N38 | in_addr_lo[12];
  assign N38 = N37 | in_addr_lo[13];
  assign N37 = N36 | in_addr_lo[14];
  assign N36 = N35 | in_addr_lo[15];
  assign N35 = N34 | in_addr_lo[16];
  assign N34 = N33 | in_addr_lo[17];
  assign N33 = in_addr_lo[19] | in_addr_lo[18];
  assign remote_store_imem_not_dmem = in_v_lo & N41;
  assign N41 = ~non_imem_bits_set;
  assign xbar_port_v_in[0] = in_v_lo & non_imem_bits_set;
  assign N15 = ~reset_i;
  assign N16 = reset_i;
  assign pkt_unfreeze = N30 & freeze_r_r;
  assign pkt_freeze = freeze_o & N29;
  assign n_0_net_ = reset_i | pkt_freeze;
  assign core_net_pkt_valid_ = remote_store_imem_not_dmem | pkt_unfreeze;
  assign N18 = ~remote_store_imem_not_dmem;
  assign core_net_pkt_header__net_op__1_ = N18;
  assign out_v_li = out_request & N48;
  assign N48 = N47 | out_credits_lo[0];
  assign N47 = N46 | out_credits_lo[1];
  assign N46 = N45 | out_credits_lo[2];
  assign N45 = N44 | out_credits_lo[3];
  assign N44 = N43 | out_credits_lo[4];
  assign N43 = N42 | out_credits_lo[5];
  assign N42 = out_credits_lo[7] | out_credits_lo[6];
  assign xbar_port_v_in[1] = core_to_mem[70] & N49;
  assign N49 = ~core_to_mem[64];
  assign in_yumi_li = xbar_port_yumi_out[0] | remote_store_imem_not_dmem;
  assign mem_to_core[0] = xbar_port_yumi_out[1] | launching_out;

endmodule



module bsg_manycore_hetero_socket_x_cord_width_p4_y_cord_width_p5_data_width_p32_addr_width_p20_debug_p0_bank_size_p1024_imem_size_p1024_num_banks_p1_hetero_type_p0
(
  clk_i,
  reset_i,
  link_sif_i,
  link_sif_o,
  my_x_i,
  my_y_i,
  freeze_o
);

  input [88:0] link_sif_i;
  output [88:0] link_sif_o;
  input [3:0] my_x_i;
  input [4:0] my_y_i;
  input clk_i;
  input reset_i;
  output freeze_o;
  wire [88:0] link_sif_o;
  wire freeze_o;

  bsg_manycore_proc_vanilla_x_cord_width_p4_y_cord_width_p5_data_width_p32_addr_width_p20_debug_p0_bank_size_p1024_num_banks_p1_imem_size_p1024_max_out_credits_p200_hetero_type_p0
  h_z
  (
    .clk_i(clk_i),
    .reset_i(reset_i),
    .link_sif_i(link_sif_i),
    .link_sif_o(link_sif_o),
    .my_x_i(my_x_i),
    .my_y_i(my_y_i),
    .freeze_o(freeze_o)
  );


endmodule



module bsg_manycore_tile
(
  clk_i,
  reset_i,
  link_in,
  link_out,
  my_x_i,
  my_y_i
);

  input [355:0] link_in;
  output [355:0] link_out;
  input [3:0] my_x_i;
  input [4:0] my_y_i;
  input clk_i;
  input reset_i;
  wire [355:0] link_out;
  wire [88:0] proc_link_sif_li,proc_link_sif_lo;
  reg reset_r;

  always @(posedge clk_i) begin
    if(1'b1) begin
      reset_r <= reset_i;
    end 
  end


  bsg_manycore_mesh_node_4_5_32_20_0_0_0
  rtr
  (
    .clk_i(clk_i),
    .reset_i(reset_r),
    .links_sif_i(link_in),
    .links_sif_o(link_out),
    .proc_link_sif_i(proc_link_sif_li),
    .proc_link_sif_o(proc_link_sif_lo),
    .my_x_i(my_x_i),
    .my_y_i(my_y_i)
  );


  bsg_manycore_hetero_socket_x_cord_width_p4_y_cord_width_p5_data_width_p32_addr_width_p20_debug_p0_bank_size_p1024_imem_size_p1024_num_banks_p1_hetero_type_p0
  proc
  (
    .clk_i(clk_i),
    .reset_i(reset_r),
    .link_sif_i(proc_link_sif_lo),
    .link_sif_o(proc_link_sif_li),
    .my_x_i(my_x_i),
    .my_y_i(my_y_i)
  );


endmodule

