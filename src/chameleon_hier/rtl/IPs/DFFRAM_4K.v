/*
    A parameterized DFF based RAM for SKY130A
    Use the COLS parameter to set the size
    Valid sizes: 1 (default), 2 or 4
*/
/*
    Author: Mohamed Shalan (mshalan@aucegypt.edu)
*/

`timescale 1ns / 1ps
`default_nettype none

module DFFRAM_4K
(
    CLK,
    WE,
    EN,
    Di,
    Do,
    A
);

    input           CLK;
    input   [3:0]   WE;
    input           EN;
    input   [31:0]  Di;
    output  [31:0]  Do;
    input   [7+$clog2(COLS):0]   A;

    //WBD
    localparam COLS=4;

    wire [31:0]     DOUT [COLS-1:0];
    wire [31:0]     Do_pre;
    wire [COLS-1:0] EN_lines;

    wire [9:8]      A_buf;

    generate
        genvar i;
        for (i=0; i<COLS; i=i+1) begin : COLUMN
            DFFRAM_COL4 RAMCOLS (   .CLK(CLK), 
                                    .WE(WE), 
                                    .EN(EN_lines[i]), 
                                    .Di(Di), 
                                    .Do(DOUT[i]), 
                                    .A(A[7:0]) 
                                );    
        end
        if(COLS==4) begin
            sky130_fd_sc_hd__clkbuf_8 ABUF[1:0] (.X(A_buf[9:8]), .A(A[9:8]) );
            MUX4x1_32 MUX ( .A0(DOUT[0]), .A1(DOUT[1]), .A2(DOUT[2]), .A3(DOUT[3]), .S(A_buf[9:8]), .X(Do_pre) );
            DEC2x4 DEC ( .EN(EN), .A(A[9:8]), .SEL(EN_lines) );
        end
        else if(COLS==2) begin
            sky130_fd_sc_hd__clkbuf_8 ABUF[8:8] (.X(A_buf[8]), .A(A[8]) );
            MUX2x1_32 MUX ( .A0(DOUT[0]), .A1(DOUT[1]), .S(A_buf[8]), .X(Do_pre) );
            //sky130_fd_sc_hd__inv_4 DEC0 ( .Y(EN_lines[0]), .A(A[8]) );
            //sky130_fd_sc_hd__clkbuf_4 DEC1 (.X(EN_lines[1]), .A(A[8]) );
            DEC1x2 DEC ( .EN(EN), .A(A[8]), .SEL(EN_lines[1:0]) );
            
        end
        else begin
            PASS MUX ( .A(DOUT[0]), .X(Do_pre) );
            sky130_fd_sc_hd__clkbuf_4 ENBUF (.X(EN_lines[0]), .A(EN) );
        end
    endgenerate
    
    sky130_fd_sc_hd__clkbuf_4 DOBUF[31:0] (.X(Do), .A(Do_pre));

endmodule
