.. _remote_processing:

Guide to Remote Compilation
===========================

SiliconCompiler supports a remote compilation model, allowing you to leverage cloud resources for access to pre-configured tool installations, elastic compute, and potentially NDA-protected :term:`PDKs <PDK>` or :term:`IPs <IP>`.

Remote execution runs against a server you or your organization operates.
SiliconCompiler does not host a server for you -- see
:ref:`For Developers: Custom Servers <custom-servers>` for how to stand one up.

.. note::

  The ``v1`` remote client, ``sc-server`` and its portal are **alpha**. The
  ``v1`` API they speak is versioned, but the client's commands, what it prints
  and the portal's screens may still change between releases.

.. _private-server:

Step 1: Configure Your Remote Server
------------------------------------

Run ``sc-config remote configure`` and give it the server's address:

.. code-block:: bash

  sc-config remote configure https://your-server.example.com

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
  Saved to /home/user/.sc/auth/remote.json

Where the server has a person approve the login, the command prints the page
to open and the code to enter, with this machine's key and name. The approval
page shows the key too: check that the two match before you approve, since a
code somebody else started shows a key that is not yours.

There is no default server, so the address is required: leaving it out is an
error rather than a redirect somewhere you did not choose. A server the command
cannot reach or log in to is not saved. Each server you configure keeps its own
session, so switching back to one needs no new login:

.. code-block:: bash

  sc-config remote use https://other-server.example.com

makes a server already configured on this machine the default, without
contacting it. ``sc-config remote show`` lists the servers configured here.
``show``, ``portal`` and ``logout`` act on the default server, or on another
one configured here when you name it. ``logout`` ends this machine's session on
a server and removes the server from this machine, its headers and authority
with it.

Where the server sits behind an access layer that requires headers of its own,
such as Cloudflare Access, name each one with ``-header``. Each value is asked
for without being echoed, or read from standard input a line at a time in the
order named, never from the command line; an empty value removes the header:

.. code-block:: bash

  sc-config remote configure https://your-server.example.com \
    -header CF-Access-Client-Id -header CF-Access-Client-Secret

What is written, and where
^^^^^^^^^^^^^^^^^^^^^^^^^^

Everything is in one private directory, ``$HOME/.sc/auth/``
(``C:\Users\<USERNAME>\.sc\auth\`` on Windows) -- or wherever ``SC_AUTH_DIR``
points -- in two files, and a directory once a server has an authority of
your own:

``dpop-key.pem``
  Your machine's private key. **This is the credential.**

``remote.json``
  The store: which server is the default, and for each server you have
  configured, your session with it -- the id it knows you by, its refresh
  token, or a CI credential in place of one -- any headers an operator's
  access layer requires, and the authority it is verified with, if one of your
  own. :keypath:`option,credentials` names this file. No access token is
  written down, so every command, ``sc-config remote show`` included, spends
  the refresh token once. ``sc-config remote show`` reports the session this
  machine holds -- its scope, the device it is bound to, and when its tokens
  and the session itself end -- as the server reports it.

``certs/``
  Each authority's trust bundle, the usual authorities with yours, rebuilt
  from ``remote.json`` when it is missing.

The headers are configured once, for the server, and sent to its address and
nowhere else: a live log or a download arrives through the server's own
address, or from somewhere that needs none. A ``$HOME/.sc/credentials`` file an
older client wrote, and the files it kept beside it, are moved into
``remote.json`` the first time it is read, and its upload whitelist into the
``uploads`` setting.

Two settings are not secrets, and live in ``$HOME/.sc/settings.json`` instead,
in its ``remote`` category, changed with :ref:`sc-config settings <app-sc-config>`:

``uploads``
  The directories a run may upload a directory from. A directory not on the
  list is not uploaded, and the client says so:

  .. code-block:: bash

    sc-config settings add remote uploads ~/projects/chip

``browser``
  ``false`` keeps the client from opening a browser -- for the login page, a
  job's page or the portal -- on a machine with no screen; it prints the
  address instead.

Nothing else goes with a request. The client never sends a credential it did
not put there itself, so an entry for the server in ``~/.netrc``, a credential
helper or a keychain is not used, while ``HTTPS_PROXY``, ``NO_PROXY`` and
``REQUESTS_CA_BUNDLE`` still apply.

