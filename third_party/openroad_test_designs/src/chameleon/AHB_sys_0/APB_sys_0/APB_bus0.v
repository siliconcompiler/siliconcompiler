
`timescale 1ns/1ns

module APB_BUS0 #(
    // Parameters to enable/disable ports
    
    parameter PORT0_ENABLE  = 1,
    parameter PORT1_ENABLE  = 1,
    parameter PORT2_ENABLE  = 1,
    parameter PORT3_ENABLE  = 1,
    parameter PORT4_ENABLE  = 1,
    parameter PORT5_ENABLE  = 1,
    parameter PORT6_ENABLE  = 1,
    parameter PORT7_ENABLE  = 1,
    parameter PORT8_ENABLE  = 1,
    parameter PORT9_ENABLE  = 1,
    parameter PORT10_ENABLE  = 1,
    parameter PORT11_ENABLE  = 1,
    parameter PORT12_ENABLE  = 1,
    parameter PORT13_ENABLE  = 1,
    parameter PORT14_ENABLE  = 1,
    parameter PORT15_ENABLE  = 1
    )


    (
    // --------------------------------------------------------------------------
    // Port Definitions
    // --------------------------------------------------------------------------
    //MODULE INPUTS
      input  wire  [3:0]  DEC_BITS,
      input  wire         PSEL,
          
    // Slave # 0
    output wire         PSEL_S0,
    input wire          PREADY_S0,
    input wire  [31:0]  PRDATA_S0,
    input wire          PSLVERR_S0,
    // Slave # 1
    output wire         PSEL_S1,
    input wire          PREADY_S1,
    input wire  [31:0]  PRDATA_S1,
    input wire          PSLVERR_S1,
    // Slave # 2
    output wire         PSEL_S2,
    input wire          PREADY_S2,
    input wire  [31:0]  PRDATA_S2,
    input wire          PSLVERR_S2,
    // Slave # 3
    output wire         PSEL_S3,
    input wire          PREADY_S3,
    input wire  [31:0]  PRDATA_S3,
    input wire          PSLVERR_S3,
    // Slave # 4
    output wire         PSEL_S4,
    input wire          PREADY_S4,
    input wire  [31:0]  PRDATA_S4,
    input wire          PSLVERR_S4,
    // Slave # 5
    output wire         PSEL_S5,
    input wire          PREADY_S5,
    input wire  [31:0]  PRDATA_S5,
    input wire          PSLVERR_S5,
    // Slave # 6
    output wire         PSEL_S6,
    input wire          PREADY_S6,
    input wire  [31:0]  PRDATA_S6,
    input wire          PSLVERR_S6,
    // Slave # 7
    output wire         PSEL_S7,
    input wire          PREADY_S7,
    input wire  [31:0]  PRDATA_S7,
    input wire          PSLVERR_S7,
    // Slave # 8
    output wire         PSEL_S8,
    input wire          PREADY_S8,
    input wire  [31:0]  PRDATA_S8,
    input wire          PSLVERR_S8,
    // Slave # 9
    output wire         PSEL_S9,
    input wire          PREADY_S9,
    input wire  [31:0]  PRDATA_S9,
    input wire          PSLVERR_S9,
    // Slave # 10
    output wire         PSEL_S10,
    input wire          PREADY_S10,
    input wire  [31:0]  PRDATA_S10,
    input wire          PSLVERR_S10,
    // Slave # 11
    output wire         PSEL_S11,
    input wire          PREADY_S11,
    input wire  [31:0]  PRDATA_S11,
    input wire          PSLVERR_S11,
    // Slave # 12
    output wire         PSEL_S12,
    input wire          PREADY_S12,
    input wire  [31:0]  PRDATA_S12,
    input wire          PSLVERR_S12,
    // Slave # 13
    output wire         PSEL_S13,
    input wire          PREADY_S13,
    input wire  [31:0]  PRDATA_S13,
    input wire          PSLVERR_S13,
    // Slave # 14
    output wire         PSEL_S14,
    input wire          PREADY_S14,
    input wire  [31:0]  PRDATA_S14,
    input wire          PSLVERR_S14,
    // Slave # 15
    output wire         PSEL_S15,
    input wire          PREADY_S15,
    input wire  [31:0]  PRDATA_S15,
    input wire          PSLVERR_S15,
    //MODULE OUTPUTS
    output wire         PREADY,
    output wire [31:0]  PRDATA,
    output wire         PSLVERR
);
 
    wire [15:0] en  = { 
                        (PORT15_ENABLE  == 1),
                        (PORT14_ENABLE  == 1),
                        (PORT13_ENABLE  == 1),
                        (PORT12_ENABLE  == 1),
                        (PORT11_ENABLE  == 1),
                        (PORT10_ENABLE  == 1),
                        (PORT9_ENABLE  == 1),
                        (PORT8_ENABLE  == 1),
                        (PORT7_ENABLE  == 1),
                        (PORT6_ENABLE  == 1),
                        (PORT5_ENABLE  == 1),
                        (PORT4_ENABLE  == 1),
                        (PORT3_ENABLE  == 1),
                        (PORT2_ENABLE  == 1),
                        (PORT1_ENABLE  == 1),
                        (PORT0_ENABLE  == 1)
                        };

    wire [15:0] dec  = { 
                        (DEC_BITS  == 4'd15),
                        (DEC_BITS  == 4'd14),
                        (DEC_BITS  == 4'd13),
                        (DEC_BITS  == 4'd12),
                        (DEC_BITS  == 4'd11),
                        (DEC_BITS  == 4'd10),
                        (DEC_BITS  == 4'd9),
                        (DEC_BITS  == 4'd8),
                        (DEC_BITS  == 4'd7),
                        (DEC_BITS  == 4'd6),
                        (DEC_BITS  == 4'd5),
                        (DEC_BITS  == 4'd4),
                        (DEC_BITS  == 4'd3),
                        (DEC_BITS  == 4'd2),
                        (DEC_BITS  == 4'd1),
                        (DEC_BITS  == 4'd0)
                        };


    // Setting PSEL 
    assign PSEL_S0 = PSEL & dec[0] & en[0];
    assign PSEL_S1 = PSEL & dec[1] & en[1];
    assign PSEL_S2 = PSEL & dec[2] & en[2];
    assign PSEL_S3 = PSEL & dec[3] & en[3];
    assign PSEL_S4 = PSEL & dec[4] & en[4];
    assign PSEL_S5 = PSEL & dec[5] & en[5];
    assign PSEL_S6 = PSEL & dec[6] & en[6];
    assign PSEL_S7 = PSEL & dec[7] & en[7];
    assign PSEL_S8 = PSEL & dec[8] & en[8];
    assign PSEL_S9 = PSEL & dec[9] & en[9];
    assign PSEL_S10 = PSEL & dec[10] & en[10];
    assign PSEL_S11 = PSEL & dec[11] & en[11];
    assign PSEL_S12 = PSEL & dec[12] & en[12];
    assign PSEL_S13 = PSEL & dec[13] & en[13];
    assign PSEL_S14 = PSEL & dec[14] & en[14];
    assign PSEL_S15 = PSEL & dec[15] & en[15];

    // Setting PREADY

    assign PREADY = ~PSEL |
        ( dec[0] & ( PREADY_S0 | en[0] ) ) |
        ( dec[1] & ( PREADY_S1 | en[1] ) ) |
        ( dec[2] & ( PREADY_S2 | en[2] ) ) |
        ( dec[3] & ( PREADY_S3 | en[3] ) ) |
        ( dec[4] & ( PREADY_S4 | en[4] ) ) |
        ( dec[5] & ( PREADY_S5 | en[5] ) ) |
        ( dec[6] & ( PREADY_S6 | en[6] ) ) |
        ( dec[7] & ( PREADY_S7 | en[7] ) ) |
        ( dec[8] & ( PREADY_S8 | en[8] ) ) |
        ( dec[9] & ( PREADY_S9 | en[9] ) ) |
        ( dec[10] & ( PREADY_S10 | en[10] ) ) |
        ( dec[11] & ( PREADY_S11 | en[11] ) ) |
        ( dec[12] & ( PREADY_S12 | en[12] ) ) |
        ( dec[13] & ( PREADY_S13 | en[13] ) ) |
        ( dec[14] & ( PREADY_S14 | en[14] ) ) |
        ( dec[15] & ( PREADY_S15 | en[15] ) );

    // Setting PSLVERR

    assign PSLVERR = ( PSEL_S0 & PSLVERR_S0 ) |
        ( PSEL_S1 & PSLVERR_S1 ) |
        ( PSEL_S2 & PSLVERR_S2 ) |
        ( PSEL_S3 & PSLVERR_S3 ) |
        ( PSEL_S4 & PSLVERR_S4 ) |
        ( PSEL_S5 & PSLVERR_S5 ) |
        ( PSEL_S6 & PSLVERR_S6 ) |
        ( PSEL_S7 & PSLVERR_S7 ) |
        ( PSEL_S8 & PSLVERR_S8 ) |
        ( PSEL_S9 & PSLVERR_S9 ) |
        ( PSEL_S10 & PSLVERR_S10 ) |
        ( PSEL_S11 & PSLVERR_S11 ) |
        ( PSEL_S12 & PSLVERR_S12 ) |
        ( PSEL_S13 & PSLVERR_S13 ) |
        ( PSEL_S14 & PSLVERR_S14 ) |
        ( PSEL_S15 & PSLVERR_S15 );

    // Setting PRDATA

    assign PRDATA = ( {32{PSEL_S0}} & PRDATA_S0 ) |
        ( {32{PSEL_S1}} & PRDATA_S1 ) |
        ( {32{PSEL_S2}} & PRDATA_S2 ) |
        ( {32{PSEL_S3}} & PRDATA_S3 ) |
        ( {32{PSEL_S4}} & PRDATA_S4 ) |
        ( {32{PSEL_S5}} & PRDATA_S5 ) |
        ( {32{PSEL_S6}} & PRDATA_S6 ) |
        ( {32{PSEL_S7}} & PRDATA_S7 ) |
        ( {32{PSEL_S8}} & PRDATA_S8 ) |
        ( {32{PSEL_S9}} & PRDATA_S9 ) |
        ( {32{PSEL_S10}} & PRDATA_S10 ) |
        ( {32{PSEL_S11}} & PRDATA_S11 ) |
        ( {32{PSEL_S12}} & PRDATA_S12 ) |
        ( {32{PSEL_S13}} & PRDATA_S13 ) |
        ( {32{PSEL_S14}} & PRDATA_S14 ) |
        ( {32{PSEL_S15}} & PRDATA_S15 );
    
endmodule
    