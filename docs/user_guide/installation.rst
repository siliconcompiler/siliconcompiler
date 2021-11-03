Installation
===================================

Before installing SiliconCompiler you will need to set up a Python virtual
environment for your platform. SiliconCompiler requires Python 3.6 - 3.10.

Ubuntu
-------
Open up a terminal and enter the following command sequence.

.. code-block:: bash

    python3 --version                                      # check for Python 3.6 - 3.10
    sudo apt update                                        # update package information
    sudo apt install python3-dev python3-pip python3-venv  # install dependencies
    python3 -m venv --system-site-packages ./venv          # create a virtual env
    source ./venv/bin/activate                             # active virtual env (bash/zsh)

macOS
-----
Open up a terminal and enter the following command sequence.

.. code-block:: bash

   /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
   export PATH="/usr/local/opt/python/libexec/bin:$PATH"
   brew update
   brew install python
   python3 --version                                      # check for Python 3.6 - 3.10
   python3 -m venv --system-site-packages ./venv          # create a virtual env
   source ./venv/bin/activate                             # active virtual env (bash/zsh)

Windows
-------

Install the latest Python package directly from `Python.org <https://www.python.org/downloads>`_ using the Windows installer. Open up a Windows shell by pressing the 'Windows' key,  typing 'PowerShell' or 'cmd', and pressing enter. Once inside the shell, enter the following sequence to activate a virtual environment.

.. code-block:: doscon

  python -m venv --system-site-packages .\venv
  .\venv\Scripts\activate

Installation from PyPI
-----------------------

To install SiliconCompiler within your Python virtual working environment, activate the session
environment (see above) based on your platform and enter the followinq commands.

.. code-block:: bash

   pip install --upgrade pip                # upgrade pip in virtual env
   pip list                                 # show installed packages in venv
   pip install --upgrade siliconcompiler    # install siliconcompiler in venv
   python -m pip show siliconcompiler       # will display SC package information
   python -c "import siliconcompiler;chip = siliconcompiler.Chip();print(chip.get('scversion'))"
   deactivate                               # deactivate the virtual environment

The output should be the version number you expect to see, similar to below:

.. parsed-literal::

   \ |release|


Installation from source
------------------------

Installing directly from the repository sources is supported for Linux/MacOS platforms.

.. code-block:: bash

   git clone https://github.com/siliconcompiler/siliconcompiler
   cd siliconcompiler
   pip install -r requirements.txt
   python -m pip install -e .

Python dependencies
-------------------

SiliconCompiler relies on the following Python packages. Note that these will be
installed automatically when installing SC via pip, so there should be no need
to install them manually.

.. requirements::

Pre-requisites
---------------

SiliconCompiler relies on a number of external tools and projects. Supporting the multi-platform
installation of those tools is beyond the scope of the project, but we have included easy access
links to installation instructions in the reference manual :ref:`tools<Tools directory>` section.

Note that you can bypass the installation process using the remote processing workflow if you have
access to a server where the tools are pre-installed. See the :ref:`Quickstart guide<Quickstart guide>` for more details.
