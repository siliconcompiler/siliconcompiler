/*
        APB Wrapper for TIMER32 macro 
        Automatically generated from a JSON description by Mohamed Shalan
        Generated at 2020-11-26 12:31:7 
*/

`timescale 1ns/1ns
   
module APB_TIMER32 (
	// APB Interface
	// clock and reset 
	input  wire        PCLK,    
	//input  wire        PCLKG,   // Gated clock
	input  wire        PRESETn, // Reset

	// input ports
	input  wire        PSEL,    // Select
	input  wire [19:2] PADDR,   // Address
	input  wire        PENABLE, // Transfer control
	input  wire        PWRITE,  // Write control
	input  wire [31:0] PWDATA,  // Write data

	// output ports
	output wire [31:0] PRDATA,  // Read data
	output wire        PREADY,
	// Device ready

	// IP Interface
	output		IRQ,

	// TMR register/fields
	input [31:0] TMR,


	// PRE register/fields
	output [31:0] PRE,


	// TMRCMP register/fields
	output [31:0] TMRCMP,


	// TMROV register/fields
	input [0:0] TMROV,


	// TMROVCLR register/fields
	output [0:0] TMROVCLR,


	// TMREN register/fields
	output [0:0] TMREN

);
	wire rd_enable;
	wire wr_enable;
	assign  rd_enable = PSEL & (~PWRITE); 
	assign  wr_enable = PSEL & PWRITE & (PENABLE); 
	assign  PREADY = 1'b1;
    

    reg [31:0] PRE;

    reg [31:0] TMRCMP;

    reg [0:0] TMROVCLR;

    reg [0:0] TMREN;

    wire[31:0] TMR;
    wire[0:0] TMROV;

	// Register: PRE
	wire PRE_select = wr_enable & (PADDR[19:2] == 18'h1);

    always @(posedge PCLK or negedge PRESETn)
    begin
        if (~PRESETn)
            PRE <= 32'h0;
        else if (PRE_select)
            PRE <= PWDATA;
    end
    
	// Register: TMRCMP
	wire TMRCMP_select = wr_enable & (PADDR[19:2] == 18'h2);

    always @(posedge PCLK or negedge PRESETn)
    begin
        if (~PRESETn)
            TMRCMP <= 32'h0;
        else if (TMRCMP_select)
            TMRCMP <= PWDATA;
    end
    
	// Register: TMROVCLR
	wire TMROVCLR_select = wr_enable & (PADDR[19:2] == 18'h4);

    always @(posedge PCLK or negedge PRESETn)
    begin
        if (~PRESETn)
            TMROVCLR <= 1'h0;
        else if (TMROVCLR_select)
            TMROVCLR <= PWDATA;
    end
    
	// Register: TMREN
	wire TMREN_select = wr_enable & (PADDR[19:2] == 18'h5);

    always @(posedge PCLK or negedge PRESETn)
    begin
        if (~PRESETn)
            TMREN <= 1'h0;
        else if (TMREN_select)
            TMREN <= PWDATA;
    end
    

	// IRQ Enable Register @ offset 0x100
	reg[0:0] IRQEN;
	wire IRQEN_select = wr_enable & (PADDR[19:2] == 18'h40);

    always @(posedge PCLK or negedge PRESETn)
    begin
        if (~PRESETn)
            IRQEN <= 1'h0;
        else if (IRQEN_select)
            IRQEN <= PWDATA;
    end
    
	assign IRQ = ( TMROV & IRQEN[0] ) ;

	assign PRDATA = 
		(PADDR[19:2] == 18'h0) ? TMR : 
		(PADDR[19:2] == 18'h1) ? PRE : 
		(PADDR[19:2] == 18'h2) ? TMRCMP : 
		(PADDR[19:2] == 18'h3) ? {31'd0,TMROV} : 
		(PADDR[19:2] == 18'h4) ? {31'd0,TMROVCLR} : 
		(PADDR[19:2] == 18'h5) ? {31'd0,TMREN} : 
		(PADDR[19:2] == 18'h40) ? {31'd0,IRQEN} : 
		32'hDEADBEEF;

endmodule