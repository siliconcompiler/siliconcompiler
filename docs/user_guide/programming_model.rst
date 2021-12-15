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
