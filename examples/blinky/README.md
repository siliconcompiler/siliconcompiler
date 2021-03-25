# Blinky ice40 Example

This example tests support for the ice40 FPGA flow by generating a blinky
bitstream for the [iCEBreaker](https://1bitsquared.com/products/icebreaker) dev
board.

## Prerequisites

To run this flow, the following tools need to be installed (along with Verilator
and Yosys):
- The IceStorm Tools
- NextPNR

See this page for installation instructions: http://www.clifford.at/icestorm/.

## How to run

To run the example, call `./examples/blinky/run.sh` on the command line. This
will produce an output bitstream at `build/export/job1/outputs/blinky.bit`.

The resulting bitstream can be loaded onto a connected dev board with the
command: `iceprog build/export/job1/outputs/blinky.bit`.
