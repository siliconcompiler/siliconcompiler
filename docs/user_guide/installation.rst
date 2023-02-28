Installation
===================================


Installing Python
-----------------

Before installing the SiliconCompiler package you will need to set up a Python environment. Currently Python 3.6-3.10 is supported.
The following sections will walk you through how to install the appropriate python dependencies and start a Python virtual environment. Note that at any time, if you need to exit the Python virtual environment, type 'deactivate' and hit enter. 

.. _Python install:

Ubuntu (>=18.04)
^^^^^^^^^^^^^^^^
Open up a terminal and enter the following command sequence.

.. code-block:: bash

    python3 --version                                      # check for Python 3.6 - 3.10
    sudo apt update                                        # update package information
    sudo apt install python3-dev python3-pip python3-venv  # install dependencies
    python3 -m venv  ./venv                                # create a virtual env
    source ./venv/bin/activate                             # active virtual env (bash/zsh)

Skip ahead to `SC Install`_.

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
   python3 -m venv ./venv                                             # create a virtual env
   source ./venv/bin/activate                                         # active virtual env (bash/zsh)
   pip install --upgrade pip                                          # upgrade Pip

Skip ahead to `SC Install`_.

macOS (>=10.15)
^^^^^^^^^^^^^^^
Open up a terminal and enter the following command sequence.

.. code-block:: bash

   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   export PATH="/usr/local/opt/python/libexec/bin:$PATH"
   brew update
   brew install python
   python3 --version                                      # check for Python 3.6 - 3.10
   python3 -m venv  ./venv                                # create a virtual env
   source ./venv/bin/activate                             # active virtual env

Skip ahead to `SC Install`_.

Windows (>= Windows 10)
^^^^^^^^^^^^^^^^^^^^^^^^

Install the latest Python package from `Python.org <https://www.python.org/downloads>`_ using the Windows installer. Open up a Windows shell by:

1. Pressing the 'Windows' key
2. Typing 'cmd', and pressing enter.

From the command shell, enter the following sequence to create and activate a virtual environment.

.. code-block:: doscon

  python -m venv  .\venv
  .\venv\Scripts\activate


.. _SC Install:


Installing SiliconCompiler
--------------------------



After you've got the python dependencies installed, you will need to install SiliconCompiler. There are a few different ways to do this:

1. The `recommended method`_ is to install the last stable version published to `pypi.org <https://pypi.org>`_, or
2. You can do an `offline install`_ with a tarball (for Linux only), or
3. You can install `directly from the git repository`_ (best for developers).

.. _recommended method:

Install from pypi.org 
^^^^^^^^^^^^^^^^^^^^^
SiliconCompiler can be installed directly from `pypi.org <https://pypi.org>`_ using pip. Activate your `Python Virtual Environment <https://docs.python.org/3/library/venv.html>`_ and follow the instructions below. 

.. code-block:: bash

 (venv) pip install --upgrade pip                # upgrade pip in virtual env
 (venv) pip list                                 # show installed packages in venv
 (venv) pip install --upgrade siliconcompiler    # install SiliconCompiler in venv
 (venv) python -m pip show siliconcompiler       # will display  SiliconCompiler package information

.. include:: installation_confirm_version.rst

.. include:: installation_prep_path.rst 

Skip to `Running SiliconCompiler`_.
	     
.. _offline install:

Offline Install (Linux only)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We also provide packages that bundle SC with all of its Python dependencies to enable installation on machines without an external internet connection. 

To access them:

1. Go our  `builds page <https://github.com/siliconcompiler/siliconcompiler/actions/workflows/wheels.yml>`_. 
2. Click on the most recent, passing Wheels package. This should be the first green-colored build in the list.
3. On the bottom of that page, you will see an "Artifacts" section. Click on the "artifact" to download it.
4. The packages are named ``scdeps-<pyversion>.tar.gz``, depending on which Python version they are associated with.

Then untar the package and install SiliconCompiler:

.. code-block:: bash

   (venv) tar -xzvf scdeps-<pyversion>.tar.gz
   (venv) pip install --upgrade pip --no-index --find-links scdeps
   (venv) pip install siliconcompiler --no-index --find-links scdeps

.. include:: installation_confirm_version.rst

