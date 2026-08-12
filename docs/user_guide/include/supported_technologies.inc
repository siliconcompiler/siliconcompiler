.. Shared by the landing page and "What is SiliconCompiler?", so the table is
   written once. The including document supplies the heading.

============== =========================================================
Type           Supported
============== =========================================================
Languages      C, Verilog, SV, VHDL, Chisel, Migen/Amaranth, Bluespec, `MLIR <https://en.wikipedia.org/wiki/MLIR_(software)>`_
Simulation     Verilator, Icarus, GHDL, Xyce
Synthesis      Yosys, Vivado, Synopsys, Cadence
ASIC APR       OpenROAD, Synopsys, Cadence
FPGA APR       VPR, nextpnr, Vivado
Layout Viewer  Klayout, OpenROAD, Cadence, Synopsys
DRC/LVS        Klayout, Magic, Synopsys, Siemens
Open PDKs      sky130, ihp130, gf180, asap7, freepdk45, gt2n, interposer -- all shipped by `lambdapdk <https://github.com/siliconcompiler/lambdapdk>`_
Foundry PDKs   gf12lp, gf22fdx, intel16 -- require a foundry agreement; see :ref:`packaging an external library <dev_external_libraries>`
============== =========================================================
