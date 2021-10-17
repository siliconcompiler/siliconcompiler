Tool configuration
===================================

Before tools can be used within SC they must first be set up appropriately. At a
minimum, the name of the executable and any mandatory options must be defined. Tools
for hardware generally fall into one of two groups: 1.) tools that are configured
through a TCL program (eg. openroad, yosys), and 2.) tools configured with a large
number of command line switches (e.g. verilator).

A tool is configured on a per step and per index basis within the 'eda' dictionary
of the SC schema independently of all other parameters.

The code snippet below shows the setup for the openroad tool controlled by a TCL
based reference flow. ::

  chip.set('eda', 'openroad', 'apr', '0', 'exe', 'openroad')
  chip.set('eda', 'openroad', 'apr', '0', 'refdir', '/usr/local/share/openroad')
  chip.set('eda', 'openroad', 'apr', '0', 'script', 'sc_apr.tcl')


In this case, the data handoff from the SC schema to openroad is handled by using the
write_manifest() function to write out a TCL dictionary that gets read in by sc_apr.tcl.
It is then the responsibility of the person writing the TCL to correctly leverage the SC parameters
to interface with the native API. The code below shows an excerpt of the SC schema written
to file as a TCL dictionary. All communication between SC and underlying tools must be done through
parameters recorded in the SC schema.

dict set sc_cfg asic targetlib [list  NangateOpenCellLibrary ]
dict set sc_cfg asic maxfanout [list  64 ]
dict set sc_cfg design [list  gcd ]
dict set sc_cfg constraint [list gcd.sdc ]
dict set sc_cfg source [list gcd.v ]


See the openroad tool module for more information: `openroad.py <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/tools/openroad/openroad.py>`_

For a command line tool like verilator, the data exchange from SC to the tool is
handled by mapping the SC schema parameters to the names and behavior of the tool
switches.::

  chip.set('eda', 'verilator', 'lint', '0', 'exe', 'verilator')
  chip.set('eda', 'verilator', 'lint', '0', 'option', 'cmdline', ['-sv','--lint-only'])
  for item in chip.get('source'):
      chip.add('eda', 'verilator', 'lint', '0', 'option', 'cmdline', item)

See the verilator tool module fore more information: `verilator.py <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/tools/verilator/verilator.py>`_

In addition, a number of optional parameters can be set up to control tool execution:

  * **option**:  string options to pass tool
  * **vswitch**: command line switch to used to query executable version number
  * **version**: required tool version number
  * **threads**: number of threads to use for index execution
  * **path**: Filepath to executable
  * **license**: License server address
  * **req**: SC parameters required for correct operation
  * **input**: List inf tool input fiiles required
  * **output**: List of tool output files produced

See the schema manual for a full description of all 'eda' parameters supported by the SC schema.
