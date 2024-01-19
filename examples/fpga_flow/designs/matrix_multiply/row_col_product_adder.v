//row_col_product_adder.v
//Peter Grossmann
//6 July 2023
//$Id$
//$Log$

module row_col_product_adder
  # ( 
      parameter PRODUCT_WIDTH = 16,
      parameter SUM_WIDTH = 32,
      parameter ROW_COL_SIZE = 16
      )
   (
    input [(ROW_COL_SIZE*PRODUCT_WIDTH-1):0]  product,
    output [(SUM_WIDTH-1):0] sum
    );
   
   `ifdef VERILATOR
      genvar 		      i;

      /* verilator lint_off UNOPTFLAT */
      wire [(SUM_WIDTH*ROW_COL_SIZE-1):0] partial_sum;
      /* verilator lint_on UNOPTFLAT */
      
      assign sum = partial_sum[ROW_COL_SIZE*SUM_WIDTH-1-:SUM_WIDTH];
      
      generate
         for (i = 0; i < ROW_COL_SIZE; i = i + 1) begin : adder_gen

      if (i == 0) begin
         /* verilator lint_off WIDTH */
         assign partial_sum[(i+1)*SUM_WIDTH-1-:SUM_WIDTH] = product[(PRODUCT_WIDTH-1):0];
         /* verilator lint_on WIDTH */
      end
      else begin
         /* verilator lint_off WIDTH */
         assign partial_sum[(i+1)*SUM_WIDTH-1-:SUM_WIDTH] 
            = partial_sum[i*SUM_WIDTH-1-:SUM_WIDTH] + product[((i+1)*PRODUCT_WIDTH-1):(i*PRODUCT_WIDTH)];
         /* verilator lint_on WIDTH */
      end
      
         end // block: adder_gen
      endgenerate
   `else // !`ifdef VERILATOR
      genvar 		      i;

      /* verilator lint_off UNOPTFLAT */
      wire [(SUM_WIDTH-1):0] partial_sum[(ROW_COL_SIZE-1):0];
      /* verilator lint_on UNOPTFLAT */
      
      assign sum = partial_sum[(ROW_COL_SIZE-1)][(SUM_WIDTH-1):0];
      
      generate
         for (i = 0; i < ROW_COL_SIZE; i = i + 1) begin : adder_gen

      if (i == 0) begin
         /* verilator lint_off WIDTH */
         assign partial_sum[i] = product[(PRODUCT_WIDTH-1):0];
         /* verilator lint_on WIDTH */
      end
      else begin
         /* verilator lint_off WIDTH */
         assign partial_sum[i] 
            = partial_sum[i-1] + product[((i+1)*PRODUCT_WIDTH-1):(i*PRODUCT_WIDTH)];
         /* verilator lint_on WIDTH */
      end
      
         end // block: adder_gen
      endgenerate
   `endif
endmodule // row_col_product_adder

