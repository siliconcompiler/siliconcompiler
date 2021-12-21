interface FibOne_IFC;
   method Action nextFib;
   method ActionValue #(int)  getFib;
endinterface

(* synthesize *)
module mkFibOne(FibOne_IFC);
   // register containing the current Fibonacci value
   Reg#(int) this_fib <- mkReg (0);
   Reg#(int) next_fib <- mkReg (1);

   method Action nextFib;
      this_fib <= next_fib;
      next_fib <= this_fib + next_fib;  // note that this uses stale this_fib
  endmethod

  method ActionValue#(int) getFib;
    return this_fib;
  endmethod

endmodule: mkFibOne

