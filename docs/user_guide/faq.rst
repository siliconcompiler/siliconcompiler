.. _faq:

.. index:: ! FAQ, ! frequently asked questions

##########################
Frequently Asked Questions
##########################

Questions people actually ask, drawn from the issue tracker and the
`Help (Q&A) discussions <https://github.com/siliconcompiler/siliconcompiler/discussions/categories/help-q-a>`_.

If you are looking for "which method call does X", that is the companion page:
:ref:`How do I…? <howto>`.

Getting started
===============

.. index:: ! try without installing tools

Do I need to install EDA tools, or can I just try it?
-----------------------------------------------------

You can try it with nothing but Docker and ``pip install siliconcompiler``, by
running the tools in containers:

.. code-block:: bash

   python -m siliconcompiler.demos.asic_demo -scheduler docker

Running them natively needs four tools -- :ref:`Yosys <tool-yosys>`,
:ref:`OpenROAD <tool-openroad>`, :ref:`OpenSTA <tool-opensta>` and
:ref:`KLayout <tool-klayout>`. It is the better answer if you expect to keep
building, but it is not a five-minute detour, so it is not the one to start on.
:ref:`Where the compilation runs <choose_run_mode>` compares the two, and
:ref:`Using SiliconCompiler with Docker <docker>` sets the container path up.

.. index:: ! confidential, ! proprietary IP, ! privacy

Does my design leave my machine?
--------------------------------

Not on a local or :ref:`Docker <docker>` run -- both read and write your working
directory and nothing else.

It does on a :ref:`remote run <remote_processing>`, which uploads the design to
the server named in your ``credentials`` file. SiliconCompiler does not host a
server for you, so that is a machine you or your organization operates, under
whatever terms that operator sets. You are responsible for having the right to
distribute any IP contained in what you upload.

.. index:: ! Windows, ! WSL

Can I use SiliconCompiler on Windows?
-------------------------------------

The package installs and runs on Windows, and is tested there on every commit,
but that testing does not cover running EDA tools. There are no tool install
scripts for Windows and local flows are not supported on it.

From Windows, use the :ref:`Docker image <docker>`, WSL, or a
:ref:`remote run <remote_processing>`.
KLayout is worth installing natively so :ref:`sc-show <app-sc-show>` can display
results. See :ref:`External Tools <external_tools>`.

.. index:: ! which PDK, ! getting started PDK

Which PDK should I start with?
------------------------------

**Sky130.** It is what the :ref:`ASIC demo <asic_demo>` and the
:ref:`Quickstart <quickstart_guide>` use, so it is the best-trodden path and the
one most likely to work first time.

Every open :term:`PDK` SiliconCompiler supports is packaged in
`lambdapdk <https://github.com/siliconcompiler/lambdapdk>`_ and listed under
:ref:`pre-defined PDKs <builtin_pdks>`. Maturity varies, and the catalogue does
not yet say by how much; if a target does not behave, searching the
`discussions <https://github.com/siliconcompiler/siliconcompiler/discussions>`_
for its name is usually faster than debugging it.

Understanding the tool
======================

.. index:: ! target vs flow vs PDK

What is the difference between a target, a flow and a PDK?
----------------------------------------------------------

A :term:`PDK` is foundry data. A :term:`flow` is the sequence of steps to run. A
:term:`target` is a single function that selects both -- PDK, standard cell
:term:`libraries <library>`, flows and physical defaults -- so one call
configures a project for a technology:

.. code-block:: python

   from siliconcompiler.targets import skywater130_demo

   skywater130_demo(project)     # picks the PDK, libraries and flows in one call

The :ref:`glossary <glossary>` defines these and the rest of the vocabulary.

.. index:: ! where does my module go, ! new PDK, ! new tool, ! new library

I have a new PDK, library or tool. Where does it go?
----------------------------------------------------

Three answers depending on what it is: open PDKs go to ``lambdapdk``, closed or
proprietary data goes in a package of your own and never into this repository,
and tool drivers, flows and targets go in-tree.

