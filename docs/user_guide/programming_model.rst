Programming model
=================

The SiliconCompiler project includes a Python API and programming model to facilitate development
of advanced hardware compilation flows. The basic programming model includes the following ordered steps.

Object Creation
----------------

Compilation is based on a single chip object that follows the design from start to finish. A chip object is created by calling the :ref:`Core API` class constructor. ::

  import siliconcompiler

  chip = siliconcompiler.Chip()


Setup
----------------

Once the chip object has been created, functions and data are all contained within that object. A compilation is set up by accessing methods and parameters from the chip object. Parameters can generally be configured in any order during setup. The exceptions are flowarg and techarg parameters, which must be set before calling chip.target().

The snippet of code below shows the basic principles. ::

  chip.set('design', <name>)


Run
------------

Once all the parameters have been setup, compilation is done by a single atomic call to run(). ::

  chip.run()


Inspection
------------

Once the compilation has completed, chip object can be queried and another run() can be called. ::

  chip.summary()
  print(chip.get('metric', 'syn', '0', 'cellarea', 'real')
  #..do something else


For complete information, see the :ref:`Core API` section of the reference manual. A summary of all available functions is shown below.

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

    ~siliconcompiler.core.Chip.audit_manifest
    ~siliconcompiler.core.Chip.calc_area
    ~siliconcompiler.core.Chip.calc_yield
    ~siliconcompiler.core.Chip.calc_dpw
    ~siliconcompiler.core.Chip.check_manifest
    ~siliconcompiler.core.Chip.clock
    ~siliconcompiler.core.Chip.create_cmdline
    ~siliconcompiler.core.Chip.create_env
    ~siliconcompiler.core.Chip.find_files
    ~siliconcompiler.core.Chip.find_function
    ~siliconcompiler.core.Chip.find_result
    ~siliconcompiler.core.Chip.hash_files
    ~siliconcompiler.core.Chip.list_metrics
    ~siliconcompiler.core.Chip.list_steps
    ~siliconcompiler.core.Chip.merge_manifest
    ~siliconcompiler.core.Chip.package
    ~siliconcompiler.core.Chip.read_manifest
    ~siliconcompiler.core.Chip.show
    ~siliconcompiler.core.Chip.summary
    ~siliconcompiler.core.Chip.target
    ~siliconcompiler.core.Chip.write_manifest
    ~siliconcompiler.core.Chip.write_flowgraph
