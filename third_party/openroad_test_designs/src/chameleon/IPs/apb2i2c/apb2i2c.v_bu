module APB_I2C(
    //APB Inputs
    input wire PCLK,
    input wire PRESETn,
    input wire PWRITE,
    input wire [31:0] PWDATA,
    input wire [31:0] PADDR,
    input wire PENABLE,
    
    input PSEL,
    
    //APB Outputs
    output wire PREADY,
    output wire [31:0] PRDATA,

    // i2c Ports
    input 	wire scl_i,	    // SCL-line input
	output 	wire scl_o,	    // SCL-line output (always 1'b0)
	output 	wire scl_oen_o, // SCL-line output enable (active low)
	input	wire sda_i,     // SDA-line input
	output	wire sda_o,	    // SDA-line output (always 1'b0)
	output	wire sda_oen_o // SDA-line output enable (active low)
    
);

  assign PREADY = 1'b1; //always ready
  
  wire[7:0] io_do;
  wire io_we = PENABLE & PWRITE & PREADY & PSEL;
  wire io_re = PENABLE & ~PWRITE & PREADY & PSEL;

  wire i2c_irq;
  
  i2c_master i2c (
    		.sys_clk(PCLK),
    		.sys_rst(~PRESETn),
    		//
    		.io_a(PADDR[7:2]),
		    .io_di(PWDATA[7:0]),
			.io_do(io_do),
			.io_re(io_re),
			.io_we(io_we),
			//
			.i2c_irq(i2c_irq),
			//
			.scl_i(scl_i),	   // SCL-line input
			.scl_o(scl_o),	   // SCL-line output (always 1'b0)
			.scl_oen_o(scl_oen_o), // SCL-line output enable (active low)
			.sda_i(sda_i),		// SDA-line input
			.sda_o(sda_o),	   // SDA-line output (always 1'b0)
			.sda_oen_o(sda_oen_o)  // SDA-line output enable (active low)
	);
  
  assign PRDATA[31:0] = io_do;//I2C_DATA_REG;
  
endmodule
