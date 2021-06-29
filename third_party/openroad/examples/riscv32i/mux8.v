
module mux8
#(
  parameter WIDTH = 8
)
(
  input  wire [WIDTH-1:0] d0,
  input  wire [WIDTH-1:0] d1,
  input  wire [WIDTH-1:0] d2,
  input  wire [WIDTH-1:0] d3,
  input  wire [WIDTH-1:0] d4,
  input  wire [WIDTH-1:0] d5,
  input  wire [WIDTH-1:0] d6,
  input  wire [WIDTH-1:0] d7,
  input  wire [2:0]       s, 
  output wire [WIDTH-1:0] y
);

wire y0;
wire y1;
   
assign y0 = s[1] ? (s[0] ? d3 : d2) : (s[0] ? d1 : d0);
assign y1 = s[1] ? (s[0] ? d7 : d6) : (s[0] ? d5 : d4);
assign y  = s[2] ? y1 : y0;

endmodule // mux4

