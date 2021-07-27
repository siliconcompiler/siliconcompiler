
`timescale 1ns/1ns
module apb_sys_0(
`ifdef USE_POWER_PINS
    input VPWR,
    input VGND,
`endif
    // Global signals 
    input wire          HCLK,
    input wire          HRESETn,

    // AHB Slave inputs 
    input wire  [31:0]  HADDR,
    input wire  [1:0]   HTRANS,
    input wire          HWRITE,
    input wire  [31:0]  HWDATA,
    input wire          HSEL,
    input wire          HREADY,

    // AHB Slave outputs 
    output wire [31:0]  HRDATA,
    output wire         HREADYOUT,
	input wire [0: 0] RsRx_S0,
	output wire [0: 0] RsTx_S0,

	input wire [0: 0] RsRx_S1,
	output wire [0: 0] RsTx_S1,

	input wire [0: 0] MSI_S2,
	output wire [0: 0] MSO_S2,
	output wire [0: 0] SSn_S2,
	output wire [0: 0] SCLK_S2,

	input wire [0: 0] MSI_S3,
	output wire [0: 0] MSO_S3,
	output wire [0: 0] SSn_S3,
	output wire [0: 0] SCLK_S3,

	input wire [0: 0] scl_i_S4,
	output wire [0: 0] scl_o_S4,
	output wire [0: 0] scl_oen_o_S4,
	input wire [0: 0] sda_i_S4,
	output wire [0: 0] sda_o_S4,
	output wire [0: 0] sda_oen_o_S4,

	input wire [0: 0] scl_i_S5,
	output wire [0: 0] scl_o_S5,
	output wire [0: 0] scl_oen_o_S5,
	input wire [0: 0] sda_i_S5,
	output wire [0: 0] sda_o_S5,
	output wire [0: 0] sda_oen_o_S5,

	output wire [0: 0] pwm_S6,
	output wire [0: 0] pwm_S7,

    output [15:0] IRQ
);
    
    // APB Master Signals
    wire PCLK;
    wire PRESETn;
    wire [31:0] PADDR;
    wire PWRITE;
    wire [31:0] PWDATA;
    wire PENABLE;
    
    // APB Slave Signals
    wire PREADY;
    wire [31:0] PRDATA ;
    wire 		PSLVERR;

    //ADDED PSEL Signal
    //wire PSEL = HSEL; 
    wire PSEL_next = HSEL;
    reg PSEL_next_next;
    reg PSEL;
    always @ (posedge HCLK, negedge HRESETn)
    begin
        if(!HRESETn)
        PSEL <= 1'b0;
        else begin
            PSEL_next_next <= PSEL_next;
            PSEL <= PSEL_next | PSEL_next_next;
        end
    end
    //Instantiating the bridge

    ahb_2_apb AHB2APB_BR (
        .HCLK(HCLK),
        .HRESETn(HRESETn),
        .HADDR(HADDR[31:0]),
        .HSEL(HSEL),
        .HREADY(HREADY),
        .HTRANS(HTRANS[1:0]),
        .HWDATA(HWDATA[31:0]),
        .HWRITE(HWRITE),
        .HRDATA(HRDATA),
        .HREADYOUT(HREADYOUT),
        .PCLK(PCLK),
        .PRESETn(PRESETn),
        .PADDR(PADDR[31:0]),
        .PWRITE(PWRITE),
        .PWDATA(PWDATA[31:0]),
        .PENABLE(PENABLE),
        .PREADY(PREADY),
        .PRDATA(PRDATA[31:0])
    );
        
        
    //Bus Signals
        
    //Slave #0
    wire PSEL_S0;
    wire [31:0] PRDATA_S0;
    wire PREADY_S0;
    wire PSLVERR_S0;
    
    //Slave #1
    wire PSEL_S1;
    wire [31:0] PRDATA_S1;
    wire PREADY_S1;
    wire PSLVERR_S1;
    
    //Slave #2
    wire PSEL_S2;
    wire [31:0] PRDATA_S2;
    wire PREADY_S2;
    wire PSLVERR_S2;
    
    //Slave #3
    wire PSEL_S3;
    wire [31:0] PRDATA_S3;
    wire PREADY_S3;
    wire PSLVERR_S3;
    
    //Slave #4
    wire PSEL_S4;
    wire [31:0] PRDATA_S4;
    wire PREADY_S4;
    wire PSLVERR_S4;
    
    //Slave #5
    wire PSEL_S5;
    wire [31:0] PRDATA_S5;
    wire PREADY_S5;
    wire PSLVERR_S5;
    
    //Slave #6
    wire PSEL_S6;
    wire [31:0] PRDATA_S6;
    wire PREADY_S6;
    wire PSLVERR_S6;
    
    //Slave #7
    wire PSEL_S7;
    wire [31:0] PRDATA_S7;
    wire PREADY_S7;
    wire PSLVERR_S7;
    
    //Slave #8
    wire PSEL_S8;
    wire [31:0] PRDATA_S8;
    wire PREADY_S8;
    wire PSLVERR_S8;
    
    //Slave #9
    wire PSEL_S9;
    wire [31:0] PRDATA_S9;
    wire PREADY_S9;
    wire PSLVERR_S9;
    
    //Slave #10
    wire PSEL_S10;
    wire [31:0] PRDATA_S10;
    wire PREADY_S10;
    wire PSLVERR_S10;
    
    //Slave #11
    wire PSEL_S11;
    wire [31:0] PRDATA_S11;
    wire PREADY_S11;
    wire PSLVERR_S11;
    
    //Slave #12
    wire PSEL_S12;
    wire [31:0] PRDATA_S12;
    wire PREADY_S12;
    wire PSLVERR_S12;
    
    //Slave #13
    wire PSEL_S13;
    wire [31:0] PRDATA_S13;
    wire PREADY_S13;
    wire PSLVERR_S13;
    
    //Unused Ports Signals
    wire PSEL_S14;
    wire PSEL_S15;

    wire [31: 0] PRE_S6;
    wire [31: 0] TMRCMP1_S6;
    wire [31: 0] TMRCMP2_S6;
    wire [0: 0] TMREN_S6;
    wire [31: 0] PRE_S7;
    wire [31: 0] TMRCMP1_S7;
    wire [31: 0] TMRCMP2_S7;
    wire [0: 0] TMREN_S7;
    wire [31: 0] TMR_S8;
    wire [31: 0] PRE_S8;
    wire [31: 0] TMRCMP_S8;
    wire [0: 0] TMROV_S8;
    wire [0: 0] TMROVCLR_S8;
    wire [0: 0] TMREN_S8;
    wire [31: 0] TMR_S9;
    wire [31: 0] PRE_S9;
    wire [31: 0] TMRCMP_S9;
    wire [0: 0] TMROV_S9;
    wire [0: 0] TMROVCLR_S9;
    wire [0: 0] TMREN_S9;
    wire [31: 0] TMR_S10;
    wire [31: 0] PRE_S10;
    wire [31: 0] TMRCMP_S10;
    wire [0: 0] TMROV_S10;
    wire [0: 0] TMROVCLR_S10;
    wire [0: 0] TMREN_S10;
    wire [31: 0] TMR_S11;
    wire [31: 0] PRE_S11;
    wire [31: 0] TMRCMP_S11;
    wire [0: 0] TMROV_S11;
    wire [0: 0] TMROVCLR_S11;
    wire [0: 0] TMREN_S11;
    wire [31: 0] WDTMR_S12;
    wire [31: 0] WDLOAD_S12;
    wire [0: 0] WDOV_S12;
    wire [0: 0] WDOVCLR_S12;
    wire [0: 0] WDEN_S12;
    wire [31: 0] WDTMR_S13;
    wire [31: 0] WDLOAD_S13;
    wire [0: 0] WDOV_S13;
    wire [0: 0] WDOVCLR_S13;
    wire [0: 0] WDEN_S13;

    assign IRQ[15:12] = 4'd0;

        //Digital module # 0
        APB_UART S0 (
            .PCLK(PCLK),
            .PRESETn(PRESETn),
            .PSEL(PSEL_S0),
            .PADDR(PADDR),
            .PREADY(PREADY_S0),
            .PWRITE(PWRITE),
            .PWDATA(PWDATA),
            .PRDATA(PRDATA_S0),
            .PENABLE(PENABLE),

            .RsRx(RsRx_S0),   
            .RsTx(RsTx_S0),   
            .uart_irq(IRQ[0])
        );

        //Digital module # 1
        APB_UART S1 (
            .PCLK(PCLK),
            .PRESETn(PRESETn),
            .PSEL(PSEL_S1),
            .PADDR(PADDR),
            .PREADY(PREADY_S1),
            .PWRITE(PWRITE),
            .PWDATA(PWDATA),
            .PRDATA(PRDATA_S1),
            .PENABLE(PENABLE),

            .RsRx(RsRx_S1),   
            .RsTx(RsTx_S1),   
            .uart_irq(IRQ[1])
        );

        //Digital module # 2
        APB_SPI S2 (
            .PCLK(PCLK),
            .PRESETn(PRESETn),
            .PSEL(PSEL_S2),
            .PADDR(PADDR),
            .PREADY(PREADY_S2),
            .PWRITE(PWRITE),
            .PWDATA(PWDATA),
            .PRDATA(PRDATA_S2),
            .PENABLE(PENABLE),

            .MSI(MSI_S2),   
            .MSO(MSO_S2),   
            .SSn(SSn_S2),   
            .SCLK(SCLK_S2),

            .IRQ(IRQ[2])
        );

        //Digital module # 3
        APB_SPI S3 (
            .PCLK(PCLK),
            .PRESETn(PRESETn),
            .PSEL(PSEL_S3),
            .PADDR(PADDR),
            .PREADY(PREADY_S3),
            .PWRITE(PWRITE),
            .PWDATA(PWDATA),
            .PRDATA(PRDATA_S3),
            .PENABLE(PENABLE),

            .MSI(MSI_S3),   
            .MSO(MSO_S3),   
            .SSn(SSn_S3),   
            .SCLK(SCLK_S3),

            .IRQ(IRQ[3])
        );

        //Digital module # 4
        APB_I2C S4 (
            .PCLK(PCLK),
            .PRESETn(PRESETn),
            .PSEL(PSEL_S4),
            .PADDR(PADDR),
            .PREADY(PREADY_S4),
            .PWRITE(PWRITE),
            .PWDATA(PWDATA),
            .PRDATA(PRDATA_S4),
            .PENABLE(PENABLE),

            .scl_i(scl_i_S4),   
            .scl_o(scl_o_S4),   
            .scl_oen_o(scl_oen_o_S4),   
            .sda_i(sda_i_S4),   
            .sda_o(sda_o_S4),   
            .sda_oen_o(sda_oen_o_S4),

            .IRQ(IRQ[4])
        );

        //Digital module # 5
        APB_I2C S5 (
            .PCLK(PCLK),
            .PRESETn(PRESETn),
            .PSEL(PSEL_S5),
            .PADDR(PADDR),
            .PREADY(PREADY_S5),
            .PWRITE(PWRITE),
            .PWDATA(PWDATA),
            .PRDATA(PRDATA_S5),
            .PENABLE(PENABLE),

            .scl_i(scl_i_S5),   
            .scl_o(scl_o_S5),   
            .scl_oen_o(scl_oen_o_S5),   
            .sda_i(sda_i_S5),   
            .sda_o(sda_o_S5),   
            .sda_oen_o(sda_oen_o_S5),

            .IRQ(IRQ[5])
        );

        //Digital module # 6
        PWM32 S6 (
            .clk(PCLK),
            .rst(~PRESETn),
            .PRE(PRE_S6),
            .TMRCMP1(TMRCMP1_S6),
            .TMRCMP2(TMRCMP2_S6),
            .TMREN(TMREN_S6),

            .pwm(pwm_S6)
        );

        //APB Slave # 6
        APB_PWM32 S_6 (
            .PCLK(PCLK),
            //.PCLKG(),
            .PRESETn(PRESETn),
            .PSEL(PSEL_S6),
            .PADDR(PADDR [19:2]),
            .PREADY(PREADY_S6),
            .PWRITE(PWRITE),
            .PENABLE(PENABLE),
            .PWDATA(PWDATA),

            .PRE(PRE_S6),
            .TMRCMP1(TMRCMP1_S6),
            .TMRCMP2(TMRCMP2_S6),
            .TMREN(TMREN_S6),
            .PRDATA(PRDATA_S6)
        );

        //Digital module # 7
        PWM32 S7 (
            .clk(PCLK),
            .rst(~PRESETn),
            .PRE(PRE_S7),
            .TMRCMP1(TMRCMP1_S7),
            .TMRCMP2(TMRCMP2_S7),
            .TMREN(TMREN_S7),

            .pwm(pwm_S7)
        );

        //APB Slave # 7
        APB_PWM32 S_7 (
            .PCLK(PCLK),
            //.PCLKG(),
            .PRESETn(PRESETn),
            .PSEL(PSEL_S7),
            .PADDR(PADDR [19:2]),
            .PREADY(PREADY_S7),
            .PWRITE(PWRITE),
            .PENABLE(PENABLE),
            .PWDATA(PWDATA),

            .PRE(PRE_S7),
            .TMRCMP1(TMRCMP1_S7),
            .TMRCMP2(TMRCMP2_S7),
            .TMREN(TMREN_S7),
            .PRDATA(PRDATA_S7)
        );

        //Digital module # 8
        TIMER32 S8 (
            .clk(PCLK),
            .rst(~PRESETn),
            .TMR(TMR_S8),
            .PRE(PRE_S8),
            .TMRCMP(TMRCMP_S8),
            .TMROV(TMROV_S8),
            .TMROVCLR(TMROVCLR_S8),
            .TMREN(TMREN_S8)

        );

        //APB Slave # 8
        APB_TIMER32 S_8 (
            .PCLK(PCLK),
            //.PCLKG(),
            .PRESETn(PRESETn),
            .PSEL(PSEL_S8),
            .PADDR(PADDR [19:2]),
            .PREADY(PREADY_S8),
            .PWRITE(PWRITE),
            .PENABLE(PENABLE),
            .PWDATA(PWDATA),

            .TMR(TMR_S8),
            .PRE(PRE_S8),
            .TMRCMP(TMRCMP_S8),
            .TMROV(TMROV_S8),
            .TMROVCLR(TMROVCLR_S8),
            .TMREN(TMREN_S8),

            .IRQ(IRQ[6]),
            .PRDATA(PRDATA_S8)
        );

        //Digital module # 9
        TIMER32 S9 (
            .clk(PCLK),
            .rst(~PRESETn),
            .TMR(TMR_S9),
            .PRE(PRE_S9),
            .TMRCMP(TMRCMP_S9),
            .TMROV(TMROV_S9),
            .TMROVCLR(TMROVCLR_S9),
            .TMREN(TMREN_S9)

        );

        //APB Slave # 9
        APB_TIMER32 S_9 (
            .PCLK(PCLK),
            //.PCLKG(),
            .PRESETn(PRESETn),
            .PSEL(PSEL_S9),
            .PADDR(PADDR [19:2]),
            .PREADY(PREADY_S9),
            .PWRITE(PWRITE),
            .PENABLE(PENABLE),
            .PWDATA(PWDATA),

            .TMR(TMR_S9),
            .PRE(PRE_S9),
            .TMRCMP(TMRCMP_S9),
            .TMROV(TMROV_S9),
            .TMROVCLR(TMROVCLR_S9),
            .TMREN(TMREN_S9),

            .IRQ(IRQ[7]),
            .PRDATA(PRDATA_S9)
        );

        //Digital module # 10
        TIMER32 S10 (
            .clk(PCLK),
            .rst(~PRESETn),
            .TMR(TMR_S10),
            .PRE(PRE_S10),
            .TMRCMP(TMRCMP_S10),
            .TMROV(TMROV_S10),
            .TMROVCLR(TMROVCLR_S10),
            .TMREN(TMREN_S10)
        );

        //APB Slave # 10
        APB_TIMER32 S_10 (
            .PCLK(PCLK),
            //.PCLKG(),
            .PRESETn(PRESETn),
            .PSEL(PSEL_S10),
            .PADDR(PADDR [19:2]),
            .PREADY(PREADY_S10),
            .PWRITE(PWRITE),
            .PENABLE(PENABLE),
            .PWDATA(PWDATA),

            .TMR(TMR_S10),
            .PRE(PRE_S10),
            .TMRCMP(TMRCMP_S10),
            .TMROV(TMROV_S10),
            .TMROVCLR(TMROVCLR_S10),
            .TMREN(TMREN_S10),

            .IRQ(IRQ[8]),
            .PRDATA(PRDATA_S10)
        );

        //Digital module # 11
        TIMER32 S11 (
            .clk(PCLK),
            .rst(~PRESETn),
            .TMR(TMR_S11),
            .PRE(PRE_S11),
            .TMRCMP(TMRCMP_S11),
            .TMROV(TMROV_S11),
            .TMROVCLR(TMROVCLR_S11),
            .TMREN(TMREN_S11)

        );

        //APB Slave # 11
        APB_TIMER32 S_11 (
            .PCLK(PCLK),
            //.PCLKG(),
            .PRESETn(PRESETn),
            .PSEL(PSEL_S11),
            .PADDR(PADDR [19:2]),
            .PREADY(PREADY_S11),
            .PWRITE(PWRITE),
            .PENABLE(PENABLE),
            .PWDATA(PWDATA),

            .TMR(TMR_S11),
            .PRE(PRE_S11),
            .TMRCMP(TMRCMP_S11),
            .TMROV(TMROV_S11),
            .TMROVCLR(TMROVCLR_S11),
            .TMREN(TMREN_S11),
            .IRQ(IRQ[9]),
            .PRDATA(PRDATA_S11)
        );

        //Digital module # 12
        WDT32 S12 (
            .clk(PCLK),
            .rst(~PRESETn),
            .WDTMR(WDTMR_S12),
            .WDLOAD(WDLOAD_S12),
            .WDOV(WDOV_S12),
            .WDOVCLR(WDOVCLR_S12),
            .WDEN(WDEN_S12)

        );

        //APB Slave # 12
        APB_WDT32 S_12 (
            .PCLK(PCLK),
            //.PCLKG(),
            .PRESETn(PRESETn),
            .PSEL(PSEL_S12),
            .PADDR(PADDR [19:2]),
            .PREADY(PREADY_S12),
            .PWRITE(PWRITE),
            .PENABLE(PENABLE),
            .PWDATA(PWDATA),

            .WDTMR(WDTMR_S12),
            .WDLOAD(WDLOAD_S12),
            .WDOV(WDOV_S12),
            .WDOVCLR(WDOVCLR_S12),
            .WDEN(WDEN_S12),
            .IRQ(IRQ[10]),
            .PRDATA(PRDATA_S12)
        );

        //Digital module # 13
        WDT32 S13 (
            .clk(PCLK),
            .rst(~PRESETn),
            .WDTMR(WDTMR_S13),
            .WDLOAD(WDLOAD_S13),
            .WDOV(WDOV_S13),
            .WDOVCLR(WDOVCLR_S13),
            .WDEN(WDEN_S13)

        );

        //APB Slave # 13
        APB_WDT32 S_13 (
            .PCLK(PCLK),
            //.PCLKG(),
            .PRESETn(PRESETn),
            .PSEL(PSEL_S13),
            .PADDR(PADDR [19:2]),
            .PREADY(PREADY_S13),
            .PWRITE(PWRITE),
            .PENABLE(PENABLE),
            .PWDATA(PWDATA),

            .WDTMR(WDTMR_S13),
            .WDLOAD(WDLOAD_S13),
            .WDOV(WDOV_S13),
            .WDOVCLR(WDOVCLR_S13),
            .WDEN(WDEN_S13),

            .IRQ(IRQ[11]),
            .PRDATA(PRDATA_S13)
        );


        //APB Bus
        APB_BUS0 #(
            .PORT0_ENABLE   (1),
            .PORT1_ENABLE   (1),
            .PORT2_ENABLE   (1),
            .PORT3_ENABLE   (1),
            .PORT4_ENABLE   (1),
            .PORT5_ENABLE   (1),
            .PORT6_ENABLE   (1),
            .PORT7_ENABLE   (1),
            .PORT8_ENABLE   (1),
            .PORT9_ENABLE   (1),
            .PORT10_ENABLE   (1),
            .PORT11_ENABLE   (1),
            .PORT12_ENABLE   (1),
            .PORT13_ENABLE   (1),
            .PORT14_ENABLE   (0),
            .PORT15_ENABLE   (0)
        )
        apbBus(
            // Inputs
            .DEC_BITS   (PADDR[23:20]),
            .PSEL       (PSEL),

            .PSEL_S0         (PSEL_S0),
            .PREADY_S0       (PREADY_S0),
            .PRDATA_S0       (PRDATA_S0),
            // .PSLVERR0     (timer0_pslverr),
            .PSLVERR_S0      (1'b0),

            .PSEL_S1         (PSEL_S1),
            .PREADY_S1       (PREADY_S1),
            .PRDATA_S1       (PRDATA_S1),
            // .PSLVERR1     (timer1_pslverr),
            .PSLVERR_S1      (1'b0),

            .PSEL_S2         (PSEL_S2),
            .PREADY_S2       (PREADY_S2),
            .PRDATA_S2       (PRDATA_S2),
            // .PSLVERR2     (timer2_pslverr),
            .PSLVERR_S2      (1'b0),

            .PSEL_S3         (PSEL_S3),
            .PREADY_S3       (PREADY_S3),
            .PRDATA_S3       (PRDATA_S3),
            // .PSLVERR3     (timer3_pslverr),
            .PSLVERR_S3      (1'b0),

            .PSEL_S4         (PSEL_S4),
            .PREADY_S4       (PREADY_S4),
            .PRDATA_S4       (PRDATA_S4),
            // .PSLVERR4     (timer4_pslverr),
            .PSLVERR_S4      (1'b0),

            .PSEL_S5         (PSEL_S5),
            .PREADY_S5       (PREADY_S5),
            .PRDATA_S5       (PRDATA_S5),
            // .PSLVERR5     (timer5_pslverr),
            .PSLVERR_S5      (1'b0),

            .PSEL_S6         (PSEL_S6),
            .PREADY_S6       (PREADY_S6),
            .PRDATA_S6       (PRDATA_S6),
            // .PSLVERR6     (timer6_pslverr),
            .PSLVERR_S6      (1'b0),

            .PSEL_S7         (PSEL_S7),
            .PREADY_S7       (PREADY_S7),
            .PRDATA_S7       (PRDATA_S7),
            // .PSLVERR7     (timer7_pslverr),
            .PSLVERR_S7      (1'b0),

            .PSEL_S8         (PSEL_S8),
            .PREADY_S8       (PREADY_S8),
            .PRDATA_S8       (PRDATA_S8),
            // .PSLVERR8     (timer8_pslverr),
            .PSLVERR_S8      (1'b0),

            .PSEL_S9         (PSEL_S9),
            .PREADY_S9       (PREADY_S9),
            .PRDATA_S9       (PRDATA_S9),
            // .PSLVERR9     (timer9_pslverr),
            .PSLVERR_S9      (1'b0),

            .PSEL_S10         (PSEL_S10),
            .PREADY_S10       (PREADY_S10),
            .PRDATA_S10       (PRDATA_S10),
            // .PSLVERR10     (timer10_pslverr),
            .PSLVERR_S10      (1'b0),

            .PSEL_S11         (PSEL_S11),
            .PREADY_S11       (PREADY_S11),
            .PRDATA_S11       (PRDATA_S11),
            // .PSLVERR11     (timer11_pslverr),
            .PSLVERR_S11      (1'b0),

            .PSEL_S12         (PSEL_S12),
            .PREADY_S12       (PREADY_S12),
            .PRDATA_S12       (PRDATA_S12),
            // .PSLVERR12     (timer12_pslverr),
            .PSLVERR_S12      (1'b0),

            .PSEL_S13         (PSEL_S13),
            .PREADY_S13       (PREADY_S13),
            .PRDATA_S13       (PRDATA_S13),
            // .PSLVERR13     (timer13_pslverr),
            .PSLVERR_S13      (1'b0),

            .PSEL_S14         (PSEL_S14),
            .PREADY_S14       (1'b1),
            .PRDATA_S14       (32'h00000000),
            .PSLVERR_S14      (1'b0),

            .PSEL_S15         (PSEL_S15),
            .PREADY_S15       (1'b1),
            .PRDATA_S15       (32'h00000000),
            .PSLVERR_S15      (1'b0),

            // Output
            .PREADY            (PREADY),
            .PRDATA            (PRDATA),
            .PSLVERR           (PSLVERR)
        );
       
endmodule
    