:ref:`Where your module belongs <module_placement>` has the decision table,
and :ref:`Packaging an External Library <dev_external_libraries>` covers the
proprietary case, including how to reference foundry decks out-of-band so they
never enter a published package.

.. index:: ! package version, ! schema version, ! schemaversion

What is the difference between the package version and the schema version?
--------------------------------------------------------------------------

They are versioned independently. The package is currently |version|; the
:term:`schema` has its own version (0.57.0 at the time of writing) recorded in
every :term:`manifest`.

That is what lets SiliconCompiler tell you a manifest was written by an
incompatible schema. When one does not load, the
:ref:`Schema Changes <schema_changelog>` appendix records what was added,
renamed or removed at each schema version.

.. index:: ! raw set get, ! typed accessors

Should I write ``set()``/``get()`` or the typed accessors?
----------------------------------------------------------

Prefer the typed accessor whenever one exists; use a keypath when there is no
accessor, which mostly means reading :term:`metrics <metric>` and
:term:`records <record>`. Neither is deprecated -- see
:ref:`Working with the Schema <schema_access>`.

.. index:: ! where are files written, ! build directory location

Where does SiliconCompiler put things?
--------------------------------------

Build artifacts go under ``build/<design>/<jobname>/``; downloaded data,
settings and credentials live in ``~/.sc``.
:ref:`Directory structures <directory_structures>` maps both.

When things go wrong
====================

.. index:: ! run failed, ! where are the logs, ! reading logs

My run failed. Where are the logs?
----------------------------------

In the node directory of the step that failed,
``build/<design>/<jobname>/<step>/<index>/``. There are two logs and they answer
different questions:

* ``<step>.log`` -- what the tool printed. Start here when the tool failed.
* ``sc_<step>_<index>.log`` -- what SiliconCompiler did around it: which files
  it resolved, which parameters it passed.

``<step>.errors`` and ``<step>.warnings`` hold the lines matched as errors and
warnings, and are what the :keypath:`metric,errors` and
:keypath:`metric,warnings` metrics count. See
:ref:`Inside a node directory <directory_structures>`.

.. index:: ! bug report, ! testcase, ! reproducer

How do I file a useful bug report?
----------------------------------

Use :ref:`sc-issue <app-sc-issue>`, which packages a single failing node and its
inputs into a standalone, runnable test case:

.. code-block:: bash

   sc-issue -cfg build/<design>/<jobname>/<step>/<index>/inputs/<design>.pkg.json

A failing run prints this command with the paths filled in. Attaching its output
saves a round trip of questions.

.. index:: ! drvs vs drcs, ! design rule violations

What is the difference between the ``drvs`` and ``drcs`` metrics?
-----------------------------------------------------------------

They count different kinds of violation, not the same violations at different
stages.

:keypath:`ASIC,metric,drvs` -- **electrical and connectivity** rule violations.
:ref:`OpenROAD <tool-openroad>` sums max slew, max capacitance and max fanout
violations, floating and overdriven nets, and antenna violations;
:ref:`OpenSTA <tool-opensta>` counts its own design rule violators; a
:term:`LEC <LEC>` task records equivalence mismatches here. No geometry is
involved.

:keypath:`ASIC,metric,drcs` -- **geometric** design rule violations, from a tool
that checks geometry against the :term:`PDK` rules.
:ref:`Detailed routing <tool-openroad>` reports these as it routes, and a
dedicated checker -- :ref:`Magic <tool-magic>` or :ref:`KLayout <tool-klayout>`
DRC -- reports them in :term:`signoff`. :ref:`Netgen <tool-netgen>` also records
:term:`LVS` errors under this metric.

