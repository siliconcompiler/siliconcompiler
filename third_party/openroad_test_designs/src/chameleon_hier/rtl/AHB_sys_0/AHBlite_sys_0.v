
`timescale 1ns/1ns

//`define DBG
module AHBlite_sys_0(
`ifdef USE_POWER_PINS
		input VPWR,
		input VGND,
`endif
		input HCLK,
		input HRESETn,
     
		input [31: 0] HADDR,
		input [31: 0] HWDATA,
		input HWRITE,
		input [1: 0] HTRANS,
		input [2:0] HSIZE,

		output HREADY,
		output [31: 0] HRDATA,

		input wire [3: 0] fdi_S0,
		output wire [3: 0] fdo_S0,
		output wire [0: 0] fdoe_S0,
		output wire [0: 0] fsclk_S0,
		output wire [0: 0] fcen_S0,
		input wire [31: 0] SRAMRDATA_S1,
		output wire [3: 0] SRAMWEN_S1,
		output wire [31: 0] SRAMWDATA_S1,
		output wire [0: 0] SRAMCS0_S1,
		//output wire [0: 0] SRAMCS1_S1,
		//output wire [0: 0] SRAMCS2_S1,
		//output wire [0: 0] SRAMCS3_S1,
		output wire [11: 0] SRAMADDR_S1,
		input wire [15: 0] GPIOIN_S2,
		output wire [15: 0] GPIOOUT_S2,
		output wire [15: 0] GPIOPU_S2,
		output wire [15: 0] GPIOPD_S2,
		output wire [15: 0] GPIOOEN_S2,
		output wire [3:0] db_reg,
		input wire [0: 0] RsRx_SS0_S0,
		output wire [0: 0] RsTx_SS0_S0,
		output wire [0: 0] uart_irq_SS0_S0,
		input wire [0: 0] RsRx_SS0_S1,
		output wire [0: 0] RsTx_SS0_S1,
		output wire [0: 0] uart_irq_SS0_S1,
		input wire [0: 0] MSI_SS0_S2,
		output wire [0: 0] MSO_SS0_S2,
		output wire [0: 0] SSn_SS0_S2,
		output wire [0: 0] SCLK_SS0_S2,
		input wire [0: 0] MSI_SS0_S3,
		output wire [0: 0] MSO_SS0_S3,
		output wire [0: 0] SSn_SS0_S3,
		output wire [0: 0] SCLK_SS0_S3,
		input wire [0: 0] scl_i_SS0_S4,
		output wire [0: 0] scl_o_SS0_S4,
		output wire [0: 0] scl_oen_o_SS0_S4,
		input wire [0: 0] sda_i_SS0_S4,
		output wire [0: 0] sda_o_SS0_S4,
		output wire [0: 0] sda_oen_o_SS0_S4,
		input wire [0: 0] scl_i_SS0_S5,
		output wire [0: 0] scl_o_SS0_S5,
		output wire [0: 0] scl_oen_o_SS0_S5,
		input wire [0: 0] sda_i_SS0_S5,
		output wire [0: 0] sda_o_SS0_S5,
		output wire [0: 0] sda_oen_o_SS0_S5,
		output wire [0: 0] pwm_SS0_S6,
		output wire [0: 0] pwm_SS0_S7,

		output wire [31:0] IRQ
	);
        
		//assign IRQ[15:0] = 0;

        //Inputs
        wire HSEL_S0, HSEL_S1, HSEL_S2, HSEL_S3, HSEL_S4, HSEL_SS0;

        //Outputs
        wire    [31:0]   HRDATA_S0, HRDATA_S1, HRDATA_S2, HRDATA_S3, HRDATA_S4, HRDATA_SS0, HRDATA;
        wire             HREADY_S0, HREADY_S1, HREADY_S2, HREADY_S3, HREADY_S4, HREADY_SS0, HREADY;
        wire  [1:0]   HRESP;
       // wire          IRQ;
        
		wire [15: 0] WGPIODIN_S2;
		wire [15: 0] WGPIODOUT_S2;
		wire [15: 0] WGPIOPU_S2;
		wire [15: 0] WGPIOPD_S2;
		wire [15: 0] WGPIODIR_S2;

	//Digital module # 0
	QSPI_XIP_CTRL S0 ( 
	`ifdef USE_POWER_PINS
		.VPWR(VPWR),
		.VGND(VGND),
	`endif
		.HCLK(HCLK),
		.HRESETn(HRESETn),
		.HSEL(HSEL_S0),
		.HADDR(HADDR),
		.HREADY(HREADY),
		.HWRITE(HWRITE),
		.HTRANS(HTRANS),
		//.HSIZE(HSIZE),
		.HRDATA(HRDATA_S0),
		.HREADYOUT(HREADY_S0),
		.din(fdi_S0),
		.dout(fdo_S0),
		.douten(fdoe_S0),
		.sck(fsclk_S0),
		.ce_n(fcen_S0)
	);

		
	//Digital module # 1
	AHBSRAM S1 ( 
		.HCLK(HCLK),
		.HRESETn(HRESETn),
		.HSEL(HSEL_S1),
		.HADDR(HADDR),
		.HREADY(HREADY),
		.HWRITE(HWRITE),
		.HTRANS(HTRANS),
		.HSIZE(HSIZE),
		.HWDATA(HWDATA),
		.HRDATA(HRDATA_S1),
		.HREADYOUT(HREADY_S1),
		.SRAMRDATA(SRAMRDATA_S1),
		.SRAMWEN(SRAMWEN_S1),
		.SRAMWDATA(SRAMWDATA_S1),
		.SRAMCS0(SRAMCS0_S1),
		//.SRAMCS1(SRAMCS1_S1),
		//.SRAMCS2(SRAMCS2_S1),
		//.SRAMCS3(SRAMCS3_S1),
		.SRAMADDR(SRAMADDR_S1)
	);
		
	//Digital module # 2
	GPIO S2 ( 
		.WGPIODIN(WGPIODIN_S2),
		.WGPIODOUT(WGPIODOUT_S2),
		.WGPIOPU(WGPIOPU_S2),
		.WGPIOPD(WGPIOPD_S2),
		.WGPIODIR(WGPIODIR_S2),
		.GPIOIN(GPIOIN_S2),
		.GPIOOUT(GPIOOUT_S2),
		.GPIOPU(GPIOPU_S2),
		.GPIOPD(GPIOPD_S2),
		.GPIOOEN(GPIOOEN_S2)
	);
		
	//AHB Slave # 2
	AHBlite_GPIO S_2 (
		.HCLK(HCLK),
		.HRESETn(HRESETn),
		.HSEL(HSEL_S2),
		.HADDR(HADDR[23:2]),
		.HREADY(HREADY),
		.HWRITE(HWRITE),
		.HTRANS(HTRANS),
		.HSIZE(HSIZE),
		.HWDATA(HWDATA),

		.WGPIODIN(WGPIODIN_S2),
		.WGPIODOUT(WGPIODOUT_S2),
		.WGPIOPU(WGPIOPU_S2),
		.WGPIOPD(WGPIOPD_S2),
		.WGPIODIR(WGPIODIR_S2),
		.HRDATA(HRDATA_S2),
		.HREADYOUT(HREADY_S2),
		.HRESP(HRESP), 

		.IRQ(IRQ[15:0])
	);
			
	//AHB Slave # 3
