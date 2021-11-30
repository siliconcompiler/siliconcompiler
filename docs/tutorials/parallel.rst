Parallel Programming
=====================

Parallel programming will likely never reach the productivity of single threaded Python code. Unfortunately, single threaded program performance has saturated, so if we want to make hardware compilation fast, we need to figure out how to make effective use of massively parallel hardware.

Working in our favor is the fact that: 1.) the data to compute ratio for the most compute intensive compilation steps is very high, and 2.) some of those steps can be easily partitioned into embarrassingly parallel problems.

In this tutorial, we show how the SiliconCompiler flowgraph execution model can be used to achieve an order of magnitude speedup on a single workstation compared to single threaded loops.
