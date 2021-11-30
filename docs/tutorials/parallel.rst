Parallel Programming
=====================

Single threaded program performance has saturated, so if we want to make hardware compilation fast, we need to figure out how to make effective use of massively parallel hardware.

Working in our favor is the fact that 1.) the data to compute ratio for the most compute intensive compilation steps is very high, and 2.) some of those steps can be easily partitioned into embarrassingly parallel problems.

In this tutorial, we show how the SiliconCompiler flowgraph execution model can be used to achieve an order of magnitude speedup on a single workstation compared to single threaded loops. Speedups within cloud execution is even higher.

The tutorail runs the same design three different approaches:

1.) Completely serial (two nested for loops N * M).

2.) One blocking for loop (N) to launch runs with parallel index launches for synthesis, placement, cts, and routing steps.

3.) One asynchronous for loop leveraging the Python multiprocessing package to launchc N independent flows.

Run the program on your machine to see what kind of speedup you get! Here is `example source code <https://github.com/siliconcompiler/siliconcompiler/blob/main/docs/tutorials/examples/parallel.py>`_

.. literalinclude:: examples/parallel.py