A server signed by your own authority
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Where the server's certificate is signed by a certificate authority of your
organisation's, give that authority's certificate when you configure it:

.. code-block:: bash

  sc-config remote configure https://your-server.example.com -cert ./our-ca.pem

It prints each certificate's subject and SHA-256 fingerprint: check them with
whoever runs the server. The authority is kept for that server once it
verifies it, and every later command verifies the server with it. When the
authority is replaced, run the same command with the new file; your session is
kept, since it is bound to this machine's key rather than to the certificate.
A server certificate renewed by the same authority needs nothing.

The authority is trusted in addition to the usual ones, never in place of them,
so an upload to public storage still verifies, and so does a server that moves
to a publicly signed certificate. A ``REQUESTS_CA_BUNDLE`` in the environment
still takes precedence. The client never trusts a certificate the server
presents: only one you gave it.

.. warning::

   ``dpop-key.pem`` identifies this machine to the server. Treat it the way
   you would an SSH private key.

   * The store is created readable only by you, and the client **refuses to
     run** if something widened it -- it does not repair it, because a key
     others could read may already be copied. Restore the modes
     (``chmod 700`` on the directory, ``chmod 600`` on each file), then replace
     the key with ``sc-config remote rotate-key``.
   * **Never commit the store**, and do not paste its contents into an
     issue, a pull request or a build log.
   * Do not copy the key between machines. Each machine generates its own.
     ``sc-config remote rotate-key`` replaces it deliberately; nothing else does.

.. note::

   A server that does not verify who you are -- which the bundled
   ``sc-server`` does not -- separates your jobs from other users' but is not a
   security boundary. ``sc-config remote configure`` says so when it connects.

Step 2: Verify the Connection
-----------------------------

After configuration, run ``sc-config remote show`` to test the connection to your server.

.. code-block:: bash

  sc-config remote show

A successful connection will typically display a status message or an empty list of your remote jobs, confirming that your configuration and credentials are correct.

It also prints every notice the server publishes, such as scheduled downtime,
and names any terms document whose next version takes effect soon and that you
have not accepted, with the page where you can accept it early. A remote run
shows each of these once. The client never accepts terms for you.

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

What goes into the archive is decided by what owns each file, and you set
nothing to control it:

* **your design's files -- always;**
* **a PDK's, standard-cell library's or FPGA device's files -- only when they
  come from a local path or a package installed editable.** One fetched from a
  release, like the PDKs in ``lambdapdk``, stays behind even though a copy is in
  your cache: the server supplies its own. A path rooted in an environment
  variable -- ``$FOUNDRY_ROOT/...`` -- is a local path: your machine expands
  the variable and the files go up;
* **a tool's scripts -- only when they come from a local path or a package
  installed editable**, such as a SiliconCompiler checkout you are working in;
* **plus the manifest**, and, for a run that starts part-way through the flow,
  the results of the nodes it starts from.

**And of those, only what the flow reads.** Each task declares the keys it
reads, through :meth:`.Task.add_required_key`, and a file goes up only when its
key is among them for a node that will run. A local library with views for ten
tools uploads the three a synthesis-to-routing flow uses, and a PDK the flow
reads nothing of is never fetched by the server either. Tasks declare what they
read when they are set up, so the client sets up every node on a copy of your
project first -- a fraction of a second, with nothing run and nothing downloaded
-- and sends the declarations in the manifest, where the server reads the same
list. If a task cannot be set up on your machine (one needing a Python package
only the server has, say), the client says so and uploads by owner alone.

.. note::

   **A file a task reads without declaring it is left behind**, and the node
   that reads it fails on the server. That is a bug in the task: its setup
   should call :meth:`.Task.add_required_key` for it. A file the server expected
   and did not get is refused at submit, naming its keypath, before anything
   runs.

**A testbench's own Python packages travel as a list, not as files.** For each
node the run executes whose tool runs Python of yours -- a cocotb testbench --
the client follows the imports of the node's test modules, through your own
helper modules beside them, to the packages they reach, and lists them once for
the whole job when it creates it: each package installed from an index, at the
version installed on your machine, and, as constraints, the versions of what
those packages depend on. It leaves out what the server's image already holds
(SiliconCompiler, and cocotb itself). The list names no index and the client
reads no pip configuration: the server installs from its own indexes, while the
job is staging, and a package that will not install there rejects the job
before any node runs.

