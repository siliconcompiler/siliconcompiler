//matrix_multiply.v
//Peter Grossmann
//6 July 2023
//$Id$
//$Log$

module matrix_multiply
  # (
     parameter DATA_WIDTH = 4,
     parameter RESULT_WIDTH = 8,
     parameter ROW_COL_SIZE = 3,
     parameter A_MATRIX_HEIGHT = 3,
     parameter B_MATRIX_WIDTH = 3,
     parameter NUM_PARALLEL_OUTPUTS = 1,
     parameter ROW_COL_ALL_ACCESS = (NUM_PARALLEL_OUTPUTS == 1) ? 0 : 1,
     parameter ROW_DATA_BUS_WIDTH = (ROW_COL_ALL_ACCESS == 1) ? A_MATRIX_HEIGHT*ROW_COL_SIZE*DATA_WIDTH : ROW_COL_SIZE*DATA_WIDTH,
     parameter COL_DATA_BUS_WIDTH = (ROW_COL_ALL_ACCESS == 1) ? B_MATRIX_WIDTH*ROW_COL_SIZE*DATA_WIDTH : ROW_COL_SIZE*DATA_WIDTH,
     parameter A_MATRIX_ADDRESS_WIDTH = $clog2(A_MATRIX_HEIGHT),
     parameter B_MATRIX_ADDRESS_WIDTH = $clog2(B_MATRIX_WIDTH),
     parameter RESULT_MATRIX_HEIGHT = A_MATRIX_HEIGHT,
     parameter RESULT_MATRIX_WIDTH = B_MATRIX_WIDTH,
     parameter RESULT_ADDRESS_WIDTH = $clog2(RESULT_MATRIX_HEIGHT)
     )
   (
    input 				     clk,
    input 				     resetn,
    input 				     start,
    input 				     read,

    input 				     row_write_enable,
    input 				     col_write_enable,

    input [(ROW_COL_SIZE*DATA_WIDTH-1):0]    mem_datain,
    input [(A_MATRIX_ADDRESS_WIDTH-1):0]     mem_address,
    output [(ROW_COL_SIZE*RESULT_WIDTH-1):0] mem_dataout,
    output reg [(RESULT_ADDRESS_WIDTH-1):0]  mem_address_out,
    output 				     mem_dataout_valid,
    
    output 				     done,
    output 				     read_done
    );


   genvar 				   i;
   genvar 				   k;
   
   wire [(ROW_DATA_BUS_WIDTH-1):0] row_dataout;
   wire [(ROW_COL_SIZE*DATA_WIDTH-1):0] 		row_datain;
   
   wire [(ROW_COL_SIZE*DATA_WIDTH-1):0] 		col_datain;
   wire [(COL_DATA_BUS_WIDTH-1):0] 	col_dataout;
   
   reg [(RESULT_MATRIX_HEIGHT*RESULT_WIDTH-1):0] 	all_row_col_sums;
   wire [(RESULT_MATRIX_HEIGHT-1):0] 			output_write_enable;

   wire 						col_done;
   wire 						busy;
   wire 						read_busy;
      

   wire [(A_MATRIX_ADDRESS_WIDTH-1):0] 			row_select_base;
   reg [(A_MATRIX_ADDRESS_WIDTH-1):0] 			row_select_base_sync;
   wire [(B_MATRIX_ADDRESS_WIDTH-1):0] 			col_select_base;
   
   wire [(A_MATRIX_ADDRESS_WIDTH-1):0] 			row_address;
   wire [(B_MATRIX_ADDRESS_WIDTH-1):0] 			col_address;
   
   wire [(ROW_COL_SIZE*RESULT_WIDTH-1):0] 		output_buffer_dataout;
      
   wire 						row_data_write_enable;
   wire 						col_data_write_enable;

   reg 							result_write_enable;
   reg [(RESULT_ADDRESS_WIDTH-1):0] 			result_address;
   wire [(RESULT_MATRIX_WIDTH*RESULT_WIDTH-1):0] 	result_datain;
   wire [(ROW_COL_SIZE*RESULT_WIDTH-1):0] 		result_dataout;

   wire [(RESULT_ADDRESS_WIDTH-1):0] 			      output_select;
   
   assign row_address = (start || busy) ? row_select_base : mem_address;
   assign col_address = (start || busy) ? col_select_base : mem_address;
   
   assign row_datain = mem_datain;
   assign col_datain = mem_datain;

   //assign mem_dataout_valid = read_busy;
   //assign mem_address_out = result_address;
   assign mem_dataout = result_dataout;
   
   always @(posedge clk) begin
      row_select_base_sync <= row_select_base;
   end

   reg read_busy_sync;
   
   always @(posedge clk) begin
      mem_address_out <= result_address;
      read_busy_sync <= read_busy;
      mem_dataout_valid <= read_busy_sync;
   end
   
   always @(posedge clk) begin
      if (~resetn) begin
	 result_address <= 'h0;
      end
      else begin
	 if (read) begin
	    result_address <= output_select;
	 end
	 else begin
	    result_address <= row_select_base_sync;
	 end
      end
   end
   
   assign result_datain = all_row_col_sums;

   always @(posedge clk) begin
      if (~resetn) begin
	 result_write_enable <= 1'b0;
      end
      else begin
	 result_write_enable <= col_done;
      end
   end
   

   row_col_memory
     # (
	.DATA_WIDTH(DATA_WIDTH),
	.ROW_COL_SIZE(ROW_COL_SIZE),
	.MATRIX_SIZE(A_MATRIX_HEIGHT),
	.ALL_ACCESS_OUTPUT(ROW_COL_ALL_ACCESS)
	)
   row_memory
     (
      .clk(clk),
      .address(row_address),
      .write_enable(row_write_enable),
      .datain(row_datain),
      .dataout(row_dataout)
      );

   row_col_memory
     # (
	.DATA_WIDTH(DATA_WIDTH),
	.ROW_COL_SIZE(ROW_COL_SIZE),
	.MATRIX_SIZE(B_MATRIX_WIDTH),
	.ALL_ACCESS_OUTPUT(ROW_COL_ALL_ACCESS)
	)
   col_memory
     (
      .clk(clk),
      .address(col_address),
      .write_enable(col_write_enable),
      .datain(col_datain),
      .dataout(col_dataout)
      );
   

   row_col_memory
     # (
	.DATA_WIDTH(RESULT_WIDTH),
	.ROW_COL_SIZE(RESULT_MATRIX_HEIGHT),
	.MATRIX_SIZE(RESULT_MATRIX_WIDTH),
	.ALL_ACCESS_OUTPUT(0)
	)
   result_memory (
		  .clk(clk),
		  .address(result_address),
		  .write_enable(result_write_enable),
		  .datain(result_datain),
		  .dataout(result_dataout)
		  ); 

	matrix_multiply_control
		# (
		.ROW_COL_SIZE(ROW_COL_SIZE),
		.MATRIX_SIZE(A_MATRIX_HEIGHT),
		.NUM_PARALLEL_OUTPUTS(NUM_PARALLEL_OUTPUTS)
	)
	matrix_multiply_control (
				.clk(clk),
				.resetn(resetn),
				.start(start),
				.col_done(col_done),
				.done(done),
				.read(read),
				.busy(busy),
				.read_busy(read_busy),
				.row_select(row_select_base),
				.col_select(col_select_base),
				.output_select(output_select),
				.read_done(read_done)
				);

