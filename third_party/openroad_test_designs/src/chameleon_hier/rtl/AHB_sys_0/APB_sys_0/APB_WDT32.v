/*
        APB Wrapper for WDT32 macro 
        Automatically generated from a JSON description by Mohamed Shalan
        Generated at 2020-11-26 12:31:7 
*/

`timescale 1ns/1ns
   
module APB_WDT32 (
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

	// WDTMR register/fields
	input [31:0] WDTMR,


	// WDLOAD register/fields
	output [31:0] WDLOAD,


	// WDOV register/fields
	input [0:0] WDOV,


	// WDOVCLR register/fields
	output [0:0] WDOVCLR,


	// WDEN register/fields
	output [0:0] WDEN

);
	wire rd_enable;
	wire wr_enable;
	assign  rd_enable = PSEL & (~PWRITE); 
	assign  wr_enable = PSEL & PWRITE & (PENABLE); 
	assign  PREADY = 1'b1;
    

    reg [31:0] WDLOAD;

    reg [0:0] WDOVCLR;

    reg [0:0] WDEN;

    wire[31:0] WDTMR;
    wire[0:0] WDOV;

	// Register: WDLOAD
	wire WDLOAD_select = wr_enable & (PADDR[19:2] == 18'h1);

    always @(posedge PCLK or negedge PRESETn)
    begin
        if (~PRESETn)
            WDLOAD <= 32'h0;
        else if (WDLOAD_select)
            WDLOAD <= PWDATA;
    end
    
	// Register: WDOVCLR
	wire WDOVCLR_select = wr_enable & (PADDR[19:2] == 18'h4);

    always @(posedge PCLK or negedge PRESETn)
    begin
        if (~PRESETn)
            WDOVCLR <= 1'h0;
        else if (WDOVCLR_select)
            WDOVCLR <= PWDATA;
    end
    
	// Register: WDEN
	wire WDEN_select = wr_enable & (PADDR[19:2] == 18'h5);

    always @(posedge PCLK or negedge PRESETn)
    begin
        if (~PRESETn)
            WDEN <= 1'h0;
        else if (WDEN_select)
            WDEN <= PWDATA;
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
    
	assign IRQ = ( WDOV & IRQEN[0] ) ;

	assign PRDATA = 
		(PADDR[19:2] == 18'h0) ? WDTMR : 
		(PADDR[19:2] == 18'h1) ? WDLOAD : 
		(PADDR[19:2] == 18'h3) ? {31'd0,WDOV} : 
		(PADDR[19:2] == 18'h4) ? {31'd0,WDOVCLR} : 
		(PADDR[19:2] == 18'h5) ? {31'd0,WDEN} : 
		(PADDR[19:2] == 18'h40) ? {31'd0,IRQEN} : 
		32'hDEADBEEF;

endmodule