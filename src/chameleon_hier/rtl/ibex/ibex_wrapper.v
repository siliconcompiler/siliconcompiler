module ibex_wrapper
  (
 `ifdef USE_POWER_PINS
	input VPWR,
	input VGND,
`endif
    input  wire         HCLK,							// System clock
    input  wire         HRESETn,						// System Reset, active low

    // AHB-LITE MASTER PORT for Instructions
    output wire [31:0]  HADDR,				// AHB transaction address
    output wire [ 2:0]  HSIZE,				// AHB size: byte, half-word or word
    output wire [ 1:0]  HTRANS,				// AHB transfer: non-sequential only
    output wire [31:0]  HWDATA,				// AHB write-data
    output wire         HWRITE,				// AHB write control
    input  wire [31:0]  HRDATA,				// AHB read-data
    input  wire         HREADY,				// AHB stall signal

    // MISCELLANEOUS 
    input  wire         NMI,				// Non-maskable interrupt input
    input  wire         EXT_IRQ,				// Interrupt request line
    input wire [14:0]   IRQ, 
    input  wire [23:0]	SYSTICKCLKDIV

);
  
  wire dpower = 1'b1;
  wire dground = 1'b0;

  reg [1:0] addr_offset;
  
  wire alert_minor_o;
  wire alert_major_o;
  wire core_sleep_o;

  reg [2:0] data_hsize;
  reg [1:0] data_addr_off;

  wire [31:0] instr_wdata_o;
  wire [31:0] instr_addr_o;
  wire [31:0] instr_rdata_i;
  wire instr_rvalid_i;
  wire instr_req_o;
  wire instr_gnt_i;

  wire [3:0] data_be_o;
  wire [31:0] data_wdata_o;
  wire [31:0] data_addr_o;
  wire [31:0] data_rdata_i;
  wire data_rvalid_i;
  wire data_req_o;
  wire data_gnt_i;
  wire data_we_o;
  

  /* SYSTICK */
  wire div;
	reg  [23:0]  clkdiv;
	reg 		systickclk;
  assign div = (clkdiv == SYSTICKCLKDIV);

  always @(posedge HCLK or negedge HRESETn)
    if(!HRESETn) clkdiv <= 24'd0;
		else if(div) 
				clkdiv <= 24'h0;
			else
				clkdiv <= clkdiv + 24'h1; 

  always @(posedge HCLK or negedge HRESETn)
    if(!HRESETn) systickclk <= 1'b1;
		else if(div) 
				systickclk <= 1'b1;
			else
				systickclk <= 1'b0;	 


  ibex_core core (
    // Clock and Reset
    .clk_i(HCLK),
    .rst_ni(HRESETn),

    .test_en_i(dground),     // enable all clock gates for testing

    .hart_id_i(32'b0),  //???
    .boot_addr_i(32'b0), //???

    // Instruction memory interface
    .instr_req_o(instr_req_o),
    .instr_gnt_i(instr_gnt_i),
    .instr_rvalid_i(instr_rvalid_i),
    .instr_addr_o(instr_addr_o),
    .instr_rdata_i(instr_rdata_i),
    .instr_err_i(dground),

    // Data memory interface
    .data_req_o(data_req_o),
    .data_gnt_i(data_gnt_i),
    .data_rvalid_i(data_rvalid_i),
    .data_we_o(data_we_o),
    .data_be_o(data_be_o),
    .data_addr_o(data_addr_o),
    .data_wdata_o(data_wdata_o),
    .data_rdata_i(data_rdata_i),
    .data_err_i(dground),

    // Interrupt inputs
     .irq_software_i(dground),
     .irq_timer_i(systickclk),
     .irq_external_i(EXT_IRQ),
     .irq_fast_i(IRQ),
     .irq_nm_i(NMI),       // non-maskeable interrupt

    // Debug Interface
     .debug_req_i(dground),

    // CPU Control Signals
    .fetch_enable_i(dpower),
    .alert_minor_o(alert_minor_o),
    .alert_major_o(alert_major_o),
    .core_sleep_o(core_sleep_o)
);


  reg [4:0] state, nstate;
  localparam [4:0] S0 = 1;
  localparam [4:0] S1 = 2;
  localparam [4:0] S2 = 4;
  localparam [4:0] S3 = 8;
  localparam [4:0] S4 = 16;

  always @(posedge HCLK or negedge HRESETn)
    if(!HRESETn) state <= S0;
    else state <= nstate;

  always @* begin
      nstate = S0;
    case (state)
      S0  : if(data_req_o) nstate = S3; else if(instr_req_o) nstate = S1; else nstate = S0;
      S1  : nstate = S2;
      S2  : if(instr_rvalid_i) nstate = S0; else nstate = S2;
      S3  : nstate = S4;
      S4  : if(data_rvalid_i) nstate = S0; else nstate = S4;
    endcase
  end

    assign instr_gnt_i = (state == S1);
    assign instr_rvalid_i = (state == S2) ? HREADY : 0;

    assign data_gnt_i = (state == S3);
    assign data_rvalid_i = (state == S4) ? HREADY : 0;
    

    assign HADDR =  (state == S1) ? instr_addr_o  : 
                    (state == S3) ? {data_addr_o | data_addr_off}  :   32'b0;
                  
    assign HTRANS = (state == S1) ? 2'b10 : 
                    (state == S3) ? 2'b10 : 2'b00;

    assign HSIZE =  (state == S1) ? 3'b010 : 
                    (state == S3) ? data_hsize : 3'b0;

    assign HWRITE = (state == S3) ? data_we_o : 0 ; 

    assign HWDATA = data_wdata_o;
                    

    assign instr_rdata_i = HRDATA;
    assign data_rdata_i = HRDATA;

          
    always @* begin
      data_hsize = 3'b0;
      case(data_be_o)
        4'b0001 : data_hsize = 3'b000;
        4'b0010 : data_hsize = 3'b000;
        4'b0100 : data_hsize = 3'b000;
        4'b1000 : data_hsize = 3'b000;
        4'b0011 : data_hsize = 3'b001;
        4'b1100 : data_hsize = 3'b001;
        4'b1111 : data_hsize = 3'b010;
      endcase
    end 

    always @* begin
      data_addr_off = 2'b0;
      case(data_be_o)
        4'b0001 : data_addr_off = 2'b00;
        4'b0010 : data_addr_off = 2'b01;
        4'b0100 : data_addr_off = 2'b10;
        4'b1000 : data_addr_off = 2'b11;
        4'b0011 : data_addr_off = 2'b00;
        4'b1100 : data_addr_off = 2'b10;
        4'b1111 : data_addr_off = 2'b00;
      endcase
    end 

    
endmodule
  
