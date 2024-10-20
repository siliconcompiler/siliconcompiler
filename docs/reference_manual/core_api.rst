Core API
----------

This chapter describes all public methods in the SiliconCompiler core Python API.
Refer to the User Guide for architecture concepts and the :ref:`glossary` for terminology and keyword definitions.

.. currentmodule:: siliconcompiler

**Schema access:**

.. autosummary::
    :nosignatures:

    ~Chip.set
    ~Chip.add
    ~Chip.get
    ~Chip.getkeys
    ~Chip.getdict
    ~Chip.valid
    ~Chip.help
    ~Chip.unset
    ~Chip.remove

**Flowgraph execution:**

.. autosummary::
    :nosignatures:

    ~Chip.run
    ~Chip.node
    ~Chip.edge
    ~Chip.remove_node

**Utility functions:**

.. autosummary::
    :nosignatures:

    ~Chip.archive
    ~Chip.check_checklist
    ~Chip.check_manifest
    ~Chip.clock
    ~Chip.collect
    ~Chip.create_cmdline
    ~Chip.dashboard
    ~Chip.find_files
    ~Chip.find_result
    ~Chip.getworkdir
    ~Chip.hash_files
    ~Chip.read_manifest
    ~Chip.show
    ~Chip.summary
    ~Chip.use
    ~Chip.write_manifest
    ~Chip.write_flowgraph
    ~utils.asic.calc_area
    ~utils.asic.calc_yield
    ~utils.asic.calc_dpw
    ~utils.grep

**Tool driver utility functions:**

.. autosummary::
    :nosignatures:

    ~tools._common.get_libraries
    ~tools._common.add_require_input
    ~tools._common.get_input_files
    ~tools._common.add_frontend_requires
    ~tools._common.get_frontend_options

.. automodule:: siliconcompiler
    :members:

.. automodule:: siliconcompiler.tools._common
    :members:

.. automodule:: siliconcompiler.utils
    :members:

.. automodule:: siliconcompiler.utils.asic
    :members:
