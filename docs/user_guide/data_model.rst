Data model
===================================

The SC project relies on a unified schema to exchange data between tools, foundry PDKs, and the design during the compilation process. The SC schema is designed to hold all information needed to drive hardware compilation from start to finish while successfully tracking all transformations performed in the process.

For a complete description of the SC schema, refer to the :ref:`Schema Reference Manual<Schema>`.

The schema is not designed to be accessed directly, but rather through the :ref:`SC core API<Core API>`. Individual parameter acess is accomplished through the get(), getkeys(), set(), and add() core API methods.

The SC is rouhghy split into the following groups:

* **design**: Parameters associated with the design and compilation process. Examples of user parameters include source files, constraints, supply definitions, clock definitions, and run time compile options.

* **eda**: Parameters used to interface with tools at each step and index of the compilation flow. Examples of eda parameters include, executable name, optional command line flags, thread parallelism, install path,a nd required version number.
  
* **compilation flow**: Parameters that define the compilation flow on a per step and per index basis. A 'flowgraph' dictionary defines the function/tool to be called on a per step basis, the input/output relationship for all steps and indices, and the 'weight'/importance of each metric during the compilation process.
  
* **pdk**:  Parameters associated with a foundry PDK such file paths to design rule modles, spice models, pex models, and APR setup files.
  
* **library**: Parameters associated with a packaged library. Examples of library parameters include filepaths to timing models, layout data, netlists, source files, datasheets, user manuals, testbenches.
   
* **metric**: Parameters that hold all metrics to be tracked during the compilation process. Examples of metrics include errors, warnings, cell area, power, hold violation, setup violations, and design rule violations.
  
* **record**: Parameters that record data captured during the compilation process to track design provencence throughut the design and manufacturing process.
  

Reading and writing the schema to and from disk is done throught the read_manifest() and write_manifest() methods. The write_manifest supports dumping the complete SC schema as a JSON or YAML formatted file. In addition, dumping to TCL and CSV formatted files is supported to interface with legacy EDA tools.


The basic schema structure as implemented in python cane be seen below.


.. code-block:: python

   cfg['design'] = {
        'switch': '-design',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Design Top Module Name',
        'param_help': "design <str>",
        'example': ["cli: -design hello_world",
                    "api: chip.add('design', 'hello_world')"],
        'help': """
        Name of the top level design to compile. Required for all designs with
        more than one module.
        """
    }


Example of a nested SC schema entry. The step variable below can be any legal python sctring except for 'default'.

.. code-block:: python

   cfg['flowgraph'][step]['input'] = {
        'switch': '-flowgraph_input',
        'type': '[str]',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': [],
        'short_help': 'Flowgraph Step Input',
        'param_help': "flowgraph stepvar input <str>",
        'example': ["cli: -flowgraph_input 'cts place'",
                    "api:  chip.set('flowgraph', 'cts', 'input', 'place')"],
        'help': """
        List of input step dependancies for the current step.
        """
    }


Example of json record of SC schema:


.. code-block:: json

  "design": {
        "type": "str",
        "lock": "false",
        "requirement": "optional",
        "defvalue": null,
        "shorthelp": "Design name",
        "value": "oh_add"
    },


