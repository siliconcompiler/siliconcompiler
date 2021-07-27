`timescale 1ns/1ps
`default_nettype none

// uncomment the following line to use the optimized cache (SKY130A only)
//`define NO_HC_CACHE

/*
    AHB-Lite Quad I/O flash reader with 32x16 DM$
    Intended to be used to execute from an external Quad I/O SPI Flash Memory
*/
module QSPI_XIP_CTRL(
`ifdef USE_POWER_PINS
	input VPWR,
	input VGND,
`endif
    // AHB-Lite Slave Interface
    input               HCLK,
    input               HRESETn,
    input               HSEL,
    input wire [31:0]   HADDR,
    input wire [1:0]    HTRANS,
    //input wire [31:0]   HWDATA,
    input wire          HWRITE,
    input wire          HREADY,
    output reg          HREADYOUT,
    output wire [31:0]  HRDATA,

    // External Interface to Quad I/O
    output              sck,
    output              ce_n,
    input   wire[3:0]   din,
    output      [3:0]   dout,
    output  wire        douten     
);

    // Cache wires/buses
    wire [31:0]     c_datao;
    wire [127:0]    c_line;
    wire            c_hit;
    reg [1:0]       c_wr;
    wire [23:0]     c_A;

    // Flash Reader wires
    wire            fr_rd;
    wire            fr_done;

    // The State Machine
    localparam [1:0] st_idle    = 2'b00;
    localparam [1:0] st_wait    = 2'b01;
    localparam [1:0] st_rw      = 2'b10;
    reg [1:0]   state, nstate;

    //AHB-Lite Address Phase Regs
    reg             last_HSEL;
    reg [31:0]      last_HADDR;
    reg             last_HWRITE;
    reg [1:0]       last_HTRANS;

    always@ (posedge HCLK) begin
        if(HREADY) begin
            last_HSEL       <= HSEL;
            last_HADDR      <= HADDR;
            last_HWRITE     <= HWRITE;
            last_HTRANS     <= HTRANS;
        end
    end

    always @ (posedge HCLK or negedge HRESETn)
        if(HRESETn == 0) state <= st_idle;
        else 
            state <= nstate;

    always @* begin
        nstate = st_idle;
        case(state)
            st_idle :   if(HTRANS[1] & HSEL & HREADY & c_hit) nstate = st_rw;
                        else if(HTRANS[1] & HSEL & HREADY & ~c_hit) nstate = st_wait;
            st_wait :   if(c_wr[1]) nstate = st_rw; 
                        else  nstate = st_wait;
            st_rw   :   //nstate = st_idle; 
                        if(HTRANS[1] & HSEL & HREADY & c_hit) nstate = st_rw;
                        else if(HTRANS[1] & HSEL & HREADY & ~c_hit) nstate = st_wait;
        endcase
    end
    
    //assign HREADYOUT    = (state==st_rw);
    always @(posedge HCLK or negedge HRESETn)
        if(!HRESETn) HREADYOUT <= 1'b1;
        else
            case (state)
                st_idle :   if(HTRANS[1] & HSEL & HREADY & c_hit) HREADYOUT <= 1'b1;
                            else if(HTRANS[1] & HSEL & HREADY & ~c_hit) HREADYOUT <= 1'b0;
                            else HREADYOUT <= 1'b1;
                st_wait :   if(c_wr[1]) HREADYOUT <= 1'b1;
                            else HREADYOUT <= 1'b0;
                st_rw   :   if(HTRANS[1] & HSEL & HREADY & c_hit) HREADYOUT <= 1'b1;
                            else if(HTRANS[1] & HSEL & HREADY & ~c_hit) HREADYOUT <= 1'b0;
                            //else HREADYOUT <= 1'b1;
            endcase
        

    assign fr_rd        =   ( HTRANS[1] & HSEL & HREADY & ~c_hit & (state==st_idle) ) |
                            ( HTRANS[1] & HSEL & HREADY & ~c_hit & (state==st_rw) );

    assign c_A          = //((state==st_idle) || (state==st_wait)) ? HADDR[23:0] : 
                            last_HADDR[23:0];

`ifdef NO_HC_CACHE
    DMC_32x16
`else
    DMC_32x16HC
