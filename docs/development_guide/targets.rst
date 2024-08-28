Targets
===================================

To facilitate encapsulation and reuse of schema parameters related to design targets, SiliconCompiler implements a :meth:`Chip.use()` function which can run scripts that set up common combinations of :class:`siliconcompiler.Flow`, :class:`siliconcompiler.PDK`, :class:`siliconcompiler.Library`, and :class:`siliconcompiler.Checklist` modules.

SiliconCompiler comes with a set of built-in targets, which can be pulled in using the :meth:`.use()` function. A full list of built-in targets can be found on the :ref:`targets` page.

All target modules must contain a function called ``setup()``, which takes in a :class:`siliconcompiler.Chip` object and can modify the Chip's schema parameters in any way. It's common for targets to load at least one flow, a PDK and at least one standard cell library if the design is being built as an ASIC. They can also set up default design parameters and tool options. Targets should also include a ``make_docs()`` function which provides a descriptive docstring and returns a :class:`siliconcompiler.Chip` object with the target loaded.

SC supports additional levels of encapsulation through PDK, library, and flow modules. Unlike targets, these modules are imported as Python libraries and pulled into the :class:`siliconcompiler.Chip` object with the :meth:`.use()` method. See the :ref:`PDK<PDKs>`, :ref:`Library<Libraries>`, and :ref:`Flow<Flows>` User Guide pages to learn more about what is expected to be configured in each of these modules.

Generally, these functions will be called by targets, and then a user will only have to call :meth:`.use()` in their build script.  However, the :meth:`run()` function requires all mandatory flowgraph, pdk, and tool settings to be defined prior to execution, so if a partial target is loaded, additional setup may be required.

The following example calls the :meth:`.use()` function to load the built-in :ref:`freepdk45_demo` target. ::

  chip.use(freepdk45_demo)

The following example demonstrates the functional equivalent at the command line:

.. code-block:: bash

   sc hello.v -target "freepdk45_demo"

Targets can also be dedicated to individual projects or use cases, rather than general-purpose processing. For example, we ship a self-test target with SiliconCompiler, which builds a simple 8-bit counter to verify that everything is installed and configured correctly::

    sc -target "asic_demo"

A full list of built-in demo targets can be found on the :ref:`targets` page.
