Installation
===================================


Python
------

Before installing the SiliconCompiler package you will need to set up a Python environment. Currently Python 3-6-3.10 is supported.

Ubuntu (>=18.04)
^^^^^^^^^^^^^^^^
Open up a terminal and enter the following command sequence.

.. code-block:: bash

    python3 --version                                      # check for Python 3.6 - 3.10
    sudo apt update                                        # update package information
    sudo apt install python3-dev python3-pip python3-venv  # install dependencies
    python3 -m venv --system-site-packages ./venv          # create a virtual env
    source ./venv/bin/activate                             # active virtual env (bash/zsh)

RHEL (>=RHEL 7)
^^^^^^^^^^^^^^^^^^^
Open up a terminal and enter the following command sequence.

..  Note: when testing on AWS I had to use a different repository name in the first command:
.. sudo subscription-manager repos --enable rhel-server-rhui-rhscl-7-rpms
.. However, that seemed AWS-specific, and the command used in the docs comes from Red Hat itself:
.. https://developers.redhat.com/blog/2018/08/13/install-python3-rhel#

.. code-block:: bash

   sudo subscription-manager repos --enable rhel-server-rhscl-7-rpms  # enable Red Hat Software Collections repository
   sudo yum -y install rh-python36                                    # install Python 3.6
   scl enable rh-python36 bash                                        # enable Python in current environment
   python3 --version                                                  # check for Python 3.6 - 3.10
   python3 -m venv --system-site-packages ./venv                      # create a virtual env
   source ./venv/bin/activate                                         # active virtual env (bash/zsh)
   pip install --upgrade pip                                          # upgrade Pip


macOS (>=10.15)
^^^^^^^^^^^^^^^
Open up a terminal and enter the following command sequence.

.. code-block:: bash

   /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
   export PATH="/usr/local/opt/python/libexec/bin:$PATH"
   brew update
   brew install python
   python3 --version                                      # check for Python 3.6 - 3.10
   python3 -m venv --system-site-packages ./venv          # create a virtual env
   source ./venv/bin/activate                             # active virtual env

Windows (>= Windows 10)
^^^^^^^^^^^^^^^^^^^^^^^^

Install the latest Python package from `Python.org <https://www.python.org/downloads>`_ using the Windows installer. Open up a Windows shell by:

1. Pressing the 'Windows' key
2. Typing 'PowerShell' or 'cmd', and pressing enter.

From the command shell, enter the following sequence to create and activate a virtual environment.

.. code-block:: doscon

  python -m venv --system-site-packages .\venv
  .\venv\Scripts\activate

SiliconCompiler
---------------

Once the Python environment has been set up, SiliconCompiler can be installed directly from from PyPI using pip. Activate your Python virtual environment and following the instructions below. (identical for Windows, Linux, and macOS).

.. code-block:: bash

 (venv) pip install --upgrade pip                # upgrade pip in virtual env
 (venv) pip list                                 # show installed packages in venv
 (venv) pip install --upgrade siliconcompiler    # install SiliconCompiler in venv
 (venv) python -m pip show siliconcompiler       # will display  SiliconCompiler package information
 (venv) python -c "import siliconcompiler;chip=siliconcompiler.Chip();print(chip.get('version','sc'))"

The expectedion version should be printed to the display:

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


Cloud Acccess
--------------

The SiliconCompiler project supports a remote processing model that leverages the cloud for compilation. To enable remote, processing you will need to have access to a SiliconCompiler server.

Remote server login credentials is handled through a special SiliconCompiler credentials text file, located at ~/.sc/credentials on Linux or macOS, or at C:\\Users\\USERNAME\\.sc\\credentials on Windows. The credentials file contains information about the remote server address, username, and password. An example credentials file is shown below.

.. code-block:: json

   {
   "address": "your-server",
   "username": "your-username",
   "password": "your-key"
   }

To create the credentials file, use a text editor to create the credentials file or use the SiliconCompiler 'sc-configure' app.

.. code-block:: console

  $ sc-configure
  Remote server address: "your-server"
  Remote username: "your-username"
  Remote password: "your-key"
  Remote configuration saved to: /home/<USER>/.sc/.credentials

Validate your setup with the simple example below:

.. code-block:: bash

   echo "module flipflop (input clk, d, output reg out); \
   always @ (posedge clk) out <= d; endmodule"> flipflop.v
   sc flipflop.v -remote

Layout Viewer
-------------

To view IC layout files (DEF, GDSII) we recommend installing the open source multi-platform 'klayout' viewer (available for Windows, Linux, and macOS). Installation instructions for klayout can be found `HERE <https://www.klayout.de/build.html>`_.

Other Tools
-----------

The SiliconCompiler project depends on a number of external tools (synthesis, placement, routing, etc). To run compilation locally, you will need to install each tool individually. Installation instructions for these tools are best written by the original authors so we will not include them here. For convenience, links to installation documentation for all supported tools can be found in the tools directory of the reference manual :ref:`here<Tools directory>`.
