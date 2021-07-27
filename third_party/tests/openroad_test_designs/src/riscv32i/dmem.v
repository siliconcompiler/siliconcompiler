//------------------------------------------------
// dmem.v
// James E. Stine
// February 1, 2018
// Oklahoma State University
// ECEN 4243
// Harvard Architecture Data Memory (Big Endian)
//------------------------------------------------

module dmem (clk, r_w, mem_addr, mem_data, mem_out);

   input 	 clk;      
   input 	 r_w;
   input [31:0]  mem_addr;
   input [31:0]  mem_data;
   output [31:0] mem_out;   

   // Choose smaller memory to speed simulation
   //   through smaller AddrSize (only used to
   //   allocate memory size -- processor sees
   //   32-bits)
   parameter AddrSize = 6;
   parameter WordSize = 8;

   reg [WordSize-1:0] RAM[((1<<AddrSize)-1):0];   

   // Read memory
   //   byte addressed, but appears as 32b to processor
   assign mem_out = {RAM[mem_addr+3], RAM[mem_addr+2],
                     RAM[mem_addr+1], RAM[mem_addr]};

   // Write memory
   always @(posedge clk) 
   begin
     if (r_w)
       {RAM[mem_addr+3], RAM[mem_addr+2], 
          RAM[mem_addr+1], RAM[mem_addr]} <= mem_data; 
   end
   
endmodule // mem

