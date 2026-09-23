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

**The log of every running node is printed as it is written**, exactly as a
local run prints it, with each line saying which node it came from:

.. code-block:: text

  | INFO | job0 | place.detailed | 0 | Running in /sc_server/...
  | INFO | job0 | route.global   | 0 | Tool 'openroad' found with version ...
  | INFO | job0 | place.detailed | 0 | Finished task in 12.4s

Several nodes at once are interleaved. The server says how many logs one caller
may hold open at a time (``limits.concurrent_log_streams``); past that, nodes
are named once and their logs arrive with their results like everything else.
Set :keypath:`option,quiet` to turn the live output off -- it means here what it
means locally. A server that offers no live tail simply reports node states, and
the logs still arrive with the results.

**Results arrive as each node finishes, not at the end.** A node's outputs,
reports, log and manifest come down as one object the moment that node is done,
so the local build directory and :meth:`.Project.summary` are current while the
rest of the flow is still running -- and a long flow does not end with one large
download.

With the dashboard open (:keypath:`option,nodashboard` unset) the node table is
the dashboard's, so the run prints only what changed. Per-node timers run off
the server's own start times, which makes them continuous across a poll, a
reconnect or a client restart; a node that has finished shows its final runtime
rather than a clock that never stops.

.. note::

   **Results are retrieved whether the run succeeded or failed.** A failed run
   is the one whose log you want, so the client fetches first and reports the
   failure afterwards, in a few lines that say what to do next without opening
   a URL.

Versions, and being told before you upload
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A server publishes the versions it runs, and the client checks its own against
that list at the first call of every session -- before a job exists, before a
byte moves. ``sc-remote -configure`` prints them:

.. code-block:: text

  Configured https://your-server.example.com/v1
  This server runs siliconcompiler 0.39.1, 0.39.0

Two refusals come out of that list and they mean different things:

*Unsupported client or software version*
  You are running something the server does not. Install a version it accepts,
  or ask the operator to add yours. The job is refused at creation, so nothing
  was uploaded.

*This server cannot provide that*
  Your flow needs a tool the deployment tracks and cannot place -- the name is
  in ``resource``. Waiting will not help and neither will retrying; it is a
  fact about the deployment rather than about this moment. Refused at submit,
  before the job is handed to the cluster, so nothing ran and nothing queued.

Two things a remote run does not bring back, both on purpose:

``inputs/`` and ``sc_collected_files/``
  The first is copies of the upstream node's outputs, which you already have
  from the upstream node. The second is what this machine uploaded; the client
  removes its own copy once the archive is built, so sending it back would undo
  that and pay for the same bytes twice.

Anything the server did not keep
  Retention is per kind rather than per job -- a manifest is kept for years and
  bulk results for the deployment's floor -- so an older job may list its
  manifest and nothing else. **That is a successful run, not a degraded one:**
  the manifest carries the record, so what happened is still answerable. The
  client says which objects were not available and why, in the words that fit
  the case: aged out, deleted, or held back.

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

Reading one node's log
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

  sc-remote -cfg build/<design>/<job>/sc_remote.pkg.json -tail place/0

**If the node is still running this follows the log live**, and if it has
finished it prints the archived one. The same call covers both, because a node
can finish between asking and reading and a client that decided in advance
would sometimes be wrong.

``<step>/<index>`` is two fields rather than one name on purpose: ``place/10``
and ``place1/0`` would otherwise both read as ``place10``. The index defaults to
``0``.

From Python:

.. code-block:: python

  client.tail_log(job_id, "place", "0", write=print)   # live, to the end
  client.node_log(job_id, "place", "0", "place.log")   # the archived file

A long tail survives being interrupted. The URL the server hands out has a
lifetime of its own, shorter than most place-and-route runs, so the client
re-asks and resumes from where it stopped -- which is also what happens when a
laptop closes its lid or a proxy drops an idle connection. Nothing is repeated
and nothing is skipped.

