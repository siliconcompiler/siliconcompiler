package DotProduct;

import Cntrs::*;
import FIFOF::*;
import Vector::*;
import GetPut::*;
import ClientServer::*;

import Utils::*;

typedef Server #(Tuple2 #(t, t), t) DotProduct_IFC #(numeric type n_t, type t);

module mkDotProduct (DotProduct_IFC #(n_t, t)) provisos (Bits #(t, wt), Ord #(t), Arith #(t), Eq #(t));

    Integer verbosity = 1;

    FIFOF #(Tuple2 #(t, t)) fifo_in <- mkFIFOF ();
    FIFOF #(t) fifo_out <- mkFIFOF ();

    Count #(Int #(8)) cntr <- mkCount (0);

    Reg #(Maybe #(t)) rg_temp <- mkReg (tagged Invalid);

    Integer j_max = valueOf (n_t);

    rule rl_compute (cntr < fromInteger (j_max));
        match { .a, .b } = fifo_in.first (); fifo_in.deq ();
        if (rg_temp matches tagged Valid .c)
            rg_temp <= tagged Valid (c + a * b);
        else
            rg_temp <= tagged Valid (a * b);
        cntr.incr (1);
        if (verbosity == 1)
            $display ("%0d: compute", cur_cycle);
    endrule: rl_compute

    rule rl_done (cntr == fromInteger (j_max) &&& rg_temp matches tagged Valid .c);
        fifo_out.enq (c);
        cntr.update (0);
        if (verbosity == 1)
            $display ("%0d: done", cur_cycle);
    endrule: rl_done

    return toGPServer (fifo_in, fifo_out);

endmodule: mkDotProduct

endpackage: DotProduct
