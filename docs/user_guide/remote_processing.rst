Remote processing
==================

The SiliconCompiler project supports a remote processing model that leverages the cloud to provide access to:

 #. Pre-configured tool installations.
 #. Warehouse scale elastic compute.
 #. NDA encumbered IPs, PDKs, and EDA tools.

Remote processing is enabled simply by setting the 'remote' parameter to True prior to calling the run() function. All other parameters entered are unaffected. ::

  chip.set('remote', True)

For command line compilation, remote processing is turned on with the '-remote' option.

.. code-block:: bash

   sc hello.v -remote

Remote server login credentials is handled through a special SiliconCompiler credentials text file, located at ~/.sc/credentials on Linux or macOS, or at C:\\Users\\USERNAME\\.sc\\credentials on Windows. The credentials file contains information about the remote server address, username, and password. An example credentials file is shown below.

.. code-block:: json

   {
   "address": "server.siliconcompiler.com",
   "username": "your-email",
   "password": "your-key"
   }

You can either created the credentials file manually, or leverage the SiliconCompiler sc-configure app to create generate it.

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

Once you have verified that your remote configuration works, you can try compiling the 'heartbeat' design from the `Quickstart Guide` with the remote switch.

.. code-block:: bash

   sc heartbeat.v -remote

A successful remote run should return results are identical to to a local run.