`ifdef VERILATOR
	wire [(NUM_PARALLEL_OUTPUTS*RESULT_MATRIX_HEIGHT-1):0] 			row_active;
	wire [(NUM_PARALLEL_OUTPUTS*RESULT_MATRIX_HEIGHT-1):0] 			col_active;

	wire [(A_MATRIX_ADDRESS_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] 			row_select;
	reg [(A_MATRIX_ADDRESS_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] 			row_select_sync;
	wire [(ROW_COL_SIZE*DATA_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] 		row_data_mult;

	wire [(B_MATRIX_ADDRESS_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] 			col_select;
	reg [(B_MATRIX_ADDRESS_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] 			col_select_sync;
	wire [(ROW_COL_SIZE*DATA_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] 		col_data_mult;

	wire [(ROW_COL_SIZE*RESULT_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] 		row_col_product;

	wire [(RESULT_WIDTH*NUM_PARALLEL_OUTPUTS-1):0] 				row_col_sum;

	generate
		for (k = 0; k < RESULT_MATRIX_HEIGHT; k = k + 1) begin : row_active_gen_k
			for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1) begin : row_active_gen_i
				assign row_active[k*NUM_PARALLEL_OUTPUTS+i] = (row_select_sync[(i+1)*A_MATRIX_ADDRESS_WIDTH-1-:A_MATRIX_ADDRESS_WIDTH] == k);
				assign col_active[k*NUM_PARALLEL_OUTPUTS+i] = (col_select_sync[(i+1)*A_MATRIX_ADDRESS_WIDTH-1-:B_MATRIX_ADDRESS_WIDTH] == k);
			end
		end
   	endgenerate

	generate
		for (k = 0; k < RESULT_MATRIX_HEIGHT; k = k + 1) begin : output_write_enable_gen
			assign output_write_enable[k] = |(col_active[k]) && start;
		end
   	endgenerate


	generate
		if (NUM_PARALLEL_OUTPUTS == 1) begin : dot_product

			assign row_select = row_select_base;
			assign col_select = col_select_base;

			assign row_data_mult = row_dataout;
			assign col_data_mult = col_dataout;
						
			row_col_multiply 
			# (
				.DATA_WIDTH(DATA_WIDTH),
				.PRODUCT_WIDTH(RESULT_WIDTH),
				.ROW_COL_SIZE(ROW_COL_SIZE)
				)
			row_col_multiplier (
						.a(row_data_mult),
						.b(col_data_mult),
						.y(row_col_product)
						);
		
			row_col_product_adder
			# (
				.PRODUCT_WIDTH(RESULT_WIDTH),
				.SUM_WIDTH(RESULT_WIDTH),
				.ROW_COL_SIZE(ROW_COL_SIZE)
				)
			row_col_product_adder (
					.product(row_col_product),
					.sum(row_col_sum)
					);

		
			always @(posedge clk) begin
				if (~resetn) begin
					all_row_col_sums <= 'h0;
				end
				else begin
					if (output_write_enable[col_select_sync]) begin
					all_row_col_sums[((col_select_sync)*RESULT_WIDTH)+:RESULT_WIDTH] <= row_col_sum;
					end
				end
			end
			
		end // if (NUM_PARALLEL_OUTPUTS == 1)	
		else begin
			
			for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1) begin : dot_product

				assign row_select[(i+1)*A_MATRIX_ADDRESS_WIDTH-1-:A_MATRIX_ADDRESS_WIDTH] = row_select_base + i;
				assign col_select[(i+1)*B_MATRIX_ADDRESS_WIDTH-1-:B_MATRIX_ADDRESS_WIDTH] = col_select_base + i;
				
				row_col_data_mux
					# (
					
					)
				row_mux (
						.row_col_datain(row_dataout),
						.select(row_select[(i+1)*A_MATRIX_ADDRESS_WIDTH-1-:A_MATRIX_ADDRESS_WIDTH]),
						.row_col_selected(row_data_mult[(i+1)*ROW_COL_SIZE*DATA_WIDTH-1-:ROW_COL_SIZE*DATA_WIDTH])
						);
				
				row_col_data_mux
					# (
					
					)
				col_mux (
						.row_col_datain(col_dataout),
						.select(col_select[(i+1)*B_MATRIX_ADDRESS_WIDTH-1-:B_MATRIX_ADDRESS_WIDTH]),
						.row_col_selected(col_data_mult[(i+1)*ROW_COL_SIZE*DATA_WIDTH-1-:ROW_COL_SIZE*DATA_WIDTH])
						);
				
				row_col_multiply 
				# (
				.DATA_WIDTH(DATA_WIDTH),
				.PRODUCT_WIDTH(RESULT_WIDTH)
				)
				row_col_multiplier (
						.a(row_data_mult[(i+1)*ROW_COL_SIZE*DATA_WIDTH-1-:ROW_COL_SIZE*DATA_WIDTH]),
						.b(col_data_mult[(i+1)*ROW_COL_SIZE*DATA_WIDTH-1-:ROW_COL_SIZE*DATA_WIDTH]),
						.y(row_col_product[(i+1)*ROW_COL_SIZE*RESULT_WIDTH-1-:ROW_COL_SIZE*RESULT_WIDTH])
						);
				
				row_col_product_adder
				# (
				.PRODUCT_WIDTH(RESULT_WIDTH),
				.SUM_WIDTH(RESULT_WIDTH),
				.ROW_COL_SIZE(ROW_COL_SIZE)
				)
				row_col_product_adder (
						.product(row_col_product[(i+1)*ROW_COL_SIZE*RESULT_WIDTH-1-:ROW_COL_SIZE*RESULT_WIDTH]),
						.sum(row_col_sum[(i+1)*RESULT_WIDTH-1-:RESULT_WIDTH])
						);

				always @(posedge clk) begin
					if (~resetn) begin
						all_row_col_sums <= 'h0;
					end
					else begin
						if (output_write_enable[col_select[(i+1)*B_MATRIX_ADDRESS_WIDTH-1-:B_MATRIX_ADDRESS_WIDTH]]) begin
							all_row_col_sums[((col_select[(i+1)*B_MATRIX_ADDRESS_WIDTH-1-:B_MATRIX_ADDRESS_WIDTH])*RESULT_WIDTH)+:RESULT_WIDTH] <= row_col_sum[(i+1)*RESULT_WIDTH-1-:RESULT_WIDTH];
						end
					end
				end
				
			end // for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1)

		end // else: !if(NUM_PARALLEL_OUTPUTS == 1)
   	endgenerate

	generate
		for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1) begin : select_sync_gen
			always @(posedge clk) begin
				row_select_sync[(i+1)*A_MATRIX_ADDRESS_WIDTH-1-:A_MATRIX_ADDRESS_WIDTH] <= row_select[(i+1)*A_MATRIX_ADDRESS_WIDTH-1-:A_MATRIX_ADDRESS_WIDTH];
				col_select_sync[(i+1)*B_MATRIX_ADDRESS_WIDTH-1-:B_MATRIX_ADDRESS_WIDTH] <= col_select[(i+1)*B_MATRIX_ADDRESS_WIDTH-1-:B_MATRIX_ADDRESS_WIDTH];
			end
      	end
   	endgenerate

`else // !`ifdef VERILATOR
	wire [(NUM_PARALLEL_OUTPUTS-1):0] 			row_active[(RESULT_MATRIX_HEIGHT-1):0];
	wire [(NUM_PARALLEL_OUTPUTS-1):0] 			col_active[(RESULT_MATRIX_HEIGHT-1):0];

	wire [(A_MATRIX_ADDRESS_WIDTH-1):0] 			row_select[(NUM_PARALLEL_OUTPUTS-1):0];
	reg [(A_MATRIX_ADDRESS_WIDTH-1):0] 			row_select_sync[(NUM_PARALLEL_OUTPUTS-1):0];
	wire [(ROW_COL_SIZE*DATA_WIDTH-1):0] 		row_data_mult[(NUM_PARALLEL_OUTPUTS-1):0];

	wire [(B_MATRIX_ADDRESS_WIDTH-1):0] 			col_select[(NUM_PARALLEL_OUTPUTS-1):0];
	reg [(B_MATRIX_ADDRESS_WIDTH-1):0] 			col_select_sync[(NUM_PARALLEL_OUTPUTS-1):0];
	wire [(ROW_COL_SIZE*DATA_WIDTH-1):0] 		col_data_mult[(NUM_PARALLEL_OUTPUTS-1):0];

	wire [(ROW_COL_SIZE*RESULT_WIDTH-1):0] 		row_col_product[(NUM_PARALLEL_OUTPUTS-1):0];

	wire [(RESULT_WIDTH-1):0] 				row_col_sum[(NUM_PARALLEL_OUTPUTS-1):0];

	generate
		for (k = 0; k < RESULT_MATRIX_HEIGHT; k = k + 1) begin : row_active_gen_k
			for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1) begin : row_active_gen_i
				assign row_active[k][i] = (row_select_sync[i] == k);
				assign col_active[k][i] = (col_select_sync[i] == k);
			end
		end
   	endgenerate

	generate
		for (k = 0; k < RESULT_MATRIX_HEIGHT; k = k + 1) begin : output_write_enable_gen
			assign output_write_enable[k] = |(col_active[k]) && start;
		end
   	endgenerate


	generate
		if (NUM_PARALLEL_OUTPUTS == 1) begin : dot_product

			assign row_select[0] = row_select_base;
			assign col_select[0] = col_select_base;

			assign row_data_mult[0] = row_dataout;
			assign col_data_mult[0] = col_dataout;
						
			row_col_multiply 
			# (
				.DATA_WIDTH(DATA_WIDTH),
				.PRODUCT_WIDTH(RESULT_WIDTH),
				.ROW_COL_SIZE(ROW_COL_SIZE)
				)
			row_col_multiplier (
						.a(row_data_mult[0]),
						.b(col_data_mult[0]),
						.y(row_col_product[0])
						);
		
			row_col_product_adder
			# (
				.PRODUCT_WIDTH(RESULT_WIDTH),
				.SUM_WIDTH(RESULT_WIDTH),
				.ROW_COL_SIZE(ROW_COL_SIZE)
				)
			row_col_product_adder (
					.product(row_col_product[0]),
					.sum(row_col_sum[0])
					);

		
			always @(posedge clk) begin
				if (~resetn) begin
					all_row_col_sums <= 'h0;
				end
				else begin
					if (output_write_enable[col_select_sync[0]]) begin
					all_row_col_sums[((col_select_sync[0])*RESULT_WIDTH)+:RESULT_WIDTH] <= row_col_sum[0];
					end
				end
			end
			
		end // if (NUM_PARALLEL_OUTPUTS == 1)
			
		else begin
			
			for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1) begin : dot_product

				assign row_select[i] = row_select_base + i;
				assign col_select[i] = col_select_base + i;
				
				row_col_data_mux
					# (
					
					)
				row_mux (
						.row_col_datain(row_dataout),
						.select(row_select[i]),
						.row_col_selected(row_data_mult[i])
						);
				
				row_col_data_mux
					# (
					
					)
				col_mux (
						.row_col_datain(col_dataout),
						.select(col_select[i]),
						.row_col_selected(col_data_mult[i])
						);
				
				row_col_multiply 
				# (
				.DATA_WIDTH(DATA_WIDTH),
				.PRODUCT_WIDTH(RESULT_WIDTH)
				)
				row_col_multiplier (
						.a(row_data_mult[i]),
						.b(col_data_mult[i]),
						.y(row_col_product[i])
						);
				
				row_col_product_adder
				# (
				.PRODUCT_WIDTH(RESULT_WIDTH),
				.SUM_WIDTH(RESULT_WIDTH),
				.ROW_COL_SIZE(ROW_COL_SIZE)
				)
				row_col_product_adder (
						.product(row_col_product[i]),
						.sum(row_col_sum[i])
						);

				always @(posedge clk) begin
					if (~resetn) begin
						all_row_col_sums <= 'h0;
					end
					else begin
						if (output_write_enable[col_select[i]]) begin
							all_row_col_sums[((col_select[i])*RESULT_WIDTH)+:RESULT_WIDTH] <= row_col_sum[i];
						end
					end
				end
				
			end // for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1)

		end // else: !if(NUM_PARALLEL_OUTPUTS == 1)
   	endgenerate

	generate
		for (i = 0; i < NUM_PARALLEL_OUTPUTS; i = i + 1) begin : select_sync_gen
			always @(posedge clk) begin
				row_select_sync[i] <= row_select[i];
				col_select_sync[i] <= col_select[i];
			end
      	end
   	endgenerate

`endif
	
endmodule // matrix_multiply
