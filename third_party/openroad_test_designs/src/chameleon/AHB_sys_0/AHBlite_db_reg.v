`timescale 1ns/1ns
    module AHBlite_db_reg (
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
		// IP Interface
	// db_reg register/fields
	output [3:0] db_reg


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
            IOADDR <= HADDR[23:0];
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
    

    reg [3:0] db_reg;


	// Register: db_reg
    wire db_reg_select = wr_enable & (IOADDR[23:2] == 20'h0);
    
    always @(posedge HCLK or negedge HRESETn)
    begin
        if (~HRESETn)
            db_reg <= 4'h0;
        else if (db_reg_select)
            db_reg <= HWDATA;
    end
    
    assign HRDATA = 
      	(IOADDR[23:2] == 22'h0) ? {28'd0,db_reg} : 
	32'hDEADBEEF;
	assign HREADYOUT = 1'b1;     // Always ready

endmodule