The server installs exactly the version listed. Where no index it uses lists
that version -- even one listing other versions of the same name -- it asks for
your wheel of it instead. Where the version is listed but nothing of it installs
on the server, or it has been yanked, the newest of its release line is
installed in its place, and the client says so once the job has staged. What
the server did while staging is saved in the job directory as
``remote-staging.log``, and staging as a whole is bounded by the
``max_staging_seconds`` in ``GET /v1/me``'s limits: past it the job fails
``staging-timed-out``.

A package you installed editable, from a local path or from version control
has no index to come from, so the client builds it into a wheel -- with
``pip wheel --no-deps`` for an editable or local-directory install, and from
the installed files otherwise -- and uploads it, and the server installs it
with the rest. A package the server's indexes turn out not to have is asked for
the same way, while the job stages, and the client answers with its wheel.
Installing a wheel runs none of its code.

Your own modules -- the helpers your tests import -- go up as files, in the
same collected folder as the test that imports them and under their own names,
so the test imports them on the server as it does here. None of it is installed
or run on the way.

**A job that runs your Python names the Python it was written for**, the major
and minor version of the one you are running (``==3.12.*``). The server places
such a node only in an image running a matching Python, and refuses the job at
create where it has none, naming the versions it does have. Nothing in the job
changes that: the server's operator would have to add one, or you run from a
Python it has.

**A compiled package is published, not uploaded.** A wheel the client builds
here was built for your machine, so a package with a compiled extension cannot
go up as one. Publish a wheel of it built for the server's platform to one of
the server's indexes, and the client lists it like any other package. The server
installs binary wheels: a package its indexes offer only as a source
distribution is asked of the client where it is pure Python, and refused where
it is compiled, unless the deployment's operator lets it build from source.

A deployment may also grant these per account, as capabilities in
``GET /v1/me``: ``python-packages`` to have packages installed, and
``python-wheels`` to upload wheels as well. The client checks before it creates
the job, and names what is missing. A deployment that grants nothing gates
nothing, and ``python.env`` alone decides.

The client stops before creating the job if a package it would send as a wheel,
or a helper module, holds a compiled extension (``.so``, ``.pyd``, ``.dylib``),
if a wheel holds a file that runs by itself (a ``.pth``, a
``sitecustomize.py``) or depends on a package by URL, if a wheel will not build,
if two sources would supply the same file, if a node that runs your Python
cannot be set up on your machine, if the job has packages to install and the
server does not offer ``python.env``, or if your account lacks a capability the
job needs. A testbench whose only Python is its own modules needs no
``python.env`` at all. It warns, and carries on, where a package it lists
installs a ``.pth`` file, and where an editable package's wheel leaves out
files its module directory holds -- a data file its packaging does not name,
which the node will not have.

An import made dynamically, through ``importlib`` or a plugin entry point, is
not followed and fails on the server at import. Add a plain import of the
package to a test module. Nor is an import under a platform check,
``if sys.platform == "win32":``, which is for a platform the server's may not
be; import it outside the check if the server needs it.

The client prints what goes up, per dataroot, with sizes, before anything
moves.

**Files marked private never go up.** A dataroot registered with a ``+private``
scheme -- ``file+private://``, ``git+ssh+private://`` and the rest -- is data
whose bytes must not leave your machine, the design's included. The server
supplies it itself: from its operator's copy, from a copy of its source it
already holds, or by fetching that source where its allowlist admits it --
never by asking you -- or refuses the job before anything uploads, and it
refuses a job whose upload carries one anyway, keeping none of it. A ``file+private://`` source is on your machine, where no
server can fetch it, so only an operator's copy can supply it. A private
dataroot is named by where the manifest keeps it: a library's as
``library,<name>,dataroot,<root>``, and a task's own as
``tool,<tool>,task,<task>,dataroot,<root>``, so two tasks of one tool with a
dataroot of the same name are two dataroots, and a refusal says which one --
*the private dataroot tool,acme_sim,task,run,dataroot,scripts is not held by
this server*. Files go up a value at a time, so a private file stays here
beside a file of the same fileset that goes up.

