//#############################################################################
//# Function: Generic Memory Example                                          #
//#############################################################################
//# Author:   Andreas Olofsson                                                #
//# License:  MIT                                                             # 
//#############################################################################

module hello_world  # (parameter DW      = 32,          // memory width
		       parameter DEPTH   = 32,           // memory depth
		       parameter REG     = 1,            // register output
		       parameter DUALPORT= 1,            // limit dual port
		       parameter AW      = $clog2(DEPTH) // address width
		       ) 
   (input           clk, //single clock
    // read-port
    input 	    rd_en, // memory access
    input [AW-1:0]  rd_addr, // address 
    output [DW-1:0] rd_dout, // data output   
    // write-port
    input 	    wr_en, // memory access
    input [AW-1:0]  wr_addr, // address
    input [DW-1:0]  wr_din // data input
    );
   
   reg [DW-1:0]        ram    [0:DEPTH-1];  
   wire [DW-1:0]       rdata;
   wire [AW-1:0]       dp_addr;

   //#########################################
   // limiting dual port
   //#########################################	

   assign dp_addr[AW-1:0] = (DUALPORT==1) ? rd_addr[AW-1:0] :
			                    wr_addr[AW-1:0];
   
   //#########################################
   //write port
   //#########################################	

   always @(posedge clk)    
     if (wr_en) 
       ram[wr_addr[AW-1:0]] <= wr_din[DW-1:0];

   //#########################################
   //read port
   //#########################################

   assign rdata[DW-1:0] = ram[dp_addr[AW-1:0]];
   
   //Configurable output register
   reg [DW-1:0]        rd_reg;
   always @ (posedge clk)
     if(rd_en)       
       rd_reg[DW-1:0] <= rdata[DW-1:0];
   
   //Drive output from register or RAM directly
   assign rd_dout[DW-1:0] = (REG==1) ? rd_reg[DW-1:0] :
		                       rdata[DW-1:0];
     
endmodule // hello_world








  
     

