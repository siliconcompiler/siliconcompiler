module parity 
   (
    input      clk,// clock
    input[7:0]  data,    
    output reg out //parity result
    );

    always @(posedge clk)
    begin
      out <= ^ data;
    end

   
endmodule