**What the server cannot supply, it asks for.** A source the server does not
hold and will not fetch itself -- a private git repository behind your own key,
not marked ``+private``, is the common case -- is named in the answer to the
first call, and the client fetches it with your credentials and adds it to the
upload. If it fails later -- the server's own fetch of a release was refused
-- the job goes back to waiting for input, and the client sends only what was
asked for. If your
machine cannot reach it either, the run stops here, naming it, and nothing is
uploaded.

A server never reads a path your job names on its own disk: every file either
arrives in the upload or is supplied by the server under its own name for it.

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
the logs still arrive with the results. A live log survives a dropped
connection: the client asks again and resumes where it stopped, so nothing is
repeated and nothing is skipped.

**Results arrive as each node finishes, not at the end.** A node's outputs,
reports, log and manifest come down as one object the moment that node is done,
so the local build directory and :meth:`.Project.summary` are current while the
rest of the flow is still running -- and a long flow does not end with one large
download.

**A passed-through file comes back as a link to the node that produced it.** A
task that hands an input on unchanged holds it as a link, and the server keeps
it that way rather than storing a second copy: the file resolves once its home
node is in the job's directory beside it. Fetching the whole job gives you a
consistent tree; to use one node on its own, fetch the node its links point at
too. A link out of the job is never sent back, and neither is one to nothing.
The same holds going up: a ``-from`` run sends each linked file once, and stops
before anything moves if an upstream result links to a node that is not on
your machine.

With the dashboard open (:keypath:`option,nodashboard` unset) the node table is
the dashboard's, so the run prints only what changed. Per-node timers run off
the server's own start times, which makes them continuous across a poll, a
reconnect or a client restart; a node that has finished shows its final runtime
rather than a clock that never stops.

.. note::

   **Results are retrieved whether the run succeeded or failed.** A failed run
   is the one whose log you want, so the client fetches first and reports the
   failure afterwards, in a few lines that say what to do next without opening
   a URL. Each failed node follows on a line of its own, with what the server
   knows of why: the time or memory limit it ran into, or the image that would
   not pull.

Versions, and being told before you upload
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A server publishes the versions it runs, and the client checks its own against
that list at the first call of every session -- before a job exists, before a
byte moves. ``sc-config remote configure`` prints them:

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

What a remote run does not bring back, on purpose:

``sc_collected_files/``
  What this machine uploaded; the client removes its own copy once the archive
  is built, so sending it back would undo that and pay for the same bytes twice.

A node's ``inputs/`` -- copies of its upstream node's outputs -- comes back
where the server sends it: ``sc-server`` returns each node's whole directory,
``inputs/`` included.

Anything the server did not keep
  Retention is per kind rather than per job -- a manifest is kept for years and
  bulk results for the deployment's floor -- so an older job may list its
  manifest and nothing else. **That is a successful run, not a degraded one:**
  the manifest carries the record, so what happened is still answerable. The
  client says which objects were not available and why, in the words that fit
  the case: aged out, deleted, or held back.

Interrupting a run
^^^^^^^^^^^^^^^^^^

Interrupting a run with ``Ctrl-C`` disconnects from it without stopping it: the
job keeps running on the server, and you follow, cancel or delete it in the
portal. A run interrupted before its job was submitted cancels the job, since
nothing else would submit it.

A job whose submit is refused -- a terms document to accept, or an account to
be provisioned -- is cancelled the same way: once that is done, run the flow
again.

Looking at it in a browser
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

  sc-config remote portal

A server carries a portal: your jobs and their nodes, each node's log live or
archived, the artifacts a run produced, the machines that may act as you, your
account, and the images the deployment runs jobs in. A job is cancelled and
deleted there.

**What went in is kept alongside what came out.** Every archive the job
uploaded is its own artifact -- the first, and each follow-up the server asked
for -- and so is each node's ``inputs`` directory, what its upstream handed it.
All of them can be opened in the portal and read file by file, and every
artifact shows its ``sha256`` hash, which for an upload is the digest your
client declared and the server checked. The client never downloads them back:
it has the uploads, and a node's inputs are its upstream's outputs.

