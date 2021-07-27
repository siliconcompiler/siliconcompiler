/**
 * Copyright (C) 2009 Ubixum, Inc.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
 **/

// Author:    Lane Brooks
// Date:      10/31/2009
// Desc: Implements a low level SPI master interface. Set the
//       DATA_WIDTH parameter at instatiation. Put the data you want
//       to send on the 'datai' port and strobe the 'go' signal. The
//       bits of 'datai' will get serially shifted out to the device
//       and the bits coming back from the device will get serially
//       shifted into the 'datao' register.  Hook up the 'csb',
//       'sclk', 'din', and 'dout' wires to the device.  'busy' is
//       high while the shift is running and goes low when the shift
//       is complete.
//
//       The NUM_PORTS parameter can be used when the 'csb' and 'sclk'
//       lines are shared with multiple devices and the 'din' and 'dout'
//       lines are unique. For example, if you have two devices, the
//       specify NUM_PORTS=2 and 'din' and 'dout' become width 2 ports
//       and 'datai' and 'datao' become DATA_WIDTH*NUM_PORTS wide.
//
//       Set the CLK_DIVIDER_WIDTH at instantiation. The rate of
//       'sclk' to the device is then set by the input 'clk_divider'.
//       'clk_divider' must be at least 4.
//
//       The clock polarity and phasing of this master is set via the
//       CPOL and CPHA inputs. See
//       http://en.wikipedia.org/wiki/Serial_Peripheral_Interface_Bus
//       a description of these conventions.
//


`timescale 1ns/1ps
`default_nettype none


module spi_master
  #(parameter DATA_WIDTH=16,
    NUM_PORTS=1,
    CLK_DIVIDER_WIDTH=8,
    SAMPLE_PHASE=0
    )
  (input clk,
   input resetb,
   input CPOL,
   input CPHA,
   input [CLK_DIVIDER_WIDTH-1:0] clk_divider,

   input go,
   input [(NUM_PORTS*DATA_WIDTH)-1:0] datai,
   output [(NUM_PORTS*DATA_WIDTH)-1:0] datao,
   output reg busy,
   output reg done,

   input [NUM_PORTS-1:0] dout,
   output [NUM_PORTS-1:0] din,
   output reg csb,
   output reg sclk
   );

   reg  [CLK_DIVIDER_WIDTH-1:0]  clk_count;
   wire [CLK_DIVIDER_WIDTH-1:0]  next_clk_count = clk_count + 1;
   wire pulse = next_clk_count == (clk_divider >> 1);
   reg    state;

`ifdef verilator
   localparam LOG2_DATA_WIDTH = $clog2(DATA_WIDTH+1);
`else
   function integer log2;
      input integer value;
      integer       count;
      begin
         value = value-1;
         for (count=0; value>0; count=count+1)
           value = value>>1;
         log2=count;
      end
   endfunction
   localparam LOG2_DATA_WIDTH = log2(DATA_WIDTH+1);
`endif

   reg [LOG2_DATA_WIDTH:0] shift_count;

   wire start = shift_count == 0;
   /* verilator lint_off WIDTH */
   wire stop  = shift_count >= 2*DATA_WIDTH-1;
   /* verilator lint_on WIDTH */
   reg 	stop_s;

   localparam IDLE_STATE = 0,
              RUN_STATE = 1;

   sro #(.DATA_WIDTH(DATA_WIDTH)) sro[NUM_PORTS-1:0]
     (.clk(clk),
      .resetb(resetb),
      .shift(pulse && !csb && (shift_count[0] == SAMPLE_PHASE) && !stop_s),
      .dout(dout),
      .datao(datao));

   sri #(.DATA_WIDTH(DATA_WIDTH)) sri[NUM_PORTS-1:0]
     (.clk(clk),
      .resetb(resetb),
      .datai(datai),
      .sample(go && (state == IDLE_STATE)), // we condition on state so that if the user holds 'go' high, this will sample only at the start of the transfer
      .shift(pulse && !csb && (shift_count[0] == 1) && !stop),
      .din(din));

`ifdef SYNC_RESET
   always @(posedge clk) begin
`else
   always @(posedge clk or negedge resetb) begin
`endif
      if(!resetb) begin
         clk_count <= 0;
         shift_count <= 0;
         sclk  <= 1;
         csb   <= 1;
         state <= IDLE_STATE;
         busy  <= 0;
         done  <= 0;
	 stop_s <= 0;
      end else begin
         // generate the pulse train
         if(pulse) begin
            clk_count <= 0;
	    stop_s <= stop;
         end else begin
            clk_count <= next_clk_count;
         end


         // generate csb
         if(state == IDLE_STATE) begin
            csb  <= 1;
            shift_count <= 0;
            done <= 0;
            if(go && !busy) begin // the !busy condition here allows the user to hold go high and this will then run transactions back-to-back at maximum speed where busy drops at for at least one clock cycle but we stay in this idle state for two clock cycles. Staying in idle state for two cycles probably isn't a big deal since the serial clock is running slower anyway.
               state  <= RUN_STATE;
               busy   <= 1;
            end else begin
               busy   <= 0;
            end
         end else begin
            if(pulse) begin
               if(stop) begin
                  //csb <= 1;
                  if(done) begin
		     state <= IDLE_STATE;
		     done <= 0;
		     busy <= 0;
		  end else begin
                     done  <= 1;
		  end
               end else begin
                  csb <= 0;
                  if(!csb) begin
                     shift_count <= shift_count + 1;
                  end
               end
            end
         end

         // generate sclk
         if(pulse) begin
            if((CPHA==1 && state==RUN_STATE && !stop) ||
               (CPHA==0 && !csb && !stop)) begin
               sclk <= !sclk;
            end else begin
               sclk <= CPOL;
            end
         end
      end
   end
endmodule // spi_master

module sri
  // This is a shift register that sends data out to the di lines of
  // spi slaves.
  #(parameter DATA_WIDTH=16)
  (input clk,
   input resetb,
   input [DATA_WIDTH-1:0] datai,
   input sample,
   input shift,
   output din
   );

   reg [DATA_WIDTH-1:0] sr_reg;
   assign din = sr_reg[DATA_WIDTH-1];

`ifdef SYNC_RESET
   always @(posedge clk) begin
`else
   always @(posedge clk or negedge resetb) begin
`endif
      if(!resetb) begin
         sr_reg <= 0;
      end else begin
         if(sample) begin
            sr_reg <= datai;
         end else if(shift) begin
            sr_reg <= sr_reg << 1;
         end
      end
   end
endmodule

module sro
  // This is a shift register that receives data on the dout lines
  // from spi slaves.
  #(parameter DATA_WIDTH=16)
  (input clk,
   input resetb,
   input shift,
   input dout,
   output reg [DATA_WIDTH-1:0] datao
   );
   reg                     dout_s;

`ifdef SYNC_RESET
   always @(posedge clk) begin
`else
   always @(posedge clk or negedge resetb) begin
`endif
      if(!resetb) begin
         dout_s <= 0;
         datao <= 0;
      end else begin
         dout_s <= dout;
         if(shift) begin
            datao <= { datao[DATA_WIDTH-2:0], dout_s };
         end
      end
   end
endmodule