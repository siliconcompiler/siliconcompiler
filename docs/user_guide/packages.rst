Packages
===================================

The SiliconCompiler Schema includes built in support for project packaging and distribution through the 'package' dictionary group. Modern programming languages like JavaScript and Rust have shown the importance of treating package management as a first class object rather than as an after thought. There is no reason we can't do the same thing in hardware.

To support correct by construction record keeping and package management, identical packaging dictionaries are instantiated in the 'root' dictionary, 'library' dictionary, and 'record' dictionary. Refer to the :ref:`Schema <SiliconCompiler Schema>` section of the reference manual for more information. The table below includes a summary of all package parameters.

To following code snippets illustrate how to retrieve these dictionaries from the schema. ::

 chip.getdict('package')                               # project package settings
 chip.getdict('library',<libname>,'package')           # library package settings
 chip.getdict('record',<job>,<step>,<index>,'package') # record package settings


The table below includes a summary of all package parameters.

.. packagegen::
