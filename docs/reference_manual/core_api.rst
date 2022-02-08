Core API
----------

This chapter describes all public methods in the SiliconCompiler core Python API. Refer to the User Guide for architecture concepts and the :ref:`glossary` for terminology and keyword definitions.

.. currentmodule:: siliconcompiler

**Schema access:**

.. autosummary::
    :nosignatures:

    ~siliconcompiler.core.Chip.set
    ~siliconcompiler.core.Chip.add
    ~siliconcompiler.core.Chip.get
    ~siliconcompiler.core.Chip.getkeys
    ~siliconcompiler.core.Chip.getdict
    ~siliconcompiler.core.Chip.valid
    ~siliconcompiler.core.Chip.help

**Flowgraph execution:**

.. autosummary::
    :nosignatures:

    ~siliconcompiler.core.Chip.run
    ~siliconcompiler.core.Chip.node
    ~siliconcompiler.core.Chip.edge
    ~siliconcompiler.core.Chip.join
    ~siliconcompiler.core.Chip.minimum
    ~siliconcompiler.core.Chip.maximum
    ~siliconcompiler.core.Chip.mux
    ~siliconcompiler.core.Chip.verify

**Utility functions:**

.. autosummary::
    :nosignatures:

    ~siliconcompiler.core.Chip.archive
    ~siliconcompiler.core.Chip.audit_manifest
    ~siliconcompiler.core.Chip.calc_area
    ~siliconcompiler.core.Chip.calc_yield
    ~siliconcompiler.core.Chip.calc_dpw
    ~siliconcompiler.core.Chip.check_checklist
    ~siliconcompiler.core.Chip.check_manifest
    ~siliconcompiler.core.Chip.check_logfile
    ~siliconcompiler.core.Chip.clock
    ~siliconcompiler.core.Chip.create_cmdline
    ~siliconcompiler.core.Chip.find_files
    ~siliconcompiler.core.Chip.find_function
    ~siliconcompiler.core.Chip.find_result
    ~siliconcompiler.core.Chip.grep
    ~siliconcompiler.core.Chip.hash_files
    ~siliconcompiler.core.Chip.list_metrics
    ~siliconcompiler.core.Chip.list_steps
    ~siliconcompiler.core.Chip.load_flow
    ~siliconcompiler.core.Chip.load_lib
    ~siliconcompiler.core.Chip.load_pdk
    ~siliconcompiler.core.Chip.load_target
    ~siliconcompiler.core.Chip.merge_manifest
    ~siliconcompiler.core.Chip.package
    ~siliconcompiler.core.Chip.publish
    ~siliconcompiler.core.Chip.read_file
    ~siliconcompiler.core.Chip.read_manifest
    ~siliconcompiler.core.Chip.show
    ~siliconcompiler.core.Chip.summary
    ~siliconcompiler.core.Chip.write_manifest
    ~siliconcompiler.core.Chip.write_flowgraph

.. automodule:: siliconcompiler.core
    :members:
