
module wb_ram #(parameter DEPTH=128, parameter MEMFILE="")
(
   input  logic                     clk_i,
   input  logic                     cyc_i,
   input  logic                     stb_i,
   input  logic                     we_i,
   output logic                     ack_o,
   input  logic [3:0]               be_i,
   input  logic [$clog2(DEPTH)-1:0] adr_i,
   input  logic [31:0]              dat_i,
   output logic [31:0]              dat_o

);

logic read_enable;
logic write_enable;
logic chip_enable;
logic [31:0] mask;

assign read_enable   = cyc_i & stb_i & ~we_i;
assign write_enable  = cyc_i & stb_i & we_i;
assign chip_enable   = read_enable | write_enable;
assign mask          = {{8{be_i[3]}}, {8{be_i[2]}}, {8{be_i[1]}}, {8{be_i[0]}}};

always @(posedge clk_i) begin
   ack_o <= 'b0;

   if (read_enable) begin
      ack_o <= ~ack_o;
   end else if (write_enable) begin
      ack_o <= ~ack_o;
   end
end

la_spram #(
    .DW(32),
    .AW($clog2(DEPTH))
) ram (
    .clk(clk_i),
    .ce(chip_enable),
    .we(write_enable),
    .wmask(mask),
    .addr(adr_i),
    .din(dat_i),
    .dout(dat_o)
);

endmodule

// Copyright (c) 2023 - 2024 Meinhard Kissich
// SPDX-License-Identifier: MIT
// -----------------------------------------------------------------------------
// File  :  fazyrv_ram_sp.v
// Usage :  General purpose RAM used in FazyRV SoCs.
//
// Param
//  - REGW        Width of registers.
//  - ADRW        Width of address.
//  - DEPTH       Depth of memory.
//
// Ports
//  - clk_i       Clock input, sensitive to rising edge.
//  - we_i        Write enable.
//  - waddr_i     Write address.
//  - raddr_i     Read address.
//  - wdata_i     Write data.
//  - rdata_o     Read data.
// -----------------------------------------------------------------------------

module fazyrv_ram_sp #( parameter REGW=32, parameter ADRW=5, parameter DEPTH=32 ) (
  input  logic            clk_i,
  input  logic            we_i,
  input  logic [ADRW-1:0] waddr_i,
  input  logic [ADRW-1:0] raddr_i,
  input  logic [REGW-1:0] wdata_i,
  output logic [REGW-1:0] rdata_o
);

la_spram #(
        .DW(REGW),
        .AW(ADRW)
    ) ram (
        .clk(clk_i),
        .ce('b1),
        .we(we_i),
        .wmask({REGW{1'b1}}),
        .addr(we_i ? waddr_i : raddr_i),
        .din(wdata_i),
        .dout(rdata_o)
    );

endmodule
