.. _dev_targets:

Targets
===================================

To facilitate encapsulation and reuse of schema parameters related to design targets, SiliconCompiler implements a :meth:`Chip.use()` function which can run scripts that set up common combinations of :class:`siliconcompiler.Flow`, :class:`siliconcompiler.PDK`, :class:`siliconcompiler.Library`, and :class:`siliconcompiler.Checklist` modules.

SiliconCompiler comes with a set of built-in targets, which can be pulled in using the :meth:`.use()` function.
A full list of built-in targets can be found on the :ref:`builtin_targets` page.

The following example calls the :meth:`.use()` function to load the built-in :ref:`freepdk45_demo` target.

.. code-block:: python

  from siliconcompiler.targets import freepdk45_demo

  chip.use(freepdk45_demo)

The following example demonstrates the functional equivalent at the command line:

.. code-block:: bash

   sc hello.v -target "freepdk45_demo"

Targets can also be dedicated to individual projects or use cases, rather than general-purpose processing.
For example, we ship a self-test target with SiliconCompiler, which builds a simple 8-bit counter to verify that everything is installed and configured correctly.

.. code-block:: bash

    sc -target "asic_demo"

Functions
---------

The table below shows the function interfaces for setting up Flow objects.

.. list-table::
   :widths: 10 10 10 10 10 10
   :header-rows: 1

   * - Function
     - Description
     - Arg
     - Returns
     - Used by
     - Required

   * - :ref:`setup() <target_setup>`
     - Target setup function
     - :class:`.Chip` and optional keyword arguments
     - N/A
     - :meth:`.use()`
     - yes

   * - :ref:`make_docs() <target_make_docs>`
     - Doc generator
     - :class:`.Chip`
     - N/A
     - sphinx
     - no


.. _target_setup:

setup(chip)
-----------

All target modules must contain a function called ``setup()``, which takes in a :class:`.Chip` object and can modify the Chip's schema parameters in any way.
It's common for targets to load at least one flow, a PDK and at least one standard cell library if the design is being built as an ASIC.
They can also set up default design parameters and tool options.

SC supports additional levels of encapsulation through PDK, library, and flow modules.
See the :ref:`PDK<dev_pdks>`, :ref:`Library<dev_libraries>`, and :ref:`Flow<dev_flows>` pages to learn more about what is expected to be configured in each of these modules.

Generally, these functions will be called by targets, and then a user will only have to call :meth:`.use()` in their build script.
However, the :meth:`run()` function requires all mandatory flowgraph, pdk, and tool settings to be defined prior to execution, so if a partial target is loaded, additional setup may be required.

An example is shown below.

.. code-block:: python

    from siliconcompiler.pdk import asap7
    from siliconcompiler.libs import asap7sc7p5t
    from siliconcompiler.flows import asicflow

    # Load a PDK
    chip.use(asap7)
    chip.set('option', 'pdk', 'asap7')
    chip.set('option', 'stackup', '10M')

    # Load a library
    chip.use(asap7sc7p5t)
    chip.add('asic', 'logiclib', 'asap7sc7p5t_rvt')

    # Load flow
    chip.use(asicflow)
    chip.set('option', 'flow', 'asicflow')

    ...

.. _target_make_docs:

make_docs(chip)
---------------
The ``make_docs()`` function is used by the projects auto-doc generation.
This function is only needed if the target requires additional inputs to be setup correctly.
The function should include a call to the setup function to populate the schema with all settings as shown below.
The input to this function ``chip`` is a chip object created by the auto-doc generator.

.. code-block:: python

  def make_docs(chip):
    setup(chip)
