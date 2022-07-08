#include "Vheartbeat.h"

int main() {
    Vheartbeat *tb = new Vheartbeat;

    // Reset
    tb->nreset = 1;
    tb->eval();
    tb->nreset = 0;
    tb->eval();
    tb->nreset = 1;

    // Tick 256 times
    for (int i=0; i<256; i++) {
        tb->clk = 0;
        tb->eval();
        tb->clk = 1;
        tb->eval();
    }

    if (tb->out == 1) {
        printf("SUCCESS\n");
    }  else {
        printf("FAIL\n");
    }

    delete tb;
}
