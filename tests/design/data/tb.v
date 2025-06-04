module tb();

   localparam PERIOD = 2;
   localparam TIMEOUT = PERIOD * 64;

   reg        nreset;
   reg        clk;

   // control block
   initial
     begin
        $dumpfile("dump.vcd");
        $dumpvars(0, tb);
        #(TIMEOUT)
        $finish;
     end

   // test program
   initial
     begin
        #(1)
        nreset = 'b0;
        clk = 'b0;
        #(1)
        nreset = 'b1;
     end

   // clk
   always
     #(PERIOD/2) clk = ~clk;

   heartbeat #(.N(8))
   heartbeat(/*AUTOINST*/
             // Outputs
             .out             (out),
             // Inputs
             .clk             (clk),
             .nreset          (nreset));

endmodule
