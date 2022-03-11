# Blinky ice40 Example

This example tests support for the ice40 FPGA flow by generating a blinky
bitstream for the [iCEBreaker](https://1bitsquared.com/products/icebreaker) dev
board.

## Prerequisites

To run this flow, the following tools need to be installed (along with Verilator
and Yosys):
- The IceStorm Tools
- NextPNR

See this page for installation instructions: http://bygone.clairexen.net/icestorm/.

## How to run

To run the example, run `python blinky.py`. This will produce an output
bitstream at `build/job0/export/0/outputs/blinky.bit`.

The resulting bitstream can be loaded onto a connected dev board with the
command: `iceprog build/job0/export/0/outputs/blinky.bit`.
