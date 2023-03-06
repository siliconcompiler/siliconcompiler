Remote processing
==================

The SiliconCompiler project supports a remote processing model that leverages the cloud to provide access to:

 #. Pre-configured tool installations.
 #. Warehouse scale elastic compute.
 #. NDA encumbered IPs, PDKs, and EDA tools.

.. note::

    Note that our public beta currently only supports open-source tools and PDKs. You can access the public beta without a signup or login, and it is designed to delete your data after your jobs finish, but it is not intended to process proprietary or restricted intellectual property! Please `review our terms of service <https://www.siliconcompiler.com/terms-of-service>`_, and do not submit IP which you are not allowed to distribute.

    Currently, our public beta servers will only return a report containing a rendering and metrics for your build results. For the full GDS results, you can build and install the open-source tools and run the job on your local machine. See :ref:`local run` for more instructions.

    In the event that our servers are busy processing a large number of jobs, your job may get queued and experience delays in processing. We appreciate your patience during this public beta period.

Even though our publicly-available servers only support open-source IP and tools, the remote API is capable of supporting any SiliconCompiler modules which the server operators wish to install. If you are interested in creating a custom server implementation, we provide a minimal example development server which can be used as a starting point. You can also find descriptions of the core remote API calls in the :ref:`remote API <Server API>` section.

See the :ref:`Quickstart guide` for instructions on running a simple example on our public servers.

Configuring a Different Remote Server
-------------------------------------

If you have a custom remote endpoint that you wish to use with SiliconCompiler, you can run the :ref:`sc-configure` command to set that up with your SiliconCompiler installation.

Public Server
^^^^^^^^^^^^^

If your remote server does not require authentication, you can simply pass its address in as a command-line argument:

``sc-configure https://server.siliconcompiler.com``

If a previous credentials file already exists, you will be prompted to overwrite it. Your credentials file will be placed in ``$HOME/.sc/``, if you want to back it up or delete it. SiliconCompiler will default to using our public beta address if you have not configured anything, and it will remind you that your design is being uploaded to a public service for processing before starting each remote job.

.. _private-server:

Private Server
^^^^^^^^^^^^^^

If your custom remote server requires authentication, you can run ``sc-configure`` with no arguments and fill in the address, username, and password fields that it prompts you for.

SiliconCompiler also supports private servers which require authentication to access. If you have such a server to connect to, you will need a credentials text file located at ``~/.sc/credentials`` on Linux or macOS, or at ``C:\\Users\\USERNAME\\.sc\\credentials`` on Windows. The credentials file is a JSON formatted file containing information about the remote server address, username, and password.

.. code-block:: json

   {
   "address": "your-server",
   "username": "your-username",
   "password": "your-key"
   }

Use a text editor to create the credentials file. Alternatively you can use :ref:`sc-configure` app to generate it from the command line.

.. code-block:: console

  (venv) sc-configure
  Remote server address: your-server
  Remote username: your-username
  Remote password: your-key
  Remote configuration saved to: /home/<USER>/.sc/credentials

To verify that your credentials file and server is configured correctly, run the :ref:`sc-ping` command.

.. code-block:: console

  (venv) sc-ping
  User myname validated successfully!
  Remaining compute time: 1440.00 minutes
  Remaining results bandwidth: 5242880 KiB

Troubleshooting
---------------

Our public beta servers do not prune or pre-process Schema parameters, in order to make the remote processing environment as close to a local environment as possible. The jobs will be run in isolated environments with limited communication interfaces, however, so some network and filesystem calls may not work properly.

Any changes that you make to SiliconCompiler's built-in tool setup scripts on your local machine will not be reflected in jobs which are run on a remote server. Likewise, any changes that you make to the built-in open-source PDKs and standard cell libraries will not be sent to the remote servers. If you have suggestions for improving the open-source modules, `check out our contributing guidelines <https://github.com/siliconcompiler/siliconcompiler/blob/main/CONTRIBUTING.md>`_.

Please report any issues that you encounter with the remote workflow on `the SiliconCompiler repository's issue page <https://github.com/siliconcompiler/siliconcompiler/issues>`_.