So ``drcs`` is not exclusively a signoff number:
:ref:`asicflow <schema-siliconcompiler-flows-asicflow-asicflow>` reports it from
detailed routing. A clean ``drcs`` there means the router believes the layout is
legal, which is a weaker statement than a signoff DRC run in
:ref:`signoffflow <schema-siliconcompiler-flows-signoffflow-signoffflow>` using
the foundry deck.

See :ref:`Working with Metrics <dev_metrics>` for how metrics are recorded and
compared, and the :ref:`metric schema <schema>` for the full list.

.. index:: ! rerun a step, ! resume, ! run only synthesis

How do I run only part of the flow, or re-run one step?
--------------------------------------------------------

Use :keypath:`option,from`, :keypath:`option,to` and :keypath:`option,prune`.
A re-run resumes by default, reusing nodes that already completed, so restarting
from a step is enough to re-run it and everything after it:

.. code-block:: python

   project.option.add_from('synthesis')     # start here, reusing earlier results
   project.option.add_to('route.detailed')  # and stop here

``from`` and ``to`` take step names only, not indices -- deliberately, to keep
them simple. To drop individual nodes, use ``prune``. To discard previous
results entirely, see :keypath:`option,clean` in
:ref:`Directory structures <directory_structures>`.

.. index:: ! vector power, ! VCD, ! switching activity, ! power estimation

Is vector-based power estimation supported?
-------------------------------------------

Yes. If a :term:`VCD` is available, OpenSTA annotates switching activity from
it, so power numbers reflect real toggle rates rather than default assumptions.
Add the :term:`waveform` to a fileset and the timing task picks it up:

.. code-block:: python

   with design.active_fileset("vcd"):
       design.add_file("sim.vcd")

A VCD produced by an earlier node in the same flow is picked up automatically.
Where the VCD hierarchy does not start at the design top, set the
``power_activities`` variable on the OpenSTA timing task to map a scope to the
fileset holding the waveform.

Doing more
==========

.. index:: ! CI, ! continuous integration, ! automation

Can I run this in CI?
---------------------

Yes -- a build is an ordinary Python script, so anything that runs Python runs
it. Two things make it practical:

* Point :keypath:`option,cachedir` at a cached directory so :term:`PDKs <PDK>`
  and :term:`libraries <library>` are not re-downloaded on every job -- see
  :ref:`the data cache <sc_home>`.
* Use :ref:`sc-install <app-sc-install>` in the image build, or the
  :ref:`Docker image <docker>`, rather than installing tools per job.

SiliconCompiler's own CI does both -- it runs inside a prebuilt tools container
and restores the data cache between jobs. The workflows under
``.github/workflows/`` are a working reference.

.. index:: ! commercial tools, ! Synopsys, ! Cadence, ! proprietary EDA

Which commercial EDA tools are supported?
-----------------------------------------

SiliconCompiler supports a number of commercial tools, but those drivers cannot
be published for NDA reasons, so they are not in this repository and are not in
the :ref:`tool catalogue <builtin_tools>`. If you need commercial tool support,
raise it on the
`discussions board <https://github.com/siliconcompiler/siliconcompiler/discussions>`_.

Nothing stops you writing your own driver for a proprietary tool and keeping it
in your own package -- see :ref:`Setting up a Tool <dev_tools>` and
:ref:`Packaging an External Library <dev_external_libraries>`.

.. index:: ! old script, ! Chip, ! porting a script, ! legacy API

I have an old script that uses ``Chip()``. How do I port it?
------------------------------------------------------------

``Chip`` was removed in v0.35.0 and split into a :term:`design` and a project.
:ref:`Migrating from the Chip API <migration_guide>` maps the old names onto the
new ones, method by method, and shows the same build written both ways.

If a code assistant wrote the script you are porting, this is the most likely
explanation: the ``Chip`` API is what most of the material written about
SiliconCompiler still describes.

Still stuck?
============

If your question is not here, the
`Help (Q&A) discussions <https://github.com/siliconcompiler/siliconcompiler/discussions/categories/help-q-a>`_
are actively answered, and questions asked there are where this page comes from.
