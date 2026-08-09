How to Contribute a New Module
==============================

SiliconCompiler is built for community collaboration.
Our goal is to support hundreds of PDKs, tools, and flows, which is only possible with help from contributors like you.
This guide outlines the process for adding a new module to the project.

Before You Begin: The Ground Rules
----------------------------------

* **Check for Existing Modules:** Before starting, please browse the repository to see if a module for your target tool or PDK already exists.
* **Permissions and NDAs:** Ensure you have the right to contribute the code and that it does not violate any Non-Disclosure Agreements (NDAs) or copyrights. As a general rule, new PDK modules should be contributed by the foundry, and tool modules by the tool's authors or maintainers.

The Contribution Workflow in 4 Steps
------------------------------------

Step 1: Set Up Your Development Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

First, clone the official SiliconCompiler repository to your local machine and install it in editable mode. This allows your local changes to be immediately reflected when you run tests.

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/siliconcompiler/siliconcompiler.git
   cd siliconcompiler

   # Install in editable mode
   pip install -e .


.. _module_placement:

Step 2: Decide Where Your Module Belongs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Not every module belongs in this repository. Before writing any code, find your
case in the table below -- putting a module in the wrong place is the most common
reason a contribution has to be restarted.

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - What you have
     - Where it goes
     - How to build it
   * - An **open-source PDK** or standard cell library
     - The `lambdapdk <https://github.com/siliconcompiler/lambdapdk>`_ package
     - Contribute it to ``lambdapdk``, which is where every open PDK
       SiliconCompiler ships lives. See :ref:`Defining a PDK <dev_pdks>` and
       :ref:`Defining a Library <dev_libraries>` for how to write one.
   * - A **closed or proprietary PDK**, or IP you cannot publish
     - Your own ``pip``-installable package
     - Never commit foundry data here. :ref:`Packaging an External Library
       <dev_external_libraries>` covers the package layout, licensing, and how to
       reference foundry decks out-of-band through environment-variable
       dataroots.
   * - A **tool driver, flow, or target**
     - In-tree, under ``siliconcompiler/``
     - Continue with Step 3 below.

.. note::
   PDK modules should generally be contributed by the foundry, and tool modules
   by the tool's authors or maintainers. If your PDK is under NDA, the second row
   is the path you want -- it is designed so that foundry data never enters a
   published package.

Step 3: Create Your New Module File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This step applies to tools, flows, and targets, which live in this repository.
Using existing modules as a reference, place your new Python file in the matching
directory:

.. code-block:: text

   siliconcompiler/
   ├── flows/
   │   ├── asicflow.py
   │   └── your_flow.py    <--
   ├── targets/
   │   ├── skywater130_demo.py
   │   └── your_target.py  <--
   └── tools/
       ├── openroad/
       │   └── openroad.py
       └── your_tool/
           └── your_tool.py  <--

If you are building a library or PDK as its own package, the layout is different
and is described in :ref:`Packaging an External Library <dev_external_libraries>`.

Step 4: Submit Your Contribution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once you have created and tested your module, you are ready to submit it for review.

Please read our `CONTRIBUTING.md <https://github.com/siliconcompiler/siliconcompiler/blob/main/CONTRIBUTING.md>`_ guide on GitHub.
It contains essential information about our pull request process, coding standards, and how to format your commit messages.
