Quickstart guide
===================================

In this quickstart guide, we will illustrate core concepts of the project by
translating a simple Verilog based design into a GDSII IC layout database using
the :ref:`freepdk45` virtual PDK.

Design
-------
As a case study we will use the simple "heartbeat" design shown below. The heartbeat
module is a free running counter that creates a single clock cycle pulse
("heartbeat") every time the counter rolls over. Copy paste the code into your
favorite text editor (vim, emacs, atom, notepad, etc) and save it to disk as
"heartbeat.v".

.. literalinclude:: examples/heartbeat/heartbeat.v
   :language: verilog

To constrain the design,  we need to also define a constraints file. Save the
following snippet as "heartbeat.sdc". If you are not familiar with timing constraints,
don't worry about it for now.

.. literalinclude:: examples/heartbeat/heartbeat.sdc

Setup
-----------------

To address the complex process of modern hardware compilation, the SiliconCompiler
schema includes over 300 parameters. For this simple example, we only need a small
fraction of these parameters. The code snippet below illustrates the use of the
:ref:`Python API<Core API>` to set up and run a compilation. To run the example,
copy paste the code into your text editor and save it to disk as "heartbeat.py".

.. literalinclude:: examples/heartbeat/heartbeat.py

Much of the complexity of setting up a hardware compilation flow is abstracted away
from the user through the :meth:`.load_target` function which sets up a large number of PDK,
flow, and tool parameters based on a target setup module. To understand the
complete target configuration, see the :ref:`Flows Directory`, :ref:`PDK
Directory`, and :ref:`Targets Directory` sections of the reference manual and read the source code for
`asicflow <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/flows/asicflow.py>`_,
`freepdk45 <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/pdks/freepdk45.py>`_, and
`freepdk45_demo <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/targets/freepdk45_demo.py>`_.

.. note::

   The example assumes that :ref:`Surelog <surelog>`, :ref:`Yosys <yosys>`, :ref:`OpenROAD <openroad>`, and :ref:`KLayout <klayout>` are all correctly
   installed. Links to individual tool installation instructions and platform
   limitations can be found in the :ref:`Tools directory`.

   It also requires downloading and pointing SC to :ref:`FreePDK45 <freepdk45>`, which is bundled
   with the SiliconCompiler repo. To install, clone the repo and set up an
   environment variable ``SCPATH`` pointing at the ``siliconcompiler/``
   directory inside of it:

   .. parsed-literal::

     git clone -b v\ |release| https://github.com/siliconcompiler/siliconcompiler
     export SCPATH=$PWD/siliconcompiler/siliconcompiler

   To simplify tool/PDK installation and job scheduling, SiliconCompiler supports a
   "-remote" option, which directs the compiler to send all steps to a remote
   server for processing. The "-remote" option relies on a credentials file
   located at ``~/.sc/credentials`` on Linux or macOS, or
   at ``C:\\Users\\USERNAME\\.sc\\credentials`` on Windows, which is generated using :ref:`sc-configure`.

   Remote processing option is enabled by setting the :keypath:`option,remote`
   parameter to True. ::

     chip.set('option', 'remote', True)

Compilation
------------

To compile the example, simply execute the 'heartbeat.py' program from
your Python virtual environment.

.. code-block:: bash

   python heartbeat.py

Alternatively, the simple heartbeat example can be run calling the
SiliconCompiler :ref:`sc` program directly from the command line.

.. literalinclude:: examples/heartbeat/run.sh
   :language: bash

If the compilation was successful, you should see a flood of tool specific
information printed to the screen followed by a summary resembling the summary
shown below. Set the :keypath:`option,quiet` parameter to True of you want to
redirect this information to a log file. By default, all SiliconCompiler outputs
are placed in the ``build/<design>`` directory.

::

   SUMMARY:

   design : heartbeat
   params : None
   jobdir : <...>
   foundry : virtual
   process : freepdk45
   targetlibs : nangate45

                     import0        syn0      floorplan0      physyn0        place0         cts0         route0         dfm0        export0      export1
   errors               0            0             0             0             0             0             0             0             0            0
   warnings             1            75            16            0             0             2             7             18            1            0
   drvs                ---          ---            0             0             0             0             0             0            ---          ---
   unconstrained       ---          ---            1             1             1             1             1             1            ---          ---
   cellarea            ---          67.0         76.076        76.076         79.8         85.386        85.386        85.386         ---          ---
   totalarea           ---          ---         614.992       614.992       614.992       614.992       614.992       614.992         ---          ---
   utilization         ---          ---         0.123702      0.123702      0.129758      0.138841      0.138841      0.138841        ---          ---
   peakpower           ---          ---      6.93981e-06   6.93981e-06   7.74635e-06   1.54335e-05   1.53541e-05   1.47438e-05        ---          ---
   leakagepower        ---          ---      1.18215e-06   1.18215e-06   1.38328e-06   1.64165e-06   1.64165e-06   1.64165e-06        ---          ---
   holdpaths           ---          ---            0             0             0             0             0             0            ---          ---
   setuppaths          ---          ---            0             0             0             0             0             0            ---          ---
   holdslack           ---          ---        0.0575973     0.0575973     0.0656163     0.0665752     0.0670199      0.06596         ---          ---
   holdwns             ---          ---           0.0           0.0           0.0           0.0           0.0           0.0           ---          ---
   holdtns             ---          ---           0.0           0.0           0.0           0.0           0.0           0.0           ---          ---
   setupslack          ---          ---         9.68597       9.68597       9.67944       9.67789       9.67996       9.68388         ---          ---
   setupwns            ---          ---           0.0           0.0           0.0           0.0           0.0           0.0           ---          ---
   setuptns            ---          ---           0.0           0.0           0.0           0.0           0.0           0.0           ---          ---
   macros              ---          ---            0             0             0             0             0             0            ---          ---
   cells               ---           24            58            58            58            61            61            61           ---          ---
   registers           ---           9             9             9             9             9             9             9            ---          ---
   buffers             ---          ---            1             1             1             4             4             4            ---          ---
   pins                ---          ---            3             3             3             3             3             3            ---          ---
   nets                ---          ---            37            37            37            40            40            40           ---          ---
   vias                ---          ---           ---           ---           ---           ---           185           ---           ---          ---
   wirelength          ---          ---           ---           ---           ---           ---          212.0          ---           ---          ---
   memory          27222016.0   30126080.0    95330304.0    89309184.0   127594496.0   102363136.0   708177920.0    97525760.0   395513856.0   81055744.0
   exetime             0.21         0.51          0.41          0.31          0.51          1.42          2.36          0.31          1.24         0.41
   tasktime            0.35         1.4           0.83          0.6           0.8           1.71          2.69          0.66          2.2          0.74


View layout
------------

If you have Klayout installed, you can view the output from the :ref:`asicflow` by
calling :meth:`chip.show() <.show>` from your Python program or by calling the
:ref:`sc-show` program from the command line as shown below:

.. code-block:: bash

   (venv) sc-show -design heartbeat

.. image:: _images/heartbeat.png
