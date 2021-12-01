Installation
===================================


Python Setup
-------------

Before installing the SiliconCompiler package you will need to set up a Python environment. Currently Python 3-6-3.10 is supported.

Ubuntu
^^^^^^^

Open up a terminal and enter the following command sequence.

.. code-block:: bash

    python3 --version                                      # check for Python 3.6 - 3.10
    sudo apt update                                        # update package information
    sudo apt install python3-dev python3-pip python3-venv  # install dependencies
    python3 -m venv --system-site-packages ./venv          # create a virtual env
    source ./venv/bin/activate                             # active virtual env (bash/zsh)

macOS
^^^^^
Open up a terminal and enter the following command sequence.

.. code-block:: bash

   /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
   export PATH="/usr/local/opt/python/libexec/bin:$PATH"
   brew update
   brew install python
   python3 --version                                      # check for Python 3.6 - 3.10
   python3 -m venv --system-site-packages ./venv          # create a virtual env
   source ./venv/bin/activate                             # active virtual env

Windows
^^^^^^^

Install the latest Python package from `Python.org <https://www.python.org/downloads>`_ using the Windows installer. Open up a Windows shell by:

1. Pressing the 'Windows' key
2. Typing 'PowerShell' or 'cmd', and pressing enter.

From the command shell, enter the following sequence to create and activate a virtual environment.

.. code-block:: doscon

  python -m venv --system-site-packages .\venv
  .\venv\Scripts\activate

SiliconCompiler Setup
---------------------

Once the Python environment has been set up, SiliconCompiler can be installed directly from from PyPI using pip. The instructions are the same for Windows, Linux, and macOS.

.. code-block:: bash

   (venv) pip install --upgrade pip                # upgrade pip in virtual env
   (venv) pip list                                 # show installed packages in venv
   (venv) pip install --upgrade siliconcompiler    # install SiliconCompiler in venv
   (venv) python -m pip show siliconcompiler       # will display  SiliconCompiler package information
   (venv) python -c "import siliconcompiler;chip = siliconcompiler.Chip();print(chip.get('scversion'))"

The output should be the expected version number, similar to below:

.. parsed-literal::

   \ |release|

To exit the Python virtual environment, type 'deactivate' and hit enter. More information about the Python virtual environment can be found in the `Python 'venv' documentation <https://docs.python.org/3/library/venv.html>`_.

You can also install SiliconCompiler from the latest `SiliconCompiler GitHub Repository <https://github.com/siliconcompiler/siliconcompiler>`_. This option is currently
only supported on Linux/MacOS platforms.

.. code-block:: bash

   git clone https://github.com/siliconcompiler/siliconcompiler
   cd siliconcompiler
   pip install -r requirements.txt
   python -m pip install -e .


Tool Setup
------------

The SiliconCompiler project depends on a number of external tools (synthesis, placement, routing, etc). Installation instructions for these tools are best written by the original authors so we will not include them here. For convenience, links to installation documentation for all supported tools can be found in the tools directory of the reference manual :ref:`here<Tools directory>`.

The tool installation process can be skipped entirely by leveraging the :ref:`Remote Processing<Remote processing>` workflow to access a server with pre-installed tools.

To view IC layout files (DEF, GDSII) we recommend installing the open source multi-platform 'klayout' viewer (available for Windows, Linux, and macOS). Installation instructions for klayout can be found `HERE <https://www.klayout.de/build.html>`_.
