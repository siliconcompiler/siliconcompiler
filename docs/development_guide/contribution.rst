How to Contribute a New Module
==============================

SiliconCompiler is built for community collaboration.
Our goal is to support hundreds of PDKs, tools, and flows, which is only possible with help from contributors like you.
This guide outlines the process for adding a new module to the project.

Before You Begin: The Ground Rules
----------------------------------

* **Check for Existing Modules:** Before starting, please browse the repository to see if a module for your target tool or PDK already exists.
* **Permissions and NDAs:** Ensure you have the right to contribute the code and that it does not violate any Non-Disclosure Agreements (NDAs) or copyrights. As a general rule, new PDK modules should be contributed by the foundry, and tool modules by the tool's authors or maintainers.

The Contribution Workflow in 3 Steps
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


Step 2: Create Your New Module File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Using existing modules as a reference, create your new Python file for the flow, PDK, library, or tool you are adding.
Place the file in the correct directory within the ``siliconcompiler/`` source tree:

.. code-block:: text

   siliconcompiler/
   ├── flows/
   │   ├── asicflow.py
   │   └── your_flow.py  <--
   ├── libs/
   │   ├── sky130hd.py
   │   └── your_lib.py   <--
   ├── pdks/
   │   ├── skywater130.py
   │   └── your_pdk.py   <--
   └── tools/
      ├── openroad/
      │   └── openroad.py
      └── your_tool/
         └── your_tool.py  <--

Step 3: Submit Your Contribution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once you have created and tested your module, you are ready to submit it for review.

Please read our `CONTRIBUTING.md <https://github.com/siliconcompiler/siliconcompiler/blob/main/CONTRIBUTING.md>`_ guide on GitHub.
It contains essential information about our pull request process, coding standards, and how to format your commit messages.
