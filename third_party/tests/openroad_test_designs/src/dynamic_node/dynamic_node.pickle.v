/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

//File: network_input_blk_multi_out.v

/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

/////////////////////////////////////////////////////////////////////////////////////////////
// 63         50 49      42 41      34 33           30 29      22 21                 0
// ------------------------------------------------------------------------------------
// |            |          |          |               |          |                    |
// |  Chip ID   |  Dest X  |  Dest Y  |  Final Route  |  Length  |    Header Payload  |
// |            |          |          |               |          |                    |
// ------------------------------------------------------------------------------------
////////////////////////////////////////////////////////////////////////////////////////////////











 //whether the routing is based on chipid or x y position
 //`define    ROUTING_CHIP_ID


 //defines for different topology, only one should be active
 //`define    NETWORK_TOPO_2D_MESH
 //`define    NETWORK_TOPO_3D_MESH

module network_input_blk_multi_out
   #(parameter LOG2_NUMBER_FIFO_ELEMENTS = 2)
(
   input wire clk,
   input wire reset,
   input wire [64-1:0] data_in,
   input wire valid_in,
   input wire thanks_in,

   output wire yummy_out,
   // data_val and data_val1 are the same, this is just done for buffering to
   // convince the synthesis tool to buffer up these high fanout nets
   output wire [64-1:0] data_val,
   output wire [64-1:0] data_val1,
   output wire data_avail
);

reg [64-1:0] storage_data_f [0:(1<<LOG2_NUMBER_FIFO_ELEMENTS)-1];

reg [LOG2_NUMBER_FIFO_ELEMENTS-1:0] head_ptr_f;
reg [LOG2_NUMBER_FIFO_ELEMENTS-1:0] tail_ptr_f;
reg [LOG2_NUMBER_FIFO_ELEMENTS:0] elements_in_array_f;

reg [LOG2_NUMBER_FIFO_ELEMENTS-1:0] head_ptr_next;
reg [LOG2_NUMBER_FIFO_ELEMENTS-1:0] tail_ptr_next;
reg [LOG2_NUMBER_FIFO_ELEMENTS:0] elements_in_array_next;

reg yummy_out_f;

assign yummy_out = yummy_out_f;

// data_val and data_val1 are the same, just done for buffering
assign data_val = storage_data_f[head_ptr_f];
assign data_val1 = storage_data_f[head_ptr_f];
assign data_avail = elements_in_array_f != 0;

always @ *
begin
   head_ptr_next = head_ptr_f;
   tail_ptr_next = tail_ptr_f;
   elements_in_array_next = elements_in_array_f;
   case({valid_in,thanks_in})
      2'b00:
         begin
            // do nothing here
         end
      2'b01:
         begin
            // we are being dequeued from
            head_ptr_next = head_ptr_f + 1;
            elements_in_array_next = elements_in_array_f - 1;
         end
      2'b10:
         begin
            // we are being enqueued into
            tail_ptr_next = tail_ptr_f + 1;
            elements_in_array_next = elements_in_array_f + 1;
         end
      2'b11:
         begin
            // simultaneous enqueue and dequeue
            head_ptr_next = head_ptr_f + 1;
            tail_ptr_next = tail_ptr_f + 1;
         end
      default:
         begin
            // this is an error because this is a full parallel case statement
         end
   endcase
end

always @ (posedge clk)
begin
   if (reset)
   begin
      yummy_out_f <= 0;
      head_ptr_f <= 0;
      tail_ptr_f <= 0;
      elements_in_array_f <= 0;
   end
   else
   begin
      yummy_out_f <= thanks_in; // this is just a feed through via a flip flop
      head_ptr_f <= head_ptr_next;
      tail_ptr_f <= tail_ptr_next;
      elements_in_array_f <= elements_in_array_next;
      if(valid_in)
      begin
         storage_data_f[tail_ptr_f] <= data_in;
      end
   end
end

endmodule
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

//Function: This module keeps track of how many spots are free in the NIB that
//	we are sending to
//
//State: count_f, yummy_f, valid_f
//
//Instantiates:

module space_avail_top (valid,
		    yummy,
		    spc_avail,
		    clk,
		    reset);

parameter BUFFER_SIZE = 4;
parameter BUFFER_BITS = 3;


input valid;			// sending data to the output
input yummy;			// output consumed data

output spc_avail;		// is there space available?

input clk;
input reset;

//This is the state
reg yummy_f;
reg valid_f;
reg [BUFFER_BITS-1:0] count_f;

reg is_one_f;
reg is_two_or_more_f;

//wires
wire [BUFFER_BITS-1:0] count_plus_1;
wire [BUFFER_BITS-1:0] count_minus_1;
wire up;
wire down;

//wire regs
reg [BUFFER_BITS-1:0] count_temp;


//assigns
assign count_plus_1 = count_f + 1'b1;
assign count_minus_1 = count_f - 1'b1;
assign spc_avail = (is_two_or_more_f | yummy_f | (is_one_f & ~valid_f));
assign up = yummy_f & ~valid_f;
assign down = ~yummy_f & valid_f;

always @ (count_f or count_plus_1 or count_minus_1 or up or down)
begin
	case (count_f)
	0:
		begin
			if(up)
			begin
				count_temp <= count_plus_1;
			end
			else
			begin
				count_temp <= count_f;
			end
		end
	BUFFER_SIZE:
		begin
			if(down)
			begin
				count_temp <= count_minus_1;
			end
			else
			begin
				count_temp <= count_f;
			end
		end
	default:
		begin
			case ({up, down})
				2'b10:	count_temp <= count_plus_1;
				2'b01:	count_temp <= count_minus_1;
				default:	count_temp <= count_f;
			endcase
		end
	endcase
end

wire top_bits_zero_temp = ~| count_temp[BUFFER_BITS-1:1];


always @ (posedge clk)
begin
	if(reset)
	begin
	   count_f <= BUFFER_SIZE;
	   yummy_f <= 1'b0;
	   valid_f <= 1'b0;
	   is_one_f <= (BUFFER_SIZE == 1);
	   is_two_or_more_f <= (BUFFER_SIZE >= 2);
	end
	else
	begin
	   count_f <= count_temp;
	   yummy_f <= yummy;
	   valid_f <= valid;
	   is_one_f         <= top_bits_zero_temp & count_temp[0];
   	   is_two_or_more_f <= ~top_bits_zero_temp;
	end
end

endmodule

/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

module bus_compare_equal (a, b, bus_equal);
    parameter WIDTH = 8;
    parameter BHC = 10;

    input [WIDTH-1:0] a, b;
    output wire bus_equal;

    assign bus_equal = (a==b) ? 1'b1 : 1'b0;
endmodule
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

module flip_bus (in, out);
    parameter WIDTH = 8;
    parameter BHC = 10;

    input [WIDTH-1:0] in;
    output wire [WIDTH-1:0] out;

    assign out = ~in;
endmodule
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

