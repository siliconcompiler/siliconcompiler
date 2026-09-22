.. _remote_processing:

Guide to Remote Compilation
===========================

SiliconCompiler supports a remote compilation model, allowing you to leverage cloud resources for access to pre-configured tool installations, elastic compute, and potentially NDA-protected :term:`PDKs <PDK>` or :term:`IPs <IP>`.

Remote execution runs against a server you or your organization operates.
SiliconCompiler does not host a server for you -- see
:ref:`For Developers: Custom Servers <custom-servers>` for how to stand one up.

.. _private-server:

Step 1: Configure Your Remote Server
------------------------------------

Run ``sc-remote -configure`` and give it the server's address:

.. code-block:: bash

  sc-remote -configure -server https://your-server.example.com

There is no username and no password. On first use the client generates a
**key pair** for this machine, keeps the private half locally, and proves it
holds that key on every request. The server records the public half the first
time it sees you, and thereafter only something holding that key can act as
you.

The command reaches the server, logs in, and reports what it found:

.. code-block:: text

  Configured https://your-server.example.com/v1
  This machine's key: 6VnuUMHokGfjlyAQjS56zCQTPEIb1PesAsRNubDmHK4
  You are 01a0cac7-2bb6-75ae-bdfd-59ff615f6dc1 on this server
  Saved to /home/user/.sc/credentials

There is no default server, so the address is required: leaving it out is an
error rather than a redirect somewhere you did not choose.

What is written, and where
^^^^^^^^^^^^^^^^^^^^^^^^^^

Two files, both in ``$HOME/.sc/`` (``C:\Users\<USERNAME>\.sc\`` on Windows),
both readable only by you:

``credentials``
  JSON: the server address, your session, and the upload whitelist.

``credentials.key``
  Your machine's private key. **This is the credential.**

.. warning::

   ``credentials.key`` identifies this machine to the server. Treat it the way
   you would an SSH private key.

   * Both files are created readable only by you, and re-running
     ``sc-remote -configure`` tightens them if something widened them. If you
     copy them yourself, restrict them too -- ``chmod 600`` on Linux and macOS;
     on Windows, remove the inherited permissions through the file's
     *Properties > Security* dialog or ``icacls``.
   * **Never commit either file**, and do not paste their contents into an
     issue, a pull request or a build log.
   * Do not copy the key between machines. Each machine generates its own, and
     a server shows you the list: ``sc-remote -configure -list``.

.. note::

   A server that does not verify who you are -- which the bundled
   ``sc-server`` does not -- separates your jobs from other users' but is not a
   security boundary. ``sc-remote -configure`` says so when it connects.

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

Submitting is four calls and the client makes all of them: it creates the job,
asks where to put the bytes, uploads the archive, and then tells the server the
archive is complete and what its checksum is. The job can be refused at the
first of those -- before a gigabyte has moved -- which is why the create carries
what the client already knows about the run.

While it runs, the client polls and reports each node as the server moves it:

.. code-block:: text

  Your job's reference ID is: 01a0cb02-c9bd-743c-b1a2-a0bddd938bc7
  Uploading 22699 bytes
  Job submitted
  Job is still running (running): 1/2 nodes
    Completed (1): stepone/0
    Running (1): steptwo/0
  Remote job completed

The server sets the polling interval per response, so a client never guesses one.

.. note::

   **Retrieving what the run produced is not available yet.** The job runs to
   completion on the server and its build directory there is complete, but the
   endpoints that fetch the results back have not landed on this branch. A
   finished run says so rather than leaving an empty build directory
   unexplained.

Watching, cancelling and reconnecting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A remote run writes ``sc_remote.pkg.json`` into its job directory **before it
uploads anything**, and every command that acts on a job takes that path:

.. code-block:: bash

  sc-remote -cfg build/<design>/<job>/sc_remote.pkg.json              # status
  sc-remote -cfg build/<design>/<job>/sc_remote.pkg.json -reconnect   # re-enter the wait
  sc-remote -cfg build/<design>/<job>/sc_remote.pkg.json -cancel
  sc-remote -cfg build/<design>/<job>/sc_remote.pkg.json -delete

Interrupting a run with ``Ctrl-C`` disconnects from it without stopping it, and
prints the first two of those commands with the path filled in. The job keeps
running on the server.

``-cancel`` and ``-delete`` are both safe to repeat: cancelling a job that has
already stopped, or deleting one that is already deleted, is the same answer
again. A job cannot be deleted while it is still running -- cancel it first.

Troubleshooting
---------------

* **Local Changes Not Reflected:** Any modifications you make to local, built-in tool scripts, PDKs, or libraries will not be used in a remote job. The remote server uses its own pre-configured environment.
* **Network and Filesystem Issues:** Jobs run in isolated environments on the server. Code that relies on specific network or local filesystem calls may not work as expected.
* **Reporting Issues:** If you encounter problems with the remote workflow, please open an issue on the `SiliconCompiler repository's issue page <https://github.com/siliconcompiler/siliconcompiler/issues>`_.

.. _custom-servers:

For Developers: Custom Servers
------------------------------

If you are interested in deploying your own custom server, we provide a minimal example development server that can be used as a starting point: :ref:`sc-server <app-sc-server>`, run as ``python3 -m siliconcompiler.remote.server``.

Running a server needs the ``server`` :ref:`extra <install_extras>`, which a default install does not carry -- submitting jobs to one, as the rest of this page does, needs nothing beyond SiliconCompiler itself:

.. code-block:: bash

   pip install --upgrade "siliconcompiler[server]"

A ready-to-run deployment of it is checked in at ``setup/server/``: a Docker Compose stack that brings up ``sc-server`` backed by a real Slurm cluster -- ``slurmctld``, ``slurmdbd`` with a MariaDB accounting store, ``slurmrestd``, and one or more ``slurmd`` compute nodes -- with the EDA tools already in the image, so full flows run and not just the scheduler path.

.. code-block:: bash

   cd setup/server
   docker compose up -d --build

The server is then reachable on ``http://localhost:8080``, so :ref:`Step 1 <private-server>` is:

.. code-block:: bash

   sc-remote -configure -server http://localhost:8080

Add compute nodes with ``docker compose up -d --scale scrunner=4``; they register themselves, so no configuration changes. ``setup/server/README.md`` covers the rest, including how to build the stack from a git worktree.

What the server decides, and what it does not
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A submitted manifest says what to build. How it runs is the server's answer and
is not negotiable: it turns the dashboard off, it turns :keypath:`option,remote`
off so the compute node does not submit the job again, and it puts the build
directory and the download cache inside a tree belonging to the submitting user
-- ``<datadir>/users/<user>/{builds,cache}/``. Per user rather than shared,
because tools that create their own cache directories create them owned by
whoever ran first, and nothing can repair a directory it did not create.

Each job is handed to the cluster as **one batch job**, not one dispatch per
node, and the server polls it once per run. ``-cluster`` names how that handover
happens: ``local`` runs it in a process on the server itself, ``slurm`` submits
it with ``sbatch``.
