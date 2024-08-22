// Verilator testbench for heartbeat.v

#include <iostream>

#include "verilated.h"
#include "Vheartbeat.h"

#if VM_TRACE
#include <verilated_vcd_c.h>
#endif

int main(int argc, char **argv, char **env) {
    Verilated::commandArgs(argc, argv);

    Vheartbeat *dut = new Vheartbeat;

#if VM_TRACE
#ifdef SILICONCOMPILER_TRACE_FILE
    // If verilator was invoked with --trace argument
    VerilatedVcdC* tfp = NULL;
    Verilated::traceEverOn(true);  // Verilator must compute traced signals
    VL_PRINTF("Enabling waves...\n");
    tfp = new VerilatedVcdC;
    dut->trace(tfp, 99);  // Trace 99 levels of hierarchy
    Verilated::mkdir(SILICONCOMPILER_TRACE_DIR);
    tfp->open(SILICONCOMPILER_TRACE_FILE);  // Open the dump file
#endif
#endif

    int heartbeats = 0;
    int sim_time = 0;

    dut->clk = 0;
    dut->nreset = 1;
    dut->eval();

    while (!Verilated::gotFinish()) {
        if (sim_time % 10 == 0) {
            if ((int)dut->out == 1) {
                heartbeats++;
            }

            std::cout << "t=" << sim_time;
            std::cout << " clk=" << (int)dut->clk;
            std::cout << " nreset=" << (int)dut->nreset;
            std::cout << " out=" << (int)dut->out;
            std::cout << " heartbeats=" << (int)heartbeats;
            std::cout << std::endl;
        }
        if (sim_time >= 1 && sim_time <= 10) {
            // hold reset flow for 9 ns
            dut->nreset = 0;
        }
        else {
            dut->nreset = 1;
        }

        if (sim_time % 5 == 0) {
            dut->clk ^= 1;
        }

        if (heartbeats >= 10) {
            break;
        }

        dut->eval();

#if VM_TRACE
        // Dump trace data for this cycle
        if (tfp) tfp->dump(sim_time);
#endif

        sim_time ++;
    }
    dut->final();

#if VM_TRACE
    // Close trace if opened
    if (tfp) {
        tfp->close();
        tfp = NULL;
    }
#endif

    delete dut;
    exit(0);
}
