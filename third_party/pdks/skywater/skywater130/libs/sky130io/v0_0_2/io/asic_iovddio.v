module asic_iovddio #(
    parameter DIR = "NO",
    parameter TYPE = "SOFT",
    parameter TECH_RING_WIDTH = 8
) (
    inout vdd,
    inout vss,
    inout vddio,
    inout vssio,
    inout poc,

    inout [TECH_RING_WIDTH-1:0] ring
);

sky130_ef_io__vddio_hvc_pad iovddio (
    .VDDIO(vddio),
    .VDDIO_Q(ring[0]),
    .VDDA(ring[6]),
    .VCCD(vdd),
    .VSWITCH(ring[1]),
    .VCCHIB(ring[2]),
    .VSSA(ring[7]),
    .VSSD(vss),
    .VSSIO_Q(ring[3]),
    .VSSIO(vssio),

    .AMUXBUS_A(ring[4]),
    .AMUXBUS_B(ring[5])
);

endmodule