A node that has not started yet is reported as not ready and is worth asking
about again. A deployment that keeps finished logs but serves no live tail says
so permanently rather than transiently, so a client stops asking for the tail
and still gets the log when the node finishes.

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

.. _server-images:

What a job runs in
^^^^^^^^^^^^^^^^^^

A server can run each job inside a container it has registered. **The submitter
names a version and the operator names the image** -- and that inversion is the
whole of the security argument. A client that could name an image would choose
what executes on the cluster; a client naming ``siliconcompiler==0.39.1`` is
naming data, which either matches something an operator added on purpose or
does not.

It is off until an operator turns it on, because whether the compute nodes can
run a container at all is not something the server can find out by looking. A
deployment that runs jobs on the host is a supported deployment, not a degraded
one. To turn it on, put ``{"containers": true}`` in ``<datadir>/config.json``
and register at least one image:

.. code-block:: bash

  python3 -m siliconcompiler.remote.server.registry -datadir <dir> \
      add-software siliconcompiler
  python3 -m siliconcompiler.remote.server.registry -datadir <dir> \
      add-version siliconcompiler 0.39.1 -preference 10
  python3 -m siliconcompiler.remote.server.registry -datadir <dir> \
      add-image ghcr.io/org/sc-runtime:0.39.1 -contains siliconcompiler==0.39.1

``add-image`` **resolves the tag to a digest once, there and then**, and the
digest is what is dispatched. Rebuilding ``sc-runtime:0.39.1`` afterwards does
not change what any job runs -- that takes registering it again, which is a
decision somebody made rather than one that happened. Nothing is ever deleted:
retiring a row stops it being used and keeps it readable, because a job from
last year names it.

Four things follow, and each is a behaviour rather than a setting:

**A version is advertised only when it is runnable.** ``software`` renders from
what is registered, joined to a live image that holds it. A version with no
image is not offered, so a client is never told yes and refused at submit.

**Submit resolves one image per node.** An import node running thirty seconds of
Python has no business pulling a twelve-gigabyte OpenROAD image, so among the
images that fit, the one with the fewest declared contents wins. There is no
flag for *this one is python-only* -- an image whose contents are framework
distributions and no tool already is one.

**A tool with no image fails the whole submit**, before anything is handed to
the cluster. Only a tool the deployment has registered counts: a server that
curates images for the framework and says nothing about Verilator is not
claiming to have a Verilator image and is not refused for lacking one.
Registering the name is how an operator takes that claim on.

**A node waiting for its image reports** ``preparing``. A tool image is minutes
on a host that has not seen it, and without a state for that the wait is
indistinguishable from a hang.

Whatever is scheduling is what places the container, and the two mechanisms are
mutually exclusive because :keypath:`option,scheduler,name` holds one value:

``-cluster slurm``
  The node runs as a Slurm step, ``srun --overlap --container <bundle>``, inside
  the one allocation the job already has. The cluster needs an OCI runtime and
  an ``/etc/slurm/oci.conf`` telling Slurm how to call it; bundles are unpacked
  to ``<datadir>/images/<digest>/`` and shared by every job that names that
  digest.

``-cluster local``
  There is no Slurm to place anything, so the node runs through
  SiliconCompiler's own docker scheduler, by digest.

.. important::

   On a cluster :keypath:`option,scheduler,queue` keeps meaning what it means
   there -- the **partition** -- and the server does not touch it. A server that
   wrote an image reference into it would submit every node to a partition named
   after a container.

.. warning::

   ``-contains`` is **declared and unverified**. Nothing opens the image to
   check that what it claims to hold is inside it, so a wrong entry means a job
   runs in a container without what it asked for and fails at run time rather
   than at submit. ``resolve`` shows what a job would be placed in without
   submitting one:

   .. code-block:: bash

     python3 -m siliconcompiler.remote.server.registry -datadir <dir> \
         resolve -versions siliconcompiler==0.39.1 -tools openroad
