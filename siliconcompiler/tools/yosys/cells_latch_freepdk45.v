// Techmap file implementing Yosys generic latch using FreePDK45 standard cell.
// Source: https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/10f030fccea33ec8084bb3974024d840cabc3782/flow/platforms/nangate45/cells_latch.v

module $_DLATCH_P_(input E, input D, output Q);
    DLH_X1 _TECHMAP_REPLACE_ (
        .D(D),
        .G(E),
        .Q(Q)
        );
endmodule

module $_DLATCH_N_(input E, input D, output Q);
    DLL_X1 _TECHMAP_REPLACE_ (
        .D(D),
        .GN(E),
        .Q(Q)
        );
endmodule