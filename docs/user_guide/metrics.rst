Metrics
===================================

The SiliconCompiler schema includes a :keypath:`metric` dictionary with a large number of parameters to be tracked on a per step and per index basis.

The metric values are used in the :meth:`.minimum()` and :meth:`.maximum()` functions to select the best compilation based on the associated :keypath:`flowgraph, <flow>, <step>, <index>, goal` and :keypath:`flowgraph, <flow>, <step>, <index>, weight` set for the step and index within the flowgraph. For a complete description of the :meth:`.minimum()` function, see the :ref:`Core API` section of the reference manual.

The default 'asicflow' demonstrates a traditional ASIC optimization function, with hard requirements set up for hold, setup, warnings, and errors and soft requirements for area and power. ::

  if metric in ('errors','warnings','drvs','holdwns','setupwns','holdtns','setuptns'):
      chip.set('flowgraph', flow, step, index, 'weight', metric, 1.0)
      chip.set('flowgraph', flow, step, index, metric, 'goal', 0)
  elif metric in ('cellarea', 'peakpower', 'standbypower'):
      chip.set('flowgraph', flow, step, index, 'weight', metric, 1.0)
  else:
      chip.set('flowgraph', flow, step, index, 'weight', metric, 0.001)

In addition to step wise minimization, metrics are used by the :meth:`.summary()` function to present a dashboard view of the compilation results, and can be accessed through :meth:`.set()`/:meth:`.get()` by the user to create custom reporting and optimization loops. The metrics are cleared before each step/index run and then updated by the post_process() function for each tool. For an example of post_process setup, see the
`openroad module. <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/tools/openroad/openroad.py>`_

The following table shows a summary of all the available metrics. For a complete descriptions, refer to the :ref:`Schema<SiliconCompiler Schema>` section of the reference manual.

.. schema_category_summary::
   :category: metric
