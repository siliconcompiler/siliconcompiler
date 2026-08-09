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
       uses: siliconcompiler/siliconcompiler/.github/workflows/docker_image.yml@main
       with:
         sc_version: latest        # or a tag such as v0.38.2
         tool: tools               # the image with the EDA tools in it

     build:
       needs: image
       runs-on: ubuntu-latest
       container: ${{ needs.image.outputs.sc_tool }}
       steps:
         - uses: actions/checkout@v4
         - run: python make.py

``sc_tool`` comes back as a digest-pinned name -- for example
``ghcr.io/siliconcompiler/sc_tools:af23682…`` -- so the job is reproducible and
moves forward only when you change ``sc_version``. Behind
`docker_image.yml <https://github.com/siliconcompiler/siliconcompiler/blob/main/.github/workflows/docker_image.yml>`_
is ``setup/docker/builder.py``, which derives the image from the tool versions
pinned in ``_tools.json``, so the container and the tool pins cannot disagree.

Two images are published and they are not interchangeable: ``sc_tools`` carries
the EDA tools and is what a build job wants, while ``sc_runner`` is the smaller
package-only image the :ref:`Docker scheduler <docker_two_ways>` launches per
node.

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
     env:
       SC_CACHEDIR: ~/.sc/cache

Without this every job re-downloads the PDK, which usually costs more than the
build.

Failing for the right reason
============================

:meth:`.Project.run` raises on a failed run, so a build that cannot complete
fails the job by itself. What it will *not* do is fail because the result got
worse -- that is yours to assert:

.. code-block:: python

   project.run()
   project.summary()

   slack = project.get("metric", "setupslack", step="route", index="0")
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
