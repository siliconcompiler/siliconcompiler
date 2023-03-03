Remote processing
==================

The SiliconCompiler project supports a remote processing model that leverages the cloud to provide access to:

 #. Pre-configured tool installations.
 #. Warehouse scale elastic compute.
 #. NDA encumbered IPs, PDKs, and EDA tools.

.. note::

    Note that our public beta currently only supports open-source tools and PDKs. You can access the public beta without a signup or login, and it is designed to delete your data after your jobs finish, but it is not intended to process proprietary or restricted intellectual property! Please `review our terms of service <https://www.siliconcompiler.com/terms-of-service>`_, and do not submit IP which you are not allowed to distribute.

    Currently, our public beta servers will only return a report containing a rendering and metrics for your build results. For the full GDS results, you can build and install the open-source tools and run the job on your local machine. We provide `setup scripts to help install these tools on Ubuntu systems <https://github.com/siliconcompiler/siliconcompiler/tree/main/setup>`.

Even though our publicly-available servers only support open-source IP and tools, the remote API is capable of supporting any SiliconCompiler modules which the server operators wish to install, and we provide a minimal example development server which can be used as a starting point for custom server implementations. You can also find descriptions of the core remote API calls in the :ref:`remote API <Server API>` section.

Quickstart Guide
----------------

To perform a minimal self-test using the remote flow, you can run the following commands::

    pip install siliconcompiler
    sc -target asic_demo -remote

The job should only take a few minutes to run if the servers aren't too busy, and once it completes, you should receive a PDF file containing a screenshot and metrics for the build results. The self-test design is a simple 8-bit counter, so your results should look something like this:

.. image:: ../_images/selftest_report.png

Configuring a Different Remote Server
-------------------------------------

You can run the :ref:`sc-configure` command to configure your SiliconCompiler installation with a custom remote endpoint, if you have one. If your remote server requires authentication, you can run the utility with no arguments and fill in the address, username, and password fields that it prompts you for. If your server does not require authentication, you can simply pass its address in as a command-line argument:

``sc-configure https://server.siliconcompiler.com``

If a previous credentials file already exists, you will be prompted to overwrite it. Your credentials file will be placed in ``$HOME/.sc/``, if you want to back it up or delete it.

SiliconCompiler will default to using our public beta address if you have not configured anything, and it will remind you that your design is being uploaded to a public service for processing before starting each remote job.

Building Custom Designs
-----------------------

For command line compilation, remote processing is turned on with the '-remote' option. Results from a remote compilation should be identical to results from a local compilation, although the server can choose to only return a subset of result files if the operator is concerned about bandwidth usage, distributing restricted IP, etc.

.. code-block:: bash

   echo "module flipflop (input clk, d, output reg out); \
   always @ (posedge clk) out <= d; endmodule" > flipflop.v
   sc flipflop.v -remote

Remote processing is also supported from the Python interface when the :keypath:`option, remote` parameter is set to 'True'. To get a feel for the Python interface, you can try running some of our `example designs <https://github.com/siliconcompiler/siliconcompiler/tree/main/examples/>`_ with this flag enabled::

  chip.set('option', 'remote', True)

Troubleshooting
---------------

Our public beta servers do not prune or pre-process Schema parameters, in order to make the remote processing environment as close to a local environment as possible. The jobs will be run in isolated environments with limited communication interfaces, however, so some network and filesystem calls may not work properly.

Any changes that you make to SiliconCompiler's built-in tool setup scripts on your local machine will not be reflected in jobs which are run on a remote server. Likewise, any changes that you make to the built-in open-source PDKs and standard cell libraries will not be sent to the remote servers. If you have suggestions for improving the open-source modules, `check out our contributing guidelines <https://github.com/siliconcompiler/siliconcompiler/blob/main/CONTRIBUTING.md>`_.

Please report any issues that you encounter with the remote workflow on `the SiliconCompiler repository's issue page <https://github.com/siliconcompiler/siliconcompiler/issues>`_.
