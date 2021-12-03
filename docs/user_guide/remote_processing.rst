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

For security reasons, only a subset of the full Schema parameters is currently supported. Values for disallowed keypaths will be silently dropped by the server. In addition, note that the target() function will be re-run on the server, to ensure targets are set up with their default configurations. The following table documents the list of supported remote parameters and any associated restrictions.

.. list-table::
   :widths: 10 10
   :header-rows: 1

   * - Keypath
     - Restrictions

   * - ``design``
     - Must only contain alphanumeric characters or underscores
   * - ``jobname``
     - Must only contain alphanumeric characters or underscores
   * - ``dir``
     - Must only contain alphanumeric characters or underscores
   * - ``constraint``
     - Only allowed for fpgaflow
   * - ``target``
     - Must be one of ``asicflow_freepdk45``, ``asicflow_skywater130``, or ``fpgaflow_ice40up5k-sg48``
   * - ``library, ...``
     - Allowed if key isn't the name of a built-in PDK standard cell library
   * - ``source``
     - None
   * - ``netlist``
     - None
   * - ``testbench``
     - None
   * - ``clock, ...``
     - None
   * - ``supply, ...``
     - None
   * - ``param, ...``
     - None
   * - ``define``
     - None
   * - ``ydir``
     - None
   * - ``idir``
     - None
   * - ``vlib``
     - None
   * - ``libext``
     - None
   * - ``cmdfile``
     - None
   * - ``vcd``
     - None
   * - ``saif``
     - None
   * - ``activityfactor``
     - None
   * - ``spef``
     - None
   * - ``sdf``
     - None
   * - ``exclude``
     - None
   * - ``asic, ...``
     - None
   * - ``metric, ...``
     - None
   * - ``fpga, ...``
     - None
   * - ``flowarg, ...``
     - None
   * - ``techarg, ...``
     - None
   * - ``clean``
     - None
   * - ``loglevel``
     - None
   * - ``vercheck``
     - None
   * - ``checkonly``
     - None
