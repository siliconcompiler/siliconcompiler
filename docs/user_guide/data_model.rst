Data model
===================================

* schema
* python dictionary
* json
* get/set/add
* data types (float/int/list)
* syntax


The basi structure in pythin is seen below.


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


 Using the writecfg function, the Python dictionary can be stored to disk as a JSON, YAML, or TCl file. The 'design' record in json format is shown below.

.. code-block:: json

  "design": {
        "type": "str",
        "lock": "false",
        "requirement": "optional",
        "defvalue": null,
        "short_help": "Design Top Module Name",
        "param_help": "design <str>",
        "value": "gcd"
    },
