Remote processing
==================

The SiliconCompiler project supports a remote processing model that leverages the cloud to provide access to:

 #. Pre-configured tool installations.
 #. Warehouse scale elastic compute.
 #. NDA encumbered IPs, PDKs, and EDA tools.

For command line compilation, remote processing is turned on with the '-remote' option. Results from a remote compilation should be identical to results from a local compilation.

.. code-block:: bash

   echo "module flipflop (input clk, d, output reg out); \
   always @ (posedge clk) out <= d; endmodule"> flipflop.v
   sc flipflop.v -remote

Remote processing is also supported from the Python interface when the 'remote' parameter is set to 'True'. ::

  chip.set('remote', True)
