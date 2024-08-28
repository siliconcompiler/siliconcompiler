Core API
----------

This chapter describes all public methods in the SiliconCompiler core Python API. Refer to the User Guide for architecture concepts and the :ref:`glossary` for terminology and keyword definitions.

.. currentmodule:: siliconcompiler

**Schema access:**

.. autosummary::
    :nosignatures:

    ~siliconcompiler.Chip.set
    ~siliconcompiler.Chip.add
    ~siliconcompiler.Chip.get
    ~siliconcompiler.Chip.getkeys
    ~siliconcompiler.Chip.getdict
    ~siliconcompiler.Chip.valid
    ~siliconcompiler.Chip.help
    ~siliconcompiler.Chip.unset
    ~siliconcompiler.Chip.remove

**Flowgraph execution:**

.. autosummary::
    :nosignatures:

    ~siliconcompiler.Chip.run
    ~siliconcompiler.Chip.node
    ~siliconcompiler.Chip.edge
    ~siliconcompiler.Chip.remove_node

**Utility functions:**

.. autosummary::
    :nosignatures:

    ~siliconcompiler.Chip.archive
    ~siliconcompiler.Chip.check_checklist
    ~siliconcompiler.Chip.check_manifest
    ~siliconcompiler.Chip.clock
    ~siliconcompiler.Chip.collect
    ~siliconcompiler.Chip.create_cmdline
    ~siliconcompiler.Chip.find_files
    ~siliconcompiler.Chip.find_result
    ~siliconcompiler.Chip.getworkdir
    ~siliconcompiler.Chip.hash_files
    ~siliconcompiler.Chip.read_manifest
    ~siliconcompiler.Chip.show
    ~siliconcompiler.Chip.summary
    ~siliconcompiler.Chip.use
    ~siliconcompiler.Chip.write_manifest
    ~siliconcompiler.Chip.write_flowgraph
    ~siliconcompiler.utils.asic.calc_area
    ~siliconcompiler.utils.asic.calc_yield
    ~siliconcompiler.utils.asic.calc_dpw
    ~siliconcompiler.utils.grep

**Tool driver utility functions:**

.. autosummary::
    :nosignatures:

    ~siliconcompiler.tools._common.get_libraries
    ~siliconcompiler.tools._common.add_require_input
    ~siliconcompiler.tools._common.get_input_files
    ~siliconcompiler.tools._common.add_frontend_requires
    ~siliconcompiler.tools._common.get_frontend_options

.. automodule:: siliconcompiler
    :members:

.. automodule:: siliconcompiler.use
    :members:

.. automodule:: siliconcompiler.tools._common
    :members:

.. automodule:: siliconcompiler.utils
    :members:

.. automodule:: siliconcompiler.utils.asic
    :members:
