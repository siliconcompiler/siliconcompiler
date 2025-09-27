###############################
Multi-Job Flows and Automation
###############################

As an extension of :ref:`compilation process <execution_model>`, which describes setting up only one job, you can link together different jobs and Python manipulation code for your own purposes.

At the end of each :meth:`.Project.run()` call, the current in-memory job schema entries are copied into a job history dictionary for reference later.
The user can access these to create more complex, non-linear flows that take into account run history and gradients.
The code snippet below shows a minimal sequence leveraging the multi-job feature.::

  project.run()
  project.set('option', 'jobname', 'newname')
  project.set('some parameter..')
  project.run()

Complex iterative compilation flows can be created with Python programs that:

1. Calls :meth:`.Project.run()` multiple times using a different jobname, and
2. Leverages Python logic to query per job metrics to control the compilation flow decision, for automation

.. image:: ../../_images/complex.png

.. note::

   **[In Progress]** This tutorial requires a more detailed step-by-step guide.