**There is no login.** Your machine's key is the credential, and a browser
arriving cold holds none of it -- so the client proves possession of that key
and passes a session across. The link it opens is **good for one use and lives
under a minute**, and is printed only where no browser opened: it reaches the
browser's history and possibly an access log, and spending it on arrival is what
makes both worthless.

.. note::

   **A portal session is a cookie, and it never becomes an API credential.** It
   mints no token and carries no key binding. Every credential this system
   issues is bound to a key; a cookie is not, and a path from one to the other
   would be the shortest way around that.

Cancelling a job in the browser stops a run you are still waiting on, which
reports it.

From CI
-------

A CI job has no person to approve a login. Where the server offers token
exchange, mint a CI credential in the portal and store the one line it shows
as the pipeline secret ``SC_CI_CREDENTIAL``. Then, before the build, with that
variable set:

.. code-block:: bash

  sc-config remote configure https://your-server.example.com

The session is the CI credential's. On GitHub Actions the session store goes in
the job's own temporary directory and ``SC_AUTH_DIR`` is exported to later
steps. Where the server sits behind an access layer such as Cloudflare Access,
name its headers in the same command, each value a line of standard input so
it never appears on a command line; ``-cert`` goes here too:

.. code-block:: bash

  printf '%s\n%s\n' "$CF_CLIENT_ID" "$CF_CLIENT_SECRET" | \
    sc-config remote configure https://your-server.example.com \
      -header CF-Access-Client-Id -header CF-Access-Client-Secret

A credential bound to one project needs that project named on every
job: set ``SC_REMOTE_PROJECT``. The client warns, as a GitHub annotation, when
the credential has a week left.

Troubleshooting
---------------

* **"The edge refused this request":** Something in front of the server --
  an access layer such as Cloudflare Access -- answered instead of the API.
  Check the headers the operator asked you to set: ``sc-config remote show``
  shows their names, and ``sc-config remote configure <server> -header <name>``
  sets one, reading the value from standard input.
* **"Your credentials were used elsewhere":** A session token was spent twice,
  so the server ended the session. Replace this machine's key with
  ``sc-config remote rotate-key``. On every server configured here that holds a
  session, it first revokes the device the old key is bound to, with that key,
  which ends every session it holds; then it enrols this machine with the
  default server again as a new device.
* **Local Changes Not Reflected:** Any modifications you make to local, built-in tool scripts, PDKs, or libraries will not be used in a remote job. The remote server uses its own pre-configured environment.
* **Network and Filesystem Issues:** Jobs run in isolated environments on the server. Code that relies on specific network or local filesystem calls may not work as expected.
* **Reporting Issues:** If you encounter problems with the remote workflow, please open an issue on the `SiliconCompiler repository's issue page <https://github.com/siliconcompiler/siliconcompiler/issues>`_.

.. _custom-servers:

For Developers: Custom Servers
------------------------------

SiliconCompiler ships a small server of its own, enough to test the client
against and to run jobs on one machine or a small Slurm cluster.

.. code-block:: bash

  pip install "siliconcompiler[server]"
  python3 -m siliconcompiler.remote.server -port 8080 -datadir ./sc_server -cluster local

``-port``
  The port to serve on (default ``8080``).

``-datadir``
  The directory holding the server's state: its database, each user's job
  directories and the shared package cache (default ``./sc_server``).

``-cluster``
  How a run is started: ``local`` runs it as a process of the server, ``slurm``
  submits it as one Slurm batch job. In the ``slurm`` case the compute nodes need
  SiliconCompiler, the tools a flow uses, and the data directory mounted at the
  same path as on the server. See :ref:`slurmsetup` for the cluster itself.

Then run ``sc-config remote configure http://localhost:8080`` on the client.

``setup/server/`` in the repository holds a Docker Compose deployment of the
server on a real Slurm cluster (a controller, an accounting database and
scalable compute nodes running the tools directly), used by the daily CI to run
the ASIC and FPGA demos remotely. Its ``README.md`` says how to bring it up.

The server is a test server, not a service to expose to others. It does not
verify who a caller is, and it does not offer the device login, terms or
approvals, containers or Python packages, or continuing from an earlier job.
Every node of a flow runs inside one job. A site that needs more writes its own
server to the :ref:`v1 API <remote_api>`, which the client speaks.
