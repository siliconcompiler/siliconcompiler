Packages
===================================

The SiliconCompiler Schema includes built in suppport for project packaging and distribution through the 'package' dictionary group. Modern proramming languges like javascript and Rust have shown the importance of treating package management as a first class object rather than as an after thought. There is no reason we can't do the same thing in hardware.

To support correct by construction record keeping and package management, identical packaging dictionaries are instantiated in the 'root' dictionary', 'library' dictionary, and 'record' dictionary. To followinig code snippets illustrate how to retrieve these dictionaries from the schemm. ::

 chip.getdict('package')                               # project package settings
 chip.getdict('library',<libname>,'package')           # library package settings
 chip.getdict('record',<job>,<step>,<index>,'package') # record package settings
