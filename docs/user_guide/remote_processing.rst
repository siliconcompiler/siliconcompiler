Remote processing
==================

The SiliconCompiler project supports a remote processing model that leverages the cloud to provide access to:

 #. Pre-configured tool installations.
 #. Warehouse scale elastic compute.
 #. NDA encumbered IPs, PDKs, and EDA tools.

Our publicly-available beta servers only support open-source IP and tools. The remote API is capable of supporting any SiliconCompiler modules which the server operators wish to install, however, and we provide a minimal example development server which can be used as a starting point for custom server implementations. You can also find descriptions of the core remote API calls in this documentation's Server API section.

You can run the ``sc-configure`` command to configure your SiliconCompiler installation with a remote endpoint. If your remote server requires authentication, you can run the utility with no arguments and fill in the address, username, and password fields that it prompts you for. If your server does not require authentication, you can simply pass the server address in as a command-line argument:

``sc-configure https://server.siliconcompiler.com``

If a previous credentials file already exists, you will be prompted to overwrite it. Your credentials file will be placed in ``$HOME/.sc/``, if you want to back it up or delete it.

For command line compilation, remote processing is turned on with the '-remote' option. Results from a remote compilation should be identical to results from a local compilation, although the server can choose to only return a subset of result files if the operator is concerned about bandwidth usage, distributing restricted IP, etc.

.. code-block:: bash

   echo "module flipflop (input clk, d, output reg out); \
   always @ (posedge clk) out <= d; endmodule" > flipflop.v
   sc flipflop.v -remote

Remote processing is also supported from the Python interface when the ('option', 'remote') parameter is set to 'True'. ::

  chip.set('option', 'remote', True)

Our public beta servers do not prune or pre-process Schema parameters, in order to make the remote processing environment as close to a local environment as possible. The jobs will be run in isolated environments with limited communication interfaces, however, so they jobs may not be able to perform network calls or meaningful filesystem access when they are run on our cloud beta servers.

Any changes that you make to SiliconCompiler's built-in tool setup scripts on your local machine will not be reflected in jobs which are run on a remote server. Likewise, any changes that you make to the built-in open-source PDKs and standard cell libraries will not be sent to the remote servers.

Please report any issues that you encounter with the remote workflow on `the SiliconCompiler repository's issue page <https://github.com/siliconcompiler/siliconcompiler/issues>`_.
