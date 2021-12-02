Remote processing
==================

The SiliconCompiler project supports a remote processing model that leverages the cloud to provide access to:

 #. Pre-configured tool installations.
 #. Warehouse scale elastic compute.
 #. NDA encumbered IPs, PDKs, and EDA tools.

For command line compilation, remote processing is turned on with the '-remote' option. Results from a remote compilation should be identical to results from a local compilation.

Before running a remote siliconcompiler job, you must sign up for the siliconcompiler beta program and enter your account credentials with the `sc-configure` command:

.. code-block:: console

  (siliconcompiler) $ sc-configure
  Remote server address: server.siliconcompiler.com
  Remote username: "myname"
  Remote password: "mypass"
  Configuration saved.

To verify that your credentials file and server is configured correctly, run the `sc-ping` command. This will also print your account's usage limits during our initial beta period.

.. code-block:: console

  (siliconcompiler) $ sc-ping
  User myname validated successfully!
    Remaining compute time: 1440.00 minutes
    Remaining results bandwidth: 5242880 KiB

Once you have verified that your remote configuration works, you can try compiling a simple design such as the following flip-flop:

.. code-block:: bash

   echo "module flipflop (input clk, d, output reg out); \
   always @ (posedge clk) out <= d; endmodule"> flipflop.v
   sc flipflop.v -remote

Remote processing is also supported from the Python interface when the 'remote' parameter is set to 'True'. ::

  chip.set('remote', True)

