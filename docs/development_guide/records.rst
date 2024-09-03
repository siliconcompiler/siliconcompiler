Records
=======

To support hardware provenance, SiliconCompiler supports automated tracking of a number of execution and place of origin related parameters.
SiliconCompiler will record the SiliconCompiler version, tool version and options, and task start and end times by default.
Additional tracking is off by default in SiliconCompiler, but can be turned on with the :keypath:`option,track` parameter. ::

  chip.set('option', 'track', True)

This will enable tracking of the user and machine information, which may be considered sensitive, so please use caution when enabling all tracking.

Records are kept on a per step, and index basis.
Records must be stored for each task in the flowgraph to ensure unbroken traceability from the beginning to the end in the chain of custody.

.. schema_category_summary::
  :category: record
