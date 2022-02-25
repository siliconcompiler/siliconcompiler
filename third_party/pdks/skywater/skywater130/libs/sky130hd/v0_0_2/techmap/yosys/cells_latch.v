// Techmap file implementing Yosys generic latch using Skywater130 standard cell.
// Source: https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/10f030fccea33ec8084bb3974024d840cabc3782/flow/platforms/sky130hd/cells_latch_hd.v

module $_DLATCH_P_(input E, input D, output Q);
    sky130_fd_sc_hd__dlxtp_1 _TECHMAP_REPLACE_ (
        .D(D),
        .GATE(E),
        .Q(Q)
        );
endmodule

module $_DLATCH_N_(input E, input D, output Q);
    sky130_fd_sc_hd__dlxtn_1 _TECHMAP_REPLACE_ (
        .D(D),
        .GATE_N(E),
        .Q(Q)
        );
endmodule
