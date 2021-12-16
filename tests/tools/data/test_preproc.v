module test_preproc();
`define MAKE_MEM_PATH(filename) `"`MEM_ROOT/filename`"
    initial begin
    $display(`MAKE_MEM_PATH(rom.mem));
    end
endmodule