.. note::

   Before you can start running SiliconCompiler, you will also need to make sure you have installed external PDKs and tools required to build (synthesis, place and route, etc). Typically, users of this flow have already set up their own tools and PDKs.
   If you need to set up PDKs and tools and have an internet connection, you can run the following steps.

   .. include:: installation_prep_path.rst


Skip to `Run local`_.

.. _directly from the git repository:

Install from GitHub Repo (Linux/MacOS)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
You can also install SiliconCompiler from the latest `SiliconCompiler GitHub Repository <https://github.com/siliconcompiler/siliconcompiler>`_. 

**Install Dependencies, Bison and Flex**

For Linux, you can use:

.. code-block:: bash

   sudo apt-get install flex bison
   

On MacOS, note that you must first install Bison and Flex from Homebrew.

.. code-block:: bash

   brew install bison
   brew install flex

Ensure that the path to the Homebrew packages takes priority over system
packages in your ``$PATH``. Run ``brew --prefix`` to determine where Homebrew
installs packages on your machine.

**Install SiliconCompiler**

Finally, to clone and install SiliconCompiler, run the following:

.. code-block:: bash

   git clone https://github.com/siliconcompiler/siliconcompiler
   cd siliconcompiler
   pip install -r requirements.txt
   python -m pip install -e .
   export SCPATH=<the full path for your siliconcompiler/siliconcompiler directory>

.. include:: installation_confirm_version.rst
	     

.. _Running SiliconCompiler:

Running SiliconCompiler
------------------------------

You can either run remotely in the cloud, or run locally on your machine.

Run Remote with Cloud Access
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Remote server access requires a credentials text file located at ~/.sc/credentials on Linux or macOS, or at C:\\Users\\USERNAME\\.sc\\credentials on Windows. The credentials file is a JSON formatted file containing information about the remote server address, username, and password. 

.. code-block:: json

   {
   "address": "your-server",
   "username": "your-username",
   "password": "your-key"
   }

Use a text editor to create the credentials file. Alternatively you can use :ref:`sc-configure` app to generate it from the command line.

.. code-block:: console

  (venv) sc-configure
  Remote server address: your-server
  Remote username: your-username
  Remote password: your-key
  Remote configuration saved to: /home/<USER>/.sc/credentials

To verify that your credentials file and server is configured correctly, run the :ref:`sc-ping` command.

.. code-block:: console

  (venv) sc-ping
  User myname validated successfully!
  Remaining compute time: 1440.00 minutes
  Remaining results bandwidth: 5242880 KiB

Once you have verified that your remote configuration works, try compiling a simple design:

.. code-block:: bash

   (venv) curl https://raw.githubusercontent.com/siliconcompiler/siliconcompiler/main/docs/user_guide/examples/heartbeat.v > heartbeat.v
   (venv) sc heartbeat.v -remote

For more information, see :ref:`Remote Processing`.

.. _Run local:

Run Locally
^^^^^^^^^^^

If you wish to run locally, you will need to install some external tool dependencies to start. Take a look at `External Tools`_ for a list of tools which you may want to have. The minimum set of tools required for an ASIC flow are: Surelog, Yosys, OpenRoad and KLayout.

Once you have these tools installed, try compiling a simple design:

.. code-block:: bash

    (venv) cd $SCPATH/../examples/heartbeat
    (venv) sc heartbeat.v heartbeat.sdc

See the :ref:`Quickstart guide <quickstart guide>` section to get more details on what you're running.


Layout Viewer
-------------

To view IC layout files (DEF, GDSII) we recommend installing the open source multi-platform 'klayout' viewer (available for Windows, Linux, and macOS). Installation instructions for klayout can be found in the :ref:`tools directory <klayout>`.

To test the klayout installation, run the 'sc-show' to display the 'heartbeat' layout:

.. code-block:: bash

   (venv) sc-show -design heartbeat

.. _External Tools:

External Tools
--------------

To run compilation locally (instead of remotely), you will need to install a number of tools. For reference, we have provided install scripts for many of these tools. Unless otherwise specified in the script name, these scripts target Ubuntu 20.04.

.. note::

   These install scripts are a reference for installation. If you should run into issues, please consult the official download instructions for the tool itself. All official tool documentation links can be found in the :ref:`tools directory`

.. installscripts::

