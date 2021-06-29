
module riscv_top
(
  input  wire        clk,
  input  wire        reset,
  input  wire [31:0] instr,
  input  wire        valid,
  input  wire        valid_reg,
  output wire [31:0] writedata,
  output wire [31:0] dataadr,
  output wire        memwrite,
  output wire        suspend,
  output wire        ready,
  output wire [31:0] pc
);
  wire [31:0] readdata;
  wire [31:0] instr_int;
  wire [31:0] instr_out;
  wire        memread;
  wire        ready_intm;

  assign ready_intm = (reset) ? 1'b0 : ( (valid & ~valid_reg) ? 1'b1 : 1'b0 );
  assign ready = valid;

  // instantiate processor and memories
  riscv riscv (.clk(clk), .reset(reset),
               .pc(pc), .instr(instr_out),
               .memwrite(memwrite),
               .aluout(dataadr),
               .writedata(writedata),
               .readdata(readdata),
               .memread(memread),
               .suspend(suspend));
  ROM boot (.clk(clk), .en(~pc[31]), .address(pc[30:0]), .instr(instr_int));
  mux2 #(32) pcmux(.d0(instr),
                   .d1(instr_int),
                   .s(~pc[31]),
                   .y(instr_out));
  dmem dmem (.clk(clk), .r_w(memwrite),
             .mem_addr(dataadr),
             .mem_data(writedata),
             .mem_out(readdata));
endmodule

