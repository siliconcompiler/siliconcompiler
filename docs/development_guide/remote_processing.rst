.. _remote_processing:

Guide to Remote Compilation
===========================

SiliconCompiler supports a remote compilation model, allowing you to leverage cloud resources for access to pre-configured tool installations, elastic compute, and potentially NDA-protected PDKs or IPs on private servers.

.. note::

    Our public server only supports open-source tools and PDKs.
    During periods of high traffic, your job may be queued, which could result in processing delays.
    When you run a remote job, SiliconCompiler will remind you that your design is being uploaded to a public service.

.. _private-server:

Step 1: Configure Your Remote Server
------------------------------------

All remote server settings are managed through a ``credentials`` file located in your home directory (``$HOME/.sc/`` on Linux/macOS or ``C:\Users\<USERNAME>\.sc\`` on Windows).
The file holds JSON, but has no file extension.

While you can create this file manually, the recommended method is to use the interactive ``sc-remote`` command.

Method 1: Interactive Setup (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Open your terminal and run the following command:

.. code-block:: bash

  sc-remote -configure

You will be prompted to enter your server's details. Follow the prompts based on the type of server you are connecting to:

* **Private/Authenticated Server:** Provide the server address, your username, and your password/API key when prompted.

.. code-block:: bash

  Remote server address: https://your-secure-server.com
  Remote username: your-username
  Remote password: your-key
  Remote configuration saved to: /home/user/.sc/credentials

* **Public/Unauthenticated Server:** Enter the server address and press Enter to leave the username and password fields blank.

.. code-block:: bash

  Remote server address: https://server.siliconcompiler.com
  Remote username:
  Remote password:
  Remote configuration saved to: /home/user/.sc/credentials

Method 2: Manual Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you prefer, you can create the ``credentials`` file manually in the appropriate directory.
The file must contain the following JSON structure:

.. code-block::

  {
    "address": "your-server-address",
    "username": "your-username",
    "password": "your-password-or-key"
  }

For a public server, simply leave the username and password fields as empty strings ("").

Step 2: Verify the Connection
-----------------------------

After configuration, run ``sc-remote`` without any arguments to test the connection to your server.

.. code-block:: bash

  sc-remote

A successful connection will typically display a status message or an empty list of your remote jobs, confirming that your configuration and credentials are correct.

Step 3: Run a Remote Job
------------------------

To send a compilation job to the configured remote server, set the :keypath:`option,remote` parameter in your build script:

.. code-block:: python

  project.option.set_remote(True)

Build scripts that expose a command line through :meth:`.CommandLineSchema.create_cmdline` -- including the bundled demos -- also accept a ``-remote`` flag:

.. code-block:: bash

  python -m siliconcompiler.demos.asic_demo -remote

The job will be packaged, sent to the remote server for processing, and the results will be streamed back to your local machine.
Results are downloaded for each flowgraph node as it completes, so a finished remote job leaves the same build directory contents behind as a local run.

Troubleshooting
---------------

* **Local Changes Not Reflected:** Any modifications you make to local, built-in tool scripts, PDKs, or libraries will not be used in a remote job. The remote server uses its own pre-configured environment.
* **Network and Filesystem Issues:** Jobs run in isolated environments on the server. Code that relies on specific network or local filesystem calls may not work as expected.
* **Reporting Issues:** If you encounter problems with the remote workflow, please open an issue on the `SiliconCompiler repository's issue page <https://github.com/siliconcompiler/siliconcompiler/issues>`_.

For Developers: Custom Servers
------------------------------

If you are interested in deploying your own custom server, we provide a minimal example development server that can be used as a starting point: :ref:`sc-server <app-sc-server>` using the :ref:`remote API <server_api>`.
