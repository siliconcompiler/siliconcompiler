package DotProduct_nt_Int32;

import DotProduct::*;

(* synthesize *)
module mkDotProduct_nt_Int32 (DotProduct_IFC #(16, Int #(32)));

    DotProduct_IFC #(16, Int #(32)) dut <- mkDotProduct ();
    return dut;

endmodule: mkDotProduct_nt_Int32


endpackage: DotProduct_nt_Int32
