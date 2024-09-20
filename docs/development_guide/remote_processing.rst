Remote processing
==================

The SiliconCompiler project supports a remote processing model that leverages the cloud to provide access to:

 #. Pre-configured tool installations.
 #. Warehouse scale elastic compute.
 #. NDA encumbered IPs, PDKs, and EDA tools.


.. note::

    Note that our public sever only supports open-source tools and PDKs.
    In the event that our servers are busy processing a large number of jobs, your job may get queued and experience delays in processing.

Even though our publicly-available servers only support open-source IP and tools, the remote API is capable of supporting any SiliconCompiler modules which the server operators wish to install.
If you are interested in creating a custom server implementation, we provide a minimal example development server which can be used as a starting point.
You can also find descriptions of the core remote API calls in the :ref:`remote API <Server API>` section.

See the :ref:`Quickstart guide` for instructions on running a simple example on our public servers.

Configuring a Different Remote Server
-------------------------------------

If you have a custom remote endpoint that you wish to use with SiliconCompiler, you can run the :ref:`sc-remote` command to set that up with your SiliconCompiler installation.

Public Server
^^^^^^^^^^^^^

If your remote server does not require authentication, you can simply pass its address in as a command-line argument:

``sc-remote -configure -server https://server.siliconcompiler.com``

If a previous credentials file already exists, you will be prompted to overwrite it.
Your credentials file will be placed in ``$HOME/.sc/``, if you want to back it up or delete it.
SiliconCompiler will default to using our public beta address if you have not configured anything, and it will remind you that your design is being uploaded to a public service for processing before starting each remote job.

.. _private-server:

Private Server
^^^^^^^^^^^^^^

If your custom remote server requires authentication, you can run ``sc-remote -configure`` with no additional arguments and fill in the address, username, and password fields that it prompts you for.

SiliconCompiler also supports private servers which require authentication to access.
If you have such a server to connect to, you will need a credentials text file located at ``$HOME/.sc/credentials`` on Linux or macOS, or at ``C:\\Users\\<USERNAME>\\.sc\\credentials`` on Windows.
The credentials file is a JSON formatted file containing information about the remote server address, username, and password.

.. code-block:: json

   {
      "address": "your-server",
      "username": "your-username",
      "password": "your-key"
   }

Use a text editor to create the credentials file.
Alternatively you can use :ref:`sc-remote` app to generate it from the command line.

.. code-block:: console

  (venv) sc-remote -configure
  Remote server address (leave blank to use default server): your-server
  Remote username (leave blank for no username): your-username
  Remote password (leave blank for no password): your-key
  Remote configuration saved to: $HOME/.sc/credentials

To verify that your credentials file and server is configured correctly, run the :ref:`sc-remote` command.

.. code-block:: console

  (venv) sc-remote

Once you've configured SiliconCompiler to run on your remote endpoint, see the :ref:`Quickstart guide` for instructions on running a simple example, along with expected outputs.

Troubleshooting
---------------

The jobs will be run in isolated environments with limited communication interfaces, however, so some network and filesystem calls may not work properly.

Any changes that you make to SiliconCompiler's built-in tool setup scripts on your local machine will not be reflected in jobs which are run on a remote server.
Likewise, any changes that you make to the built-in open-source PDKs and standard cell libraries will not be sent to the remote servers.
If you have suggestions for improving the open-source modules, :ref:`check out our contributing guide <Contributing modules>`.

Please report any issues that you encounter with the remote workflow on `the SiliconCompiler repository's issue page <https://github.com/siliconcompiler/siliconcompiler/issues>`_.
