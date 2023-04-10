.. Silicon Compiler documentation master file, created by
   sphinx-quickstart on Sun Apr 11 16:42:34 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. This is not the full index page. This will taking to the landing page of docs.silicompiler.com
   There is a index.rst file for each submenu
   The content of this page will largely be ignored in pdf generation
   
##################################################
Welcome to SiliconCompiler's Documentation!
##################################################

.. toctree::
   :maxdepth: 1
   :hidden:
      
   user_guide/index
   Advanced Guide <development_guide/index>
   reference_manual/index

**Useful Links**:
:ref:`Installation <installation>` | `GitHub Repo <https://github.com/siliconcompiler/siliconcompiler>`_ | `File an Issue <https://github.com/siliconcompiler/siliconcompiler/issues>`_

.. grid:: 2

    .. grid-item-card::

        The fastest way to get started after :ref:`installation` is to walk through a simple demo!

        +++

        .. button-ref:: user_guide/quickstart
            :expand:
            :color: secondary
            :click-parent:

            To the Quickstart Guide

    .. grid-item-card::

        A more complete introduction for new users, including fundamentals of SiliconCompiler, examples and tutorials.


        +++

        .. button-ref:: user_guide/index
            :expand:
            :color: secondary
            :click-parent:

            To the Complete User Guide
	    

**How the Documentation is Organized**

.. rst-class:: page-break

- The :ref:`User Guide` is for users who would like to start running SiliconCompiler with their own designs using pre-defined build flows. Useful subsections include :ref:`quickstart` and :ref:`tutorials`
- The :ref:`Advanced Guide <advanced>` is for users who are already familiar with the basics in User Guide and would like to build their own flows
- The :ref:`references` section contains useful lookup information, like :ref:`building_blocks` and :ref:`API references <api_refs>` which are helpful to search through.

**Getting Help**

.. rst-class:: page-break

- Look in the :ref:`glossary` for unfamiliar terms
- Try the :ref:`faq` for common questions
- The :ref:`API references <api_refs>` can be a good resource if you're looking for more information about functions and methods
- And if you can't find what you're looking for, the SiliconCompiler team is happy to help! Please `file an issue <https://github.com/siliconcompiler/siliconcompiler/issues>`_ so we can look into it.
  
