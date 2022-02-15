// Techmap file implementing Yosys generic latch using ASAP7 standard cell.
// Source: https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/aaef0609d0e1cc6ab000a3538f25005b6bf01244/flow/platforms/asap7/yoSys/cells_latch.v 

module $_DLATCH_P_(input E, input D, output Q);
    DHLx1_ASAP7_75t_R _TECHMAP_REPLACE_ (
        .D(D),
        .CLK(E),
        .Q(Q)
        );
endmodule

module $_DLATCH_N_(input E, input D, output Q);
    DLLx1_ASAP7_75t_R _TECHMAP_REPLACE_ (
        .D(D),
        .CLK(E),
        .Q(Q)
        );
endmodule
