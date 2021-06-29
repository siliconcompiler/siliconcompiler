module TCMP(clk, rst, a, s);
    input clk, rst;
    input a;
    output reg s;

    reg z;

    always @(posedge clk  or posedge rst) begin
        if (rst) begin
            //Reset logic goes here.
            s <= 1'b0;
            z <= 1'b0;
        end
        else begin
            //Sequential logic goes here.
            z <= a | z;
            s <= a ^ z;
        end
    end
endmodule

module CSADD(clk, rst, x, y, sum);
    input clk, rst;
    input x, y;
    output reg sum;

    reg sc;

    // Half Adders logic
    wire hsum1, hco1;
    assign hsum1 = y ^ sc;
    assign hco1 = y & sc;

    wire hsum2, hco2;
    assign hsum2 = x ^ hsum1;
    assign hco2 = x & hsum1;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            //Reset logic goes here.
            sum <= 1'b0;
            sc <= 1'b0;
        end
        else begin
            //Sequential logic goes here.
            sum <= hsum2;
            sc <= hco1 ^ hco2;
        end
    end
endmodule

module SPM(clk, rst, x, y, p);
    parameter size = 32;
    input clk, rst;
    input y;
    input[size-1:0] x;
    output p;

    wire[size-1:1] pp;
    wire[size-1:0] xy;

    genvar i;

    CSADD csa0 (.clk(clk), .rst(rst), .x(x[0]&y), .y(pp[1]), .sum(p));
    generate for(i=1; i<size-1; i=i+1) begin
        CSADD csa (.clk(clk), .rst(rst), .x(x[i]&y), .y(pp[i+1]), .sum(pp[i]));
    end endgenerate
    TCMP tcmp (.clk(clk), .rst(rst), .a(x[size-1]&y), .s(pp[size-1]));

endmodule

module AHB_SPM #(parameter SIZE=32) (
    input  wire         HCLK,      
    input  wire         HRESETn,   
    input  wire         HSEL,      
    input  wire         HREADY,    
    input  wire [1:0]   HTRANS,    
    input  wire [2:0]   HSIZE,     
    input  wire         HWRITE,    
    input  wire [31:0]  HADDR,     
    input  wire [31:0]  HWDATA,    
    output wire         HREADYOUT, 
    output wire [1:0]   HRESP,
    output wire [31:0]  HRDATA
);

    localparam  X_OFF = 0, Y_OFF = 4, P1_OFF = 8, P2_OFF = 12;
    localparam  S0=0, S1=1, S2=2, S3=3;

    reg [7:0]   AHB_ADDR;    
    wire        ahb_access   = HTRANS[1] & HSEL & HREADY;
    wire        _ahb_write_    = ahb_access &  HWRITE;
    wire        ahb_read     = ahb_access & (~HWRITE);
    reg         AHB_WRITE;
    reg         AHB_READ;

    wire        p;
    reg [31:0]  X, Y, P0, P1; 
    reg [7:0]   CNT, ncnt;

    reg [3:0]   STATE, nstate;

    always @(posedge HCLK or negedge HRESETn)
    if(~HRESETn) begin
        AHB_WRITE   <=  1'b0;
        AHB_READ    <=  1'b0;
        AHB_ADDR    <=  8'b0;
    end
    else begin
        AHB_WRITE   <=  _ahb_write_;
        AHB_READ    <=  ahb_read;
        AHB_ADDR    <=  HADDR[7:0];  
    end

    always @(posedge HCLK or negedge HRESETn)
        if(~HRESETn)
            X  <= 32'b0;
        else if(AHB_WRITE && (AHB_ADDR == X_OFF))
            X <= HWDATA;

    always @(posedge HCLK or negedge HRESETn)
        if(~HRESETn)
            Y  <= 32'b0;
        else if(AHB_WRITE && (AHB_ADDR == Y_OFF))
            Y <= HWDATA;
        else if(STATE==S1) Y <= Y >> 1;

    always @(posedge HCLK or negedge HRESETn)
        if(~HRESETn)
            P0  <= 32'b0;
        else if(STATE==S1)
            P0 <= {p,P0[31:1]};

    always @(posedge HCLK or negedge HRESETn)
        if(~HRESETn)
            STATE  <= S0;
        else 
            STATE <= nstate;

    always @*
        case(STATE)
            S0: if(AHB_WRITE && (AHB_ADDR == Y_OFF)) nstate=S1; else nstate=S0;
            S1: if(CNT==31) nstate=S0; else nstate=S1;
        endcase
    
    always @(posedge HCLK or negedge HRESETn)
        if(~HRESETn)
            CNT  <= 8'd0;
        else 
            CNT <= ncnt;

    always @* begin
        ncnt = 0;
        if(CNT==31) ncnt <= 0;
        else if(STATE==S1) ncnt=CNT+1;
    end

    SPM spm(
      .clk(~HCLK),
      .rst(~HRESETn),
      .x(X),
      .y(Y[0]),
      .p(p)
    );

    assign HREADYOUT = (STATE == S0);

    assign HRDATA = P0;

endmodule
/*
module SPM_EXT(clk, rst, X, Y, P, start, done);
    parameter size = 32;
    input clk, rst;
    input [size-1:0] X, Y;
    output reg [size-1:0] P;
    output done;
    input start;

    reg [31:0] Y_reg;
    wire p, y;
    assign y=Y_reg[0];
    reg [1:0] done_state, done_state_next;

    assign done = done_state[1];
    SPM spm(
      .clk(clk),
      .rst(rst),
      .x(X),
      .y(y),
      .p(p));

    reg [7:0] count;

    always @(posedge clk or posedge rst)
      if(rst) count <= 7'd0;
      else if(start) count <= count + 1'd1;
      else if(done) count <= 7'd0;

    always@(posedge clk)
      if(count==0 && start==1) P<= 64'b0;
      else if(!done) P <= {p, P[31:1]};

    always@(posedge clk or posedge rst)
      if(rst) Y_reg <= 0;
      else if(count==0 && start==1) Y_reg<= Y;
      else if(!done) Y_reg <= (Y_reg>>1);

    always @(posedge clk or posedge rst)
      if(rst) done_state <= 2'd00;
      else done_state <= done_state_next;

    always @* begin
        done_state_next = done_state;
      case (done_state)
        2'b00: if(start) done_state_next = 2'b01;
        2'b01: if(count==8'd33) done_state_next = 2'b10;
        2'b10: done_state_next = 2'b11;
        2'b11: done_state_next = 2'b00;
        default: done_state_next = done_state;
      endcase
    end
      //else if(count==7'd33) done <= 1;
      //else if(start) done <= 0;

endmodule
*/
/*
module spm_tb;
reg clk, rst, start;
wire p;


wire done;

initial begin
  rst = 0;
  clk = 0;

  start = 0;
  #100;
  rst = 1;
  #500;
  rst = 0;
  #1000;
  @(posedge clk);
  start = 1;
  @(posedge done);
  start = 0;
end

always #10 clk = ~clk;

initial begin
  $dumpfile("spm.vcd");
  $dumpvars(0);
  #100_000 ;
  $display("Timeout -- Exiting");
  $finish;
end

wire [31:0] P;

SPM_EXT spm_dut(.clk(clk), .rst(rst), .X(-15), .Y(20), .P(P), .start(start), .done(done));

endmodule
*/
