/*
module AHBSRAM#( parameter AW = 14)( // Address width 
     input           HCLK,      // system bus clock 
     input           HRESETn,   // system bus reset 
     input           HSEL,      // AHB peripheral select 
     input           HREADY,    // AHB ready input 
     input     [1:0] HTRANS,    // AHB transfer type 
     input     [2:0] HSIZE,     // AHB hsize 
     input           HWRITE,    // AHB hwrite 
     input  [AW-1:0] HADDR,     // AHB address bus 
     input    [31:0] HWDATA,    // AHB write data bus 
     output          HREADYOUT, // AHB ready output to S->M mux 
     output          HRESP,     // AHB response 
     output   [31:0] HRDATA,    // AHB read data bus 
      
     input    [31:0] SRAMRDATA, // SRAM Read Data 
     output [AW-3:0] SRAMADDR,  // SRAM address 
     output    [3:0] SRAMWEN,   // SRAM write enable (active high) 
     output   [31:0] SRAMWDATA, // SRAM write data 
     output          SRAMCS     // SRAM Chip Select  (active high) 
   ); 
   reg  [(AW-3):0] buf_addr; // Write address buffer   
   reg  [ 3:0]     buf_we;   // Write enable buffer (data phase)  
   reg             buf_hit;  // High when AHB read address  
                             // matches buffered address 
   reg  [31:0]     buf_data; // AHB write bus buffered  
   reg             buf_pend; // Buffer write data valid  
   reg                       buf_data_en;//Data buffer write enable (data phase) 
   wire  ahb_access   = HTRANS[1] & HSEL & HREADY; 
   wire  ahb_write    = ahb_access &  HWRITE; 
   wire  ahb_read     = ahb_access & (~HWRITE); 
    
   // Stored write data in pending state if new transfer is read 
   //   buf_data_en indicate new write (data phase) 
   //   ahb_read    indicate new read  (address phase) 
   //   buf_pend    is registered version of buf_pend_nxt 
   wire        buf_pend_nxt = (buf_pend | buf_data_en) & ahb_read; 
   
   // RAM write happens when  
   // - write pending (buf_pend), or 
   // - new AHB write seen (buf_data_en) at data phase, 
   // - and not reading (address phase) 
   wire        ram_write    = (buf_pend | buf_data_en)  & (~ahb_read); // ahb_write 
   // RAM WE is the buffered WE 
   assign      SRAMWEN  = {4{ram_write}} & buf_we[3:0]; 
   // RAM address is the buffered address for RAM write otherwise HADDR 
   assign      SRAMADDR = ahb_read ? HADDR[AW-1:2] : buf_addr; 
   // RAM chip select during read or write 
   assign      SRAMCS   = ahb_read | ram_write; 
   // Byte lane decoder and next state logic 
   wire       tx_byte    = (~HSIZE[1]) & (~HSIZE[0]); 
   wire       tx_half    = (~HSIZE[1]) &  HSIZE[0]; 
   wire       tx_word    =   HSIZE[1]; 
   wire       byte_at_00 = tx_byte & (~HADDR[1]) & (~HADDR[0]); 
   wire       byte_at_01 = tx_byte & (~HADDR[1]) &   HADDR[0]; 
   wire       byte_at_10 = tx_byte &   HADDR[1]  & (~HADDR[0]); 
   wire       byte_at_11 = tx_byte &   HADDR[1]  &   HADDR[0]; 
   wire       half_at_00 = tx_half & (~HADDR[1]); 
   wire       half_at_10 = tx_half &   HADDR[1]; 
   wire       word_at_00 = tx_word; 
   wire       byte_sel_0 = word_at_00 | half_at_00 | byte_at_00; 
   wire       byte_sel_1 = word_at_00 | half_at_00 | byte_at_01; 
   wire       byte_sel_2 = word_at_00 | half_at_10 | byte_at_10; 
   wire       byte_sel_3 = word_at_00 | half_at_10 | byte_at_11; 
  // Address phase byte lane strobe 
   wire [3:0] buf_we_nxt ={byte_sel_3 & ahb_write, byte_sel_2 & ahb_write, 
                           byte_sel_1 & ahb_write,byte_sel_0 & ahb_write};  
   // buf_data_en is data phase write control 
   always @(posedge HCLK or negedge HRESETn) 
     if (~HRESETn) 
       buf_data_en <= 1'b0; 
     else   
       buf_data_en <= ahb_write; 
 
   always @(posedge HCLK) 
     if(buf_we[3] & buf_data_en) 
       buf_data[31:24] <= HWDATA[31:24]; 
 
   always @(posedge HCLK) 
     if(buf_we[2] & buf_data_en) 
       buf_data[23:16] <= HWDATA[23:16]; 
  
   always @(posedge HCLK) 
     if(buf_we[1] & buf_data_en) 
       buf_data[15: 8] <= HWDATA[15: 8]; 
       
   always @(posedge HCLK) 
     if(buf_we[0] & buf_data_en) 
       buf_data[ 7: 0] <= HWDATA[ 7: 0]; 
 
   // buf_we keep the valid status of each byte (data phase) 
   always @(posedge HCLK or negedge HRESETn) 
     if (~HRESETn) 
       buf_we <= 4'b0000; 
     else if(ahb_write) 
       buf_we <= buf_we_nxt; 
 
   always @(posedge HCLK or negedge HRESETn) 
     begin 
     if (~HRESETn) 
       buf_addr <= {(AW-2){1'b0}}; 
     else if (ahb_write) 
         buf_addr <= HADDR[(AW-1):2]; 
     end 
   // Buf_hit detection logic 
   wire  buf_hit_nxt = (HADDR[AW-1:2] == buf_addr[AW-3:0]); 
   // ---------------------------------------------------------- 
   // Read data merge : This is for the case when there is a AHB  
   // write followed by AHB read to the same address. In this case 
   // the data is merged from the buffer as the RAM write to that 
   // address hasn't happened yet 
   // ---------------------------------------------------------- 
   wire [ 3:0] merge1  = {4{buf_hit}} & buf_we; // data phase, buf_we indicates data is valid 
   assign HRDATA={merge1[3] ? buf_data[31:24] : SRAMRDATA[31:24], 
                  merge1[2] ? buf_data[23:16] : SRAMRDATA[23:16], 
                  merge1[1] ? buf_data[15: 8] : SRAMRDATA[15: 8], 
                  merge1[0] ? buf_data[ 7: 0] : SRAMRDATA[ 7: 0]}; 
 
   // Synchronous state update 
   always @(posedge HCLK or negedge HRESETn) 
     if (~HRESETn) 
       buf_hit <= 1'b0; 
     else if(ahb_read) 
       buf_hit <= buf_hit_nxt; 
 
   always @(posedge HCLK or negedge HRESETn) 
     if (~HRESETn) 
       buf_pend <= 1'b0; 
     else 
       buf_pend <= buf_pend_nxt; 
 
   // if there is an AHB write and valid data in the buffer, RAM write data 
   // comes from the buffer. otherwise comes from the HWDATA 
   assign SRAMWDATA = (buf_pend) ? buf_data : HWDATA[31:0]; 
   assign HREADYOUT = 1'b1; 
   assign HRESP     = 1'b0; 
endmodule 
*/
module AHBSRAM #(
// --------------------------------------------------------------------------
// Parameter Declarations
// --------------------------------------------------------------------------
  parameter AW       = 14) // Address width
 (
// --------------------------------------------------------------------------
// Port Definitions
// --------------------------------------------------------------------------
  input  wire          HCLK,      // system bus clock
  input  wire          HRESETn,   // system bus reset
  input  wire          HSEL,      // AHB peripheral select
  input  wire          HREADY,    // AHB ready input
  input  wire    [1:0] HTRANS,    // AHB transfer type
  input  wire    [2:0] HSIZE,     // AHB hsize
  input  wire          HWRITE,    // AHB hwrite
  input  wire [31:0] HADDR,     // AHB address bus
  input  wire   [31:0] HWDATA,    // AHB write data bus
  output wire          HREADYOUT, // AHB ready output to S->M mux
  output wire   [1:0]       HRESP,     // AHB response
  output wire   [31:0] HRDATA,    // AHB read data bus

  input  wire   [31:0] SRAMRDATA, // SRAM Read Data
  output wire    [3:0] SRAMWEN,   // SRAM write enable (active high)
  output wire   [31:0] SRAMWDATA, // SRAM write data
  output wire          SRAMCS0,
  //output wire          SRAMCS1,
  //output wire          SRAMCS2,
  //output wire          SRAMCS3,
  output wire [AW:0]   SRAMADDR  // SRAM address
);   // SRAM Chip Select  (active high)

   // ----------------------------------------------------------
   // Internal state
   // ----------------------------------------------------------
   reg  [(AW-3 - 0):0]           buf_addr;        // Write address buffer
   reg  [ 3:0]               buf_we;          // Write enable buffer (data phase)
   reg                       buf_hit;         // High when AHB read address
                                              // matches buffered address
   reg  [31:0]               buf_data;        // AHB write bus buffered
   reg                       buf_pend;        // Buffer write data valid
   reg                       buf_data_en;     // Data buffer write enable (data phase)

   // ----------------------------------------------------------
   // Read/write control logic
   // ----------------------------------------------------------

   wire        ahb_access   = HTRANS[1] & HSEL & HREADY;
   wire        ahb_write    = ahb_access &  HWRITE;
   wire        ahb_read     = ahb_access & (~HWRITE);


   // Stored write data in pending state if new transfer is read
   //   buf_data_en indicate new write (data phase)
   //   ahb_read    indicate new read  (address phase)
   //   buf_pend    is registered version of buf_pend_nxt
   wire        buf_pend_nxt = (buf_pend | buf_data_en) & ahb_read;

   // RAM write happens when
   // - write pending (buf_pend), or
   // - new AHB write seen (buf_data_en) at data phase,
   // - and not reading (address phase)
   wire        ram_write    = (buf_pend | buf_data_en)  & (~ahb_read); // ahb_write

   // RAM WE is the buffered WE
   assign      SRAMWEN  = {4{ram_write}} & buf_we[3:0];

   // RAM address is the buffered address for RAM write otherwise HADDR
   assign      SRAMADDR = ahb_read ? HADDR[AW-1:2] : buf_addr;

   // RAM chip select during read or write
   wire SRAMCS_src; 
   assign      SRAMCS_src   = ahb_read | ram_write;
   assign SRAMCS0 = SRAMCS_src; // & (~HADDR[AW + 3]) & (~HADDR[AW + 2]);
   //assign SRAMCS1 = SRAMCS_src & (~HADDR[AW + 3]) & (HADDR[AW + 2]);
   //assign SRAMCS2 = SRAMCS_src & (HADDR[AW + 3]) & (~HADDR[AW + 2]);
   //assign SRAMCS3 = SRAMCS_src & (HADDR[AW + 3]) & (HADDR[AW + 2]);
   // ----------------------------------------------------------
   // Byte lane decoder and next state logic
   // ----------------------------------------------------------

   wire       tx_byte    = (~HSIZE[1]) & (~HSIZE[0]);
   wire       tx_half    = (~HSIZE[1]) &  HSIZE[0];
   wire       tx_word    =   HSIZE[1];

   wire       byte_at_00 = tx_byte & (~HADDR[1]) & (~HADDR[0]);
   wire       byte_at_01 = tx_byte & (~HADDR[1]) &   HADDR[0];
   wire       byte_at_10 = tx_byte &   HADDR[1]  & (~HADDR[0]);
   wire       byte_at_11 = tx_byte &   HADDR[1]  &   HADDR[0];

   wire       half_at_00 = tx_half & (~HADDR[1]);
   wire       half_at_10 = tx_half &   HADDR[1];

   wire       word_at_00 = tx_word;

   wire       byte_sel_0 = word_at_00 | half_at_00 | byte_at_00;
   wire       byte_sel_1 = word_at_00 | half_at_00 | byte_at_01;
   wire       byte_sel_2 = word_at_00 | half_at_10 | byte_at_10;
   wire       byte_sel_3 = word_at_00 | half_at_10 | byte_at_11;

   // Address phase byte lane strobe
   wire [3:0] buf_we_nxt = { byte_sel_3 & ahb_write,
                             byte_sel_2 & ahb_write,
                             byte_sel_1 & ahb_write,
                             byte_sel_0 & ahb_write };

   // ----------------------------------------------------------
   // Write buffer
   // ----------------------------------------------------------

   // buf_data_en is data phase write control
   always @(posedge HCLK or negedge HRESETn)
     if (~HRESETn)
       buf_data_en <= 1'b0;
     else
       buf_data_en <= ahb_write;

   always @(posedge HCLK)
     if(buf_we[3] & buf_data_en)
       buf_data[31:24] <= HWDATA[31:24];

   always @(posedge HCLK)
     if(buf_we[2] & buf_data_en)
       buf_data[23:16] <= HWDATA[23:16];

   always @(posedge HCLK)
     if(buf_we[1] & buf_data_en)
       buf_data[15: 8] <= HWDATA[15: 8];

   always @(posedge HCLK)
     if(buf_we[0] & buf_data_en)
       buf_data[ 7: 0] <= HWDATA[ 7: 0];

   // buf_we keep the valid status of each byte (data phase)
   always @(posedge HCLK or negedge HRESETn)
     if (~HRESETn)
       buf_we <= 4'b0000;
     else if(ahb_write)
       buf_we <= buf_we_nxt;

   always @(posedge HCLK or negedge HRESETn)
     begin
     if (~HRESETn)
       buf_addr <= {(AW-2){1'b0}};
     else if (ahb_write)
         buf_addr <= HADDR[(AW-1):2];
     end
   // ----------------------------------------------------------
   // Buf_hit detection logic
   // ----------------------------------------------------------

   wire  buf_hit_nxt = (HADDR[AW-1:2] == buf_addr[AW-3 - 0:0]);

   // ----------------------------------------------------------
   // Read data merge : This is for the case when there is a AHB
   // write followed by AHB read to the same address. In this case
   // the data is merged from the buffer as the RAM write to that
   // address hasn't happened yet
   // ----------------------------------------------------------

   wire [ 3:0] merge1  = {4{buf_hit}} & buf_we; // data phase, buf_we indicates data is valid

   assign HRDATA =
              { merge1[3] ? buf_data[31:24] : SRAMRDATA[31:24],
                merge1[2] ? buf_data[23:16] : SRAMRDATA[23:16],
                merge1[1] ? buf_data[15: 8] : SRAMRDATA[15: 8],
                merge1[0] ? buf_data[ 7: 0] : SRAMRDATA[ 7: 0] };

   // ----------------------------------------------------------
   // Synchronous state update
   // ----------------------------------------------------------

   always @(posedge HCLK or negedge HRESETn)
     if (~HRESETn)
       buf_hit <= 1'b0;
     else if(ahb_read)
       buf_hit <= buf_hit_nxt;

   always @(posedge HCLK or negedge HRESETn)
     if (~HRESETn)
       buf_pend <= 1'b0;
     else
       buf_pend <= buf_pend_nxt;

   // if there is an AHB write and valid data in the buffer, RAM write data
   // comes from the buffer. otherwise comes from the HWDATA
   assign SRAMWDATA = (buf_pend) ? buf_data : HWDATA[31:0];

   // ----------------------------------------------------------
   // Assign outputs
   // ----------------------------------------------------------
   assign HREADYOUT = 1'b1;
   assign HRESP     = 2'b0;


endmodule