/*	
	AHBlite_db_reg S_3 (
		.HCLK(HCLK),
		.HRESETn(HRESETn),
		.HSEL(HSEL_S3),
		.HADDR(HADDR[23:2]),
		.HREADY(HREADY),
		.HWRITE(HWRITE),
		.HTRANS(HTRANS),
		.HSIZE(HSIZE),
		.HWDATA(HWDATA),
		.db_reg(db_reg),

		.HRDATA(HRDATA_S3),
		.HREADYOUT(HREADY_S3),
		.HRESP(HRESP)
	);
*/

	AHB_SPM S_3 (
		.HCLK(HCLK),
		.HRESETn(HRESETn),
		.HSEL(HSEL_S3),
		.HADDR(HADDR),
		.HREADY(HREADY),
		.HWRITE(HWRITE),
		.HTRANS(HTRANS),
		.HSIZE(HSIZE),
		.HWDATA(HWDATA),
		//.db_reg(db_reg),

		.HRDATA(HRDATA_S3),
		.HREADYOUT(HREADY_S3),
		.HRESP(HRESP)
	);		


	// SLAVE 4
	assign HREADY_S4 = 1;


	//AHB Bus
	AHBlite_BUS0 AHB(
		.HCLK(HCLK),
		.HRESETn(HRESETn),
		
		// Master Interface
		.HADDR(HADDR),
		.HWDATA(HWDATA), 
		.HREADY(HREADY),
		.HRDATA(HRDATA),
		
		// Slave # 0
		.HSEL_S0(HSEL_S0),
		.HREADY_S0(HREADY_S0),
		.HRDATA_S0(HRDATA_S0),
		
		// Slave # 1
		.HSEL_S1(HSEL_S1),
		.HREADY_S1(HREADY_S1),
		.HRDATA_S1(HRDATA_S1),
		
		// Slave # 2
		.HSEL_S2(HSEL_S2),
		.HREADY_S2(HREADY_S2),
		.HRDATA_S2(HRDATA_S2),
		
		// Slave # 3
		.HSEL_S3(HSEL_S3),
		.HREADY_S3(HREADY_S3),
		.HRDATA_S3(HRDATA_S3),
		
		// Slave # 4
		.HSEL_S4(HSEL_S4),
		.HREADY_S4(HREADY_S4),
		.HRDATA_S4(HRDATA_S4),

		// Subsystem # 0
		.HSEL_SS0(HSEL_SS0),
		.HREADY_SS0(HREADY_SS0),
		.HRDATA_SS0(HRDATA_SS0)
	);

    //SubSystem Instantiation #0 
    apb_sys_0 apb_sys_inst_0(
    `ifdef USE_POWER_PINS
	.VPWR(VPWR),
	.VGND(VGND),
    `endif
        // Global signals 
        .HCLK(HCLK),
        .HRESETn(HRESETn),
    
        // AHB Slave inputs 
        .HADDR(HADDR),
        .HTRANS(HTRANS),
        .HWRITE(HWRITE),
        .HWDATA(HWDATA),
        .HSEL(HSEL_SS0),
        .HREADY(HREADY),
    
        // AHB Slave outputs 
        .HRDATA(HRDATA_SS0),
        .HREADYOUT(HREADY_SS0),
		.RsRx_S0(RsRx_SS0_S0),
		.RsTx_S0(RsTx_SS0_S0),

		.RsRx_S1(RsRx_SS0_S1),
		.RsTx_S1(RsTx_SS0_S1),

		.MSI_S2(MSI_SS0_S2),
		.MSO_S2(MSO_SS0_S2),
		.SSn_S2(SSn_SS0_S2),
		.SCLK_S2(SCLK_SS0_S2),

		.MSI_S3(MSI_SS0_S3),
		.MSO_S3(MSO_SS0_S3),
		.SSn_S3(SSn_SS0_S3),
		.SCLK_S3(SCLK_SS0_S3),

		.scl_i_S4(scl_i_SS0_S4),
		.scl_o_S4(scl_o_SS0_S4),
		.scl_oen_o_S4(scl_oen_o_SS0_S4),
		.sda_i_S4(sda_i_SS0_S4),
		.sda_o_S4(sda_o_SS0_S4),
		.sda_oen_o_S4(sda_oen_o_SS0_S4),

		.scl_i_S5(scl_i_SS0_S5),
		.scl_o_S5(scl_o_SS0_S5),
		.scl_oen_o_S5(scl_oen_o_SS0_S5),
		.sda_i_S5(sda_i_SS0_S5),
		.sda_o_S5(sda_o_SS0_S5),
		.sda_oen_o_S5(sda_oen_o_SS0_S5),

		.pwm_S6(pwm_SS0_S6),
		.pwm_S7(pwm_SS0_S7),

		.IRQ(IRQ[31:16])
    );
`ifdef DBG
    always @(posedge HCLK)
	if(HTRANS[1] & HREADY)
        $display("Mem request (%d) A:%X", HWRITE, HADDR);
`endif
    endmodule
        
