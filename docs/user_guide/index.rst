.. _user_guide:

##################################
User Guide
##################################

This guide provides an overview for users.
You will also want to look at API References for details.

.. toctree::
   :caption: Getting Started
   :maxdepth: 1

   What is SiliconCompiler? <what_is_sc>
   Installation <installation>
   Quickstart guide <quickstart>
   Docker guide <docker>
   Running remotely <remote_processing>

.. toctree::
   :caption: Fundamentals
   :maxdepth: 1

   Design & compilation data <data_model>
   Compilation process <execution_model>
   Directory structures <directories>
   Checklists and signoff <checklist>

.. _tutorials:

.. toctree::
   :caption: Tutorials: First runs
   :maxdepth: 1

   Lint your RTL <tutorials/lint>
   Simulate and verify <tutorials/simulate>
   Bringing your own design <tutorials/own_design>
   When a run fails <tutorials/debug>

.. toctree::
   :caption: Tutorials: Real designs
   :maxdepth: 1

   Building your own SoC <tutorials/picorv32_ram>
   Build for an FPGA <tutorials/fpga>
   Hardware design frontends <tutorials/hw_frontends>
   Implementing an IO pad ring <tutorials/padring>
   Instantiating a hardened module in a design <tutorials/hardened>
   Hardening parameterized modules (uniquify) <tutorials/uniquify>
   Calibrating the parasitic estimate (PEX) <tutorials/pex_calibration>

.. toctree::
   :caption: Tutorials: Scaling up
   :maxdepth: 1

   Multi-job flows and automation <tutorials/multi_job_flows>
   Parallel job execution <tutorials/parallel>
   Running on a cluster <tutorials/cluster>
   Running builds in CI <tutorials/ci>
   Authoring a custom flow <tutorials/custom_flow>
   Using commercial tools <tutorials/commercial_tools>
   Using the dashboard <tutorials/dashboard_tutorial>
   Job status emails <tutorials/emails>

.. toctree::
   :caption: Examples
   :maxdepth: 1

   Example designs <examples>

.. toctree::
   :caption: Appendix
   :maxdepth: 1

   glossary
   Frequently asked questions <faq>
   How do I…? <howto>
   Migrating from the Chip API <migration>