Programming model
=================

The SiliconCompiler project includes a Python API and programming model to facilitate development
of advanced hardware compilation flows. The basic programming model includes the following ordered steps.

Object Creation
----------------

Compilation is based on a single chip object that follows the design from start to finish. A chip object is created by calling the :ref:`Core API` class constructor. ::

  import siliconcompiler

  chip = siliconcompiler.Chip('topmodule')


Setup
----------------

Once the chip object has been created, functions and data are all contained within that object. A compilation is set up by accessing methods and parameters from the chip object. Parameters can generally be configured in any order during setup. The exceptions are :keypath:`arg,flow` and :keypath:`arg,pdk` parameters, which must be set before calling :meth:`chip.load_flow() <.load_flow>` or :meth:`chip.load_pdk() <.load_pdk>`, respectively.

The snippet of code below shows the basic principles. ::

  chip.set('input', 'verilog', '<file>.v')


Run
------------

Once all the parameters have been setup, compilation is done by a single atomic call to :meth:`.run()`. ::

  chip.run()


Inspection
------------

Once the compilation has completed, chip object can be queried and another :meth:`.run()` can be called. ::

  chip.summary()
  print(chip.get('metric', 'syn', '0', 'cellarea')
  #..do something else

For complete information, see the :ref:`Core API` section of the reference manual.
