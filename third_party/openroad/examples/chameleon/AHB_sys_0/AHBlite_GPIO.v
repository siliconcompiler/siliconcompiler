`timescale 1ns/1ns
    module AHBlite_GPIO (
    // AHB Interface
    // clock and reset 
    input  wire        HCLK,    
    //input  wire        HCLKG,   // Gated clock
    input  wire        HRESETn, // Reset

    // input ports
    input   wire        HSEL,    // Select
    input   wire [23:2] HADDR,   // Address
    input   wire        HREADY, // 
    input   wire        HWRITE,  // Write control
    input   wire [1:0]  HTRANS,    // AHB transfer type
    input   wire [2:0]  HSIZE,    // AHB hsize
    input   wire [31:0] HWDATA,  // Write data

    // output ports
    output wire [31:0] HRDATA,  // Read data
    output wire        HREADYOUT,  // Device ready
    output wire [1:0]   HRESP,

    output wire [15:0] IRQ,
	
    // IP Interface
	// WGPIODIN register/fields
	input [15:0] WGPIODIN,
	// WGPIODOUT register/fields
	output [15:0] WGPIODOUT,
	// WGPIOPU register/fields
	output [15:0] WGPIOPU,
	// WGPIOPD register/fields
	output [15:0] WGPIOPD,
	// WGPIODIR register/fields
	output [15:0] WGPIODIR
);
    reg         IOSEL;
    reg [23:0]  IOADDR;
    reg         IOWRITE;    // I/O transfer direction
    reg [2:0]   IOSIZE;     // I/O transfer size
    reg         IOTRANS;

    // registered HSEL, update only if selected to reduce toggling
    always @(posedge HCLK or negedge HRESETn) begin
        if (~HRESETn)
            IOSEL <= 1'b0;
        else
            IOSEL <= HSEL & HREADY;
    end
    
    // registered address, update only if selected to reduce toggling
    always @(posedge HCLK or negedge HRESETn) begin
        if (~HRESETn)
            IOADDR <= 24'd0;
        else
            IOADDR <= {HADDR[23:2], 2'b0};
    end

    // Data phase write control
    always @(posedge HCLK or negedge HRESETn)
    begin
      if (~HRESETn)
        IOWRITE <= 1'b0;
      else
        IOWRITE <= HWRITE;
    end
  
    // registered hsize, update only if selected to reduce toggling
    always @(posedge HCLK or negedge HRESETn)
    begin
      if (~HRESETn)
        IOSIZE <= {3{1'b0}};
      else
        IOSIZE <= HSIZE[2:0];
    end
  
    // registered HTRANS, update only if selected to reduce toggling
    always @(posedge HCLK or negedge HRESETn)
    begin
      if (~HRESETn)
        IOTRANS <= 1'b0;
      else
        IOTRANS <= HTRANS[1];
    end
    
    wire rd_enable;
    assign  rd_enable = IOSEL & (~IOWRITE) & IOTRANS; 
    wire wr_enable = IOTRANS & IOWRITE & IOSEL;
    

    reg [15:0] WGPIODOUT;
    reg [15:0] WGPIOPU;
    reg [15:0] WGPIOPD;
    reg [15:0] WGPIODIR;
    reg [15:0] WGPIOIM;
    wire[15:0] WGPIODIN;

	// Register: WGPIODOUT
    wire WGPIODOUT_select = wr_enable & (IOADDR[23:2] == 22'h1);
    
    always @(posedge HCLK or negedge HRESETn)
    begin
        if (~HRESETn)
            WGPIODOUT <= 16'h0;
        else if (WGPIODOUT_select)
            WGPIODOUT <= HWDATA;
    end
    
	// Register: WGPIOPU
    wire WGPIOPU_select = wr_enable & (IOADDR[23:2] == 22'h2);
    
    always @(posedge HCLK or negedge HRESETn)
    begin
        if (~HRESETn)
            WGPIOPU <= 16'h0;
        else if (WGPIOPU_select)
            WGPIOPU <= HWDATA;
    end
    
	// Register: WGPIOPD
    wire WGPIOPD_select = wr_enable & (IOADDR[23:2] == 22'h3);
    
    always @(posedge HCLK or negedge HRESETn)
    begin
        if (~HRESETn)
            WGPIOPD <= 16'h0;
        else if (WGPIOPD_select)
            WGPIOPD <= HWDATA;
    end
    
	// Register: WGPIODIR
    wire WGPIODIR_select = wr_enable & (IOADDR[23:2] == 22'h4);
    
    always @(posedge HCLK or negedge HRESETn)
    begin
        if (~HRESETn)
            WGPIODIR <= 16'h0;
        else if (WGPIODIR_select)
            WGPIODIR <= HWDATA;
    end
    
    // Register: IM
    wire WGPIOIM_select = wr_enable & (IOADDR[23:2] == 22'h5);
    
    always @(posedge HCLK or negedge HRESETn)
    begin
        if (~HRESETn)
            WGPIOIM <= 16'h0;
        else if (WGPIOIM_select)
            WGPIOIM <= HWDATA;
    end
    
    assign IRQ = (~WGPIODIR) & WGPIOIM;

    assign HRDATA = 
      	(IOADDR[23:2] == 22'h0) ? {16'd0,WGPIODIN} : 
      	(IOADDR[23:2] == 22'h1) ? {16'd0,WGPIODOUT} : 
      	(IOADDR[23:2] == 22'h2) ? {16'd0,WGPIOPU} : 
      	(IOADDR[23:2] == 22'h3) ? {16'd0,WGPIOPD} : 
      	(IOADDR[23:2] == 22'h4) ? {16'd0,WGPIODIR} :
        (IOADDR[23:2] == 22'h5) ? {16'd0,WGPIOIM} : 
	32'hDEADBEEF;
	assign HREADYOUT = 1'b1;     // Always ready

endmodule