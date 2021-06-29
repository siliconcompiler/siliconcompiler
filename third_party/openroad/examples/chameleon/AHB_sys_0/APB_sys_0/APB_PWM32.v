/*
        APB Wrapper for PWM32 macro 
        Automatically generated from a JSON description by Mohamed Shalan
        Generated at 2020-11-26 12:31:7 
*/

`timescale 1ns/1ns
   
module APB_PWM32 (
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
	// PRE register/fields
	output [31:0] PRE,


	// TMRCMP1 register/fields
	output [31:0] TMRCMP1,


	// TMRCMP2 register/fields
	output [31:0] TMRCMP2,


	// TMREN register/fields
	output [0:0] TMREN

);
	wire rd_enable;
	wire wr_enable;
	assign  rd_enable = PSEL & (~PWRITE); 
	assign  wr_enable = PSEL & PWRITE & (PENABLE); 
	assign  PREADY = 1'b1;
    

    reg [31:0] PRE;

    reg [31:0] TMRCMP1;

    reg [31:0] TMRCMP2;

    reg [0:0] TMREN;


	// Register: PRE
	wire PRE_select = wr_enable & (PADDR[19:2] == 18'h4);

    always @(posedge PCLK or negedge PRESETn)
    begin
        if (~PRESETn)
            PRE <= 32'h0;
        else if (PRE_select)
            PRE <= PWDATA;
    end
    
	// Register: TMRCMP1
	wire TMRCMP1_select = wr_enable & (PADDR[19:2] == 18'h1);

    always @(posedge PCLK or negedge PRESETn)
    begin
        if (~PRESETn)
            TMRCMP1 <= 32'h0;
        else if (TMRCMP1_select)
            TMRCMP1 <= PWDATA;
    end
    
	// Register: TMRCMP2
	wire TMRCMP2_select = wr_enable & (PADDR[19:2] == 18'h2);

    always @(posedge PCLK or negedge PRESETn)
    begin
        if (~PRESETn)
            TMRCMP2 <= 32'h0;
        else if (TMRCMP2_select)
            TMRCMP2 <= PWDATA;
    end
    
	// Register: TMREN
	wire TMREN_select = wr_enable & (PADDR[19:2] == 18'h8);

    always @(posedge PCLK or negedge PRESETn)
    begin
        if (~PRESETn)
            TMREN <= 1'h0;
        else if (TMREN_select)
            TMREN <= PWDATA;
    end
    
	assign PRDATA = 
		(PADDR[19:2] == 18'h4) ? PRE : 
		(PADDR[19:2] == 18'h1) ? TMRCMP1 : 
		(PADDR[19:2] == 18'h2) ? TMRCMP2 : 
		(PADDR[19:2] == 18'h8) ? {31'd0,TMREN} : 
		32'hDEADBEEF;

endmodule