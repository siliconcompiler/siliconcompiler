Core API
----------

This is the class and function reference for SiliconCompiler core API. Please refer
to the :ref:`user guide <user_guide>` for architecture concepts, as the class and
function specifications may not be enough to give full guidelines on their uses.
For reference on concepts repeated across the API, see :ref:`glossary`.

.. currentmodule:: siliconcompiler

**Schema access:**

.. autosummary::
    :nosignatures:

    ~siliconcompiler.core.Chip.set
    ~siliconcompiler.core.Chip.get
    ~siliconcompiler.core.Chip.add
    ~siliconcompiler.core.Chip.getkeys
    ~siliconcompiler.core.Chip.getdict


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

    ~siliconcompiler.core.Chip.audit_manifest
    ~siliconcompiler.core.Chip.calc_yield
    ~siliconcompiler.core.Chip.calc_dpw
    ~siliconcompiler.core.Chip.calc_diecost
    ~siliconcompiler.core.Chip.check_manifest
    ~siliconcompiler.core.Chip.clock
    ~siliconcompiler.core.Chip.create_commandline
    ~siliconcompiler.core.Chip.create_env
    ~siliconcompiler.core.Chip.find_file
    ~siliconcompiler.core.Chip.find_function
    ~siliconcompiler.core.Chip.find_result
    ~siliconcompiler.core.Chip.hash_files
    ~siliconcompiler.core.Chip.help
    ~siliconcompiler.core.Chip.list_metrics
    ~siliconcompiler.core.Chip.list_outputs
    ~siliconcompiler.core.Chip.list_steps
    ~siliconcompiler.core.Chip.merge_manifest
    ~siliconcompiler.core.Chip.read_manifest
    ~siliconcompiler.core.Chip.show
    ~siliconcompiler.core.Chip.summary
    ~siliconcompiler.core.Chip.target
    ~siliconcompiler.core.Chip.write_manifest
    ~siliconcompiler.core.Chip.write_flowgraph

.. automodule:: siliconcompiler.core
    :members:
