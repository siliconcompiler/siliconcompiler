// RV32i
module datapath(input 	      clk, reset,
		input [31:0]  instr,
		input [2:0]   imm,
		output [31:0] pc,
		input 	      pcsrc, pcadd, pcext,
		input 	      ISRsel,
		input [31:0]  ISR,
		input 	      unsign,
		output 	      gt, lt, eq,
		input [3:0]   alucontrol,
		input 	      alusrc, storepc, sltunsigned,
		input [1:0]   shtype,
		input 	      alu2src,
		input 	      memtoreg, regwrite,
		output [31:0] aluout, writedata4,
		input [31:0]  readdata,
		input 	      suspend,
		input 	      lh, lb, lhu, lbu,
		input 	      memwrite);

   wire [31:0] 		      pcsum, pcimm_sum, pcjalr, pctoreg;
   wire [31:0] 		      pcnext;   
   wire [31:0] 		      signimm;
   wire [31:0] 		      srca2, srcb;
   wire [31:0] 		      result, result2;
   wire [31:0] 		      shoutput, aluout2;
   wire [4:0] 		      rs1;
   wire 		      compA,compB;
   wire [31:0] 		      pcISRin, pcext_imm;
   wire [31:0] 		      SEPC;
   wire 		      zero;
   wire [31:0] 		      readdata4;
   wire [31:0] 		      writedata;   

   // SEPC
   flopenr #(32) epc(.clk(clk), .reset(reset), .en(suspend), 
		     .d(pc), .q(SEPC));
   // Branch Mux
   mux2 #(32) pcmux(.d0(pcsum), .d1(pcimm_sum), 
                    .s(pcsrc), .y(pcISRin));
   // ISR mux
   mux2 #(32) ISRmux(.d0(pcISRin), .d1(ISR),
                     .s(ISRsel), .y(pcnext));   
   // next PC logic
   flopr #(32) pcreg(.clk(clk), .reset(reset),
                     .d(pcnext), .q(pc));   
   // PC Next Adder PC+4
   adder pcadder(.a(pc), .b(32'b100), .y(pcsum));

   // need to read a zero on rs1 for lui to work.
   // this is in the decoder, not in the bit-sliced datapath
   mux2 #(5) rs1mux(.d0(instr[19:15]), .d1(5'b00000),
		    .s(imm[2]), .y(rs1));
   mux2 #(32) pcmux2(.d0(pcimm_sum), .d1(pcsum), 
                     .s(pcsrc), .y(pctoreg));   
   mux2 #(32) storepcmux(.d0(result), .d1(pctoreg),
			 .s(storepc), .y(result2));   
   // register file logic
   regfile rf (.clk(clk), .we3(regwrite),
               .ra1(rs1), .ra2(instr[24:20]),
               .wa3(instr[11:7]), .wd3(result2), 
	       .rd1(srca2), .rd2(writedata));

   // Sign Extension (Immediate)
   signext se(.a(instr[31:0]), .sel(imm), .y(signimm));
   // Shifting immediate for PC
   mux2 #(32) pcextmux(.d0(signimm), .d1({signimm[30:0],1'b0}),
                       .s(pcext), .y(pcext_imm));
   // ALU PC/imm mux
   mux2 #(32) pcsrcmux(.d0(srca2), .d1(pc),
                       .s(pcadd), .y(pcjalr));   
   // PC imm Adder PC + imm
   adder pcimm(.a(pcjalr), .b(pcext_imm), .y(pcimm_sum));
   // ALU mem/imm mux
   mux2 #(32) memsrcmux(.d0(writedata), .d1(pcext_imm),
			.s(alusrc), .y(srcb));

   // Choose whether to invert the sign bit of the comparator 
   // or not for unsigned logic change these 
   // This can be 33rd bit logic
   assign compA = srca2[31] ^ ~unsign;
   assign compB = writedata[31] ^ ~unsign; 

   // Comparator (for beq, bge, blt, beq)
   magcompare32 compare (.GT(gt), .LT(lt), .EQ(eq),
			 .A({compA, srca2[30:0]}), 
   			 .B({compB, writedata[30:0]}));
   // ALU
   alu alu (.a(srca2), .b(srcb),
            .alucont(alucontrol),
            .sltunsigned(sltunsigned),
            .result(aluout2),
	    .zero(zero));

   // Shifter
   shifter shift (.a(srca2), .shamt(srcb[4:0]), 
		  .shtype(shtype), .y(shoutput));

   // Choose ALU or Shifter output
   mux2 #(32) srccmux(.d0(aluout2), .d1(shoutput),
                      .s(alu2src), .y(aluout));

   // lw/lh/lb
   mux3 #(32) halfbytemux1(.d0(readdata), 
			   .d1({{16{readdata[15]&~lhu}}, readdata[15:0]}), 
			   .d2({{24{readdata[7]&~lbu}}, readdata[7:0]}), 
			   .s({lb, lh} & {2{~memwrite}}), .y(readdata4));
   // sw/sh/sb
   mux3 #(32) halfbytemux2(.d0(writedata), 
			   .d1({16'h0, writedata[15:0]}), 
			   .d2({24'h0, writedata[7:0]}),
			   .s({lb, lh} & {2{memwrite}}), .y(writedata4)); 			   

   // Memory Output (ALU/Shifter or memory) for WB
   mux2 #(32) resmux(.d0(aluout), .d1(readdata4),
                     .s(memtoreg), .y(result));
   
endmodule // datapath
