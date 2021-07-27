module coyote_tc (
  clk_i,
  reset_i,
  rocc_cmd_v_o,
  rocc_cmd_data_o_0,
  rocc_cmd_data_o_1,
  rocc_cmd_data_o_2,
  rocc_cmd_data_o_3,
  rocc_cmd_data_o_4,
  rocc_cmd_data_o_5,
  rocc_cmd_data_o_6,
  rocc_cmd_data_o_7,
  rocc_cmd_data_o_8,
  rocc_cmd_data_o_9,
  rocc_cmd_data_o_10,
  rocc_cmd_data_o_11,
  rocc_cmd_data_o_12,
  rocc_cmd_data_o_13,
  rocc_cmd_data_o_14,
  rocc_cmd_data_o_15,
  rocc_cmd_ready_i,
  rocc_resp_v_i,
  rocc_resp_data_i,
  rocc_resp_ready_o,
  rocc_mem_req_v_i,
  rocc_mem_req_data_i,
  rocc_mem_req_ready_o,
  rocc_mem_resp_v_o,
  rocc_mem_resp_data_o_0,
  rocc_mem_resp_data_o_1,
  rocc_mem_resp_data_o_2,
  rocc_mem_resp_data_o_3,
  rocc_mem_resp_data_o_4,
  rocc_mem_resp_data_o_5,
  rocc_mem_resp_data_o_6,
  rocc_mem_resp_data_o_7,
  rocc_mem_resp_data_o_8,
  rocc_mem_resp_data_o_9,
  rocc_mem_resp_data_o_10,
  rocc_mem_resp_data_o_11,
  rocc_mem_resp_data_o_12,
  rocc_mem_resp_data_o_13,
  rocc_mem_resp_data_o_14,
  rocc_mem_resp_data_o_15,
  rocc_mem_resp_data_o_16,
  rocc_mem_resp_data_o_17,
  rocc_mem_resp_data_o_18,
  rocc_mem_resp_data_o_19,
  rocc_mem_resp_data_o_20,
  rocc_mem_resp_data_o_21,
  rocc_mem_resp_data_o_22,
  rocc_mem_resp_data_o_23,
  rocc_mem_resp_data_o_24,
  rocc_mem_resp_data_o_25,
  rocc_mem_resp_data_o_26,
  rocc_mem_resp_data_o_27,
  rocc_mem_resp_data_o_28,
  rocc_mem_resp_data_o_29,
  rocc_mem_resp_data_o_30,
  rocc_mem_resp_data_o_31,
  rocc_mem_resp_data_o_32,
  rocc_mem_resp_data_o_33,
  rocc_mem_resp_data_o_34,
  rocc_mem_resp_data_o_35,
  rocc_mem_resp_data_o_36,
  rocc_mem_resp_data_o_37,
  rocc_mem_resp_data_o_38,
  rocc_mem_resp_data_o_39,
  rocc_mem_resp_data_o_40,
  rocc_mem_resp_data_o_41,
  rocc_mem_resp_data_o_42,
  rocc_mem_resp_data_o_43,
  rocc_mem_resp_data_o_44,
  rocc_mem_resp_data_o_45,
  rocc_mem_resp_data_o_46,
  rocc_mem_resp_data_o_47,
  rocc_mem_resp_data_o_48,
  rocc_mem_resp_data_o_49,
  rocc_mem_resp_data_o_50,
  rocc_mem_resp_data_o_51,
  rocc_mem_resp_data_o_52,
  rocc_mem_resp_data_o_53,
  rocc_mem_resp_data_o_54,
  rocc_mem_resp_data_o_55,
  rocc_mem_resp_data_o_56,
  rocc_mem_resp_data_o_57,
  rocc_mem_resp_data_o_58,
  rocc_mem_resp_data_o_59,
  rocc_mem_resp_data_o_60,
  rocc_mem_resp_data_o_61,
  rocc_mem_resp_data_o_62,
  rocc_mem_resp_data_o_63,
  fsb_node_v_i,
  fsb_node_data_i,
  fsb_node_ready_o,
  fsb_node_v_o,
  fsb_node_data_o_0,
  fsb_node_data_o_1,
  fsb_node_data_o_2,
  fsb_node_data_o_3,
  fsb_node_data_o_4,
  fsb_node_data_o_5,
  fsb_node_data_o_6,
  fsb_node_data_o_7,
  fsb_node_yumi_i,
  rocc_ctrl_i_busy_,
  rocc_ctrl_i_interrupt_,
  rocc_ctrl_o_s_,
  rocc_ctrl_o_exception_,
  rocc_ctrl_o_host_id_
);

  output rocc_cmd_data_o_0;
  output rocc_cmd_data_o_1;
  output rocc_cmd_data_o_2;
  output rocc_cmd_data_o_3;
  output rocc_cmd_data_o_4;
  output rocc_cmd_data_o_5;
  output rocc_cmd_data_o_6;
  output rocc_cmd_data_o_7;
  output rocc_cmd_data_o_8;
  output rocc_cmd_data_o_9;
  output rocc_cmd_data_o_10;
  output rocc_cmd_data_o_11;
  output rocc_cmd_data_o_12;
  output rocc_cmd_data_o_13;
  output rocc_cmd_data_o_14;
  output rocc_cmd_data_o_15;
  input [7:0] rocc_resp_data_i;
  input [31:0] rocc_mem_req_data_i;
  output rocc_mem_resp_data_o_0;
  output rocc_mem_resp_data_o_1;
  output rocc_mem_resp_data_o_2;
  output rocc_mem_resp_data_o_3;
  output rocc_mem_resp_data_o_4;
  output rocc_mem_resp_data_o_5;
  output rocc_mem_resp_data_o_6;
  output rocc_mem_resp_data_o_7;
  output rocc_mem_resp_data_o_8;
  output rocc_mem_resp_data_o_9;
  output rocc_mem_resp_data_o_10;
  output rocc_mem_resp_data_o_11;
  output rocc_mem_resp_data_o_12;
  output rocc_mem_resp_data_o_13;
  output rocc_mem_resp_data_o_14;
  output rocc_mem_resp_data_o_15;
  output rocc_mem_resp_data_o_16;
  output rocc_mem_resp_data_o_17;
  output rocc_mem_resp_data_o_18;
  output rocc_mem_resp_data_o_19;
  output rocc_mem_resp_data_o_20;
  output rocc_mem_resp_data_o_21;
  output rocc_mem_resp_data_o_22;
  output rocc_mem_resp_data_o_23;
  output rocc_mem_resp_data_o_24;
  output rocc_mem_resp_data_o_25;
  output rocc_mem_resp_data_o_26;
  output rocc_mem_resp_data_o_27;
  output rocc_mem_resp_data_o_28;
  output rocc_mem_resp_data_o_29;
  output rocc_mem_resp_data_o_30;
  output rocc_mem_resp_data_o_31;
  output rocc_mem_resp_data_o_32;
  output rocc_mem_resp_data_o_33;
  output rocc_mem_resp_data_o_34;
  output rocc_mem_resp_data_o_35;
  output rocc_mem_resp_data_o_36;
  output rocc_mem_resp_data_o_37;
  output rocc_mem_resp_data_o_38;
  output rocc_mem_resp_data_o_39;
  output rocc_mem_resp_data_o_40;
  output rocc_mem_resp_data_o_41;
  output rocc_mem_resp_data_o_42;
  output rocc_mem_resp_data_o_43;
  output rocc_mem_resp_data_o_44;
  output rocc_mem_resp_data_o_45;
  output rocc_mem_resp_data_o_46;
  output rocc_mem_resp_data_o_47;
  output rocc_mem_resp_data_o_48;
  output rocc_mem_resp_data_o_49;
  output rocc_mem_resp_data_o_50;
  output rocc_mem_resp_data_o_51;
  output rocc_mem_resp_data_o_52;
  output rocc_mem_resp_data_o_53;
  output rocc_mem_resp_data_o_54;
  output rocc_mem_resp_data_o_55;
  output rocc_mem_resp_data_o_56;
  output rocc_mem_resp_data_o_57;
  output rocc_mem_resp_data_o_58;
  output rocc_mem_resp_data_o_59;
  output rocc_mem_resp_data_o_60;
  output rocc_mem_resp_data_o_61;
  output rocc_mem_resp_data_o_62;
  output rocc_mem_resp_data_o_63;
  input [7:0] fsb_node_data_i;
  output fsb_node_data_o_0;
  output fsb_node_data_o_1;
  output fsb_node_data_o_2;
  output fsb_node_data_o_3;
  output fsb_node_data_o_4;
  output fsb_node_data_o_5;
  output fsb_node_data_o_6;
  output fsb_node_data_o_7;
  input clk_i;
  input reset_i;
  input rocc_cmd_ready_i;
  input rocc_resp_v_i;
  input rocc_mem_req_v_i;
  input fsb_node_v_i;
  input fsb_node_yumi_i;
  input rocc_ctrl_i_busy_;
  input rocc_ctrl_i_interrupt_;
  output rocc_cmd_v_o;
  output rocc_resp_ready_o;
  output rocc_mem_req_ready_o;
  output rocc_mem_resp_v_o;
  output fsb_node_ready_o;
  output fsb_node_v_o;
  output rocc_ctrl_o_s_;
  output rocc_ctrl_o_exception_;
  output rocc_ctrl_o_host_id_;

  wire [7:0] fsb_node_datai;
  wire [31:0] rocc_mem_req_data;

  reg [68:0] rocc_resp_data_int;
  reg [122:0] rocc_mem_req_data_int;
  reg [79:0] fsb_node_data_i_int;

  always @(posedge clk or negedge reset) begin
    if (~reset)
    begin
      rocc_resp_data_int <= 69'b0;
      rocc_mem_req_data_int <= 123'b0;
      fsb_node_data_i_int <= 80'b0;
    end
    else
    begin
      rocc_resp_data_int <= {61'b0,rocc_resp_data};
      rocc_mem_req_data_int <= {91'b0,rocc_mem_req_data};
      fsb_node_data_i_int <= {72'b0,fsb_node_datai};
    end
  end

  bsg_rocket_node_client_rocc u_coyote (
    .clk_i(clk),
    .reset_i(reset),
    .en_i(en),
    .rocc_cmd_v_o(rocc_cmd_v),
    .rocc_cmd_data_o(rocc_cmd_data_int),
    .rocc_cmd_ready_i(rocc_cmd_ready),
    .rocc_resp_v_i(rocc_resp_v),
    .rocc_resp_data_i(rocc_resp_data_int),
    .rocc_resp_ready_o(rocc_resp_ready),
    .rocc_mem_req_v_i(rocc_mem_req_v),
    .rocc_mem_req_data_i(rocc_mem_req_data_int),
    .rocc_mem_req_ready_o(rocc_mem_req_ready),
    .rocc_mem_resp_v_o(rocc_mem_resp_v),
    .rocc_mem_resp_data_o(rocc_mem_resp_data_int),
    .fsb_node_v_i(fsb_node_vi),
    .fsb_node_data_i(fsb_node_data_i_int),
    .fsb_node_ready_o(fsb_node_ready),
    .fsb_node_v_o(fsb_node_vo),
    .fsb_node_data_o(fsb_node_data_o_int),
    .fsb_node_yumi_i(fsb_node_yumi),
    .rocc_ctrl_i_busy_(rocc_ctrl_busy),
    .rocc_ctrl_i_interrupt_(rocc_ctrl_interrupt),
    .rocc_ctrl_o_s_(rocc_ctrl_s),
    .rocc_ctrl_o_exception_(rocc_ctrl_exception),
    .rocc_ctrl_o_host_id_(rocc_ctrl_host_id)
  );  
  
  core_pg_pads #(.NUM_PAIRS(9)) u_core_pg ();
  io_pg_pads #(.NUM_PAIRS(20)) u_io_pg ();

  input_pad u_clk (.PAD(clk_i), .y(clk));
  input_pad u_reset (.PAD(reset_i), .y(reset));
  input_pad u_en (.PAD(en_i), .y(en));
  input_pad u_rocc_cmd_ready (.PAD(rocc_cmd_ready_i), .y(rocc_cmd_ready));
  input_pad u_rocc_resp_v (.PAD(rocc_resp_v_i), .y(rocc_resp_v));
  input_pad u_rocc_mem_req_v (.PAD(rocc_mem_req_v_i), .y(rocc_mem_req_v));
  input_pad u_fsb_node_v_i (.PAD(fsb_node_v_i), .y(fsb_node_vi));
  input_pad u_fsb_node_yumi (.PAD(fsb_node_yumi_i), .y(fsb_node_yumi));
  input_pad u_rocc_ctrl_i_busy (.PAD(rocc_ctrl_i_busy_), .y(rocc_ctrl_busy));
  input_pad u_rocc_ctrl_i_interrupt (.PAD(rocc_ctrl_i_interrupt_), .y(rocc_ctrl_interrupt));

  input_bus #(.WIDTH(8)) u_rocc_resp_data_i (.PAD(rocc_resp_data_i), .y(rocc_resp_data));
  input_bus #(.WIDTH(32)) u_rocc_mem_req_data_i (.PAD(rocc_mem_req_data_i), .y(rocc_mem_req_data));
  input_bus #(.WIDTH(8)) u_fsb_node_data_i (.PAD(fsb_node_data_i), .y(fsb_node_datai));

  output_pad u_rocc_cmd_data_o_0_ (.PAD(rocc_cmd_data_o_0), .a(rocc_cmd_data_int[0]));
  output_pad u_rocc_cmd_data_o_1_ (.PAD(rocc_cmd_data_o_1), .a(rocc_cmd_data_int[1]));
  output_pad u_rocc_cmd_data_o_2_ (.PAD(rocc_cmd_data_o_2), .a(rocc_cmd_data_int[2]));
  output_pad u_rocc_cmd_data_o_3_ (.PAD(rocc_cmd_data_o_3), .a(rocc_cmd_data_int[3]));
  output_pad u_rocc_cmd_data_o_4_ (.PAD(rocc_cmd_data_o_4), .a(rocc_cmd_data_int[4]));
  output_pad u_rocc_cmd_data_o_5_ (.PAD(rocc_cmd_data_o_5), .a(rocc_cmd_data_int[5]));
  output_pad u_rocc_cmd_data_o_6_ (.PAD(rocc_cmd_data_o_6), .a(rocc_cmd_data_int[6]));
  output_pad u_rocc_cmd_data_o_7_ (.PAD(rocc_cmd_data_o_7), .a(rocc_cmd_data_int[7]));
  output_pad u_rocc_cmd_data_o_8_ (.PAD(rocc_cmd_data_o_8), .a(rocc_cmd_data_int[8]));
  output_pad u_rocc_cmd_data_o_9_ (.PAD(rocc_cmd_data_o_9), .a(rocc_cmd_data_int[9]));
  output_pad u_rocc_cmd_data_o_10_ (.PAD(rocc_cmd_data_o_10), .a(rocc_cmd_data_int[10]));
  output_pad u_rocc_cmd_data_o_11_ (.PAD(rocc_cmd_data_o_11), .a(rocc_cmd_data_int[11]));
  output_pad u_rocc_cmd_data_o_12_ (.PAD(rocc_cmd_data_o_12), .a(rocc_cmd_data_int[12]));
  output_pad u_rocc_cmd_data_o_13_ (.PAD(rocc_cmd_data_o_13), .a(rocc_cmd_data_int[13]));
  output_pad u_rocc_cmd_data_o_14_ (.PAD(rocc_cmd_data_o_14), .a(rocc_cmd_data_int[14]));
  output_pad u_rocc_cmd_data_o_15_ (.PAD(rocc_cmd_data_o_15), .a(rocc_cmd_data_int[15]));
  output_pad u_rocc_mem_resp_data_o_0_ (.PAD(rocc_mem_resp_data_o_0), .a(rocc_mem_resp_data_int[0]));
  output_pad u_rocc_mem_resp_data_o_1_ (.PAD(rocc_mem_resp_data_o_1), .a(rocc_mem_resp_data_int[1]));
  output_pad u_rocc_mem_resp_data_o_2_ (.PAD(rocc_mem_resp_data_o_2), .a(rocc_mem_resp_data_int[2]));
  output_pad u_rocc_mem_resp_data_o_3_ (.PAD(rocc_mem_resp_data_o_3), .a(rocc_mem_resp_data_int[3]));
  output_pad u_rocc_mem_resp_data_o_4_ (.PAD(rocc_mem_resp_data_o_4), .a(rocc_mem_resp_data_int[4]));
  output_pad u_rocc_mem_resp_data_o_5_ (.PAD(rocc_mem_resp_data_o_5), .a(rocc_mem_resp_data_int[5]));
  output_pad u_rocc_mem_resp_data_o_6_ (.PAD(rocc_mem_resp_data_o_6), .a(rocc_mem_resp_data_int[6]));
  output_pad u_rocc_mem_resp_data_o_7_ (.PAD(rocc_mem_resp_data_o_7), .a(rocc_mem_resp_data_int[7]));
  output_pad u_rocc_mem_resp_data_o_8_ (.PAD(rocc_mem_resp_data_o_8), .a(rocc_mem_resp_data_int[8]));
  output_pad u_rocc_mem_resp_data_o_9_ (.PAD(rocc_mem_resp_data_o_9), .a(rocc_mem_resp_data_int[9]));
  output_pad u_rocc_mem_resp_data_o_10_ (.PAD(rocc_mem_resp_data_o_10), .a(rocc_mem_resp_data_int[10]));
  output_pad u_rocc_mem_resp_data_o_11_ (.PAD(rocc_mem_resp_data_o_11), .a(rocc_mem_resp_data_int[11]));
  output_pad u_rocc_mem_resp_data_o_12_ (.PAD(rocc_mem_resp_data_o_12), .a(rocc_mem_resp_data_int[12]));
  output_pad u_rocc_mem_resp_data_o_13_ (.PAD(rocc_mem_resp_data_o_13), .a(rocc_mem_resp_data_int[13]));
  output_pad u_rocc_mem_resp_data_o_14_ (.PAD(rocc_mem_resp_data_o_14), .a(rocc_mem_resp_data_int[14]));
  output_pad u_rocc_mem_resp_data_o_15_ (.PAD(rocc_mem_resp_data_o_15), .a(rocc_mem_resp_data_int[15]));
  output_pad u_rocc_mem_resp_data_o_16_ (.PAD(rocc_mem_resp_data_o_16), .a(rocc_mem_resp_data_int[16]));
  output_pad u_rocc_mem_resp_data_o_17_ (.PAD(rocc_mem_resp_data_o_17), .a(rocc_mem_resp_data_int[17]));
  output_pad u_rocc_mem_resp_data_o_18_ (.PAD(rocc_mem_resp_data_o_18), .a(rocc_mem_resp_data_int[18]));
  output_pad u_rocc_mem_resp_data_o_19_ (.PAD(rocc_mem_resp_data_o_19), .a(rocc_mem_resp_data_int[19]));
  output_pad u_rocc_mem_resp_data_o_20_ (.PAD(rocc_mem_resp_data_o_20), .a(rocc_mem_resp_data_int[20]));
  output_pad u_rocc_mem_resp_data_o_21_ (.PAD(rocc_mem_resp_data_o_21), .a(rocc_mem_resp_data_int[21]));
  output_pad u_rocc_mem_resp_data_o_22_ (.PAD(rocc_mem_resp_data_o_22), .a(rocc_mem_resp_data_int[22]));
  output_pad u_rocc_mem_resp_data_o_23_ (.PAD(rocc_mem_resp_data_o_23), .a(rocc_mem_resp_data_int[23]));
  output_pad u_rocc_mem_resp_data_o_24_ (.PAD(rocc_mem_resp_data_o_24), .a(rocc_mem_resp_data_int[24]));
  output_pad u_rocc_mem_resp_data_o_25_ (.PAD(rocc_mem_resp_data_o_25), .a(rocc_mem_resp_data_int[25]));
  output_pad u_rocc_mem_resp_data_o_26_ (.PAD(rocc_mem_resp_data_o_26), .a(rocc_mem_resp_data_int[26]));
  output_pad u_rocc_mem_resp_data_o_27_ (.PAD(rocc_mem_resp_data_o_27), .a(rocc_mem_resp_data_int[27]));
  output_pad u_rocc_mem_resp_data_o_28_ (.PAD(rocc_mem_resp_data_o_28), .a(rocc_mem_resp_data_int[28]));
  output_pad u_rocc_mem_resp_data_o_29_ (.PAD(rocc_mem_resp_data_o_29), .a(rocc_mem_resp_data_int[29]));
  output_pad u_rocc_mem_resp_data_o_30_ (.PAD(rocc_mem_resp_data_o_30), .a(rocc_mem_resp_data_int[30]));
  output_pad u_rocc_mem_resp_data_o_31_ (.PAD(rocc_mem_resp_data_o_31), .a(rocc_mem_resp_data_int[31]));
  output_pad u_rocc_mem_resp_data_o_32_ (.PAD(rocc_mem_resp_data_o_32), .a(rocc_mem_resp_data_int[32]));
  output_pad u_rocc_mem_resp_data_o_33_ (.PAD(rocc_mem_resp_data_o_33), .a(rocc_mem_resp_data_int[33]));
  output_pad u_rocc_mem_resp_data_o_34_ (.PAD(rocc_mem_resp_data_o_34), .a(rocc_mem_resp_data_int[34]));
  output_pad u_rocc_mem_resp_data_o_35_ (.PAD(rocc_mem_resp_data_o_35), .a(rocc_mem_resp_data_int[35]));
  output_pad u_rocc_mem_resp_data_o_36_ (.PAD(rocc_mem_resp_data_o_36), .a(rocc_mem_resp_data_int[36]));
  output_pad u_rocc_mem_resp_data_o_37_ (.PAD(rocc_mem_resp_data_o_37), .a(rocc_mem_resp_data_int[37]));
  output_pad u_rocc_mem_resp_data_o_38_ (.PAD(rocc_mem_resp_data_o_38), .a(rocc_mem_resp_data_int[38]));
  output_pad u_rocc_mem_resp_data_o_39_ (.PAD(rocc_mem_resp_data_o_39), .a(rocc_mem_resp_data_int[39]));
  output_pad u_rocc_mem_resp_data_o_40_ (.PAD(rocc_mem_resp_data_o_40), .a(rocc_mem_resp_data_int[40]));
  output_pad u_rocc_mem_resp_data_o_41_ (.PAD(rocc_mem_resp_data_o_41), .a(rocc_mem_resp_data_int[41]));
  output_pad u_rocc_mem_resp_data_o_42_ (.PAD(rocc_mem_resp_data_o_42), .a(rocc_mem_resp_data_int[42]));
  output_pad u_rocc_mem_resp_data_o_43_ (.PAD(rocc_mem_resp_data_o_43), .a(rocc_mem_resp_data_int[43]));
  output_pad u_rocc_mem_resp_data_o_44_ (.PAD(rocc_mem_resp_data_o_44), .a(rocc_mem_resp_data_int[44]));
  output_pad u_rocc_mem_resp_data_o_45_ (.PAD(rocc_mem_resp_data_o_45), .a(rocc_mem_resp_data_int[45]));
  output_pad u_rocc_mem_resp_data_o_46_ (.PAD(rocc_mem_resp_data_o_46), .a(rocc_mem_resp_data_int[46]));
  output_pad u_rocc_mem_resp_data_o_47_ (.PAD(rocc_mem_resp_data_o_47), .a(rocc_mem_resp_data_int[47]));
  output_pad u_rocc_mem_resp_data_o_48_ (.PAD(rocc_mem_resp_data_o_48), .a(rocc_mem_resp_data_int[48]));
  output_pad u_rocc_mem_resp_data_o_49_ (.PAD(rocc_mem_resp_data_o_49), .a(rocc_mem_resp_data_int[49]));
  output_pad u_rocc_mem_resp_data_o_50_ (.PAD(rocc_mem_resp_data_o_50), .a(rocc_mem_resp_data_int[50]));
  output_pad u_rocc_mem_resp_data_o_51_ (.PAD(rocc_mem_resp_data_o_51), .a(rocc_mem_resp_data_int[51]));
  output_pad u_rocc_mem_resp_data_o_52_ (.PAD(rocc_mem_resp_data_o_52), .a(rocc_mem_resp_data_int[52]));
  output_pad u_rocc_mem_resp_data_o_53_ (.PAD(rocc_mem_resp_data_o_53), .a(rocc_mem_resp_data_int[53]));
  output_pad u_rocc_mem_resp_data_o_54_ (.PAD(rocc_mem_resp_data_o_54), .a(rocc_mem_resp_data_int[54]));
  output_pad u_rocc_mem_resp_data_o_55_ (.PAD(rocc_mem_resp_data_o_55), .a(rocc_mem_resp_data_int[55]));
  output_pad u_rocc_mem_resp_data_o_56_ (.PAD(rocc_mem_resp_data_o_56), .a(rocc_mem_resp_data_int[56]));
  output_pad u_rocc_mem_resp_data_o_57_ (.PAD(rocc_mem_resp_data_o_57), .a(rocc_mem_resp_data_int[57]));
  output_pad u_rocc_mem_resp_data_o_58_ (.PAD(rocc_mem_resp_data_o_58), .a(rocc_mem_resp_data_int[58]));
  output_pad u_rocc_mem_resp_data_o_59_ (.PAD(rocc_mem_resp_data_o_59), .a(rocc_mem_resp_data_int[59]));
  output_pad u_rocc_mem_resp_data_o_60_ (.PAD(rocc_mem_resp_data_o_60), .a(rocc_mem_resp_data_int[60]));
  output_pad u_rocc_mem_resp_data_o_61_ (.PAD(rocc_mem_resp_data_o_61), .a(rocc_mem_resp_data_int[61]));
  output_pad u_rocc_mem_resp_data_o_62_ (.PAD(rocc_mem_resp_data_o_62), .a(rocc_mem_resp_data_int[62]));
  output_pad u_rocc_mem_resp_data_o_63_ (.PAD(rocc_mem_resp_data_o_63), .a(rocc_mem_resp_data_int[63]));
  output_pad u_fsb_node_data_o_0_ (.PAD(fsb_node_data_o_0), .a(fsb_node_data_o_int[0]));
  output_pad u_fsb_node_data_o_1_ (.PAD(fsb_node_data_o_1), .a(fsb_node_data_o_int[1]));
  output_pad u_fsb_node_data_o_2_ (.PAD(fsb_node_data_o_2), .a(fsb_node_data_o_int[2]));
  output_pad u_fsb_node_data_o_3_ (.PAD(fsb_node_data_o_3), .a(fsb_node_data_o_int[3]));
  output_pad u_fsb_node_data_o_4_ (.PAD(fsb_node_data_o_4), .a(fsb_node_data_o_int[4]));
  output_pad u_fsb_node_data_o_5_ (.PAD(fsb_node_data_o_5), .a(fsb_node_data_o_int[5]));
  output_pad u_fsb_node_data_o_6_ (.PAD(fsb_node_data_o_6), .a(fsb_node_data_o_int[6]));
  output_pad u_fsb_node_data_o_7_ (.PAD(fsb_node_data_o_7), .a(fsb_node_data_o_int[7]));

  output_pad u_rocc_cmd_v (.PAD(rocc_cmd_v_o), .a(rocc_cmd_v));
  output_pad u_rocc_resp_ready (.PAD(rocc_resp_ready_o), .a(rocc_resp_ready));
  output_pad u_rocc_mem_req_ready (.PAD(rocc_mem_req_ready_o), .a(rocc_mem_req_ready));
  output_pad u_rocc_mem_resp_v (.PAD(rocc_mem_resp_v_o), .a(rocc_mem_resp_v));
  output_pad u_fsb_node_ready (.PAD(fsb_node_ready_o), .a(fsb_node_ready));
  output_pad u_fsb_node_v_o (.PAD(fsb_node_v_o), .a(fsb_node_vo));
  output_pad u_rocc_ctrl_o_s (.PAD(rocc_ctrl_o_s_), .a(rocc_ctrl_s));
  output_pad u_rocc_ctrl_o_exception (.PAD(rocc_ctrl_o_exception_), .a(rocc_ctrl_exception));
  output_pad u_rocc_ctrl_o_host_id (.PAD(rocc_ctrl_o_host_id_), .a(rocc_ctrl_host_id));

  input_pad u_tck(.PAD(TCK), .y(tck));
  input_pad u_tdi(.PAD(TDI), .y(tdi));
  input_pad u_tms(.PAD(TMS), .y(tms));
  input_pad u_trst(.PAD(TRST), .y(trst));
  output_pad u_tdo(.PAD(TDO), .a(tdo));
endmodule

