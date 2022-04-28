Records
=======

To support hardware provenance, the SiliconCompiler supports automated tracking of a number of execution and place of origin related parameters. Tracking is off by default in the SiliconCompiler, but can be turned on with the :keypath:`track` parameter. ::

  chip.set('track', True)

Records are kept on a per job, step, and index basis. Records must be stored for each task in the flowgraph to ensure unbroken traceability from the beginning to the end in the chain of custody.

In addition to automated machine generated tracking information, the 'record' dictionary includes a 'package' dictionary for storing human entered per task information.

.. recordgen::
