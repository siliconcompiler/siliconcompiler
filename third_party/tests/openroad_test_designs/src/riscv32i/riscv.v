module riscv (input         clk, reset,
              output [31:0] pc,
              input [31:0]  instr,
              output 	    memwrite,
              output [31:0] aluout, writedata,
              input [31:0]  readdata,
	      output 	    memread,
	      output 	    suspend);

   wire 		    memtoreg, pcsrc, branch, unsign,
			    jump, alusrc, alu2src, regwrite, sltunsigned;
   wire [3:0] 		    alucontrol;
   wire [2:0] 		    imm;
   wire 		    lt, gt, eq;
   wire [1:0] 		    shtype;
   wire [31:0] signimm;

   wire [31:0] ISR;
   wire        ISRsel;   
   wire        storepc;
   wire        pcadd;
   wire        pcext;
   wire        lh, lb, lhu, lbu;   

   // in progress
   assign ISRsel = 1'b0;
   assign ISR = 32'b0;

   controller c (.op(instr[6:0]), .funct7(instr[31:25]),
                 .funct3(instr[14:12]), .memtoreg(memtoreg),
                 .memwrite(memwrite), .pcsrc(pcsrc),
                 .alusrc(alusrc), .regwrite(regwrite),
                 .branch(branch),
                 .storepc(storepc),
                 .pcadd(pcadd),
		 .pcext(pcext),
		 .unsign(unsign),
                 .imm(imm),
                 .alucontrol(alucontrol),
		 .shtype(shtype),
		 .alu2src(alu2src),
		 .gt(gt), .lt(lt), .eq(eq),
		 .suspend(suspend),
		 .sltunsigned(sltunsigned),
		 .memread(memread), 
		 .lh(lh), .lb(lb), .lhu(lhu), .lbu(lbu));
   datapath dp (.clk(clk), .reset(reset),
                .memtoreg(memtoreg), .pcsrc(pcsrc),
                .alusrc(alusrc), .regwrite(regwrite), 
                .alucontrol(alucontrol),
		.storepc(storepc),
		.pcadd(pcadd),
		.pcext(pcext),
		.unsign(unsign),
		.imm(imm),
		.alu2src(alu2src),
		.shtype(shtype),
                .pc(pc),
                .instr(instr),
                .aluout(aluout),
                .writedata4(writedata),
                .readdata(readdata),
		.gt(gt), .lt(lt), .eq(eq),
		.sltunsigned(sltunsigned),
		.ISR(ISR), .ISRsel(ISRsel),
		.suspend(suspend), 
		.lh(lh), .lb(lb), .lhu(lhu), .lbu(lbu),
		.memwrite(memwrite));

endmodule // riscv
