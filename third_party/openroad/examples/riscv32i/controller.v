module controller (input  [6:0] op, funct7,
		   input [2:0] 	funct3,
                   output 	memtoreg, memwrite,
                   output 	pcsrc, alusrc, 
                   output 	regwrite,
		   output 	branch,
		   output 	storepc,
		   output 	pcadd,
		   output 	pcext,
		   output 	unsign,
		   output [2:0] imm,
                   output [3:0] alucontrol,
		   output [1:0] shtype,
		   output 	alu2src,
		   input 	gt, lt, eq,
		   output 	suspend,
		   output 	sltunsigned,
		   output 	memread,
		   output 	lh, lb, lhu, lbu);

   wire [2:0] 			aluop;
   wire alu2src_fake;
   wire [3:0] alucontrol_fake;
   wire       storepc_local;
   wire       auipc_cntrl;
   
   maindec md (.op(op),
               .memtoreg(memtoreg),
               .memwrite(memwrite),
               .branch(branch),
               .alusrc(alusrc),
               .regwrite(regwrite),
	       .pcext(pcext), .pcadd(pcadd),
               .storepc(storepc_local), .imm(imm), .aluop(aluop),
	       .auipc_cntrl(auipc_cntrl),
	       .gt(gt), .lt(lt), .eq(eq),
	       .suspend(suspend),
	       .memread(memread));
   aludec  ad (.funct7b(funct7[5]),
               .funct3(funct3),
               .aluop(aluop),
               .alucontrol(alucontrol_fake),
	       .alu2src(alu2src_fake),
	       .shtype(shtype),
	       .sltunsigned(sltunsigned),
	       .lh(lh), .lb(lb), .lhu(lhu), .lbu(lbu));

   mux2 #(1) mx1(.d0(alu2src_fake),.d1(1'b0),.s(imm[2]),.y(alu2src));
   mux2 #(4) mx2(.d0(alucontrol_fake),.d1(4'b0010),
		 .s(imm[2] | branch),.y(alucontrol));

   assign pcsrc = (branch & ~funct3[2] & ~funct3[1] & ~funct3[0] & eq) | 
		  (branch & funct3[2] & ~funct3[1] & funct3[0] & ~lt) | 
		  (branch & funct3[2] & ~funct3[1] & ~funct3[0] & lt) | 
		  (branch & ~funct3[2] & ~funct3[1] & funct3[0] & ~eq) |
		  (branch & funct3[2] & funct3[1] & ~funct3[0] & lt) |
		  (branch & funct3[2] & funct3[1] & funct3[0] &  (gt | eq)) | 
		  (storepc_local);
   assign unsign = branch & funct3[1];
   assign storepc = storepc_local | auipc_cntrl;
   
endmodule // controller
