.. _advanced_guide:

###############
Advanced Guide
###############

The following sections describe how to build your own custom modules in SiliconCompiler so that you can customize your own flow.
If you don't plan to build your own modules and just want to use SiliconCompiler with pre-defined modules, see the :ref:`Reference Manual <reference_manual>`.

If you intend to contribute your module back to the project, two pages are worth
reading first: :ref:`How to Contribute a New Module <module_placement>` covers
where a module belongs -- in this repository, in ``lambdapdk``, or in a package of
your own -- and `CONTRIBUTING.md
<https://github.com/siliconcompiler/siliconcompiler/blob/main/CONTRIBUTING.md>`_
covers the process: branches, tests, the four lint gates every pull request is
checked against, and how to build the docs.


.. toctree::
   :caption: Building modules
   :maxdepth: 3

   targets
   flows
   tools
   pdks
   libraries
   external_libraries


.. toctree::
   :caption: Appendix
   :maxdepth: 3

   contribution
   metrics
   records
   remote_processing
   options
