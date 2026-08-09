.. _ci_tutorial:

##########################
Running Builds in CI
##########################

A SiliconCompiler build is an ordinary Python script, so any CI system that runs
Python runs it. The interesting part is not getting it to run once -- it is
getting it to run in minutes rather than an hour, and to fail for the right
reasons.

Start with what costs nothing
=============================

Not every check needs EDA tools. The cheapest gates catch most breakage and run
in seconds on a stock runner:

.. code-block:: yaml

   - run: pip install siliconcompiler
   - run: python -c "from mydesign import design; assert design().check_filepaths()"
   - run: python lint.py

:ref:`Linting <lint_tutorial>` needs no tools at all -- the default linter ships
as a Python package. :ref:`Formal checks <simulate_tutorial>` and simulation need
a simulator but no :term:`PDK`. Run these on every push, and save the full flow
for something less frequent.

The two things that make it practical
=====================================

**Do not install tools per job.** Use the
:ref:`Docker image <docker>`, which has them already:

.. code-block:: yaml

   jobs:
     build:
       runs-on: ubuntu-latest
       container: ghcr.io/siliconcompiler/sc_runner:latest
       steps:
         - uses: actions/checkout@v4
         - run: python make.py

Pinning ``:latest`` is a trap, though: the image drifts from the release you
meant, and you end up debugging a tool version nobody chose. **Ask
SiliconCompiler which image to use.** It publishes a reusable workflow that
resolves the exact digest for a tool set, which you call rather than reimplement:

.. code-block:: yaml

   jobs:
     image:
       uses: siliconcompiler/siliconcompiler/.github/workflows/docker_image.yml@v0.38.2
       with:
         sc_version: v0.38.2       # 'latest' resolves to the newest release
         tool: runner              # SiliconCompiler + the tools; see below

     build:
       needs: image
       runs-on: ubuntu-latest
       container: ${{ needs.image.outputs.sc_tool }}
       steps:
         - uses: actions/checkout@v4
         - run: python make.py

Pin both: the ``@`` ref decides which workflow definition runs, and
``sc_version`` decides which image it resolves. A tag is the readable choice; a
commit SHA is the strict one, since a tag can be moved. ``latest`` and ``@main``
are convenient and reproducible only until someone releases.

``sc_tool`` comes back fully qualified -- ``ghcr.io/siliconcompiler/sc_runner:v0.38.2``
for ``runner``, or a digest-pinned ``sc_tools:af23682…`` for ``tools`` -- so the
job moves forward only when you change ``sc_version``. Behind
`docker_image.yml <https://github.com/siliconcompiler/siliconcompiler/blob/main/.github/workflows/docker_image.yml>`_
is ``setup/docker/builder.py``, which derives the image from the tool versions
pinned in ``_tools.json``, so the container and the tool pins cannot disagree.

Two images are published and they are **not** interchangeable:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Image
     - Contains
   * - ``tool: runner``
     - ``sc_runner`` -- the EDA tools **plus** SiliconCompiler, at the release
       the image was built for. Run a build script with nothing to install.
   * - ``tool: tools``
     - ``sc_tools`` -- the EDA tools and **not** the SiliconCompiler package.
       For jobs that install it themselves: testing a checkout, or pinning a
       version other than the image's.

Getting this backwards is the easy mistake: ``sc_tools`` followed by
``python make.py`` fails on ``ImportError: siliconcompiler``.

Or build your own with :ref:`sc-install <app-sc-install>` and reuse it. Either
way the install happens once, not once per job.

**Cache the data.** :term:`PDKs <PDK>`, libraries and git-fetched sources are
downloaded into :ref:`the cache <sc_home>` on first use. Point it somewhere your
CI can restore:

.. code-block:: yaml

   - uses: actions/cache@v4
     with:
       path: ~/.sc/cache
       key: sc-cache-${{ hashFiles('**/make.py') }}
   - run: python make.py

``~/.sc/cache`` is the default location, so caching that path is enough. To put
it somewhere else, set it in the script -- there is no environment variable for
it:

.. code-block:: python

   project.option.set_cachedir("/mnt/ci-cache")

Without this every job re-downloads the PDK, which usually costs more than the
build.

Failing for the right reason
============================

:meth:`.Project.run` raises on a failed run, so a build that cannot complete
fails the job by itself. What it will *not* do is fail because the result got
worse -- that is yours to assert. Read the metrics from the history object
``run()`` returns, not from the live project, which is reset when the job ends:

.. code-block:: python

   history = project.run()
   project.summary()

   slack = history.get("metric", "setupslack", step="route", index="0")
   assert slack >= 0, f"timing did not close: {slack}"

For anything beyond a couple of assertions, :ref:`checklists <checklists>` are
the structured form -- a named set of criteria checked against recorded metrics,
which is a better artifact than a wall of asserts and produces the same
pass/fail.

.. tip::
   Record the numbers, not just the verdict. Publishing
   ``build/<design>/<jobname>/<design>.pkg.json`` as an artifact means a
   regression can be diffed against the last good run rather than re-argued.
   :ref:`Directory structures <build_directory>` says what else is worth
   keeping.

Keeping it fast
===============

* **Split the flow.** :keypath:`option,from` / :keypath:`option,to` run
  synthesis on every push and the full flow nightly.
* **Bound the parallelism.** CI runners are small; a flow built with ``_np``
  widths that suit a workstation will thrash. See
  :keypath:`option,scheduler,maxnodes` and
  :ref:`Parallel Job Execution <parallel_execution>`.
* **Give each configuration its own jobname** so results do not overwrite each
  other -- :ref:`Multi-Job Flows <multi_job_flows>`.

A worked reference
==================

SiliconCompiler's own CI does all of the above: it runs inside a prebuilt tools
container, restores the data cache between jobs, and splits fast checks from the
nightly EDA runs. The workflows under `.github/workflows
<https://github.com/siliconcompiler/siliconcompiler/tree/main/.github/workflows>`_
are the reference implementation, and are worth copying from rather than
starting fresh.

.. seealso::
   :ref:`When a Run Fails <debug_tutorial>` -- what to collect from a CI failure
   so it can be diagnosed without re-running it, and ``sc-issue`` for packaging
   a reproduction out of a build directory.
