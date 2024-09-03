###############################
Multi-Job Flows and Automation
###############################

As an extension of :ref:`compilation process`, which describes setting up only one job, you can link together different jobs and Python manipulation code for your own purposes.

.. rst-class:: page-break

At the end of each :meth:`.run()` call, the current in-memory job schema entries are copied into a job history dictionary for reference later.
The user can access these to create more complex, non-linear flows that take into account run history and gradients.
The code snippet below shows a minimal sequence leveraging the multi-job feature.::

  chip.run()
  chip.set('option', 'jobname', 'newname')
  chip.set('some parameter..')
  chip.run()

Complex iterative compilation flows can be created with Python programs that:

1.
Calls run() multiple times using a different jobname, and
2.
Leverages Python logic to query per job metrics to control the compilation flow decision, for automation

.. image:: ../../_images/complex.png

.. note::

   **[In Progress]** This tutorial requires a more detailed step-by-step guide.


