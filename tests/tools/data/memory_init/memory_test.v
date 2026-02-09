module memory_test (
    input clk,
    input [3:0] addr,
    output reg [7:0] data_hex,
    output reg [7:0] data_mem
);

    reg [7:0] rom_hex [16];
    reg [7:0] rom_mem [16];

    initial begin
        $readmemh("init.hex", rom_hex);
        $readmemh("init.mem", rom_mem);
    end

    always @(posedge clk) begin
        data_hex <= rom_hex[addr];
        data_mem <= rom_mem[addr];
    end

endmodule
