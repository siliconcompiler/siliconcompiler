
`timescale 1ns/1ns
module ahb_2_apb(
// Global signals --------------------------------------------------------------
  input wire          HCLK,
  input wire          HRESETn,
  
// AHB Slave inputs ------------------------------------------------------------  
  input wire  [31:0]  HADDR,
  input wire  [1:0]   HTRANS,
  input wire          HWRITE,
  input wire  [31:0]  HWDATA,
  input wire          HSEL,
  input wire          HREADY,
  
// APB Master inputs -----------------------------------------------------------
  input wire  [31:0]  PRDATA,
  input wire          PREADY,
  
// AHB Slave outputs -----------------------------------------------------------
  output wire [31:0]  HRDATA,
  output reg          HREADYOUT,
  
// APB Master outputs ----------------------------------------------------------
  output wire [31:0]  PWDATA,
  output reg          PENABLE,
  output reg  [31:0]  PADDR,
  output reg          PWRITE,
  
  output wire         PCLK,
  output wire         PRESETn
);
  
//Constants

  `define ST_IDLE 2'b00
  `define ST_SETUP 2'b01
  `define ST_ACCESS 2'b11


  wire          Transfer;
  wire          ACRegEn;
  reg   [31:0]  last_HADDR;
  reg           last_HWRITE;
  
  wire  [31:0]  HADDR_Mux;
  
  reg   [1:0]   CurrentState;
  reg   [1:0]   NextState;
  
  reg           HREADY_next;  
  wire          PWRITE_next;
  wire          PENABLE_next;
  wire          APBEn;
  
  
  assign PCLK = HCLK;
  assign PRESETn = HRESETn;
  
  assign Transfer = HSEL & HREADY & HTRANS[1];
  
  assign ACRegEn = HSEL & HREADY;
  
  //Set register values of AHB signals
  
  always @ (posedge HCLK, negedge HRESETn)
  begin
    if(!HRESETn)
      begin
        last_HADDR <= {32{1'b0}};
        last_HWRITE <= 1'b0;
      end
    
    else
      begin
        if(ACRegEn)
          begin
            last_HADDR <= HADDR;
            last_HWRITE <= HWRITE;
          end
      end
  end
  
  
// Next State Logic

  always @ (CurrentState,PREADY, Transfer)
  begin
    case (CurrentState)
      `ST_IDLE: 
        begin
          if(Transfer)
            NextState = `ST_SETUP;
          else
            NextState = `ST_IDLE;
        end
      
      `ST_SETUP:
        begin
          NextState = `ST_ACCESS;
        end
      
      `ST_ACCESS:
        begin
          if(!PREADY)
            NextState = `ST_ACCESS;
          else
            begin
              if(Transfer)
                NextState = `ST_SETUP;
              else
                NextState = `ST_IDLE;
            end
        end
      default:
        NextState = `ST_IDLE;
    endcase
  end
  
// State Machine

  always @ (posedge HCLK, negedge HRESETn)
  begin
    if(!HRESETn)
      CurrentState <= `ST_IDLE;
    else
      CurrentState <= NextState;
  end
  
  
//HREADYOUT

  always @ (NextState, PREADY)
  begin
    case (NextState)
      `ST_IDLE:
        HREADY_next = 1'b1;
      `ST_SETUP:
        HREADY_next = 1'b0;
      `ST_ACCESS: 
        HREADY_next = PREADY;
      default:
        HREADY_next = 1'b1;
    endcase
  end

  always @(posedge HCLK, negedge HRESETn)
  begin
    if(!HRESETn)
      HREADYOUT <= 1'b1;
    else
      HREADYOUT <= HREADY_next;
  end

  
// HADDRMux
  assign HADDR_Mux = ((NextState == `ST_SETUP) ? HADDR :
                      last_HADDR);

//APBen
  assign APBEn = ((NextState == `ST_SETUP) ? 1'b1 : 1'b0);

//PADDR

  always @ (posedge HCLK, negedge HRESETn)
  begin
    if (!HRESETn)
      PADDR <= {31{1'b0}};
    else
      begin
        if (APBEn)
          PADDR <= HADDR_Mux;
      end
  end

//PWDATA

  assign PWDATA = HWDATA;


//PENABLE

  assign PENABLE_next = ((NextState == `ST_ACCESS) ? 1'b1 : 1'b0);
  
  always @ (posedge HCLK, negedge HRESETn)
  begin
    if(!HRESETn)
      PENABLE <= 1'b0;
    else
      PENABLE <= PENABLE_next;
  end
  
//PWRITE

  assign PWRITE_next = ((NextState == `ST_SETUP) ? HWRITE : last_HWRITE);

  always @ (posedge HCLK, negedge HRESETn)
  begin
    if(!HRESETn)
      PWRITE <= 1'b0;
    else
      begin
        if (APBEn)
          PWRITE <= PWRITE_next;
      end
  end


//HRDATA
  assign HRDATA = PRDATA;



endmodule