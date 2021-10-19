Metrics
===================================

The SiliconCompiler schema includes a a 'metric' dictionary with a large number of parameters
to be tracked on a per step and per index basis. Each type of 'metric' has a 'goal' and a 'real'
value. The 'goal' value is used to track the expected/intended result while the 'real'
value is used by the SC run() infrastructure to record results captured during compilation.

The 'real' metrics  values are used in the step_minimum() and step_maximum() functions to
select the best compilation based on the metrics 'goal' specified and the metric 'weight set for
the step and index within the 'flowgraph. For a complete description of the step_minimum()
function, see the core API reference manual.

The default 'asicflow' demonstrates a traditional ASIC optimziation function, with hard
requirements set up for hold, setup, warnings, and errors and soft requirements for area and power.::

  if metric in ('errors','warnings','drvs','holdwns','setupwns','holdtns','setuptns'):
      chip.set('flowgraph', step, index, 'weight', metric, 1.0)
      chip.set('metric', step, index, metric, 'goal', 0)
  elif metric in ('cellarea', 'peakpower', 'standbypower'):
      chip.set('flowgraph', step, index, 'weight', metric, 1.0)
  else:
      chip.set('flowgraph', step, index, 'weight', metric, 0.001)

In addition to step wise minimization, metrics are used by the summary() function to present a
dashboard view of the compilation results, and can be accessed through set()/get() by the user
to create custom reporting and optimization loops.

The 'real' metrics are cleared before each step/index run and then updated by the post_process()
function for each tool. For an example of post_process setup, see the
`openroad module. <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/tools/openroad/openroad.py>`_

The following table shows a summary of all the available metrics. For a complete descriptions,
refer to the :ref:`Schema Reference Manual<Schema>`.

**Metrics Summary**

.. metricgen::