`endif
                CACHE ( 
               `ifdef USE_POWER_PINS
			.VPWR(VPWR),
			.VGND(VGND),
	        `endif
                	 .clk(HCLK), .rst_n(HRESETn), 
                        .A(last_HADDR[23:0]), .A_h(HADDR[23:0]), .Do(c_datao), .hit(c_hit), 
                        .line(c_line), .wr(c_wr[1]) );
    
    FLASH_READER FR (   .clk(HCLK), .rst_n(HRESETn), 
                        .addr({HADDR[23:4], 4'd0}), .rd(fr_rd), .done(fr_done), .line(c_line),
                        .sck(sck), .ce_n(ce_n), .din(din), .dout(dout), .douten(douten) );

    assign HRDATA   = c_datao;
    //always @(posedge HCLK)
    //    HRDATA <= c_datao;

    //assign c_wr     = fr_done;
    always @ (posedge HCLK) begin
        c_wr[0] <= fr_done;
        c_wr[1] <= c_wr[0];
    end
  
endmodule

/*
    RTL Model for reading from Quad I/O flash using the QUAD I/O FAST READ (0xEB) command
    The Quad I/O bit has to be set in the flash memory (through flash programming); the 
    provided flash memory model has the bit set.

    Every transaction reads 128 bits (16 bytes) from the flash.
    To start a transaction, provide the memory address and assert rd for 1 clock cycle.
    done is a sserted for 1 clock cycle when the data is ready

*/
module FLASH_READER #(parameter LINE_SIZE=128)(
    input   wire                    clk,
    input   wire                    rst_n,
    input   wire [23:0]             addr,
    input   wire                    rd,
    output  wire                    done,
    output  wire [LINE_SIZE-1: 0]   line,      

    output  reg                     sck,
    output  reg                     ce_n,
    input   wire[3:0]               din,
    output      [3:0]               dout,
    output  wire                    douten
);

    localparam LINE_BYTES = LINE_SIZE/8;
    localparam LINE_CYCLES = LINE_BYTES * 8;

    parameter IDLE=1'b0, READ=1'b1;

    reg         state, nstate;
    reg [7:0]   counter;
    reg [23:0]  saddr;
    reg [7:0]   data [LINE_BYTES-1 : 0]; 

    reg         first;

    wire[7:0]   EBH     = 8'heb;
    
    // for debugging
    wire [7:0] data_0 = data[0];
    wire [7:0] data_1 = data[1];
    wire [7:0] data_15 = data[15];


    always @*
        case (state)
            IDLE: if(rd) nstate = READ; else nstate = IDLE;
            READ: if(done) nstate = IDLE; else nstate = READ;
        endcase 

    always @ (posedge clk or negedge rst_n)
        if(!rst_n) first = 1'b1;
        else if(first & done) first <= 0;

    
    always @ (posedge clk or negedge rst_n)
        if(!rst_n) state = IDLE;
        else state <= nstate;

    always @ (posedge clk or negedge rst_n)
        if(!rst_n) sck <= 1'b0;
        else if(~ce_n) sck <= ~ sck;
        else if(state == IDLE) sck <= 1'b0;

    always @ (posedge clk or negedge rst_n)
        if(!rst_n) ce_n <= 1'b1;
        else if(state == READ) ce_n <= 1'b0;
        else ce_n <= 1'b1;

    always @ (posedge clk or negedge rst_n)
        if(!rst_n) counter <= 8'b0;
        else if(sck & ~done) counter <= counter + 1'b1;
        else if(state == IDLE) 
            if(first) counter <= 8'b0;
            else counter <= 8'd8;

    always @ (posedge clk or negedge rst_n)
        if(!rst_n) saddr <= 24'b0;
        else if((state == IDLE) && rd) saddr <= addr;

    always @ (posedge clk)
        if(counter >= 20 && counter <= 19+LINE_BYTES*2)
            if(sck) data[counter/2 - 10] <= {data[counter/2 - 10][3:0], din}; // Optimize!

    //assign busy = (state == READ);

    assign dout     =   (counter < 8)   ? EBH[7 - counter] :
                        (counter == 8)  ? saddr[23:20] : 
                        (counter == 9)  ? saddr[19:16] :
                        (counter == 10)  ? saddr[15:12] :
                        (counter == 11)  ? saddr[11:8] :
                        (counter == 12)  ? saddr[7:4] :
                        (counter == 13)  ? saddr[3:0] :
                        (counter == 14)  ? 4'hA :
                        (counter == 15)  ? 4'h5 : 4'h0;    
        
    assign douten   = (counter < 20);

    assign done     = (counter == 19+LINE_BYTES*2);


    generate
        genvar i; 
        for(i=0; i<LINE_BYTES; i=i+1)
            assign line[i*8+7: i*8] = data[i];
    endgenerate

endmodule



/*
    32 lines x 16 bytes Direct Mapped Cache
*/
`ifdef NO_HC_CACHE

module DMC_32x16 (
`ifdef USE_POWER_PINS
    input VPWR,
    input VGND,
`endif
    input wire          clk,
    input wire          rst_n,
    // 
    input wire  [23:0]  A,
    input wire  [23:0]  A_h,
    output wire [31:0]  Do,
    output wire         hit,
    //
    input wire [127:0]  line,
    input wire          wr
);

    //
    reg [127:0] LINES   [31:0];
    reg [14:0]  TAGS    [31:0];
    reg         VALID   [31:0];

    wire [3:0]  offset  = A[3:0];
    wire [4:0]  index   = A[8:4];
    wire [14:0] tag     = A[23:9];

    wire [4:0]  index_h   = A_h[8:4];
    wire [14:0] tag_h     = A_h[23:9];

    
    assign  hit =   VALID[index_h] & (TAGS[index_h] == tag_h);

    assign  Do  =   (offset[3:2] == 2'd0) ?  LINES[index][31:0] :
                    (offset[3:2] == 2'd1) ?  LINES[index][63:32] :
                    (offset[3:2] == 2'd2) ?  LINES[index][95:64] :
                    LINES[index][127:96];

    // clear the VALID flags
    integer i;
    always @ (posedge clk or negedge rst_n)
        if(!rst_n) 
            for(i=0; i<32; i=i+1)
                VALID[i] <= 1'b0;
        else  if(wr)  VALID[index]    <= 1'b1;

    always @(posedge clk)
        if(wr) begin
            LINES[index]    <= line;
            TAGS[index]     <= tag;
        end

endmodule
`endif
