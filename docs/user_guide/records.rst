Records
=======

To support hardware provenance, the SiliconCompiler supports automated tracking of a number of execution and place of origin related parameters. Tracking is off by default in the SiliconCompiler, but can be turned on with the 'track' parameter. ::

  chip.set('track', True)

Records are kept on a per job, step, and index basis. Records must be stored for each task performanded in the flowgraph to ensure unbroken tracability from the beginning to the end in the chain of custody.

In addition automated machine generated tracking inormation, the 'record' dictionaryto a 'package' dictionary for storing human entered per task information.



.. recordgen::
