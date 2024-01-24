
module \$_tech_bram_ #(
    parameter PORT_A_WIDTH = 8,
    parameter PORT_A_ABITS = 13,
    parameter PORT_A_WR_EN_WIDTH = 1,
    parameter PORT_B_WIDTH = 8,
    parameter PORT_B_ABITS = 13,
    parameter PORT_B_WR_EN_WIDTH = 1

) (
    input PORT_A_CLK,
    input PORT_A_RD_EN,
    input [(PORT_A_WR_EN_WIDTH-1):0] PORT_A_WR_EN,
    input [(PORT_A_ABITS-1):0] PORT_A_ADDR,
    input [PORT_A_WIDTH-1:0] PORT_A_WR_DATA,
    output [PORT_A_WIDTH-1:0] PORT_A_RD_DATA,
    input PORT_B_CLK,
    input PORT_B_RD_EN,
    input [(PORT_B_WR_EN_WIDTH-1):0] PORT_B_WR_EN,
    input [(PORT_B_ABITS-1):0] PORT_B_ADDR,
    input [PORT_B_WIDTH-1:0] PORT_B_WR_DATA,
    output [PORT_B_WIDTH-1:0] PORT_B_RD_DATA
);

    generate

        sram _TECHMAP_REPLACE_ (
            .clk_a(PORT_A_CLK),
            .write_enable_a(PORT_A_WR_EN),
            .read_enable_a(PORT_A_RD_EN),
            .address_a(PORT_A_ADDR),
            .datain_a(PORT_A_WR_DATA),
            .dataout_a(PORT_A_RD_DATA),
            .clk_b(PORT_B_CLK),
            .write_enable_b(PORT_B_WR_EN),
            .read_enable_b(PORT_B_RD_EN),
            .address_b(PORT_B_ADDR),
            .datain_b(PORT_B_WR_DATA),
            .dataout_b(PORT_B_RD_DATA)
        );

    endgenerate


endmodule  // tech_bram