module one_of_eight(in0,in1,in2,in3,in4,in5,in6,in7,sel,out);
    parameter WIDTH = 8;
    parameter BHC = 10;
    input [2:0] sel;
    input [WIDTH-1:0] in0,in1,in2,in3,in4,in5,in6,in7;
    output reg [WIDTH-1:0] out;
    always@ (*)
    begin
        out={WIDTH{1'b0}};
        case(sel)
            3'd0:out=in0;
            3'd1:out=in1;
            3'd2:out=in2;
            3'd3:out=in3;
            3'd4:out=in4;
            3'd5:out=in5;
            3'd6:out=in6;
            3'd7:out=in7;
            default:; // indicates null
        endcase
    end
endmodule


/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

module one_of_five(in0,in1,in2,in3,in4,sel,out);
    parameter WIDTH = 8;
    parameter BHC = 10;
    input [2:0] sel;
    input [WIDTH-1:0] in0,in1,in2,in3,in4;
    output reg [WIDTH-1:0] out;
    always@(*)
    begin
        out={WIDTH{1'b0}};
        case(sel)
            3'd0:out=in0;
            3'd1:out=in1;
            3'd2:out=in2;
            3'd3:out=in3;
            3'd4:out=in4;
            default:; // indicates null
        endcase
    end
endmodule


/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

// Just a simple D Flip Flip without a reset

module net_dff #(parameter WIDTH=8, parameter BHC=10)
    (input wire [WIDTH-1:0] d,
    output reg [WIDTH-1:0] q,
    input wire clk);

always @ (posedge clk)
begin
    q <= d;
end

endmodule
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

//Function: This maintains the control of where different signals want to go
//and counters of how many words are left in messages
//
//State:
//header_temp_f  //header_temp from the previous cycle
//count_f       //the counter of how much more we have to go
//tail_last_f   //what the tail bit wa the last cycle
//count_zero_f  //whether the counter now is zero
//count_one_f   //whether the counter now is one
//
//Instantiates: dynamic_input_route_request_calc
//
//Note:
//
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

/////////////////////////////////////////////////////////////////////////////////////////////
// 63         50 49      42 41      34 33           30 29      22 21                 0
// ------------------------------------------------------------------------------------
// |            |          |          |               |          |                    |
// |  Chip ID   |  Dest X  |  Dest Y  |  Final Route  |  Length  |    Header Payload  |
// |            |          |          |               |          |                    |
// ------------------------------------------------------------------------------------
////////////////////////////////////////////////////////////////////////////////////////////////











 //whether the routing is based on chipid or x y position
 //`define    ROUTING_CHIP_ID


 //defines for different topology, only one should be active
 //`define    NETWORK_TOPO_2D_MESH
 //`define    NETWORK_TOPO_3D_MESH

module dynamic_input_control(thanks_all_temp_out,
                             route_req_n_out, route_req_e_out, route_req_s_out, route_req_w_out, route_req_p_out,
                             default_ready_n, default_ready_e, default_ready_s, default_ready_w, default_ready_p,
                             tail_out, clk, reset,
                             my_loc_x_in, my_loc_y_in, my_chip_id_in,
                             abs_x, abs_y, abs_chip_id, final_bits, valid_in,
                             thanks_n, thanks_e, thanks_s, thanks_w, thanks_p,
                             length);

// begin port declarations

output thanks_all_temp_out;
output route_req_n_out;
output route_req_e_out;
output route_req_s_out;
output route_req_w_out;
output route_req_p_out;
output default_ready_n;
output default_ready_e;
output default_ready_s;
output default_ready_w;
output default_ready_p;
output tail_out;

input clk;
input reset;

input [8-1:0] my_loc_x_in;
input [8-1:0] my_loc_y_in;
input [14-1:0] my_chip_id_in;
input [8-1:0] abs_x;
input [8-1:0] abs_y;
input [14-1:0] abs_chip_id;
input [2:0] final_bits;
input valid_in;
input thanks_n;
input thanks_e;
input thanks_s;
input thanks_w;
input thanks_p;
input [8-1:0] length;

// end port declarations

//This is the state
reg [8-1:0] count_f;
reg header_last_f;
reg thanks_all_f;
reg count_zero_f;
reg count_one_f;
reg tail_last_f;

//inputs to the state
reg [8-1:0] count_temp;
wire header_last_temp;
wire thanks_all_temp;
wire count_zero_temp;
wire count_one_temp;
wire tail_last_temp;


//wires
wire header;
wire [8-1:0] count_minus_one;
wire length_zero; //for use in calculating tail bit for
                  //zero length messages on the default route
wire tail;

//wire regs
reg header_temp;

//assigns
assign thanks_all_temp = thanks_n | thanks_e | thanks_s | thanks_w | thanks_p;
assign header = valid_in & header_temp;
assign count_zero_temp = count_temp == 0;
assign count_one_temp = count_temp == 1;
assign thanks_all_temp_out = thanks_all_temp;
assign tail_out = tail;
assign count_minus_one = count_f - 1;
assign length_zero = length == 0;
assign header_last_temp = header_temp;
//nasty control logic which I really hope is correct
assign tail = (header & length_zero) | ((~thanks_all_f) & tail_last_f) | (thanks_all_f & count_one_f);
assign tail_last_temp = tail;

//instantiations
dynamic_input_route_request_calc tail_calc(.route_req_n(route_req_n_out),
                                           .route_req_e(route_req_e_out),
                                           .route_req_s(route_req_s_out),
                                           .route_req_w(route_req_w_out),
                                           .route_req_p(route_req_p_out),
                                           .default_ready_n(default_ready_n),
                                           .default_ready_e(default_ready_e),
                                           .default_ready_s(default_ready_s),
                                           .default_ready_w(default_ready_w),
                                           .default_ready_p(default_ready_p),
                                           .my_loc_x_in(my_loc_x_in),
                                           .my_loc_y_in(my_loc_y_in),
                                           .my_chip_id_in(my_chip_id_in),
                                           .abs_x(abs_x),
                                           .abs_y(abs_y),
                                           .abs_chip_id(abs_chip_id),
                                           .final_bits(final_bits),
                                           .length(length),
                                           .header_in(header));

always @ (header_last_f or thanks_all_f or count_zero_f)
begin
        case({header_last_f, count_zero_f, thanks_all_f})
        3'b000: header_temp <= 1'b0;
        3'b001: header_temp <= 1'b0;
        3'b010: header_temp <= 1'b0;
        3'b011: header_temp <= 1'b1;
        3'b100: header_temp <= 1'b1;
        //yanqiz change 0->1
        3'b101: header_temp <= 1'b0;
        3'b110: header_temp <= 1'b1;
        3'b111: header_temp <= 1'b1;
        default:
                header_temp <= 1'b1;
        endcase
end

always @ (header or thanks_all_f or count_f or count_minus_one or length)
begin
        if(header)
        begin
                count_temp <= length;
        end
        else
        begin
                if(thanks_all_f)
                begin
                        count_temp <= count_minus_one;
                end
                else
                begin
                        count_temp <= count_f;
                end
        end
end

//take care of synchronous stuff
always @ (posedge clk)
begin
        if(reset)
        begin
                count_f <= 5'd0;
                header_last_f <= 1'b1;
                thanks_all_f <= 1'b0;
                count_zero_f <= 1'b1; //I think that this must reset to 1 to work!
                count_one_f <= 1'b0;
                tail_last_f <= 1'b0;
        end
        else
        begin
                count_f <= count_temp;
                header_last_f <= header_last_temp;
                thanks_all_f <= thanks_all_temp;
                count_zero_f <= count_zero_temp;
                count_one_f <= count_one_temp;
                tail_last_f <= tail_last_temp;
        end
end
endmodule

/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

//Function: This generates all of the route_request lines and the default_ready lines from
//the absolute location of the tile, the abs address of the message, and the fbits of the message
//
//State:
//NONE
//
//Instantiates:
//
//Note:
//

/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

/////////////////////////////////////////////////////////////////////////////////////////////
// 63         50 49      42 41      34 33           30 29      22 21                 0
// ------------------------------------------------------------------------------------
// |            |          |          |               |          |                    |
// |  Chip ID   |  Dest X  |  Dest Y  |  Final Route  |  Length  |    Header Payload  |
// |            |          |          |               |          |                    |
// ------------------------------------------------------------------------------------
////////////////////////////////////////////////////////////////////////////////////////////////











 //whether the routing is based on chipid or x y position
 //`define    ROUTING_CHIP_ID


 //defines for different topology, only one should be active
 //`define    NETWORK_TOPO_2D_MESH
 //`define    NETWORK_TOPO_3D_MESH


module dynamic_input_route_request_calc(route_req_n, route_req_e, route_req_s, route_req_w, route_req_p,
                                        default_ready_n, default_ready_e, default_ready_s, default_ready_w, default_ready_p,
                                        my_loc_x_in, my_loc_y_in, my_chip_id_in, abs_x, abs_y, abs_chip_id, final_bits, length, header_in);

// begin port declarations

output route_req_n;
output route_req_e;
output route_req_s;
output route_req_w;
output route_req_p;
output default_ready_n;
output default_ready_e;
output default_ready_s;
output default_ready_w;
output default_ready_p;

input [8-1:0] my_loc_x_in;
input [8-1:0] my_loc_y_in;
input [14-1:0] my_chip_id_in;
input [8-1:0] abs_x;
input [8-1:0] abs_y;
input [14-1:0] abs_chip_id;

input [2:0] final_bits;
input [8-1:0] length;
input header_in;

// end port declarations

//fbit declarations






//This is the state
//NONE

//inputs to the state
//NONE

//wires
wire more_x;
wire more_y;
wire less_x;
wire less_y;
wire done_x;
wire done_y;
wire off_chip;

wire done;

wire north;
wire east;
wire south;
wire west;
wire proc;

wire north_calc;
wire south_calc;

//wire regs

//assigns

assign off_chip = abs_chip_id != my_chip_id_in;
assign more_x = off_chip ? 0 > my_loc_x_in : abs_x > my_loc_x_in;
assign more_y = off_chip ? 0 > my_loc_y_in : abs_y > my_loc_y_in;

assign less_x = off_chip ? 0 < my_loc_x_in : abs_x < my_loc_x_in;
assign less_y = off_chip ? 0 < my_loc_y_in : abs_y < my_loc_y_in;

assign done_x = off_chip ? 0 == my_loc_x_in : abs_x == my_loc_x_in;
assign done_y = off_chip ? 0 == my_loc_y_in : abs_y == my_loc_y_in;

assign done = done_x & done_y;

assign north_calc = done_x & less_y;
assign south_calc = done_x & more_y;

assign north = north_calc | ((final_bits == 3'b101) & done);
assign south = south_calc | ((final_bits == 3'b011) & done);
assign east = more_x | ((final_bits == 3'b100) & done);
assign west = less_x | ((final_bits == 3'b010) & done);
assign proc = ((final_bits == 3'b000) & done);

assign route_req_n = header_in & north;
assign route_req_e = header_in & east;
assign route_req_s = header_in & south;
assign route_req_w = header_in & west;
assign route_req_p = header_in & proc;

assign default_ready_n = route_req_n;
assign default_ready_e = route_req_e;
assign default_ready_s = route_req_s;
assign default_ready_w = route_req_w;
assign default_ready_p = route_req_p;

//instantiations

endmodule

/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

//Function: This ties together a 16 space NIB with the dynamic_input_control logic
//
//State:
//
//Instantiates: dynamic_input_control, network_input_blk_4elmt
//
//Note:
//
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

/////////////////////////////////////////////////////////////////////////////////////////////
// 63         50 49      42 41      34 33           30 29      22 21                 0
// ------------------------------------------------------------------------------------
// |            |          |          |               |          |                    |
// |  Chip ID   |  Dest X  |  Dest Y  |  Final Route  |  Length  |    Header Payload  |
// |            |          |          |               |          |                    |
// ------------------------------------------------------------------------------------
////////////////////////////////////////////////////////////////////////////////////////////////











 //whether the routing is based on chipid or x y position
 //`define    ROUTING_CHIP_ID


 //defines for different topology, only one should be active
 //`define    NETWORK_TOPO_2D_MESH
 //`define    NETWORK_TOPO_3D_MESH


module dynamic_input_top_16(route_req_n_out, route_req_e_out, route_req_s_out, route_req_w_out, route_req_p_out, default_ready_n_out, default_ready_e_out, default_ready_s_out, default_ready_w_out, default_ready_p_out, tail_out, yummy_out, data_out, valid_out, clk, reset, my_loc_x_in, my_loc_y_in, my_chip_id_in, valid_in, data_in, thanks_n, thanks_e, thanks_s, thanks_w, thanks_p);

// begin port declarations

output route_req_n_out;
output route_req_e_out;
output route_req_s_out;
output route_req_w_out;
output route_req_p_out;
output default_ready_n_out;
output default_ready_e_out;
output default_ready_s_out;
output default_ready_w_out;
output default_ready_p_out;
output tail_out;
output yummy_out;
output [64-1:0] data_out;
output valid_out;
//yanqi fixed

input clk;
input reset;

input [8-1:0] my_loc_x_in;
input [8-1:0] my_loc_y_in;
input [14-1:0] my_chip_id_in;
input valid_in;
input [64-1:0] data_in;
input thanks_n;
input thanks_e;
input thanks_s;
input thanks_w;
input thanks_p;

// end port declarations

//This is the state

//inputs to the state

//wires
wire thanks_all_temp;
wire valid_out_internal;
wire [64-1:0] data_out_internal;
wire [64-1:0] data_out_internal_pre;
//wire regs

//assigns
assign valid_out = valid_out_internal;
assign data_out = data_out_internal;

//instantiations
network_input_blk_multi_out #(.LOG2_NUMBER_FIFO_ELEMENTS(4)) NIB(.clk(clk), .reset(reset), .data_in(data_in), .valid_in(valid_in), .yummy_out(yummy_out), .thanks_in(thanks_all_temp), .data_val(data_out_internal_pre), .data_val1(), .data_avail(valid_out_internal));

// need buffering for this one
// rBuffer #(`DATA_WIDTH, 1) NIB_buf(.A(data_out_internal_pre), .Z(data_out_internal));
assign data_out_internal = data_out_internal_pre;

// Change fbits position in order to be compatible
dynamic_input_control control(.thanks_all_temp_out(thanks_all_temp), .route_req_n_out(route_req_n_out), .route_req_e_out(route_req_e_out), .route_req_s_out(route_req_s_out), .route_req_w_out(route_req_w_out), .route_req_p_out(route_req_p_out), .default_ready_n(default_ready_n_out), .default_ready_e(default_ready_e_out), .default_ready_s(default_ready_s_out), .default_ready_w(default_ready_w_out), .default_ready_p(default_ready_p_out), .tail_out(tail_out), .clk(clk), .reset(reset), .my_loc_x_in(my_loc_x_in), .my_loc_y_in(my_loc_y_in),
    .my_chip_id_in(my_chip_id_in), .abs_x(data_out_internal[64-14-1:64-14-8]), .abs_y(data_out_internal[64-14-8-1:64-14-2*8]), .abs_chip_id(data_out_internal[64-1:64-14]),.final_bits(data_out_internal[64-14-2*8-2:64-14-2*8-4]), .valid_in(valid_out_internal), .thanks_n(thanks_n), .thanks_e(thanks_e), .thanks_s(thanks_s), .thanks_w(thanks_w), .thanks_p(thanks_p), .length(data_out_internal[64-14-2*8-5:64-14-2*8-4-8]));

endmodule
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

//Function: This ties together a 4 space NIB with the dynamic_input_control logic
//
//State:
//
//Instantiates: dynamic_input_control, network_input_blk_4elmt
//
//Note:
//
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

/////////////////////////////////////////////////////////////////////////////////////////////
// 63         50 49      42 41      34 33           30 29      22 21                 0
// ------------------------------------------------------------------------------------
// |            |          |          |               |          |                    |
// |  Chip ID   |  Dest X  |  Dest Y  |  Final Route  |  Length  |    Header Payload  |
// |            |          |          |               |          |                    |
// ------------------------------------------------------------------------------------
////////////////////////////////////////////////////////////////////////////////////////////////











 //whether the routing is based on chipid or x y position
 //`define    ROUTING_CHIP_ID


 //defines for different topology, only one should be active
 //`define    NETWORK_TOPO_2D_MESH
 //`define    NETWORK_TOPO_3D_MESH


module dynamic_input_top_4(route_req_n_out, route_req_e_out, route_req_s_out, route_req_w_out, route_req_p_out,
                           default_ready_n_out, default_ready_e_out, default_ready_s_out, default_ready_w_out, default_ready_p_out,
                           tail_out, yummy_out, data_out, valid_out, clk, reset,
                           my_loc_x_in, my_loc_y_in, my_chip_id_in,  valid_in, data_in,
                           thanks_n, thanks_e, thanks_s, thanks_w, thanks_p);

// begin port declarations

output route_req_n_out;
output route_req_e_out;
output route_req_s_out;
output route_req_w_out;
output route_req_p_out;
output default_ready_n_out;
output default_ready_e_out;
output default_ready_s_out;
output default_ready_w_out;
output default_ready_p_out;
output tail_out;
output yummy_out;
output [64-1:0] data_out;
output valid_out;

input clk;
input reset;

input [8-1:0] my_loc_x_in;
input [8-1:0] my_loc_y_in;
input [14-1:0] my_chip_id_in;
input valid_in;
input [64-1:0] data_in;
input thanks_n;
input thanks_e;
input thanks_s;
input thanks_w;
input thanks_p;

// end port declarations

//This is the state

//inputs to the state

//wires
wire thanks_all_temp;
wire [64-1:0] data_internal;
wire valid_out_internal;

//wire regs

//assigns
assign valid_out = valid_out_internal;

//instantiations
network_input_blk_multi_out #(.LOG2_NUMBER_FIFO_ELEMENTS(2)) NIB(.clk(clk),
                                      .reset(reset),
                                      .data_in(data_in),
                                      .valid_in(valid_in),
                                      .yummy_out(yummy_out),
                                      .thanks_in(thanks_all_temp),
                                      .data_val(data_out),
                                      .data_val1(data_internal), // same as data_val, done for buffering
                                      .data_avail(valid_out_internal));

dynamic_input_control control(.thanks_all_temp_out(thanks_all_temp),
                              .route_req_n_out(route_req_n_out),
                              .route_req_e_out(route_req_e_out),
                              .route_req_s_out(route_req_s_out),
                              .route_req_w_out(route_req_w_out),
                              .route_req_p_out(route_req_p_out),
                              .default_ready_n(default_ready_n_out),
                              .default_ready_e(default_ready_e_out),
                              .default_ready_s(default_ready_s_out),
                              .default_ready_w(default_ready_w_out),
                              .default_ready_p(default_ready_p_out),
                              .tail_out(tail_out),
                              .clk(clk), .reset(reset),
                              .my_loc_x_in(my_loc_x_in),
                              .my_loc_y_in(my_loc_y_in),
                              .my_chip_id_in(my_chip_id_in),
                              .abs_x(data_internal[64-14-1:64-14-8]),
                              .abs_y(data_internal[64-14-8-1:64-14-2*8]),
                              .abs_chip_id(data_internal[64-1:64-14]),
                              .final_bits(data_internal[64-14-2*8-2:64-14-2*8-4]),
                              .valid_in(valid_out_internal),
                              .thanks_n(thanks_n), .thanks_e(thanks_e), .thanks_s(thanks_s), .thanks_w(thanks_w), .thanks_p(thanks_p),
                              .length(data_internal[64-14-2*8-5:64-14-2*8-4-8]));

endmodule
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

//Function: This maintains the control of the output mux for a dynamic network port.
//	This does the scheduling for the output.
//	It takes as input what all of the other ports want to do and outputs the control
//	for the respective crossbar mux and the validOut signal for a respective direction.
//
//Instantiates:
//
//State: current_route_f [2:0], planned_f
//
//Note:
//
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

/////////////////////////////////////////////////////////////////////////////////////////////
// 63         50 49      42 41      34 33           30 29      22 21                 0
// ------------------------------------------------------------------------------------
// |            |          |          |               |          |                    |
// |  Chip ID   |  Dest X  |  Dest Y  |  Final Route  |  Length  |    Header Payload  |
// |            |          |          |               |          |                    |
// ------------------------------------------------------------------------------------
////////////////////////////////////////////////////////////////////////////////////////////////











 //whether the routing is based on chipid or x y position
 //`define    ROUTING_CHIP_ID


 //defines for different topology, only one should be active
 //`define    NETWORK_TOPO_2D_MESH
 //`define    NETWORK_TOPO_3D_MESH


module dynamic_output_control(thanks_a, thanks_b, thanks_c, thanks_d, thanks_x, valid_out, current_route, ec_wants_to_send_but_cannot, clk, reset, route_req_a_in, route_req_b_in, route_req_c_in, route_req_d_in, route_req_x_in, tail_a_in, tail_b_in, tail_c_in, tail_d_in, tail_x_in, valid_out_temp, default_ready, space_avail);

// begin port declarations

output thanks_a;
output thanks_b;
output thanks_c;
output thanks_d;
output thanks_x;

output valid_out;

output [2:0] current_route;
output    ec_wants_to_send_but_cannot;

input clk;
input reset;

input route_req_a_in;
input route_req_b_in;
input route_req_c_in;
input route_req_d_in;
input route_req_x_in;

input tail_a_in;
input tail_b_in;
input tail_c_in;
input tail_d_in;
input tail_x_in;

input valid_out_temp;

input default_ready;

input space_avail;

// end port declarations







//This is the state
reg [2:0]current_route_f;
reg planned_f;

//inputs to the state
wire [2:0] current_route_temp;

//wires
wire planned_or_default;
// wire route_req_all_or;
wire route_req_all_or_with_planned;
wire route_req_all_but_default;
wire valid_out_internal;

//wire regs
reg new_route_needed;
reg planned_temp;
reg [2:0] new_route;
reg tail_current_route;
/*reg route_req_planned;*/
reg route_req_a_mask;
reg route_req_b_mask;
reg route_req_c_mask;
reg route_req_d_mask;
reg route_req_x_mask;


//more wire regs for the thanks lines
reg thanks_a;
reg thanks_b;
reg thanks_c;
reg thanks_d;
reg thanks_x;

reg    ec_wants_to_send_but_cannot;

//assigns
assign planned_or_default = planned_f | default_ready;
assign valid_out_internal = valid_out_temp & planned_or_default & space_avail;

// mbt: if valid_out_interal is a critical path, we can use some "bleeder" gates to decrease the load of the ec stuff
always @(posedge clk)
  begin
     ec_wants_to_send_but_cannot <= valid_out_temp & planned_or_default & ~space_avail;
  end

/* assign route_req_all_or = route_req_a_in | route_req_b_in | route_req_c_in | route_req_d_in | route_req_x_in; */
assign current_route_temp = (new_route_needed) ? new_route : current_route_f;
assign current_route = current_route_f;
//this is everything except the currentl planned route's request
assign route_req_all_or_with_planned = (route_req_a_in & route_req_a_mask) | (route_req_b_in & route_req_b_mask) | (route_req_c_in & route_req_c_mask) | (route_req_d_in & route_req_d_mask) | (route_req_x_in & route_req_x_mask);
//calculates whether the nib that we are going to has space
assign route_req_all_but_default = route_req_b_in | route_req_c_in | route_req_d_in | route_req_x_in;

assign valid_out = valid_out_internal;

//instantiations
//space_avail space(.valid(valid_out_internal), .clk(clk), .reset(reset), .yummy(yummy_in), .spc_avail(space_avail));
//THIS HAS BEEN MOVED to dynamic_output_top

//a mux for current_route_f's tail bit
always @ (current_route_f or tail_a_in or tail_b_in or tail_c_in or tail_d_in or tail_x_in)
begin
	(* parallel_case *) case(current_route_f)
	3'b000:
	begin
		tail_current_route <= tail_a_in;
	end
	3'b001:
	begin
		tail_current_route <= tail_b_in;
	end
	3'b010:
	begin
		tail_current_route <= tail_c_in;
	end
	3'b011:
	begin
		tail_current_route <= tail_d_in;
	end
	3'b100:
	begin
		tail_current_route <= tail_x_in;
	end
	default:
	begin
		tail_current_route <= 1'bx; //This is probably dangerous, but I
					    //really need the speed here and
					    //I don't want the synthesizer to
					    //mess me up if I put a real value
					    //here
	end
	endcase
end

always @ (current_route_f or valid_out_internal)
begin
	case(current_route_f)
	3'b000:
	begin
		thanks_a <= valid_out_internal;
		thanks_b <= 1'b0;
		thanks_c <= 1'b0;
		thanks_d <= 1'b0;
		thanks_x <= 1'b0;
	end
	3'b001:
	begin
		thanks_a <= 1'b0;
		thanks_b <= valid_out_internal;
		thanks_c <= 1'b0;
		thanks_d <= 1'b0;
		thanks_x <= 1'b0;
	end
	3'b010:
	begin
		thanks_a <= 1'b0;
		thanks_b <= 1'b0;
		thanks_c <= valid_out_internal;
		thanks_d <= 1'b0;
		thanks_x <= 1'b0;
	end
	3'b011:
	begin
		thanks_a <= 1'b0;
		thanks_b <= 1'b0;
		thanks_c <= 1'b0;
		thanks_d <= valid_out_internal;
		thanks_x <= 1'b0;
	end
	3'b100:
	begin
		thanks_a <= 1'b0;
		thanks_b <= 1'b0;
		thanks_c <= 1'b0;
		thanks_d <= 1'b0;
		thanks_x <= valid_out_internal;
	end
	default:
	begin
		thanks_a <= 1'bx;
		thanks_b <= 1'bx;
		thanks_c <= 1'bx;
		thanks_d <= 1'bx;
		thanks_x <= 1'bx;
					//once again this is very dangerous
					//but I want to see the timing this
					//way and we sould never get here
	end
	endcase
end

//this is the rotating priority encoder
/*
always @(current_route_f or route_req_a_in or route_req_b_in or route_req_c_in or route_req_d_in or route_req_x_in)
begin
	case(current_route_f)
	`ROUTE_A:
	begin
		new_route <= (route_req_b_in)?`ROUTE_B:((route_req_c_in)?`ROUTE_C:((route_req_d_in)?`ROUTE_D:((route_req_x_in)?`ROUTE_X:`ROUTE_A)));
	end
	`ROUTE_B:
	begin
		new_route <= (route_req_c_in)?`ROUTE_C:((route_req_d_in)?`ROUTE_D:((route_req_x_in)?`ROUTE_X:((route_req_a_in)?`ROUTE_A:((route_req_b_in)?`ROUTE_B:`ROUTE_A))));
	end
	`ROUTE_C:
	begin
		new_route <= (route_req_d_in)?`ROUTE_D:((route_req_x_in)?`ROUTE_X:((route_req_a_in)?`ROUTE_A:((route_req_b_in)?`ROUTE_B:((route_req_c_in)?`ROUTE_C:`ROUTE_A))));
	end
	`ROUTE_D:
	begin
		new_route <= (route_req_c_in)?`ROUTE_C:((route_req_d_in)?`ROUTE_D:((route_req_x_in)?`ROUTE_X:((route_req_a_in)?`ROUTE_A:((route_req_b_in)?`ROUTE_B:`ROUTE_A))));
	end
	`ROUTE_X:
	begin
		new_route <= (route_req_x_in)?`ROUTE_X:((route_req_a_in)?`ROUTE_A:((route_req_b_in)?`ROUTE_B:((route_req_c_in)?`ROUTE_C:((route_req_d_in)?`ROUTE_D:`ROUTE_A))));
	end
	default:
	begin
		new_route <= `ROUTE_A;
			//this one I am not willing to chince on
	end
	endcase
end
*/
//end the rotating priority encoder

//this is the rotating priority encoder
always @(current_route_f or route_req_a_in or route_req_b_in or route_req_c_in or route_req_d_in or route_req_x_in)
begin
	case(current_route_f)
	3'b000:
	begin
		new_route <= (route_req_b_in)?3'b001:((route_req_c_in)?3'b010:((route_req_d_in)?3'b011:((route_req_x_in)?3'b100:3'b000)));
	end
	3'b001:
	begin
		new_route <= (route_req_c_in)?3'b010:((route_req_d_in)?3'b011:((route_req_x_in)?3'b100:((route_req_a_in)?3'b000:3'b000)));
	end
	3'b010:
	begin
		new_route <= (route_req_d_in)?3'b011:((route_req_x_in)?3'b100:((route_req_a_in)?3'b000:((route_req_b_in)?3'b001:3'b000)));
	end
	3'b011:
	begin
		new_route <= (route_req_x_in)?3'b100:((route_req_a_in)?3'b000:((route_req_b_in)?3'b001:((route_req_c_in)?3'b010:3'b000)));
	end
	3'b100:
	begin
		new_route <= (route_req_a_in)?3'b000:((route_req_b_in)?3'b001:((route_req_c_in)?3'b010:((route_req_d_in)?3'b011:3'b000)));
	end
	default:
	begin
		new_route <= 3'b000;
			//this one I am not willing to chince on
	end
	endcase
end
//end the rotating priority encoder

always @(current_route_f or planned_f)
begin
	if(planned_f)
	begin
		case(current_route_f)
		3'b000:
			begin
				route_req_a_mask <= 1'b0;
				route_req_b_mask <= 1'b1;
				route_req_c_mask <= 1'b1;
				route_req_d_mask <= 1'b1;
				route_req_x_mask <= 1'b1;
			end
		3'b001:
			begin
				route_req_a_mask <= 1'b1;
				route_req_b_mask <= 1'b0;
				route_req_c_mask <= 1'b1;
				route_req_d_mask <= 1'b1;
				route_req_x_mask <= 1'b1;
			end
		3'b010:
			begin
				route_req_a_mask <= 1'b1;
				route_req_b_mask <= 1'b1;
				route_req_c_mask <= 1'b0;
				route_req_d_mask <= 1'b1;
				route_req_x_mask <= 1'b1;
			end
		3'b011:
			begin
				route_req_a_mask <= 1'b1;
				route_req_b_mask <= 1'b1;
				route_req_c_mask <= 1'b1;
				route_req_d_mask <= 1'b0;
				route_req_x_mask <= 1'b1;
			end
		3'b100:
			begin
				route_req_a_mask <= 1'b1;
				route_req_b_mask <= 1'b1;
				route_req_c_mask <= 1'b1;
				route_req_d_mask <= 1'b1;
				route_req_x_mask <= 1'b0;
			end
		default:
			begin
				route_req_a_mask <= 1'b1;
				route_req_b_mask <= 1'b1;
				route_req_c_mask <= 1'b1;
				route_req_d_mask <= 1'b1;
				route_req_x_mask <= 1'b1;
			end
		endcase
	end
	else
	begin
		route_req_a_mask <= 1'b1;
		route_req_b_mask <= 1'b1;
		route_req_c_mask <= 1'b1;
		route_req_d_mask <= 1'b1;
		route_req_x_mask <= 1'b1;
	end
end

//calculation of new_route_needed
always @ (planned_f or tail_current_route or valid_out_internal or default_ready)
begin
	(* parallel_case *) case({default_ready, valid_out_internal, tail_current_route, planned_f})
	4'b0000:	new_route_needed <= 1'b1;
	4'b0001:	new_route_needed <= 1'b0;
	4'b0010:	new_route_needed <= 1'b1;
	4'b0011:	new_route_needed <= 1'b0;
	4'b0100:	new_route_needed <= 1'b0;	//This line should probably be turned to a 1 if we are to implement "Mikes fairness" schema
	4'b0101:	new_route_needed <= 1'b0;	//This line should probably be turned to a 1 if we are to implement "Mikes fairness" schema
	4'b0110:	new_route_needed <= 1'b1;
	4'b0111:	new_route_needed <= 1'b1;

	4'b1000:	new_route_needed <= 1'b1;
	4'b1001:	new_route_needed <= 1'b0;
//	4'b1010:	new_route_needed <= 1'b0;	//this is scary CHECK THIS BEFORE CHIP SHIPS
	4'b1010:	new_route_needed <= 1'b1;	//this is the case where there is a zero length message on the default route that is not being sent this cycle therefore we should let something be locked in, but it doesn't necessarily just the default route.  Remember that the default route is the last choice in the priority encoder, but if nothing else is requesting, the default route will be planned and locked in.
    //yanqiz change from 0->1
	4'b1011:	new_route_needed <= 1'b0;
	4'b1100:	new_route_needed <= 1'b0;
	4'b1101:	new_route_needed <= 1'b0;
	4'b1110:	new_route_needed <= 1'b1;
	4'b1111:	new_route_needed <= 1'b1;
	default:	new_route_needed <= 1'b1;
			//safest choice should never occur
	endcase
end

//calculation of planned_temp
//random five input function
always @ (planned_f or tail_current_route or valid_out_internal or default_ready or route_req_all_or_with_planned or route_req_all_but_default)
begin
	(* parallel_case *) case({route_req_all_or_with_planned, default_ready, valid_out_internal, tail_current_route, planned_f})
	5'b00000:	planned_temp <= 1'b0;
	5'b00001:	planned_temp <= 1'b1;
	5'b00010:	planned_temp <= 1'b0;
	5'b00011:	planned_temp <= 1'b1;
	5'b00100:	planned_temp <= 1'b0;	//error what did we just send
	5'b00101:	planned_temp <= 1'b1;
	5'b00110:	planned_temp <= 1'b0;	//error
	5'b00111:	planned_temp <= 1'b0;

	5'b01000:	planned_temp <= 1'b0;	//error
	5'b01001:	planned_temp <= 1'b1;
	5'b01010:	planned_temp <= 1'b0;	//This actually cannot happen
	5'b01011:	planned_temp <= 1'b1;
	5'b01100:	planned_temp <= 1'b0;	//What did we just send?
	5'b01101:	planned_temp <= 1'b1;
	5'b01110:	planned_temp <= 1'b0;	//error
	5'b01111:	planned_temp <= 1'b0;	//The default route is
						//currently planned but
						//is ending this cycle
						//and nobody else wants to go
						//This is a delayed zero length
						//message on the through route
	5'b10000:	planned_temp <= 1'b1;
	5'b10001:	planned_temp <= 1'b1;
	5'b10010:	planned_temp <= 1'b1;
	5'b10011:	planned_temp <= 1'b1;
	5'b10100:	planned_temp <= 1'b1;
	5'b10101:	planned_temp <= 1'b1;
	5'b10110:	planned_temp <= 1'b1;
	5'b10111:	planned_temp <= 1'b1;
	5'b11000:	planned_temp <= 1'b1;
	5'b11001:	planned_temp <= 1'b1;
	5'b11010:	planned_temp <= 1'b1;
	5'b11011:	planned_temp <= 1'b1;
	5'b11100:	planned_temp <= 1'b1;
	5'b11101:	planned_temp <= 1'b1;
//	5'b11110:	planned_temp <= 1'b0;	//This is wrong becasue if
						//there is a default
						//route zero length message
						//that is being sent and
						//somebody else wants to send
						//on the next cycle
	5'b11110:	planned_temp <= route_req_all_but_default;
	5'b11111:	planned_temp <= 1'b1;
	default:	planned_temp <= 1'b0;
	endcase
end

//take care of syncrhonous stuff
always @(posedge clk)
begin
	if(reset)
	begin
		current_route_f <= 3'd0;
		planned_f <= 1'd0;
	end
	else
	begin
		current_route_f <= current_route_temp;
		planned_f <= planned_temp;
	end
end

endmodule
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

//Function: This is the Datapath for the dynamic output
//
//Instantiates:
//
//State: NONE
//
//Note:
//
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

/////////////////////////////////////////////////////////////////////////////////////////////
// 63         50 49      42 41      34 33           30 29      22 21                 0
// ------------------------------------------------------------------------------------
// |            |          |          |               |          |                    |
// |  Chip ID   |  Dest X  |  Dest Y  |  Final Route  |  Length  |    Header Payload  |
// |            |          |          |               |          |                    |
// ------------------------------------------------------------------------------------
////////////////////////////////////////////////////////////////////////////////////////////////











 //whether the routing is based on chipid or x y position
 //`define    ROUTING_CHIP_ID


 //defines for different topology, only one should be active
 //`define    NETWORK_TOPO_2D_MESH
 //`define    NETWORK_TOPO_3D_MESH


module dynamic_output_datapath(data_out, valid_out_temp, data_a_in, data_b_in, data_c_in, data_d_in, data_x_in, valid_a_in, valid_b_in, valid_c_in, valid_d_in, valid_x_in, current_route_in);

// begin port declarations

output [64-1:0] data_out;
output valid_out_temp;

input [64-1:0] data_a_in;
input [64-1:0] data_b_in;
input [64-1:0] data_c_in;
input [64-1:0] data_d_in;
input [64-1:0] data_x_in;
input valid_a_in;
input valid_b_in;
input valid_c_in;
input valid_d_in;
input valid_x_in;
input [2:0] current_route_in;

// end port declarations

// `define ROUTE_A 3'b000
// `define ROUTE_B 3'b001
// `define ROUTE_C 3'b010
// `define ROUTE_D 3'b011
// `define ROUTE_X 3'b100

//This is the state
//NONE HERE

//inputs to the state
//NOTHING HERE EITHER

//wires

//wire regs

//assigns

//instantiations
one_of_five #(64) data_mux(.in0(data_a_in), .in1(data_b_in), .in2(data_c_in), .in3(data_d_in), .in4(data_x_in), .sel(current_route_in), .out(data_out));
one_of_five #(1) valid_mux(.in0(valid_a_in), .in1(valid_b_in), .in2(valid_c_in), .in3(valid_d_in), .in4(valid_x_in), .sel(current_route_in), .out(valid_out_temp));

endmodule
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

//Function: The top level module that glues together the datapath and
//the control for a dynamic_output port
//
//Instantiates: dynamic_output_control dynamic_output_datapath space_avail
//
//State: NONE
//
//Note:
//
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

/////////////////////////////////////////////////////////////////////////////////////////////
// 63         50 49      42 41      34 33           30 29      22 21                 0
// ------------------------------------------------------------------------------------
// |            |          |          |               |          |                    |
// |  Chip ID   |  Dest X  |  Dest Y  |  Final Route  |  Length  |    Header Payload  |
// |            |          |          |               |          |                    |
// ------------------------------------------------------------------------------------
////////////////////////////////////////////////////////////////////////////////////////////////











 //whether the routing is based on chipid or x y position
 //`define    ROUTING_CHIP_ID


 //defines for different topology, only one should be active
 //`define    NETWORK_TOPO_2D_MESH
 //`define    NETWORK_TOPO_3D_MESH


module dynamic_output_top(data_out, thanks_a_out, thanks_b_out, thanks_c_out, thanks_d_out, thanks_x_out, valid_out, popped_interrupt_mesg_out, popped_memory_ack_mesg_out, popped_memory_ack_mesg_out_sender, ec_wants_to_send_but_cannot, clk, reset, route_req_a_in, route_req_b_in, route_req_c_in, route_req_d_in, route_req_x_in, tail_a_in, tail_b_in, tail_c_in, tail_d_in, tail_x_in, data_a_in, data_b_in, data_c_in, data_d_in, data_x_in, valid_a_in, valid_b_in, valid_c_in, valid_d_in, valid_x_in, default_ready_in, yummy_in);

parameter KILL_HEADERS = 1'b0;

// begin port declarations
output [64-1:0] data_out;

output thanks_a_out;
output thanks_b_out;
output thanks_c_out;
output thanks_d_out;
output thanks_x_out;

output valid_out;

output popped_interrupt_mesg_out;
output popped_memory_ack_mesg_out;
output [9:0] popped_memory_ack_mesg_out_sender;

output ec_wants_to_send_but_cannot;

input clk;
input reset;

input route_req_a_in;
input route_req_b_in;
input route_req_c_in;
input route_req_d_in;
input route_req_x_in;

input tail_a_in;
input tail_b_in;
input tail_c_in;
input tail_d_in;
input tail_x_in;

input [64-1:0] data_a_in;
input [64-1:0] data_b_in;
input [64-1:0] data_c_in;
input [64-1:0] data_d_in;
input [64-1:0] data_x_in;
input valid_a_in;
input valid_b_in;
input valid_c_in;
input valid_d_in;
input valid_x_in;

input default_ready_in;
input yummy_in;

// end port declarations







//This is the state
//NOTHING HERE BUT US CHICKENS

//inputs to the state
//NOTHING HERE EITHER

//wires
wire valid_out_temp_connection;
wire [2:0] current_route_connection;
wire space_avail_connection;
wire valid_out_pre;
wire data_out_len_zero;
wire data_out_interrupt_user_bits_set;
wire data_out_memory_ack_user_bits_set;
wire [64-1:0] data_out_internal;
wire valid_out_internal;

//wire regs
reg current_route_req;

//assigns
assign valid_out_internal = valid_out_pre & ~(KILL_HEADERS & current_route_req);
assign data_out_len_zero = data_out_internal[64-14-2*8-4:64-14-2*8-3-8] == 8'd0;
assign data_out_interrupt_user_bits_set = data_out_internal[23:20] == 4'b1111;
assign data_out_memory_ack_user_bits_set = data_out_internal[23:20] == 4'b1110;
//assign popped_zero_len_mesg_out = data_out_len_zero & valid_out_pre & (KILL_HEADERS & current_route_req);
assign popped_interrupt_mesg_out = data_out_interrupt_user_bits_set & data_out_len_zero & valid_out_pre & (KILL_HEADERS & current_route_req);
assign popped_memory_ack_mesg_out = data_out_memory_ack_user_bits_set & data_out_len_zero & valid_out_pre & (KILL_HEADERS & current_route_req);
assign popped_memory_ack_mesg_out_sender = data_out_internal[19:10] & { 10 { KILL_HEADERS} };

assign data_out = data_out_internal;
assign valid_out = valid_out_internal;

//instantiations
space_avail_top space(.valid(valid_out_internal), .clk(clk), .reset(reset), .yummy(yummy_in),.spc_avail(space_avail_connection));
dynamic_output_datapath datapath(.data_out(data_out_internal), .valid_out_temp(valid_out_temp_connection), .data_a_in(data_a_in), .data_b_in(data_b_in), .data_c_in(data_c_in), .data_d_in(data_d_in), .data_x_in(data_x_in), .valid_a_in(valid_a_in), .valid_b_in(valid_b_in), .valid_c_in(valid_c_in), .valid_d_in(valid_d_in), .valid_x_in(valid_x_in), .current_route_in(current_route_connection));

dynamic_output_control control(.thanks_a(thanks_a_out), .thanks_b(thanks_b_out), .thanks_c(thanks_c_out), .thanks_d(thanks_d_out), .thanks_x(thanks_x_out), .valid_out(valid_out_pre), .current_route(current_route_connection), .ec_wants_to_send_but_cannot(ec_wants_to_send_but_cannot), .clk(clk), .reset(reset), .route_req_a_in(route_req_a_in), .route_req_b_in(route_req_b_in), .route_req_c_in(route_req_c_in), .route_req_d_in(route_req_d_in), .route_req_x_in(route_req_x_in), .tail_a_in(tail_a_in), .tail_b_in(tail_b_in), .tail_c_in(tail_c_in), .tail_d_in(tail_d_in), .tail_x_in(tail_x_in), .valid_out_temp(valid_out_temp_connection), .default_ready(default_ready_in), .space_avail(space_avail_connection));
//NOTE TO READER.  I like the way that these instantiations look so if it
//really bothers you go open this in emacs and re-tabify everything
//and don't complain to me

always @ (current_route_connection or route_req_a_in or route_req_b_in or route_req_c_in or route_req_d_in or route_req_x_in)
begin
	case(current_route_connection)
	3'b000:	current_route_req <= route_req_a_in;
	3'b001:	current_route_req <= route_req_b_in;
	3'b010:	current_route_req <= route_req_c_in;
	3'b011:	current_route_req <= route_req_d_in;
	3'b100:	current_route_req <= route_req_x_in;
	default:	current_route_req <= 1'bx;
	endcase
end

endmodule
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

//File: dynamic_node_top_wrap.v
////Creator: Michael McKeown
////Created: Sept. 21, 2014
////
////Function: This wraps the dynamic_node top and ties off signals
//            we will not be using at the tile level
////
////State:
////
////Instantiates: dynamic_node_top
////
////

// Copyright (c) 2015 Princeton University
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//     * Redistributions of source code must retain the above copyright
//       notice, this list of conditions and the following disclaimer.
//     * Redistributions in binary form must reproduce the above copyright
//       notice, this list of conditions and the following disclaimer in the
//       documentation and/or other materials provided with the distribution.
//     * Neither the name of Princeton University nor the
//       names of its contributors may be used to endorse or promote products
//       derived from this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
// ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
// WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
// DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
// DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
// (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
// LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
// ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
// SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

//==================================================================================================
//  Filename      : define.h
//  Created On    : 2014-02-20
//  Last Modified : 2018-11-16 17:14:11
//  Revision      :
//  Author        : Yaosheng Fu
//  Company       : Princeton University
//  Email         : yfu@princeton.edu
//
//  Description   : main header file defining global architecture parameters
//
//
//==================================================================================================




// Uncomment to define USE_GENERIC_SRAM_IMPLEMENTATION to use the old unsynthesizable BRAM
// `define USE_GENERIC_SRAM_IMPLEMENTATION




/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

/////////////////////////////////////////////////////////////////////////////////////////////
// 63         50 49      42 41      34 33           30 29      22 21                 0
// ------------------------------------------------------------------------------------
// |            |          |          |               |          |                    |
// |  Chip ID   |  Dest X  |  Dest Y  |  Final Route  |  Length  |    Header Payload  |
// |            |          |          |               |          |                    |
// ------------------------------------------------------------------------------------
////////////////////////////////////////////////////////////////////////////////////////////////











 //whether the routing is based on chipid or x y position
 //`define    ROUTING_CHIP_ID


 //defines for different topology, only one should be active
 //`define    NETWORK_TOPO_2D_MESH
 //`define    NETWORK_TOPO_3D_MESH


// Tile config

// devices.xml





// NoC interface





















// NodeID decomposition








//========================
//Packet format
//=========================

//Header decomposition































// these shifted fields are added for convienience
// HEADER 2








// HEADER 3








//NoC header information










// Width of MSG_ADDR field - you're probably looking for PHY_ADDR_WIDTH


//Coherence information





//Requests from L15 to L2
// Should always make #0 an error








//condition satisfied

//condition not satisfied

//Both SWAP and LDSTUB are the same for L2









//RISC-V AMO requests









//RISC-V AMO L2-internal phase 1









//RISC-V AMO L2-internal phase 2












//Forward requests from L2 to L15







//Memory requests from L2 to DRAM






//Forward acks from L15 to L2







//Memory acks from memory to L2









//Acks from L2 to L15


//TODO



//Only exist within L2





//`define MSG_TYPE_LOAD_REQ           8'd31 if this is enabled, don't use 31





// These should be defined in l2.vh, not the global defines











//Physical address










//Transition data size












//`define HOME_ID_MASK_X          10:10
//Additional fields for Sharer Domain ID and Logical Sharer ID
//For coherence domain restriction only


// Tri: dynamically adjust these parameters based on how many tiles are available
//  Assumption: 8x8 topology























































//`define DMBR_TAG_WIDTH 4

//Clumpy Shared Memory






////////////////////////////////////////////
// SOME CONFIGURATION REGISTERS DEFINES
////////////////////////////////////////////
// example: read/write to csm_en would be 0xba_0000_0100

// `define ASI_ADDRESS_MASK    `L15_ADDR_TYPE
// `define CONFIG_ASI_ADDRESS  `L15_ADDR_TYPE_WIDTH'hba










// DMBR Config register 1 fields















// DMBR Config register 2 fields



//Home allocation method






//Additional fields for Sharer Domain ID and Logical Sharer ID
//For coherence domain restriction only

































//`define TTE_CSM_WIDTH           64
//`define TTE_CSM                 63:0
//`define TTE_CSM_VALID           63
//`define TTE_CSM_SZL             62:61
//`define TTE_CSM_NFO             60
//`define TTE_CSM_IE              59
//`define TTE_CSM_SOFT2           58:49
//`define TTE_CSM_SZH             48
//`define TTE_CSM_DIAG            47:40
//`define TTE_CSM_RES1            39
//`define TTE_CSM_SDID            38:29
//`define TTE_CSM_HDID            28:19
//`define TTE_CSM_LSID            18:13
//`define TTE_CSM_SOFT            12:8
//`define TTE_CSM_RES2            7
//`define TTE_CSM_LOCK            6
//`define TTE_CSM_CP              5
//`define TTE_CSM_CV              4
//`define TTE_CSM_E               3
//`define TTE_CSM_P               2
//`define TTE_CSM_W               1
//`define TTE_CSM_RES3            0












// Packet format for home id





/////////////////////////////////////
// BIST
/////////////////////////////////////

// the data width from tap to individual sram wrappers



//deprecated































/////////////////////////////////////
// IDs for JTAG-Core interface
/////////////////////////////////////

// 48b for writing the PC reset vector

// 94b for reading the sscan data











// Execution Drafting Synchronization Method Values





// Execution Drafting timeout counter bit width


// Configuration registers












// Execution Drafting configuration register bit positions








// Execution Drafting configuration register default values
// ED disabled, STSM sync method, LFSR seed = 16'b0, LFSR load = 1'b0,
// Counter Timeout = 16'd32



//Clumpy sharer memory configuration registers

























module dynamic_node_top_wrap
(
    input clk,
    input reset_in,

    input [64-1:0] dataIn_N,   // data inputs from neighboring tiles
    input [64-1:0] dataIn_E,
    input [64-1:0] dataIn_S,
    input [64-1:0] dataIn_W,
     input [64-1:0] dataIn_P,   // data input from processor

    input validIn_N,        // valid signals from neighboring tiles
    input validIn_E,
    input validIn_S,
    input validIn_W,
    input validIn_P,        // valid signal from processor

    input yummyIn_N,        // neighbor consumed output data
    input yummyIn_E,
    input yummyIn_S,
    input yummyIn_W,
    input yummyIn_P,        // processor consumed output data

    input [8-1:0] myLocX,       // this tile's position
    input [8-1:0] myLocY,
    input [14-1:0] myChipID,

    output [64-1:0] dataOut_N, // data outputs to neighbors
    output [64-1:0] dataOut_E,
    output [64-1:0] dataOut_S,
     output [64-1:0] dataOut_W,
     output [64-1:0] dataOut_P, // data output to processor

    output validOut_N,      // valid outputs to neighbors
    output validOut_E,
    output validOut_S,
    output validOut_W,
    output validOut_P,      // valid output to processor

    output yummyOut_N,      // yummy signal to neighbors' output buffers
    output yummyOut_E,
    output yummyOut_S,
    output yummyOut_W,
    output yummyOut_P,      // yummy signal to processor's output buffer


    output thanksIn_P      // thanksIn to processor's space_avail
);

    dynamic_node_top dynamic_node_top
    (
        .clk(clk),
        .reset_in(reset_in),
        .dataIn_N(dataIn_N),
        .dataIn_E(dataIn_E),
        .dataIn_S(dataIn_S),
        .dataIn_W(dataIn_W),
        .dataIn_P(dataIn_P),
        .validIn_N(validIn_N),
        .validIn_E(validIn_E),
        .validIn_S(validIn_S),
        .validIn_W(validIn_W),
        .validIn_P(validIn_P),
        .yummyIn_N(yummyIn_N),
        .yummyIn_E(yummyIn_E),
        .yummyIn_S(yummyIn_S),
        .yummyIn_W(yummyIn_W),
        .yummyIn_P(yummyIn_P),
        .myLocX(myLocX),
        .myLocY(myLocY),
        .myChipID(myChipID),
        .ec_cfg(15'b0),
        .store_meter_partner_address_X(5'b0),
        .store_meter_partner_address_Y(5'b0),
        .dataOut_N(dataOut_N),
        .dataOut_E(dataOut_E),
        .dataOut_S(dataOut_S),
        .dataOut_W(dataOut_W),
        .dataOut_P(dataOut_P),
        .validOut_N(validOut_N),
        .validOut_E(validOut_E),
        .validOut_S(validOut_S),
        .validOut_W(validOut_W),
        .validOut_P(validOut_P),
        .yummyOut_N(yummyOut_N),
        .yummyOut_E(yummyOut_E),
        .yummyOut_W(yummyOut_W),
        .yummyOut_S(yummyOut_S),
        .yummyOut_P(yummyOut_P),
        .thanksIn_P(thanksIn_P),
        .external_interrupt(),
        .store_meter_ack_partner(),
        .store_meter_ack_non_partner(),
        .ec_out()
    );

endmodule
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

//Function: This wires everything together to make a crossbar
//

// Copyright (c) 2015 Princeton University
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//     * Redistributions of source code must retain the above copyright
//       notice, this list of conditions and the following disclaimer.
//     * Redistributions in binary form must reproduce the above copyright
//       notice, this list of conditions and the following disclaimer in the
//       documentation and/or other materials provided with the distribution.
//     * Neither the name of Princeton University nor the
//       names of its contributors may be used to endorse or promote products
//       derived from this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
// ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
// WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
// DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
// DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
// (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
// LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
// ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
// SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

//==================================================================================================
//  Filename      : define.h
//  Created On    : 2014-02-20
//  Last Modified : 2018-11-16 17:14:11
//  Revision      :
//  Author        : Yaosheng Fu
//  Company       : Princeton University
//  Email         : yfu@princeton.edu
//
//  Description   : main header file defining global architecture parameters
//
//
//==================================================================================================






































































































































































































































































































































































































































































































































































































module dynamic_node_top(clk,
		    reset_in,
		    dataIn_N,
		    dataIn_E,
		    dataIn_S,
		    dataIn_W,
		    dataIn_P,
		    validIn_N,
		    validIn_E,
		    validIn_S,
		    validIn_W,
		    validIn_P,
		    yummyIn_N,
		    yummyIn_E,
		    yummyIn_S,
		    yummyIn_W,
		    yummyIn_P,
		    myLocX,
		    myLocY,
            myChipID,
		    store_meter_partner_address_X,
		    store_meter_partner_address_Y,
		    ec_cfg,
		    dataOut_N,
		    dataOut_E,
		    dataOut_S,
		    dataOut_W,
		    dataOut_P,
		    validOut_N,
		    validOut_E,
		    validOut_S,
		    validOut_W,
		    validOut_P,
		    yummyOut_N,
		    yummyOut_E,
		    yummyOut_S,
		    yummyOut_W,
		    yummyOut_P,
		    thanksIn_P,
		    external_interrupt,
		    store_meter_ack_partner,
		    store_meter_ack_non_partner,
		    ec_out);

// begin port declarations

input clk;
input reset_in;

input [64-1:0] dataIn_N;	// data inputs from neighboring tiles
input [64-1:0] dataIn_E;
input [64-1:0] dataIn_S;
input [64-1:0] dataIn_W;
input [64-1:0] dataIn_P;	// data input from processor

input validIn_N;		// valid signals from neighboring tiles
input validIn_E;
input validIn_S;
input validIn_W;
input validIn_P;		// valid signal from processor

input yummyIn_N;		// neighbor consumed output data
input yummyIn_E;
input yummyIn_S;
input yummyIn_W;
input yummyIn_P;		// processor consumed output data

input [8-1:0] myLocX;		// this tile's position
input [8-1:0] myLocY;
input [14-1:0] myChipID;

input [4:0] store_meter_partner_address_X;
input [4:0] store_meter_partner_address_Y;

input [14:0] ec_cfg;            // NESWP 3 bits each selecter of event to monitor


output [64-1:0] dataOut_N;	// data outputs to neighbors
output [64-1:0] dataOut_E;
output [64-1:0] dataOut_S;
output [64-1:0] dataOut_W;
output [64-1:0] dataOut_P;	// data output to processor

output validOut_N;		// valid outputs to neighbors
output validOut_E;
output validOut_S;
output validOut_W;
output validOut_P;		// valid output to processor

output yummyOut_N;		// yummy signal to neighbors' output buffers
output yummyOut_E;
output yummyOut_S;
output yummyOut_W;
output yummyOut_P;		// yummy signal to processor's output buffer

output thanksIn_P;		// thanksIn to processor's space_avail

output external_interrupt;	//is used for the proc to know
				//that an external interrupt occured
output store_meter_ack_partner;      // strobes high when a memory ack word is popped off of the network
                                     // and the sender ID matches the "partner port" id from the STORE_METER
output store_meter_ack_non_partner;  // strobes high when a memory ack word is popped off of the network
                                     // and the sender ID does not match the "partner port" id from the STORE_METER


output [4:0] ec_out;


wire   ec_wants_to_send_but_cannot_N,
       ec_wants_to_send_but_cannot_E,
       ec_wants_to_send_but_cannot_S,
       ec_wants_to_send_but_cannot_W,
       ec_wants_to_send_but_cannot_P;

// end port declarations

   wire store_ack_received;
   wire store_ack_received_r;
   wire [9:0] store_ack_addr;
   wire [9:0] store_ack_addr_r;

//wires

wire north_input_tail;
wire east_input_tail;
wire south_input_tail;
wire west_input_tail;
wire proc_input_tail;

wire [64-1:0] north_input_data;
wire [64-1:0] east_input_data;
wire [64-1:0] south_input_data;
wire [64-1:0] west_input_data;
wire [64-1:0] proc_input_data;

wire north_input_valid;
wire east_input_valid;
wire south_input_valid;
wire west_input_valid;
wire proc_input_valid;

wire thanks_n_to_n;
wire thanks_n_to_e;
wire thanks_n_to_s;
wire thanks_n_to_w;
wire thanks_n_to_p;

wire thanks_e_to_n;
wire thanks_e_to_e;
wire thanks_e_to_s;
wire thanks_e_to_w;
wire thanks_e_to_p;

wire thanks_s_to_n;
wire thanks_s_to_e;
wire thanks_s_to_s;
wire thanks_s_to_w;
wire thanks_s_to_p;

wire thanks_w_to_n;
wire thanks_w_to_e;
wire thanks_w_to_s;
wire thanks_w_to_w;
wire thanks_w_to_p;

wire thanks_p_to_n;
wire thanks_p_to_e;
wire thanks_p_to_s;
wire thanks_p_to_w;
wire thanks_p_to_p;

wire route_req_n_to_n;
wire route_req_n_to_e;
wire route_req_n_to_s;
wire route_req_n_to_w;
wire route_req_n_to_p;

wire route_req_e_to_n;
wire route_req_e_to_e;
wire route_req_e_to_s;
wire route_req_e_to_w;
wire route_req_e_to_p;

wire route_req_s_to_n;
wire route_req_s_to_e;
wire route_req_s_to_s;
wire route_req_s_to_w;
wire route_req_s_to_p;

wire route_req_w_to_n;
wire route_req_w_to_e;
wire route_req_w_to_s;
wire route_req_w_to_w;
wire route_req_w_to_p;

wire route_req_p_to_n;
wire route_req_p_to_e;
wire route_req_p_to_s;
wire route_req_p_to_w;
wire route_req_p_to_p;

wire default_ready_n_to_s;
wire default_ready_e_to_w;
wire default_ready_s_to_n;
wire default_ready_s_to_p;
wire default_ready_w_to_e;

// input/output buffered signals
wire yummyOut_N_internal;
wire yummyOut_E_internal;
wire yummyOut_S_internal;
wire yummyOut_W_internal;
wire yummyOut_P_internal;

wire validOut_N_internal;
wire validOut_E_internal;
wire validOut_S_internal;
wire validOut_W_internal;
wire validOut_P_internal;

wire [64-1:0] dataOut_N_internal;
wire [64-1:0] dataOut_E_internal;
wire [64-1:0] dataOut_S_internal;
wire [64-1:0] dataOut_W_internal;
wire [64-1:0] dataOut_P_internal;

wire yummyOut_N_flip1_out;
wire yummyOut_E_flip1_out;
wire yummyOut_S_flip1_out;
wire yummyOut_W_flip1_out;
//wire yummyOut_P_flip1_out;

wire validOut_N_flip1_out;
wire validOut_E_flip1_out;
wire validOut_S_flip1_out;
wire validOut_W_flip1_out;
//wire validOut_P_flip1_out;

wire [64-1:0] dataOut_N_flip1_out;
wire [64-1:0] dataOut_E_flip1_out;
wire [64-1:0] dataOut_S_flip1_out;
wire [64-1:0] dataOut_W_flip1_out;
//wire [`DATA_WIDTH-1:0] dataOut_P_flip1_out;

wire yummyIn_N_internal;
wire yummyIn_E_internal;
wire yummyIn_S_internal;
wire yummyIn_W_internal;
wire yummyIn_P_internal;

wire validIn_N_internal;
wire validIn_E_internal;
wire validIn_S_internal;
wire validIn_W_internal;
//wire validIn_P_internal;

wire [64-1:0] dataIn_N_internal;
wire [64-1:0] dataIn_E_internal;
wire [64-1:0] dataIn_S_internal;
wire [64-1:0] dataIn_W_internal;
//wire [`DATA_WIDTH-1:0] dataIn_P_internal;

wire yummyIn_N_flip1_out;
wire yummyIn_E_flip1_out;
wire yummyIn_S_flip1_out;
wire yummyIn_W_flip1_out;
//wire yummyIn_P_flip1_out;

wire validIn_N_flip1_out;
wire validIn_E_flip1_out;
wire validIn_S_flip1_out;
wire validIn_W_flip1_out;
//wire validIn_P_flip1_out;

wire [64-1:0] dataIn_N_flip1_out;
wire [64-1:0] dataIn_E_flip1_out;
wire [64-1:0] dataIn_S_flip1_out;
wire [64-1:0] dataIn_W_flip1_out;
//wire [`DATA_WIDTH-1:0] dataIn_P_flip1_out;

//state
reg [8-1:0] myLocX_f;
reg [8-1:0] myLocY_f;
reg [14-1:0] myChipID_f;
wire   reset;


// event counter logic
//
//

reg ec_thanks_n_to_n_reg, ec_thanks_n_to_e_reg, ec_thanks_n_to_s_reg, ec_thanks_n_to_w_reg, ec_thanks_n_to_p_reg;
reg ec_thanks_e_to_n_reg, ec_thanks_e_to_e_reg, ec_thanks_e_to_s_reg, ec_thanks_e_to_w_reg, ec_thanks_e_to_p_reg;
reg ec_thanks_s_to_n_reg, ec_thanks_s_to_e_reg, ec_thanks_s_to_s_reg, ec_thanks_s_to_w_reg, ec_thanks_s_to_p_reg;
reg ec_thanks_w_to_n_reg, ec_thanks_w_to_e_reg, ec_thanks_w_to_s_reg, ec_thanks_w_to_w_reg, ec_thanks_w_to_p_reg;
reg ec_thanks_p_to_n_reg, ec_thanks_p_to_e_reg, ec_thanks_p_to_s_reg, ec_thanks_p_to_w_reg, ec_thanks_p_to_p_reg;
reg ec_wants_to_send_but_cannot_N_reg, ec_wants_to_send_but_cannot_E_reg, ec_wants_to_send_but_cannot_S_reg, ec_wants_to_send_but_cannot_W_reg, ec_wants_to_send_but_cannot_P_reg;
reg ec_north_input_valid_reg, ec_east_input_valid_reg, ec_south_input_valid_reg, ec_west_input_valid_reg, ec_proc_input_valid_reg;


// let's register these babies before they do any damage to the cycle time -- mbt
always @(posedge clk)
  begin
     ec_thanks_n_to_n_reg <= thanks_n_to_n; ec_thanks_n_to_e_reg <= thanks_n_to_e; ec_thanks_n_to_s_reg <= thanks_n_to_s; ec_thanks_n_to_w_reg <= thanks_n_to_w; ec_thanks_n_to_p_reg <= thanks_n_to_p;
     ec_thanks_e_to_n_reg <= thanks_e_to_n; ec_thanks_e_to_e_reg <= thanks_e_to_e; ec_thanks_e_to_s_reg <= thanks_e_to_s; ec_thanks_e_to_w_reg <= thanks_e_to_w; ec_thanks_e_to_p_reg <= thanks_e_to_p;
     ec_thanks_s_to_n_reg <= thanks_s_to_n; ec_thanks_s_to_e_reg <= thanks_s_to_e; ec_thanks_s_to_s_reg <= thanks_s_to_s; ec_thanks_s_to_w_reg <= thanks_s_to_w; ec_thanks_s_to_p_reg <= thanks_s_to_p;
     ec_thanks_w_to_n_reg <= thanks_w_to_n; ec_thanks_w_to_e_reg <= thanks_w_to_e; ec_thanks_w_to_s_reg <= thanks_w_to_s; ec_thanks_w_to_w_reg <= thanks_w_to_w; ec_thanks_w_to_p_reg <= thanks_w_to_p;
     ec_thanks_p_to_n_reg <= thanks_p_to_n; ec_thanks_p_to_e_reg <= thanks_p_to_e; ec_thanks_p_to_s_reg <= thanks_p_to_s; ec_thanks_p_to_w_reg <= thanks_p_to_w; ec_thanks_p_to_p_reg <= thanks_p_to_p;
     ec_wants_to_send_but_cannot_N_reg <= ec_wants_to_send_but_cannot_N;
     ec_wants_to_send_but_cannot_E_reg <= ec_wants_to_send_but_cannot_E;
     ec_wants_to_send_but_cannot_S_reg <= ec_wants_to_send_but_cannot_S;
     ec_wants_to_send_but_cannot_W_reg <= ec_wants_to_send_but_cannot_W;
     ec_wants_to_send_but_cannot_P_reg <= ec_wants_to_send_but_cannot_P;
     ec_north_input_valid_reg <= north_input_valid;
     ec_east_input_valid_reg  <= east_input_valid;
     ec_south_input_valid_reg <= south_input_valid;
     ec_west_input_valid_reg  <= west_input_valid;
     ec_proc_input_valid_reg  <= proc_input_valid;
  end

   wire ec_thanks_to_n = ec_thanks_n_to_n_reg | ec_thanks_e_to_n_reg | ec_thanks_s_to_n_reg | ec_thanks_w_to_n_reg | ec_thanks_p_to_n_reg;
   wire ec_thanks_to_e = ec_thanks_n_to_e_reg | ec_thanks_e_to_e_reg | ec_thanks_s_to_e_reg | ec_thanks_w_to_e_reg | ec_thanks_p_to_e_reg;
   wire ec_thanks_to_s = ec_thanks_n_to_s_reg | ec_thanks_e_to_s_reg | ec_thanks_s_to_s_reg | ec_thanks_w_to_s_reg | ec_thanks_p_to_s_reg;
   wire ec_thanks_to_w = ec_thanks_n_to_w_reg | ec_thanks_e_to_w_reg | ec_thanks_s_to_w_reg | ec_thanks_w_to_w_reg | ec_thanks_p_to_w_reg;
   wire ec_thanks_to_p = ec_thanks_n_to_p_reg | ec_thanks_e_to_p_reg | ec_thanks_s_to_p_reg | ec_thanks_w_to_p_reg | ec_thanks_p_to_p_reg;

one_of_eight #(1) ec_mux_north(.in0(ec_wants_to_send_but_cannot_N),
                        .in1(ec_thanks_p_to_n_reg),
                        .in2(ec_thanks_w_to_n_reg),
                        .in3(ec_thanks_s_to_n_reg),
                        .in4(ec_thanks_e_to_n_reg),
                        .in5(ec_thanks_n_to_n_reg),
                        .in6(ec_thanks_to_n),
                        .in7(ec_north_input_valid_reg & ~ec_thanks_to_n),
                        .sel(ec_cfg[14:12]),
                        .out(ec_out[4]));

one_of_eight #(1) ec_mux_east(.in0(ec_wants_to_send_but_cannot_E),
                       .in1(ec_thanks_p_to_e_reg),
                       .in2(ec_thanks_w_to_e_reg),
                       .in3(ec_thanks_s_to_e_reg),
                       .in4(ec_thanks_e_to_e_reg),
                       .in5(ec_thanks_n_to_e_reg),
                       .in6(ec_thanks_to_e),
                       .in7(ec_east_input_valid_reg & ~ec_thanks_to_e),
                       .sel(ec_cfg[11:9]),
                       .out(ec_out[3]));

one_of_eight #(1) ec_mux_south(.in0(ec_wants_to_send_but_cannot_S),
                        .in1(ec_thanks_p_to_s_reg),
                        .in2(ec_thanks_w_to_s_reg),
                        .in3(ec_thanks_s_to_s_reg),
                        .in4(ec_thanks_e_to_s_reg),
                        .in5(ec_thanks_n_to_s_reg),
                        .in6(ec_thanks_to_s),
                        .in7(ec_south_input_valid_reg & ~ec_thanks_to_s),
                        .sel(ec_cfg[8:6]),
                        .out(ec_out[2]));

one_of_eight #(1) ec_mux_west( .in0(ec_wants_to_send_but_cannot_W),
                        .in1(ec_thanks_p_to_w_reg),
                        .in2(ec_thanks_w_to_w_reg),
                        .in3(ec_thanks_s_to_w_reg),
                        .in4(ec_thanks_e_to_w_reg),
                        .in5(ec_thanks_n_to_w_reg),
                        .in6(ec_thanks_to_w),
                        .in7(ec_west_input_valid_reg & ~ec_thanks_to_w),
                        .sel(ec_cfg[5:3]),
                        .out(ec_out[1]));

one_of_eight #(1) ec_mux_proc( .in0(ec_wants_to_send_but_cannot_P),
                        .in1(ec_thanks_p_to_p_reg),
                        .in2(ec_thanks_w_to_p_reg),
                        .in3(ec_thanks_s_to_p_reg),
                        .in4(ec_thanks_e_to_p_reg),
                        .in5(ec_thanks_n_to_p_reg),
                        .in6(ec_thanks_to_p),
                        .in7(ec_proc_input_valid_reg & ~ec_thanks_to_p),
                        .sel(ec_cfg[2:0]),
                        .out(ec_out[0]));

// end event counter logic

net_dff #(1) REG_reset_fin(.d(reset_in), .q(reset), .clk(clk));

net_dff #(10) REG_store_ack_addr(   .d(store_ack_addr),     .q(store_ack_addr_r),     .clk(clk));
net_dff #(1) REG_store_ack_received(.d(store_ack_received), .q(store_ack_received_r), .clk(clk));

   wire is_partner_address_v_r;
   bus_compare_equal #(10) CMP_partner_address (.a(store_ack_addr_r),
                                        .b({ store_meter_partner_address_Y, store_meter_partner_address_X } ),
                                        .bus_equal(is_partner_address_v_r));

   assign store_meter_ack_partner     = is_partner_address_v_r & store_ack_received_r;
   assign store_meter_ack_non_partner = ~is_partner_address_v_r & store_ack_received_r;

//make it so that the mdn_cfg location register has
//one cycle latency when being changed
//this was done so that these flops could be put near the
//dynamic network but this does mean that the cycle directly
//folowing a mtsr MDN_CFG which changes the location bits
//will still use the old value
//likewise it would be best to make sure there are no in-flight memory
//operations when setting the X and Y location for a tile.
always @ (posedge clk)
begin
        if(reset)
        begin
                myLocY_f <= 8'd0;
                myLocX_f <= 8'd0;
                myChipID_f <= 14'd0;
        end
        else
        begin
                myLocY_f <= myLocY;
                myLocX_f <= myLocX;
                myChipID_f <= myChipID;
        end
end

// mmckeown: Removing DUMMY modules
//dummy signals
/*`ifdef NO_DUMMY
`else
   rDUMMY #(1) default_ready_n_to_s_dummy (.A(default_ready_n_to_s));

   rDUMMY #(1) default_ready_e_to_w_dummy (.A(default_ready_e_to_w));

   rDUMMY #(1) default_ready_s_to_n_dummy (.A(default_ready_s_to_n));

   rDUMMY #(1) default_ready_s_to_p_dummy (.A(default_ready_s_to_p));

   rDUMMY #(1) default_ready_w_to_e_dummy (.A(default_ready_w_to_e));
`endif

//dummy signals for detecting the critical path for the valid and data signals
`ifdef NO_DUMMY
`else
   rDUMMY #(1) valid_out_north(.A(validOut_N_internal));
   rDUMMY #(1) valid_out_east(.A(validOut_E_internal));
   rDUMMY #(1) valid_out_south(.A(validOut_S_internal));
   rDUMMY #(1) valid_out_west(.A(validOut_W_internal));
   rDUMMY #(1) valid_out_proc(.A(validOut_P_internal));

   rDUMMY #(`DATA_WIDTH) data_out_north(.A(dataOut_N_internal));
   rDUMMY #(`DATA_WIDTH) data_out_east(.A(dataOut_E_internal));
   rDUMMY #(`DATA_WIDTH) data_out_south(.A(dataOut_S_internal));
   rDUMMY #(`DATA_WIDTH) data_out_west(.A(dataOut_W_internal));
   rDUMMY #(`DATA_WIDTH) data_out_proc(.A(dataOut_P_internal));
`endif*/

//wire regs

//assigns
assign thanksIn_P = thanks_n_to_p | thanks_e_to_p | thanks_s_to_p | thanks_w_to_p | thanks_p_to_p;

//assign validOut_N = validOut_N_internal;
//assign validOut_E = validOut_E_internal;
//assign validOut_S = validOut_S_internal;
//assign validOut_W = validOut_W_internal;
assign validOut_P = validOut_P_internal;

//assign dataOut_N = dataOut_N_internal;
//assign dataOut_E = dataOut_E_internal;
//assign dataOut_S = dataOut_S_internal;
//assign dataOut_W = dataOut_W_internal;
assign dataOut_P = dataOut_P_internal;

//more assigns
assign yummyIn_P_internal = yummyIn_P;
assign yummyOut_P = yummyOut_P_internal;


// two sets of inverters for output signals (buffering for timing purposes)
flip_bus #(1, 14) yummyOut_N_flip1(yummyOut_N_internal, yummyOut_N_flip1_out);
flip_bus #(1, 14) yummyOut_E_flip1(yummyOut_E_internal, yummyOut_E_flip1_out);
flip_bus #(1, 14) yummyOut_S_flip1(yummyOut_S_internal, yummyOut_S_flip1_out);
flip_bus #(1, 14) yummyOut_W_flip1(yummyOut_W_internal, yummyOut_W_flip1_out);
//flip_bus #(1, 14) yummyOut_P_flip1(yummyOut_P_internal, yummyOut_P_flip1_out);
flip_bus #(1, 21) yummyOut_N_flip2(yummyOut_N_flip1_out, yummyOut_N);
flip_bus #(1, 21) yummyOut_E_flip2(yummyOut_E_flip1_out, yummyOut_E);
flip_bus #(1, 21) yummyOut_S_flip2(yummyOut_S_flip1_out, yummyOut_S);
flip_bus #(1, 21) yummyOut_W_flip2(yummyOut_W_flip1_out, yummyOut_W);
//flip_bus #(1, 21) yummyOut_P_flip2(yummyOut_P_flip1_out, yummyOut_P);

flip_bus #(1, 14) validOut_N_flip1(validOut_N_internal, validOut_N_flip1_out);
flip_bus #(1, 14) validOut_E_flip1(validOut_E_internal, validOut_E_flip1_out);
flip_bus #(1, 14) validOut_S_flip1(validOut_S_internal, validOut_S_flip1_out);
flip_bus #(1, 14) validOut_W_flip1(validOut_W_internal, validOut_W_flip1_out);
//flip_bus #(1, 14) validOut_P_flip1(validOut_P_internal, validOut_P_flip1_out);
flip_bus #(1, 21) validOut_N_flip2(validOut_N_flip1_out, validOut_N);
flip_bus #(1, 21) validOut_E_flip2(validOut_E_flip1_out, validOut_E);
flip_bus #(1, 21) validOut_S_flip2(validOut_S_flip1_out, validOut_S);
flip_bus #(1, 21) validOut_W_flip2(validOut_W_flip1_out, validOut_W);
//flip_bus #(1, 21) validOut_P_flip2(validOut_P_flip1_out, validOut_P);

flip_bus #(64, 14) dataOut_N_flip1(dataOut_N_internal, dataOut_N_flip1_out);
flip_bus #(64, 14) dataOut_E_flip1(dataOut_E_internal, dataOut_E_flip1_out);
flip_bus #(64, 14) dataOut_S_flip1(dataOut_S_internal, dataOut_S_flip1_out);
flip_bus #(64, 14) dataOut_W_flip1(dataOut_W_internal, dataOut_W_flip1_out);
//flip_bus #(`DATA_WIDTH, 14) dataOut_P_flip1(dataOut_P_internal, dataOut_P_flip1_out);
flip_bus #(64, 21) dataOut_N_flip2(dataOut_N_flip1_out, dataOut_N);
flip_bus #(64, 21) dataOut_E_flip2(dataOut_E_flip1_out, dataOut_E);
flip_bus #(64, 21) dataOut_S_flip2(dataOut_S_flip1_out, dataOut_S);
flip_bus #(64, 21) dataOut_W_flip2(dataOut_W_flip1_out, dataOut_W);
//flip_bus #(`DATA_WIDTH, 21) dataOut_P_flip2(dataOut_P_flip1_out, dataOut_P);

// two sets of inverters for input signals (buffering for timing purposes)
flip_bus #(1, 14) yummyIn_N_flip1(yummyIn_N, yummyIn_N_flip1_out);
flip_bus #(1, 14) yummyIn_E_flip1(yummyIn_E, yummyIn_E_flip1_out);
flip_bus #(1, 14) yummyIn_S_flip1(yummyIn_S, yummyIn_S_flip1_out);
flip_bus #(1, 14) yummyIn_W_flip1(yummyIn_W, yummyIn_W_flip1_out);
//flip_bus #(1, 14) yummyIn_P_flip1(yummyIn_P, yummyIn_P_flip1_out);
flip_bus #(1, 10) yummyIn_N_flip2(yummyIn_N_flip1_out, yummyIn_N_internal);
flip_bus #(1, 10) yummyIn_E_flip2(yummyIn_E_flip1_out, yummyIn_E_internal);
flip_bus #(1, 10) yummyIn_S_flip2(yummyIn_S_flip1_out, yummyIn_S_internal);
flip_bus #(1, 10) yummyIn_W_flip2(yummyIn_W_flip1_out, yummyIn_W_internal);
//flip_bus #(1, 10) yummyIn_P_flip2(yummyIn_P_flip1_out, yummyIn_P_internal);

flip_bus #(1, 14) validIn_N_flip1(validIn_N, validIn_N_flip1_out);
flip_bus #(1, 14) validIn_E_flip1(validIn_E, validIn_E_flip1_out);
flip_bus #(1, 14) validIn_S_flip1(validIn_S, validIn_S_flip1_out);
flip_bus #(1, 14) validIn_W_flip1(validIn_W, validIn_W_flip1_out);
//flip_bus #(1, 14) validIn_P_flip1(validIn_P, validIn_P_flip1_out);
flip_bus #(1, 10) validIn_N_flip2(validIn_N_flip1_out, validIn_N_internal);
flip_bus #(1, 10) validIn_E_flip2(validIn_E_flip1_out, validIn_E_internal);
flip_bus #(1, 10) validIn_S_flip2(validIn_S_flip1_out, validIn_S_internal);
flip_bus #(1, 10) validIn_W_flip2(validIn_W_flip1_out, validIn_W_internal);
//flip_bus #(1, 10) validIn_P_flip2(validIn_P_flip1_out, validIn_P_internal);

flip_bus #(64, 14) dataIn_N_flip1(dataIn_N, dataIn_N_flip1_out);
flip_bus #(64, 14) dataIn_E_flip1(dataIn_E, dataIn_E_flip1_out);
flip_bus #(64, 14) dataIn_S_flip1(dataIn_S, dataIn_S_flip1_out);
flip_bus #(64, 14) dataIn_W_flip1(dataIn_W, dataIn_W_flip1_out);
//flip_bus #(`DATA_WIDTH, 14) dataIn_P_flip1(dataIn_P, dataIn_P_flip1_out);
flip_bus #(64, 10) dataIn_N_flip2(dataIn_N_flip1_out, dataIn_N_internal);
flip_bus #(64, 10) dataIn_E_flip2(dataIn_E_flip1_out, dataIn_E_internal);
flip_bus #(64, 10) dataIn_S_flip2(dataIn_S_flip1_out, dataIn_S_internal);
flip_bus #(64, 10) dataIn_W_flip2(dataIn_W_flip1_out, dataIn_W_internal);
//flip_bus #(`DATA_WIDTH, 10) dataIn_P_flip2(dataIn_P_flip1_out, dataIn_P_internal);


//instantiations


//the following dense code impliments a full crossbar.
//The two main components are a dynamic_input_top_X and a dynamic_output_top

//the difference between dynamic_input_top_4 and dynamic_input_top_16 are the size of
//the nibs inside of them.

//dynamic inputs
dynamic_input_top_4 north_input(.route_req_n_out(route_req_n_to_n), .route_req_e_out(route_req_n_to_e), .route_req_s_out(route_req_n_to_s), .route_req_w_out(route_req_n_to_w), .route_req_p_out(route_req_n_to_p), .default_ready_n_out(), .default_ready_e_out(), .default_ready_s_out(default_ready_n_to_s), .default_ready_w_out(), .default_ready_p_out(), .tail_out(north_input_tail), .yummy_out(yummyOut_N_internal), .data_out(north_input_data), .valid_out(north_input_valid), .clk(clk), .reset(reset), .my_loc_x_in(myLocX_f), .my_loc_y_in(myLocY_f), .my_chip_id_in(myChipID_f), .valid_in(validIn_N_internal), .data_in(dataIn_N_internal), .thanks_n(thanks_n_to_n), .thanks_e(thanks_e_to_n), .thanks_s(thanks_s_to_n), .thanks_w(thanks_w_to_n), .thanks_p(thanks_p_to_n));

dynamic_input_top_4 east_input(.route_req_n_out(route_req_e_to_n), .route_req_e_out(route_req_e_to_e), .route_req_s_out(route_req_e_to_s), .route_req_w_out(route_req_e_to_w), .route_req_p_out(route_req_e_to_p), .default_ready_n_out(), .default_ready_e_out(), .default_ready_s_out(), .default_ready_w_out(default_ready_e_to_w), .default_ready_p_out(), .tail_out(east_input_tail), .yummy_out(yummyOut_E_internal), .data_out(east_input_data), .valid_out(east_input_valid), .clk(clk), .reset(reset), .my_loc_x_in(myLocX_f), .my_loc_y_in(myLocY_f), .my_chip_id_in(myChipID_f), .valid_in(validIn_E_internal), .data_in(dataIn_E_internal), .thanks_n(thanks_n_to_e), .thanks_e(thanks_e_to_e), .thanks_s(thanks_s_to_e), .thanks_w(thanks_w_to_e), .thanks_p(thanks_p_to_e));

dynamic_input_top_4 south_input(.route_req_n_out(route_req_s_to_n), .route_req_e_out(route_req_s_to_e), .route_req_s_out(route_req_s_to_s), .route_req_w_out(route_req_s_to_w), .route_req_p_out(route_req_s_to_p), .default_ready_n_out(default_ready_s_to_n), .default_ready_e_out(), .default_ready_s_out(), .default_ready_w_out(), .default_ready_p_out(default_ready_s_to_p), .tail_out(south_input_tail), .yummy_out(yummyOut_S_internal), .data_out(south_input_data), .valid_out(south_input_valid), .clk(clk), .reset(reset), .my_loc_x_in(myLocX_f), .my_loc_y_in(myLocY_f), .my_chip_id_in(myChipID_f), .valid_in(validIn_S_internal), .data_in(dataIn_S_internal), .thanks_n(thanks_n_to_s), .thanks_e(thanks_e_to_s), .thanks_s(thanks_s_to_s), .thanks_w(thanks_w_to_s), .thanks_p(thanks_p_to_s));

dynamic_input_top_4 west_input(.route_req_n_out(route_req_w_to_n), .route_req_e_out(route_req_w_to_e), .route_req_s_out(route_req_w_to_s), .route_req_w_out(route_req_w_to_w), .route_req_p_out(route_req_w_to_p), .default_ready_n_out(), .default_ready_e_out(default_ready_w_to_e), .default_ready_s_out(), .default_ready_w_out(), .default_ready_p_out(), .tail_out(west_input_tail), .yummy_out(yummyOut_W_internal), .data_out(west_input_data), .valid_out(west_input_valid), .clk(clk), .reset(reset), .my_loc_x_in(myLocX_f), .my_loc_y_in(myLocY_f), .my_chip_id_in(myChipID_f), .valid_in(validIn_W_internal), .data_in(dataIn_W_internal), .thanks_n(thanks_n_to_w), .thanks_e(thanks_e_to_w), .thanks_s(thanks_s_to_w), .thanks_w(thanks_w_to_w), .thanks_p(thanks_p_to_w));

dynamic_input_top_16 proc_input(.route_req_n_out(route_req_p_to_n), .route_req_e_out(route_req_p_to_e), .route_req_s_out(route_req_p_to_s), .route_req_w_out(route_req_p_to_w), .route_req_p_out(route_req_p_to_p), .default_ready_n_out(), .default_ready_e_out(), .default_ready_s_out(), .default_ready_w_out(), .default_ready_p_out(), .tail_out(proc_input_tail), .yummy_out(yummyOut_P_internal), .data_out(proc_input_data), .valid_out(proc_input_valid), .clk(clk), .reset(reset), .my_loc_x_in(myLocX_f), .my_loc_y_in(myLocY_f), .my_chip_id_in(myChipID_f), .valid_in(validIn_P), .data_in(dataIn_P), .thanks_n(thanks_n_to_p), .thanks_e(thanks_e_to_p), .thanks_s(thanks_s_to_p), .thanks_w(thanks_w_to_p), .thanks_p(thanks_p_to_p));

//dynamic outputs

dynamic_output_top north_output(.data_out(dataOut_N_internal), .thanks_a_out(thanks_n_to_s), .thanks_b_out(thanks_n_to_w), .thanks_c_out(thanks_n_to_p), .thanks_d_out(thanks_n_to_e), .thanks_x_out(thanks_n_to_n), .valid_out(validOut_N_internal),  .popped_interrupt_mesg_out(), .popped_memory_ack_mesg_out(), .popped_memory_ack_mesg_out_sender(), .ec_wants_to_send_but_cannot(ec_wants_to_send_but_cannot_N), .clk(clk), .reset(reset), .route_req_a_in(route_req_s_to_n), .route_req_b_in(route_req_w_to_n), .route_req_c_in(route_req_p_to_n), .route_req_d_in(route_req_e_to_n), .route_req_x_in(route_req_n_to_n), .tail_a_in(south_input_tail), .tail_b_in(west_input_tail), .tail_c_in(proc_input_tail), .tail_d_in(east_input_tail), .tail_x_in(north_input_tail), .data_a_in(south_input_data), .data_b_in(west_input_data), .data_c_in(proc_input_data), .data_d_in(east_input_data), .data_x_in(north_input_data), .valid_a_in(south_input_valid), .valid_b_in(west_input_valid), .valid_c_in(proc_input_valid), .valid_d_in(east_input_valid), .valid_x_in(north_input_valid), .default_ready_in(default_ready_s_to_n), .yummy_in(yummyIn_N_internal));

dynamic_output_top east_output(.data_out(dataOut_E_internal), .thanks_a_out(thanks_e_to_w), .thanks_b_out(thanks_e_to_p), .thanks_c_out(thanks_e_to_n), .thanks_d_out(thanks_e_to_s), .thanks_x_out(thanks_e_to_e), .valid_out(validOut_E_internal),   .popped_interrupt_mesg_out(), .popped_memory_ack_mesg_out(), .popped_memory_ack_mesg_out_sender(),  .ec_wants_to_send_but_cannot(ec_wants_to_send_but_cannot_E), .clk(clk), .reset(reset), .route_req_a_in(route_req_w_to_e), .route_req_b_in(route_req_p_to_e), .route_req_c_in(route_req_n_to_e), .route_req_d_in(route_req_s_to_e), .route_req_x_in(route_req_e_to_e), .tail_a_in(west_input_tail), .tail_b_in(proc_input_tail), .tail_c_in(north_input_tail), .tail_d_in(south_input_tail), .tail_x_in(east_input_tail), .data_a_in(west_input_data), .data_b_in(proc_input_data), .data_c_in(north_input_data), .data_d_in(south_input_data), .data_x_in(east_input_data), .valid_a_in(west_input_valid), .valid_b_in(proc_input_valid), .valid_c_in(north_input_valid), .valid_d_in(south_input_valid), .valid_x_in(east_input_valid), .default_ready_in(default_ready_w_to_e), .yummy_in(yummyIn_E_internal));

dynamic_output_top south_output(.data_out(dataOut_S_internal), .thanks_a_out(thanks_s_to_n), .thanks_b_out(thanks_s_to_e), .thanks_c_out(thanks_s_to_w), .thanks_d_out(thanks_s_to_p), .thanks_x_out(thanks_s_to_s), .valid_out(validOut_S_internal),   .popped_interrupt_mesg_out(), .popped_memory_ack_mesg_out(), .popped_memory_ack_mesg_out_sender(),  .ec_wants_to_send_but_cannot(ec_wants_to_send_but_cannot_S), .clk(clk), .reset(reset), .route_req_a_in(route_req_n_to_s), .route_req_b_in(route_req_e_to_s), .route_req_c_in(route_req_w_to_s), .route_req_d_in(route_req_p_to_s), .route_req_x_in(route_req_s_to_s), .tail_a_in(north_input_tail), .tail_b_in(east_input_tail), .tail_c_in(west_input_tail), .tail_d_in(proc_input_tail), .tail_x_in(south_input_tail), .data_a_in(north_input_data), .data_b_in(east_input_data), .data_c_in(west_input_data), .data_d_in(proc_input_data), .data_x_in(south_input_data), .valid_a_in(north_input_valid), .valid_b_in(east_input_valid), .valid_c_in(west_input_valid), .valid_d_in(proc_input_valid), .valid_x_in(south_input_valid), .default_ready_in(default_ready_n_to_s), .yummy_in(yummyIn_S_internal));

dynamic_output_top west_output(.data_out(dataOut_W_internal), .thanks_a_out(thanks_w_to_e), .thanks_b_out(thanks_w_to_s), .thanks_c_out(thanks_w_to_p), .thanks_d_out(thanks_w_to_n), .thanks_x_out(thanks_w_to_w), .valid_out(validOut_W_internal),   .popped_interrupt_mesg_out(), .popped_memory_ack_mesg_out(), .popped_memory_ack_mesg_out_sender(),  .ec_wants_to_send_but_cannot(ec_wants_to_send_but_cannot_W), .clk(clk), .reset(reset), .route_req_a_in(route_req_e_to_w), .route_req_b_in(route_req_s_to_w), .route_req_c_in(route_req_p_to_w), .route_req_d_in(route_req_n_to_w), .route_req_x_in(route_req_w_to_w), .tail_a_in(east_input_tail), .tail_b_in(south_input_tail), .tail_c_in(proc_input_tail), .tail_d_in(north_input_tail), .tail_x_in(west_input_tail), .data_a_in(east_input_data), .data_b_in(south_input_data), .data_c_in(proc_input_data), .data_d_in(north_input_data), .data_x_in(west_input_data), .valid_a_in(east_input_valid), .valid_b_in(south_input_valid), .valid_c_in(proc_input_valid), .valid_d_in(north_input_valid), .valid_x_in(west_input_valid), .default_ready_in(default_ready_e_to_w), .yummy_in(yummyIn_W_internal));
//yanqi change kill headers to 0
dynamic_output_top #(1'b0) proc_output(.data_out(dataOut_P_internal), .thanks_a_out(thanks_p_to_s), .thanks_b_out(thanks_p_to_w), .thanks_c_out(thanks_p_to_n), .thanks_d_out(thanks_p_to_e), .thanks_x_out(thanks_p_to_p), .valid_out(validOut_P_internal),  .popped_interrupt_mesg_out(external_interrupt), .popped_memory_ack_mesg_out(store_ack_received), .popped_memory_ack_mesg_out_sender(store_ack_addr),  .ec_wants_to_send_but_cannot(ec_wants_to_send_but_cannot_P), .clk(clk), .reset(reset), .route_req_a_in(route_req_s_to_p), .route_req_b_in(route_req_w_to_p), .route_req_c_in(route_req_n_to_p), .route_req_d_in(route_req_e_to_p), .route_req_x_in(route_req_p_to_p), .tail_a_in(south_input_tail), .tail_b_in(west_input_tail), .tail_c_in(north_input_tail), .tail_d_in(east_input_tail), .tail_x_in(proc_input_tail), .data_a_in(south_input_data), .data_b_in(west_input_data), .data_c_in(north_input_data), .data_d_in(east_input_data), .data_x_in(proc_input_data), .valid_a_in(south_input_valid), .valid_b_in(west_input_valid), .valid_c_in(north_input_valid), .valid_d_in(east_input_valid), .valid_x_in(proc_input_valid), .default_ready_in(default_ready_s_to_p), .yummy_in(yummyIn_P_internal));


endmodule // dynamic_node
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

//File: dynamic_node_top_wrap.v
////Creator: Michael McKeown
////Created: Sept. 21, 2014
////
////Function: This wraps the dynamic_node top and ties off signals
//            we will not be using at the tile level
////
////State:
////
////Instantiates: dynamic_node_top
////
////

// Copyright (c) 2015 Princeton University
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//     * Redistributions of source code must retain the above copyright
//       notice, this list of conditions and the following disclaimer.
//     * Redistributions in binary form must reproduce the above copyright
//       notice, this list of conditions and the following disclaimer in the
//       documentation and/or other materials provided with the distribution.
//     * Neither the name of Princeton University nor the
//       names of its contributors may be used to endorse or promote products
//       derived from this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
// ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
// WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
// DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
// DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
// (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
// LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
// ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
// SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

//==================================================================================================
//  Filename      : define.h
//  Created On    : 2014-02-20
//  Last Modified : 2018-11-16 17:14:11
//  Revision      :
//  Author        : Yaosheng Fu
//  Company       : Princeton University
//  Email         : yfu@princeton.edu
//
//  Description   : main header file defining global architecture parameters
//
//
//==================================================================================================





































































































































































































































































































































































































































































































































































































// devices.xml

module dynamic_node_top_wrap_para
(
    input clk,
    input reset_in,

    input [64-1:0] dataIn_0,
    input [64-1:0] dataIn_1,

    input validIn_0,
    input validIn_1,

    input yummyIn_0,
    input yummyIn_1,

    /*
    //original
    input [`DATA_WIDTH-1:0] dataIn_N,   // data inputs from neighboring tiles
    input [`DATA_WIDTH-1:0] dataIn_E,
    input [`DATA_WIDTH-1:0] dataIn_S,
    input [`DATA_WIDTH-1:0] dataIn_W,
    input [`DATA_WIDTH-1:0] dataIn_P,   // data input from processor

    input validIn_N,        // valid signals from neighboring tiles
    input validIn_E,
    input validIn_S,
    input validIn_W,
    input validIn_P,        // valid signal from processor

    input yummyIn_N,        // neighbor consumed output data
    input yummyIn_E,
    input yummyIn_S,
    input yummyIn_W,
    input yummyIn_P,        // processor consumed output data
    */
    input [8-1:0] myLocX,       // this tile's position
    input [8-1:0] myLocY,
    input [14-1:0] myChipID,

    output [64-1:0] dataOut_0,
    output [64-1:0] dataOut_1,

    output validOut_0,
    output validOut_1,

    output yummyOut_0,
    output yummyOut_1,


    /*
    //original
    output [`DATA_WIDTH-1:0] dataOut_N, // data outputs to neighbors
    output [`DATA_WIDTH-1:0] dataOut_E,
    output [`DATA_WIDTH-1:0] dataOut_S,
    output [`DATA_WIDTH-1:0] dataOut_W,
    output [`DATA_WIDTH-1:0] dataOut_P, // data output to processor

    output validOut_N,      // valid outputs to neighbors
    output validOut_E,
    output validOut_S,
    output validOut_W,
    output validOut_P,      // valid output to processor

    output yummyOut_N,      // yummy signal to neighbors' output buffers
    output yummyOut_E,
    output yummyOut_S,
    output yummyOut_W,
    output yummyOut_P,      // yummy signal to processor's output buffer
    */

    output thanksIn_1      // thanksIn to processor's space_avail
);

    dynamic_node_top_para dynamic_node_top
    (
        .clk(clk),
        .reset_in(reset_in),

        .dataIn_0(dataIn_0),
        .dataIn_1(dataIn_1),
        .validIn_0(validIn_0),
        .validIn_1(validIn_1),
        .yummyIn_0(yummyIn_0),
        .yummyIn_1(yummyIn_1),

        .myLocX(myLocX),
        .myLocY(myLocY),
        .myChipID(myChipID),
        .ec_cfg(6'b0),
        .store_meter_partner_address_X(5'b0),
        .store_meter_partner_address_Y(5'b0),

        .dataOut_0(dataOut_0),
        .dataOut_1(dataOut_1),
        .validOut_0(validOut_0),
        .validOut_1(validOut_1),
        .yummyOut_0(yummyOut_0),
        .yummyOut_1(yummyOut_1),

        .thanksIn_1(thanksIn_1),
        .external_interrupt(),
        .store_meter_ack_partner(),
        .store_meter_ack_non_partner(),
        .ec_out()
    );

endmodule
/*
Copyright (c) 2015 Princeton University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Princeton University nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

//Function: This wires everything together to make a crossbar
//

// Copyright (c) 2015 Princeton University
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//     * Redistributions of source code must retain the above copyright
//       notice, this list of conditions and the following disclaimer.
//     * Redistributions in binary form must reproduce the above copyright
//       notice, this list of conditions and the following disclaimer in the
//       documentation and/or other materials provided with the distribution.
//     * Neither the name of Princeton University nor the
//       names of its contributors may be used to endorse or promote products
//       derived from this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY PRINCETON UNIVERSITY "AS IS" AND
// ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
// WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
// DISCLAIMED. IN NO EVENT SHALL PRINCETON UNIVERSITY BE LIABLE FOR ANY
// DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
// (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
// LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
// ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
// SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

//==================================================================================================
//  Filename      : define.h
//  Created On    : 2014-02-20
//  Last Modified : 2018-11-16 17:14:11
//  Revision      :
//  Author        : Yaosheng Fu
//  Company       : Princeton University
//  Email         : yfu@princeton.edu
//
//  Description   : main header file defining global architecture parameters
//
//
//==================================================================================================





































































































































































































































































































































































































































































































































































































// devices.xml

module dynamic_node_top_para(clk,
		    reset_in,
        dataIn_0, dataIn_1,
        validIn_0, validIn_1,
        yummyIn_0,yummyIn_1,
		    myLocX,
		    myLocY,
            myChipID,
		    store_meter_partner_address_X,
		    store_meter_partner_address_Y,
		    ec_cfg,
        dataOut_0, dataOut_1,
        validOut_0, validOut_1,
        yummyOut_0,yummyOut_1,
		    thanksIn_1,
		    external_interrupt,
		    store_meter_ack_partner,
		    store_meter_ack_non_partner,
		    ec_out);

// begin port declarations

input clk;
input reset_in;

input [64-1:0] dataIn_0;
input [64-1:0] dataIn_1;

input validIn_0;
input validIn_1;

input yummyIn_0;
input yummyIn_1;

/*
//original
input [`DATA_WIDTH-1:0] dataIn_N;	// data inputs from neighboring tiles
input [`DATA_WIDTH-1:0] dataIn_E;
input [`DATA_WIDTH-1:0] dataIn_S;
input [`DATA_WIDTH-1:0] dataIn_W;
input [`DATA_WIDTH-1:0] dataIn_P;	// data input from processor

input validIn_N;		// valid signals from neighboring tiles
input validIn_E;
input validIn_S;
input validIn_W;
input validIn_P;		// valid signal from processor

input yummyIn_N;		// neighbor consumed output data
input yummyIn_E;
input yummyIn_S;
input yummyIn_W;
input yummyIn_P;		// processor consumed output data
*/
input [8-1:0] myLocX;		// this tile's position
input [8-1:0] myLocY;
input [14-1:0] myChipID;

input [4:0] store_meter_partner_address_X;
input [4:0] store_meter_partner_address_Y;

input [5:0] ec_cfg;            // NESWP 3 bits each selecter of event to monitor

output [64-1:0] dataOut_0;
output [64-1:0] dataOut_1;

output validOut_0;
output validOut_1;

output yummyOut_0;
output yummyOut_1;

/*
//original
output [`DATA_WIDTH-1:0] dataOut_N;	// data outputs to neighbors
output [`DATA_WIDTH-1:0] dataOut_E;
output [`DATA_WIDTH-1:0] dataOut_S;
output [`DATA_WIDTH-1:0] dataOut_W;
output [`DATA_WIDTH-1:0] dataOut_P;	// data output to processor

output validOut_N;		// valid outputs to neighbors
output validOut_E;
output validOut_S;
output validOut_W;
output validOut_P;		// valid output to processor

output yummyOut_N;		// yummy signal to neighbors' output buffers
output yummyOut_E;
output yummyOut_S;
output yummyOut_W;
output yummyOut_P;		// yummy signal to processor's output buffer
*/
output thanksIn_1;		// thanksIn to processor's space_avail

output external_interrupt;	//is used for the proc to know
				//that an external interrupt occured
output store_meter_ack_partner;      // strobes high when a memory ack word is popped off of the network
                                     // and the sender ID matches the "partner port" id from the STORE_METER
output store_meter_ack_non_partner;  // strobes high when a memory ack word is popped off of the network
                                     // and the sender ID does not match the "partner port" id from the STORE_METER


output [1:0] ec_out;

wire   ec_wants_to_send_but_cannot_0;
wire   ec_wants_to_send_but_cannot_1;

// end port declarations

   wire store_ack_received;
   wire store_ack_received_r;
   wire [9:0] store_ack_addr;
   wire [9:0] store_ack_addr_r;

//wires
wire node_0_input_tail;
wire node_1_input_tail;

wire [64-1:0] node_0_input_data;
wire [64-1:0] node_1_input_data;

wire node_0_input_valid;
wire node_1_input_valid;

wire thanks_0_to_0;
wire thanks_0_to_1;

wire thanks_1_to_0;
wire thanks_1_to_1;

wire route_req_0_to_0;
wire route_req_0_to_1;

wire route_req_1_to_0;
wire route_req_1_to_1;

wire default_ready_0_to_0;
wire default_ready_0_to_1;

wire yummyOut_0_internal;
wire yummyOut_1_internal;

wire validOut_0_internal;
wire validOut_1_internal;

wire [64-1:0] dataOut_0_internal;
wire [64-1:0] dataOut_1_internal;

wire yummyOut_0_flip1_out;

wire validOut_0_flip1_out;

wire [64-1:0] dataOut_0_flip1_out;

wire yummyIn_0_internal;
wire yummyIn_1_internal;

wire validIn_0_internal;

wire [64-1:0] dataIn_0_internal;

wire yummyIn_0_flip1_out;

wire validIn_0_flip1_out;

wire [64-1:0] dataIn_0_flip1_out;

/*
//original
wire default_ready_n_to_s;
wire default_ready_e_to_w;
wire default_ready_s_to_n;
wire default_ready_s_to_p;
wire default_ready_w_to_e;

// input/output buffered signals
wire yummyOut_N_internal;
wire yummyOut_E_internal;
wire yummyOut_S_internal;
wire yummyOut_W_internal;
wire yummyOut_P_internal;

wire validOut_N_internal;
wire validOut_E_internal;
wire validOut_S_internal;
wire validOut_W_internal;
wire validOut_P_internal;

wire [`DATA_WIDTH-1:0] dataOut_N_internal;
wire [`DATA_WIDTH-1:0] dataOut_E_internal;
wire [`DATA_WIDTH-1:0] dataOut_S_internal;
wire [`DATA_WIDTH-1:0] dataOut_W_internal;
wire [`DATA_WIDTH-1:0] dataOut_P_internal;

wire yummyOut_N_flip1_out;
wire yummyOut_E_flip1_out;
wire yummyOut_S_flip1_out;
wire yummyOut_W_flip1_out;
//wire yummyOut_P_flip1_out;

wire validOut_N_flip1_out;
wire validOut_E_flip1_out;
wire validOut_S_flip1_out;
wire validOut_W_flip1_out;
//wire validOut_P_flip1_out;

wire [`DATA_WIDTH-1:0] dataOut_N_flip1_out;
wire [`DATA_WIDTH-1:0] dataOut_E_flip1_out;
wire [`DATA_WIDTH-1:0] dataOut_S_flip1_out;
wire [`DATA_WIDTH-1:0] dataOut_W_flip1_out;
//wire [`DATA_WIDTH-1:0] dataOut_P_flip1_out;

wire yummyIn_N_internal;
wire yummyIn_E_internal;
wire yummyIn_S_internal;
wire yummyIn_W_internal;
wire yummyIn_P_internal;

wire validIn_N_internal;
wire validIn_E_internal;
wire validIn_S_internal;
wire validIn_W_internal;
//wire validIn_P_internal;

wire [`DATA_WIDTH-1:0] dataIn_N_internal;
wire [`DATA_WIDTH-1:0] dataIn_E_internal;
wire [`DATA_WIDTH-1:0] dataIn_S_internal;
wire [`DATA_WIDTH-1:0] dataIn_W_internal;
//wire [`DATA_WIDTH-1:0] dataIn_P_internal;

wire yummyIn_N_flip1_out;
wire yummyIn_E_flip1_out;
wire yummyIn_S_flip1_out;
wire yummyIn_W_flip1_out;
//wire yummyIn_P_flip1_out;

wire validIn_N_flip1_out;
wire validIn_E_flip1_out;
wire validIn_S_flip1_out;
wire validIn_W_flip1_out;
//wire validIn_P_flip1_out;

wire [`DATA_WIDTH-1:0] dataIn_N_flip1_out;
wire [`DATA_WIDTH-1:0] dataIn_E_flip1_out;
wire [`DATA_WIDTH-1:0] dataIn_S_flip1_out;
wire [`DATA_WIDTH-1:0] dataIn_W_flip1_out;
//wire [`DATA_WIDTH-1:0] dataIn_P_flip1_out;
*/
//state
reg [8-1:0] myLocX_f;
reg [8-1:0] myLocY_f;
reg [14-1:0] myChipID_f;
wire   reset;


// event counter logic
//
//
reg ec_thanks_0_to_0_reg, ec_thanks_0_to_1_reg;
reg ec_thanks_1_to_0_reg, ec_thanks_1_to_1_reg;
reg ec_wants_to_send_but_cannot_0_reg, ec_wants_to_send_but_cannot_1_reg;
reg ec_0_input_valid_reg, ec_1_input_valid_reg;

/*
//original
reg ec_thanks_n_to_n_reg, ec_thanks_n_to_e_reg, ec_thanks_n_to_s_reg, ec_thanks_n_to_w_reg, ec_thanks_n_to_p_reg;
reg ec_thanks_e_to_n_reg, ec_thanks_e_to_e_reg, ec_thanks_e_to_s_reg, ec_thanks_e_to_w_reg, ec_thanks_e_to_p_reg;
reg ec_thanks_s_to_n_reg, ec_thanks_s_to_e_reg, ec_thanks_s_to_s_reg, ec_thanks_s_to_w_reg, ec_thanks_s_to_p_reg;
reg ec_thanks_w_to_n_reg, ec_thanks_w_to_e_reg, ec_thanks_w_to_s_reg, ec_thanks_w_to_w_reg, ec_thanks_w_to_p_reg;
reg ec_thanks_p_to_n_reg, ec_thanks_p_to_e_reg, ec_thanks_p_to_s_reg, ec_thanks_p_to_w_reg, ec_thanks_p_to_p_reg;
reg ec_wants_to_send_but_cannot_N_reg, ec_wants_to_send_but_cannot_E_reg, ec_wants_to_send_but_cannot_S_reg, ec_wants_to_send_but_cannot_W_reg, ec_wants_to_send_but_cannot_P_reg;
reg ec_north_input_valid_reg, ec_east_input_valid_reg, ec_south_input_valid_reg, ec_west_input_valid_reg, ec_proc_input_valid_reg;
*/

// let's register these babies before they do any damage to the cycle time -- mbt
always @(posedge clk)
  begin

    ec_thanks_0_to_0_reg <= thanks_0_to_0; ec_thanks_0_to_1_reg <= thanks_0_to_1;
    ec_thanks_1_to_0_reg <= thanks_1_to_0; ec_thanks_1_to_1_reg <= thanks_1_to_1;
    ec_wants_to_send_but_cannot_0_reg <= ec_wants_to_send_but_cannot_0;
    ec_wants_to_send_but_cannot_1_reg <= ec_wants_to_send_but_cannot_1;
    ec_0_input_valid_reg <= node_0_input_valid;
    ec_1_input_valid_reg <= node_1_input_valid;

    /*
    //original
     ec_thanks_n_to_n_reg <= thanks_n_to_n; ec_thanks_n_to_e_reg <= thanks_n_to_e; ec_thanks_n_to_s_reg <= thanks_n_to_s; ec_thanks_n_to_w_reg <= thanks_n_to_w; ec_thanks_n_to_p_reg <= thanks_n_to_p;
     ec_thanks_e_to_n_reg <= thanks_e_to_n; ec_thanks_e_to_e_reg <= thanks_e_to_e; ec_thanks_e_to_s_reg <= thanks_e_to_s; ec_thanks_e_to_w_reg <= thanks_e_to_w; ec_thanks_e_to_p_reg <= thanks_e_to_p;
     ec_thanks_s_to_n_reg <= thanks_s_to_n; ec_thanks_s_to_e_reg <= thanks_s_to_e; ec_thanks_s_to_s_reg <= thanks_s_to_s; ec_thanks_s_to_w_reg <= thanks_s_to_w; ec_thanks_s_to_p_reg <= thanks_s_to_p;
     ec_thanks_w_to_n_reg <= thanks_w_to_n; ec_thanks_w_to_e_reg <= thanks_w_to_e; ec_thanks_w_to_s_reg <= thanks_w_to_s; ec_thanks_w_to_w_reg <= thanks_w_to_w; ec_thanks_w_to_p_reg <= thanks_w_to_p;
     ec_thanks_p_to_n_reg <= thanks_p_to_n; ec_thanks_p_to_e_reg <= thanks_p_to_e; ec_thanks_p_to_s_reg <= thanks_p_to_s; ec_thanks_p_to_w_reg <= thanks_p_to_w; ec_thanks_p_to_p_reg <= thanks_p_to_p;
     ec_wants_to_send_but_cannot_N_reg <= ec_wants_to_send_but_cannot_N;
     ec_wants_to_send_but_cannot_E_reg <= ec_wants_to_send_but_cannot_E;
     ec_wants_to_send_but_cannot_S_reg <= ec_wants_to_send_but_cannot_S;
     ec_wants_to_send_but_cannot_W_reg <= ec_wants_to_send_but_cannot_W;
     ec_wants_to_send_but_cannot_P_reg <= ec_wants_to_send_but_cannot_P;
     ec_north_input_valid_reg <= north_input_valid;
     ec_east_input_valid_reg  <= east_input_valid;
     ec_south_input_valid_reg <= south_input_valid;
     ec_west_input_valid_reg  <= west_input_valid;
     ec_proc_input_valid_reg  <= proc_input_valid;
    */
  end

wire ec_thanks_to_0= ec_thanks_0_to_0_reg | ec_thanks_1_to_0_reg ;
wire ec_thanks_to_1= ec_thanks_0_to_1_reg | ec_thanks_1_to_1_reg ;

/*
//original
   wire ec_thanks_to_n = ec_thanks_n_to_n_reg | ec_thanks_e_to_n_reg | ec_thanks_s_to_n_reg | ec_thanks_w_to_n_reg | ec_thanks_p_to_n_reg;
   wire ec_thanks_to_e = ec_thanks_n_to_e_reg | ec_thanks_e_to_e_reg | ec_thanks_s_to_e_reg | ec_thanks_w_to_e_reg | ec_thanks_p_to_e_reg;
   wire ec_thanks_to_s = ec_thanks_n_to_s_reg | ec_thanks_e_to_s_reg | ec_thanks_s_to_s_reg | ec_thanks_w_to_s_reg | ec_thanks_p_to_s_reg;
   wire ec_thanks_to_w = ec_thanks_n_to_w_reg | ec_thanks_e_to_w_reg | ec_thanks_s_to_w_reg | ec_thanks_w_to_w_reg | ec_thanks_p_to_w_reg;
   wire ec_thanks_to_p = ec_thanks_n_to_p_reg | ec_thanks_e_to_p_reg | ec_thanks_s_to_p_reg | ec_thanks_w_to_p_reg | ec_thanks_p_to_p_reg;
*/
one_of_n_plus_3 #(1) ec_mux_0(.in0(ec_wants_to_send_but_cannot_0),
                        .in1(ec_thanks_1_to_0_reg),
                        .in2(ec_thanks_0_to_0_reg),
                        .in3(ec_thanks_to_0),
                        .in4(ec_0_input_valid_reg & ~ec_thanks_to_0),
                        .sel(ec_cfg[5:3]),
                        .out(ec_out[1]));
one_of_n_plus_3 #(1) ec_mux_1(.in0(ec_wants_to_send_but_cannot_1),
                        .in1(ec_thanks_1_to_1_reg),
                        .in2(ec_thanks_0_to_1_reg),
                        .in3(ec_thanks_to_1),
                        .in4(ec_1_input_valid_reg & ~ec_thanks_to_1),
                        .sel(ec_cfg[2:0]),
                        .out(ec_out[0]));

/*
//original
one_of_eight #(1) ec_mux_north(.in0(ec_wants_to_send_but_cannot_N),
                        .in1(ec_thanks_p_to_n_reg),
                        .in2(ec_thanks_w_to_n_reg),
                        .in3(ec_thanks_s_to_n_reg),
                        .in4(ec_thanks_e_to_n_reg),
                        .in5(ec_thanks_n_to_n_reg),
                        .in6(ec_thanks_to_n),
                        .in7(ec_north_input_valid_reg & ~ec_thanks_to_n),
                        .sel(ec_cfg[14:12]),
                        .out(ec_out[4]));

one_of_eight #(1) ec_mux_east(.in0(ec_wants_to_send_but_cannot_E),
                       .in1(ec_thanks_p_to_e_reg),
                       .in2(ec_thanks_w_to_e_reg),
                       .in3(ec_thanks_s_to_e_reg),
                       .in4(ec_thanks_e_to_e_reg),
                       .in5(ec_thanks_n_to_e_reg),
                       .in6(ec_thanks_to_e),
                       .in7(ec_east_input_valid_reg & ~ec_thanks_to_e),
                       .sel(ec_cfg[11:9]),
                       .out(ec_out[3]));

one_of_eight #(1) ec_mux_south(.in0(ec_wants_to_send_but_cannot_S),
                        .in1(ec_thanks_p_to_s_reg),
                        .in2(ec_thanks_w_to_s_reg),
                        .in3(ec_thanks_s_to_s_reg),
                        .in4(ec_thanks_e_to_s_reg),
                        .in5(ec_thanks_n_to_s_reg),
                        .in6(ec_thanks_to_s),
                        .in7(ec_south_input_valid_reg & ~ec_thanks_to_s),
                        .sel(ec_cfg[8:6]),
                        .out(ec_out[2]));

one_of_eight #(1) ec_mux_west( .in0(ec_wants_to_send_but_cannot_W),
                        .in1(ec_thanks_p_to_w_reg),
                        .in2(ec_thanks_w_to_w_reg),
                        .in3(ec_thanks_s_to_w_reg),
                        .in4(ec_thanks_e_to_w_reg),
                        .in5(ec_thanks_n_to_w_reg),
                        .in6(ec_thanks_to_w),
                        .in7(ec_west_input_valid_reg & ~ec_thanks_to_w),
                        .sel(ec_cfg[5:3]),
                        .out(ec_out[1]));

one_of_eight #(1) ec_mux_proc( .in0(ec_wants_to_send_but_cannot_P),
                        .in1(ec_thanks_p_to_p_reg),
                        .in2(ec_thanks_w_to_p_reg),
                        .in3(ec_thanks_s_to_p_reg),
                        .in4(ec_thanks_e_to_p_reg),
                        .in5(ec_thanks_n_to_p_reg),
                        .in6(ec_thanks_to_p),
                        .in7(ec_proc_input_valid_reg & ~ec_thanks_to_p),
                        .sel(ec_cfg[2:0]),
                        .out(ec_out[0]));
*/
// end event counter logic

net_dff #(1) REG_reset_fin(.d(reset_in), .q(reset), .clk(clk));

net_dff #(10) REG_store_ack_addr(   .d(store_ack_addr),     .q(store_ack_addr_r),     .clk(clk));
net_dff #(1) REG_store_ack_received(.d(store_ack_received), .q(store_ack_received_r), .clk(clk));

   wire is_partner_address_v_r;
   bus_compare_equal #(10) CMP_partner_address (.a(store_ack_addr_r),
                                        .b({ store_meter_partner_address_Y, store_meter_partner_address_X } ),
                                        .bus_equal(is_partner_address_v_r));

   assign store_meter_ack_partner     = is_partner_address_v_r & store_ack_received_r;
   assign store_meter_ack_non_partner = ~is_partner_address_v_r & store_ack_received_r;

//make it so that the mdn_cfg location register has
//one cycle latency when being changed
//this was done so that these flops could be put near the
//dynamic network but this does mean that the cycle directly
//folowing a mtsr MDN_CFG which changes the location bits
//will still use the old value
//likewise it would be best to make sure there are no in-flight memory
//operations when setting the X and Y location for a tile.
always @ (posedge clk)
begin
        if(reset)
        begin
                myLocY_f <= 8'd0;
                myLocX_f <= 8'd0;
                myChipID_f <= 14'd0;
        end
        else
        begin
                myLocY_f <= myLocY;
                myLocX_f <= myLocX;
                myChipID_f <= myChipID;
        end
end

// mmckeown: Removing DUMMY modules
//dummy signals
/*`ifdef NO_DUMMY
`else
   rDUMMY #(1) default_ready_n_to_s_dummy (.A(default_ready_n_to_s));

   rDUMMY #(1) default_ready_e_to_w_dummy (.A(default_ready_e_to_w));

   rDUMMY #(1) default_ready_s_to_n_dummy (.A(default_ready_s_to_n));

   rDUMMY #(1) default_ready_s_to_p_dummy (.A(default_ready_s_to_p));

   rDUMMY #(1) default_ready_w_to_e_dummy (.A(default_ready_w_to_e));
`endif

//dummy signals for detecting the critical path for the valid and data signals
`ifdef NO_DUMMY
`else
   rDUMMY #(1) valid_out_north(.A(validOut_N_internal));
   rDUMMY #(1) valid_out_east(.A(validOut_E_internal));
   rDUMMY #(1) valid_out_south(.A(validOut_S_internal));
   rDUMMY #(1) valid_out_west(.A(validOut_W_internal));
   rDUMMY #(1) valid_out_proc(.A(validOut_P_internal));

   rDUMMY #(`DATA_WIDTH) data_out_north(.A(dataOut_N_internal));
   rDUMMY #(`DATA_WIDTH) data_out_east(.A(dataOut_E_internal));
   rDUMMY #(`DATA_WIDTH) data_out_south(.A(dataOut_S_internal));
   rDUMMY #(`DATA_WIDTH) data_out_west(.A(dataOut_W_internal));
   rDUMMY #(`DATA_WIDTH) data_out_proc(.A(dataOut_P_internal));
`endif*/

//wire regs

//assigns
assign thanksIn_1 = thanks_0_to_1 | thanks_1_to_1 ;

/*
//original
assign thanksIn_P = thanks_n_to_p | thanks_e_to_p | thanks_s_to_p | thanks_w_to_p | thanks_p_to_p;
*/
//assign validOut_N = validOut_N_internal;
//assign validOut_E = validOut_E_internal;
//assign validOut_S = validOut_S_internal;
//assign validOut_W = validOut_W_internal;
assign validOut_1 = validOut_1_internal;

//assign dataOut_N = dataOut_N_internal;
//assign dataOut_E = dataOut_E_internal;
//assign dataOut_S = dataOut_S_internal;
//assign dataOut_W = dataOut_W_internal;
assign dataOut_1 = dataOut_1_internal;

//more assigns
assign yummyIn_1_internal = yummyIn_1;
assign yummyOut_1 = yummyOut_1_internal;

flip_bus #(1, 14) yummyOut_0_flip1(yummyOut_0_internal, yummyOut_0_flip1_out);

flip_bus #(1, 21) yummyOut_0_flip2(yummyOut_0_flip1_out, yummyOut_0);

flip_bus #(1, 14) validOut_0_flip1(validOut_0_internal, validOut_0_flip1_out);

flip_bus #(1, 21) validOut_0_flip2(validOut_0_flip1_out, validOut_0);

flip_bus #(64, 14) dataOut_0_flip1(dataOut_0_internal, dataOut_0_flip1_out);

flip_bus #(64, 21) dataOut_0_flip2(dataOut_0_flip1_out, dataOut_0);

flip_bus #(1, 14) yummyIn_0_flip1(yummyIn_0, yummyIn_0_flip1_out);

flip_bus #(1, 10) yummyIn_0_flip2(yummyIn_0_flip1_out, yummyIn_0_internal);

flip_bus #(1, 14) validIn_0_flip1(validIn_0, validIn_0_flip1_out);

flip_bus #(1, 10) validIn_0_flip2(validIn_0_flip1_out, validIn_0_internal);

flip_bus #(64, 14) dataIn_0_flip1(dataIn_0, dataIn_0_flip1_out);

flip_bus #(64, 10) dataIn_0_flip2(dataIn_0_flip1_out, dataIn_0_internal);


/*
//original
// two sets of inverters for output signals (buffering for timing purposes)
flip_bus #(1, 14) yummyOut_N_flip1(yummyOut_N_internal, yummyOut_N_flip1_out);
flip_bus #(1, 14) yummyOut_E_flip1(yummyOut_E_internal, yummyOut_E_flip1_out);
flip_bus #(1, 14) yummyOut_S_flip1(yummyOut_S_internal, yummyOut_S_flip1_out);
flip_bus #(1, 14) yummyOut_W_flip1(yummyOut_W_internal, yummyOut_W_flip1_out);
//flip_bus #(1, 14) yummyOut_P_flip1(yummyOut_P_internal, yummyOut_P_flip1_out);
flip_bus #(1, 21) yummyOut_N_flip2(yummyOut_N_flip1_out, yummyOut_N);
flip_bus #(1, 21) yummyOut_E_flip2(yummyOut_E_flip1_out, yummyOut_E);
flip_bus #(1, 21) yummyOut_S_flip2(yummyOut_S_flip1_out, yummyOut_S);
flip_bus #(1, 21) yummyOut_W_flip2(yummyOut_W_flip1_out, yummyOut_W);
//flip_bus #(1, 21) yummyOut_P_flip2(yummyOut_P_flip1_out, yummyOut_P);

flip_bus #(1, 14) validOut_N_flip1(validOut_N_internal, validOut_N_flip1_out);
flip_bus #(1, 14) validOut_E_flip1(validOut_E_internal, validOut_E_flip1_out);
flip_bus #(1, 14) validOut_S_flip1(validOut_S_internal, validOut_S_flip1_out);
flip_bus #(1, 14) validOut_W_flip1(validOut_W_internal, validOut_W_flip1_out);
//flip_bus #(1, 14) validOut_P_flip1(validOut_P_internal, validOut_P_flip1_out);
flip_bus #(1, 21) validOut_N_flip2(validOut_N_flip1_out, validOut_N);
flip_bus #(1, 21) validOut_E_flip2(validOut_E_flip1_out, validOut_E);
flip_bus #(1, 21) validOut_S_flip2(validOut_S_flip1_out, validOut_S);
flip_bus #(1, 21) validOut_W_flip2(validOut_W_flip1_out, validOut_W);
//flip_bus #(1, 21) validOut_P_flip2(validOut_P_flip1_out, validOut_P);

flip_bus #(`DATA_WIDTH, 14) dataOut_N_flip1(dataOut_N_internal, dataOut_N_flip1_out);
flip_bus #(`DATA_WIDTH, 14) dataOut_E_flip1(dataOut_E_internal, dataOut_E_flip1_out);
flip_bus #(`DATA_WIDTH, 14) dataOut_S_flip1(dataOut_S_internal, dataOut_S_flip1_out);
flip_bus #(`DATA_WIDTH, 14) dataOut_W_flip1(dataOut_W_internal, dataOut_W_flip1_out);
//flip_bus #(`DATA_WIDTH, 14) dataOut_P_flip1(dataOut_P_internal, dataOut_P_flip1_out);
flip_bus #(`DATA_WIDTH, 21) dataOut_N_flip2(dataOut_N_flip1_out, dataOut_N);
flip_bus #(`DATA_WIDTH, 21) dataOut_E_flip2(dataOut_E_flip1_out, dataOut_E);
flip_bus #(`DATA_WIDTH, 21) dataOut_S_flip2(dataOut_S_flip1_out, dataOut_S);
flip_bus #(`DATA_WIDTH, 21) dataOut_W_flip2(dataOut_W_flip1_out, dataOut_W);
//flip_bus #(`DATA_WIDTH, 21) dataOut_P_flip2(dataOut_P_flip1_out, dataOut_P);

// two sets of inverters for input signals (buffering for timing purposes)
flip_bus #(1, 14) yummyIn_N_flip1(yummyIn_N, yummyIn_N_flip1_out);
flip_bus #(1, 14) yummyIn_E_flip1(yummyIn_E, yummyIn_E_flip1_out);
flip_bus #(1, 14) yummyIn_S_flip1(yummyIn_S, yummyIn_S_flip1_out);
flip_bus #(1, 14) yummyIn_W_flip1(yummyIn_W, yummyIn_W_flip1_out);
//flip_bus #(1, 14) yummyIn_P_flip1(yummyIn_P, yummyIn_P_flip1_out);
flip_bus #(1, 10) yummyIn_N_flip2(yummyIn_N_flip1_out, yummyIn_N_internal);
flip_bus #(1, 10) yummyIn_E_flip2(yummyIn_E_flip1_out, yummyIn_E_internal);
flip_bus #(1, 10) yummyIn_S_flip2(yummyIn_S_flip1_out, yummyIn_S_internal);
flip_bus #(1, 10) yummyIn_W_flip2(yummyIn_W_flip1_out, yummyIn_W_internal);
//flip_bus #(1, 10) yummyIn_P_flip2(yummyIn_P_flip1_out, yummyIn_P_internal);

flip_bus #(1, 14) validIn_N_flip1(validIn_N, validIn_N_flip1_out);
flip_bus #(1, 14) validIn_E_flip1(validIn_E, validIn_E_flip1_out);
flip_bus #(1, 14) validIn_S_flip1(validIn_S, validIn_S_flip1_out);
flip_bus #(1, 14) validIn_W_flip1(validIn_W, validIn_W_flip1_out);
//flip_bus #(1, 14) validIn_P_flip1(validIn_P, validIn_P_flip1_out);
flip_bus #(1, 10) validIn_N_flip2(validIn_N_flip1_out, validIn_N_internal);
flip_bus #(1, 10) validIn_E_flip2(validIn_E_flip1_out, validIn_E_internal);
flip_bus #(1, 10) validIn_S_flip2(validIn_S_flip1_out, validIn_S_internal);
flip_bus #(1, 10) validIn_W_flip2(validIn_W_flip1_out, validIn_W_internal);
//flip_bus #(1, 10) validIn_P_flip2(validIn_P_flip1_out, validIn_P_internal);

flip_bus #(`DATA_WIDTH, 14) dataIn_N_flip1(dataIn_N, dataIn_N_flip1_out);
flip_bus #(`DATA_WIDTH, 14) dataIn_E_flip1(dataIn_E, dataIn_E_flip1_out);
flip_bus #(`DATA_WIDTH, 14) dataIn_S_flip1(dataIn_S, dataIn_S_flip1_out);
flip_bus #(`DATA_WIDTH, 14) dataIn_W_flip1(dataIn_W, dataIn_W_flip1_out);
//flip_bus #(`DATA_WIDTH, 14) dataIn_P_flip1(dataIn_P, dataIn_P_flip1_out);
flip_bus #(`DATA_WIDTH, 10) dataIn_N_flip2(dataIn_N_flip1_out, dataIn_N_internal);
flip_bus #(`DATA_WIDTH, 10) dataIn_E_flip2(dataIn_E_flip1_out, dataIn_E_internal);
flip_bus #(`DATA_WIDTH, 10) dataIn_S_flip2(dataIn_S_flip1_out, dataIn_S_internal);
flip_bus #(`DATA_WIDTH, 10) dataIn_W_flip2(dataIn_W_flip1_out, dataIn_W_internal);
//flip_bus #(`DATA_WIDTH, 10) dataIn_P_flip2(dataIn_P_flip1_out, dataIn_P_internal);
*/

//instantiations


//the following dense code impliments a full crossbar.
//The two main components are a dynamic_input_top_X and a dynamic_output_top_para

//the difference between dynamic_input_top_4_para and dynamic_input_top_16_para are the size of
//the nibs inside of them.

//dynamic inputs
dynamic_input_top_4_para node_0_input(.route_req_0_out(route_req_0_to_0), .route_req_1_out(route_req_0_to_1), .default_ready_0_out(default_ready_0_to_0), .default_ready_1_out(default_ready_0_to_1), .tail_out(node_0_input_tail), .yummy_out(yummyOut_0_internal), .data_out(node_0_input_data), .valid_out(node_0_input_valid), .clk(clk), .reset(reset), .my_loc_x_in(myLocX_f), .my_loc_y_in(myLocY_f), .my_chip_id_in(myChipID_f), .valid_in(validIn_0_internal), .data_in(dataIn_0_internal), .thanks_0(thanks_0_to_0), .thanks_1(thanks_1_to_0));
dynamic_input_top_4_para node_1_input(.route_req_0_out(route_req_1_to_0), .route_req_1_out(route_req_1_to_1), .default_ready_0_out(), .default_ready_1_out(), .tail_out(node_1_input_tail), .yummy_out(yummyOut_1_internal), .data_out(node_1_input_data), .valid_out(node_1_input_valid), .clk(clk), .reset(reset), .my_loc_x_in(myLocX_f), .my_loc_y_in(myLocY_f), .my_chip_id_in(myChipID_f), .valid_in(validIn_1), .data_in(dataIn_1), .thanks_0(thanks_0_to_1), .thanks_1(thanks_1_to_1));

/*
//original
dynamic_input_top_4 north_input(.route_req_n_out(route_req_n_to_n), .route_req_e_out(route_req_n_to_e), .route_req_s_out(route_req_n_to_s), .route_req_w_out(route_req_n_to_w), .route_req_p_out(route_req_n_to_p), .default_ready_n_out(), .default_ready_e_out(), .default_ready_s_out(default_ready_n_to_s), .default_ready_w_out(), .default_ready_p_out(), .tail_out(north_input_tail), .yummy_out(yummyOut_N_internal), .data_out(north_input_data), .valid_out(north_input_valid), .clk(clk), .reset(reset), .my_loc_x_in(myLocX_f), .my_loc_y_in(myLocY_f), .my_chip_id_in(myChipID_f), .valid_in(validIn_N_internal), .data_in(dataIn_N_internal), .thanks_n(thanks_n_to_n), .thanks_e(thanks_e_to_n), .thanks_s(thanks_s_to_n), .thanks_w(thanks_w_to_n), .thanks_p(thanks_p_to_n));

dynamic_input_top_4 east _input(.route_req_n_out(route_req_e_to_n), .route_req_e_out(route_req_e_to_e), .route_req_s_out(route_req_e_to_s), .route_req_w_out(route_req_e_to_w), .route_req_p_out(route_req_e_to_p), .default_ready_n_out(), .default_ready_e_out(), .default_ready_s_out(), .default_ready_w_out(default_ready_e_to_w), .default_ready_p_out(), .tail_out(east_input_tail), .yummy_out(yummyOut_E_internal), .data_out(east_input_data), .valid_out(east_input_valid), .clk(clk), .reset(reset), .my_loc_x_in(myLocX_f), .my_loc_y_in(myLocY_f), .my_chip_id_in(myChipID_f), .valid_in(validIn_E_internal), .data_in(dataIn_E_internal), .thanks_n(thanks_n_to_e), .thanks_e(thanks_e_to_e), .thanks_s(thanks_s_to_e), .thanks_w(thanks_w_to_e), .thanks_p(thanks_p_to_e));

dynamic_input_top_4 south_input(.route_req_n_out(route_req_s_to_n), .route_req_e_out(route_req_s_to_e), .route_req_s_out(route_req_s_to_s), .route_req_w_out(route_req_s_to_w), .route_req_p_out(route_req_s_to_p), .default_ready_n_out(default_ready_s_to_n), .default_ready_e_out(), .default_ready_s_out(), .default_ready_w_out(), .default_ready_p_out(default_ready_s_to_p), .tail_out(south_input_tail), .yummy_out(yummyOut_S_internal), .data_out(south_input_data), .valid_out(south_input_valid), .clk(clk), .reset(reset), .my_loc_x_in(myLocX_f), .my_loc_y_in(myLocY_f), .my_chip_id_in(myChipID_f), .valid_in(validIn_S_internal), .data_in(dataIn_S_internal), .thanks_n(thanks_n_to_s), .thanks_e(thanks_e_to_s), .thanks_s(thanks_s_to_s), .thanks_w(thanks_w_to_s), .thanks_p(thanks_p_to_s));

dynamic_input_top_4 west_input(.route_req_n_out(route_req_w_to_n), .route_req_e_out(route_req_w_to_e), .route_req_s_out(route_req_w_to_s), .route_req_w_out(route_req_w_to_w), .route_req_p_out(route_req_w_to_p), .default_ready_n_out(), .default_ready_e_out(default_ready_w_to_e), .default_ready_s_out(), .default_ready_w_out(), .default_ready_p_out(), .tail_out(west_input_tail), .yummy_out(yummyOut_W_internal), .data_out(west_input_data), .valid_out(west_input_valid), .clk(clk), .reset(reset), .my_loc_x_in(myLocX_f), .my_loc_y_in(myLocY_f), .my_chip_id_in(myChipID_f), .valid_in(validIn_W_internal), .data_in(dataIn_W_internal), .thanks_n(thanks_n_to_w), .thanks_e(thanks_e_to_w), .thanks_s(thanks_s_to_w), .thanks_w(thanks_w_to_w), .thanks_p(thanks_p_to_w));

dynamic_input_top_16 proc_input(.route_req_n_out(route_req_p_to_n), .route_req_e_out(route_req_p_to_e), .route_req_s_out(route_req_p_to_s), .route_req_w_out(route_req_p_to_w), .route_req_p_out(route_req_p_to_p), .default_ready_n_out(), .default_ready_e_out(), .default_ready_s_out(), .default_ready_w_out(), .default_ready_p_out(), .tail_out(proc_input_tail), .yummy_out(yummyOut_P_internal), .data_out(proc_input_data), .valid_out(proc_input_valid), .clk(clk), .reset(reset), .my_loc_x_in(myLocX_f), .my_loc_y_in(myLocY_f), .my_chip_id_in(myChipID_f), .valid_in(validIn_P), .data_in(dataIn_P), .thanks_n(thanks_n_to_p), .thanks_e(thanks_e_to_p), .thanks_s(thanks_s_to_p), .thanks_w(thanks_w_to_p), .thanks_p(thanks_p_to_p));
*/


//dynamic outputs
dynamic_output_top_para node_0_output(.data_out(dataOut_0_internal), .thanks_0_out(thanks_0_to_1), .thanks_1_out(thanks_0_to_0), .valid_out(validOut_0_internal), .popped_interrupt_mesg_out(), .popped_memory_ack_mesg_out(), .popped_memory_ack_mesg_out_sender(), .ec_wants_to_send_but_cannot(ec_wants_to_send_but_cannot_0), .clk(clk), .reset(reset), .route_req_0_in(route_req_1_to_0), .route_req_1_in(route_req_0_to_0), .tail_0_in(node_1_input_tail), .tail_1_in(node_0_input_tail), .data_0_in(node_1_input_data), .data_1_in(node_0_input_data), .valid_0_in(node_1_input_valid), .valid_1_in(node_0_input_valid), .default_ready_in(default_ready_0_to_0),.yummy_in(yummyIn_0_internal));
dynamic_output_top_para #(1'b0) node_1_output(.data_out(dataOut_1_internal), .thanks_0_out(thanks_1_to_0), .thanks_1_out(thanks_1_to_1), .valid_out(validOut_1_internal), .popped_interrupt_mesg_out(external_interrupt), .popped_memory_ack_mesg_out(store_ack_received), .popped_memory_ack_mesg_out_sender(store_ack_addr), .ec_wants_to_send_but_cannot(ec_wants_to_send_but_cannot_1), .clk(clk), .reset(reset), .route_req_0_in(route_req_0_to_1), .route_req_1_in(route_req_1_to_1), .tail_0_in(node_0_input_tail), .tail_1_in(node_1_input_tail), .data_0_in(node_0_input_data), .data_1_in(node_1_input_data), .valid_0_in(node_0_input_valid), .valid_1_in(node_1_input_valid), .default_ready_in(default_ready_0_to_1),.yummy_in(yummyIn_1_internal));

/*
//original
dynamic_output_top north_output(.data_out(dataOut_N_internal), .thanks_a_out(thanks_n_to_s), .thanks_b_out(thanks_n_to_w), .thanks_c_out(thanks_n_to_p), .thanks_d_out(thanks_n_to_e), .thanks_x_out(thanks_n_to_n), .valid_out(validOut_N_internal),  .popped_interrupt_mesg_out(), .popped_memory_ack_mesg_out(), .popped_memory_ack_mesg_out_sender(), .ec_wants_to_send_but_cannot(ec_wants_to_send_but_cannot_N), .clk(clk), .reset(reset), .route_req_a_in(route_req_s_to_n), .route_req_b_in(route_req_w_to_n), .route_req_c_in(route_req_p_to_n), .route_req_d_in(route_req_e_to_n), .route_req_x_in(route_req_n_to_n), .tail_a_in(south_input_tail), .tail_b_in(west_input_tail), .tail_c_in(proc_input_tail), .tail_d_in(east_input_tail), .tail_x_in(north_input_tail), .data_a_in(south_input_data), .data_b_in(west_input_data), .data_c_in(proc_input_data), .data_d_in(east_input_data), .data_x_in(north_input_data), .valid_a_in(south_input_valid), .valid_b_in(west_input_valid), .valid_c_in(proc_input_valid), .valid_d_in(east_input_valid), .valid_x_in(north_input_valid), .default_ready_in(default_ready_s_to_n), .yummy_in(yummyIn_N_internal));

dynamic_output_top east_output(.data_out(dataOut_E_internal), .thanks_a_out(thanks_e_to_w), .thanks_b_out(thanks_e_to_p), .thanks_c_out(thanks_e_to_n), .thanks_d_out(thanks_e_to_s), .thanks_x_out(thanks_e_to_e), .valid_out(validOut_E_internal),   .popped_interrupt_mesg_out(), .popped_memory_ack_mesg_out(), .popped_memory_ack_mesg_out_sender(),  .ec_wants_to_send_but_cannot(ec_wants_to_send_but_cannot_E), .clk(clk), .reset(reset), .route_req_a_in(route_req_w_to_e), .route_req_b_in(route_req_p_to_e), .route_req_c_in(route_req_n_to_e), .route_req_d_in(route_req_s_to_e), .route_req_x_in(route_req_e_to_e), .tail_a_in(west_input_tail), .tail_b_in(proc_input_tail), .tail_c_in(north_input_tail), .tail_d_in(south_input_tail), .tail_x_in(east_input_tail), .data_a_in(west_input_data), .data_b_in(proc_input_data), .data_c_in(north_input_data), .data_d_in(south_input_data), .data_x_in(east_input_data), .valid_a_in(west_input_valid), .valid_b_in(proc_input_valid), .valid_c_in(north_input_valid), .valid_d_in(south_input_valid), .valid_x_in(east_input_valid), .default_ready_in(default_ready_w_to_e), .yummy_in(yummyIn_E_internal));

dynamic_output_top south_output(.data_out(dataOut_S_internal), .thanks_a_out(thanks_s_to_n), .thanks_b_out(thanks_s_to_e), .thanks_c_out(thanks_s_to_w), .thanks_d_out(thanks_s_to_p), .thanks_x_out(thanks_s_to_s), .valid_out(validOut_S_internal),   .popped_interrupt_mesg_out(), .popped_memory_ack_mesg_out(), .popped_memory_ack_mesg_out_sender(),  .ec_wants_to_send_but_cannot(ec_wants_to_send_but_cannot_S), .clk(clk), .reset(reset), .route_req_a_in(route_req_n_to_s), .route_req_b_in(route_req_e_to_s), .route_req_c_in(route_req_w_to_s), .route_req_d_in(route_req_p_to_s), .route_req_x_in(route_req_s_to_s), .tail_a_in(north_input_tail), .tail_b_in(east_input_tail), .tail_c_in(west_input_tail), .tail_d_in(proc_input_tail), .tail_x_in(south_input_tail), .data_a_in(north_input_data), .data_b_in(east_input_data), .data_c_in(west_input_data), .data_d_in(proc_input_data), .data_x_in(south_input_data), .valid_a_in(north_input_valid), .valid_b_in(east_input_valid), .valid_c_in(west_input_valid), .valid_d_in(proc_input_valid), .valid_x_in(south_input_valid), .default_ready_in(default_ready_n_to_s), .yummy_in(yummyIn_S_internal));

dynamic_output_top west_output(.data_out(dataOut_W_internal), .thanks_a_out(thanks_w_to_e), .thanks_b_out(thanks_w_to_s), .thanks_c_out(thanks_w_to_p), .thanks_d_out(thanks_w_to_n), .thanks_x_out(thanks_w_to_w), .valid_out(validOut_W_internal),   .popped_interrupt_mesg_out(), .popped_memory_ack_mesg_out(), .popped_memory_ack_mesg_out_sender(),  .ec_wants_to_send_but_cannot(ec_wants_to_send_but_cannot_W), .clk(clk), .reset(reset), .route_req_a_in(route_req_e_to_w), .route_req_b_in(route_req_s_to_w), .route_req_c_in(route_req_p_to_w), .route_req_d_in(route_req_n_to_w), .route_req_x_in(route_req_w_to_w), .tail_a_in(east_input_tail), .tail_b_in(south_input_tail), .tail_c_in(proc_input_tail), .tail_d_in(north_input_tail), .tail_x_in(west_input_tail), .data_a_in(east_input_data), .data_b_in(south_input_data), .data_c_in(proc_input_data), .data_d_in(north_input_data), .data_x_in(west_input_data), .valid_a_in(east_input_valid), .valid_b_in(south_input_valid), .valid_c_in(proc_input_valid), .valid_d_in(north_input_valid), .valid_x_in(west_input_valid), .default_ready_in(default_ready_e_to_w), .yummy_in(yummyIn_W_internal));
//yanqi change kill headers to 0
dynamic_output_top #(1'b0) proc_output(.data_out(dataOut_P_internal), .thanks_a_out(thanks_p_to_s), .thanks_b_out(thanks_p_to_w), .thanks_c_out(thanks_p_to_n), .thanks_d_out(thanks_p_to_e), .thanks_x_out(thanks_p_to_p), .valid_out(validOut_P_internal),  .popped_interrupt_mesg_out(external_interrupt), .popped_memory_ack_mesg_out(store_ack_received), .popped_memory_ack_mesg_out_sender(store_ack_addr),  .ec_wants_to_send_but_cannot(ec_wants_to_send_but_cannot_P), .clk(clk), .reset(reset), .route_req_a_in(route_req_s_to_p), .route_req_b_in(route_req_w_to_p), .route_req_c_in(route_req_n_to_p), .route_req_d_in(route_req_e_to_p), .route_req_x_in(route_req_p_to_p), .tail_a_in(south_input_tail), .tail_b_in(west_input_tail), .tail_c_in(north_input_tail), .tail_d_in(east_input_tail), .tail_x_in(proc_input_tail), .data_a_in(south_input_data), .data_b_in(west_input_data), .data_c_in(north_input_data), .data_d_in(east_input_data), .data_x_in(proc_input_data), .valid_a_in(south_input_valid), .valid_b_in(west_input_valid), .valid_c_in(north_input_valid), .valid_d_in(east_input_valid), .valid_x_in(proc_input_valid), .default_ready_in(default_ready_s_to_p), .yummy_in(yummyIn_P_internal));
*/

endmodule // dynamic_node
