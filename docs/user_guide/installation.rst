.. _installation:

Installation
============


Installing Python
-----------------

Before installing the SiliconCompiler package you will need to set up a Python environment.
The following sections will walk you through how to install the appropriate python dependencies and start a `Python virtual environment <https://docs.python.org/3/library/venv.html>`_.
Note that at any time, if you need to exit the Python virtual environment, type 'deactivate' and hit enter.

.. _python_install:

Ubuntu (>=22.04)
^^^^^^^^^^^^^^^^
Open up a terminal and enter the following command sequence.

.. note::
   SiliconCompiler requires Python 3.10 or newer. Ubuntu 22.04 is the first
   release to ship a compatible ``python3`` by default. For Ubuntu 20.04, see the
   section below.

.. code-block:: bash

    python3 --version                                      # check for Python 3.10+
    sudo apt update                                        # update package information
    sudo apt install python3-dev python3-pip python3-venv  # install dependencies
    python3 -m venv  ./venv                                # create a virtual env
    source ./venv/bin/activate                             # active virtual env (bash/zsh)


.. note::
   If you plan to generate any docs or create any flowgraphs, you'll also need to install Graphviz.
   You can make sure you have this dependency by running ``sudo apt install graphviz xdot``.

Skip ahead to :ref:`SC Install <sc_install>`.

Ubuntu 20.04
^^^^^^^^^^^^

.. warning::
   Ubuntu 20.04 is only minimally supported. Pre-built tool scripts
   (``sc-install``) still exist for it but are no longer actively maintained, so
   some tools may fail to build. Installing the SiliconCompiler Python package
   itself works, but consider upgrading to Ubuntu 22.04 or newer.

Ubuntu 20.04 ships Python 3.8 by default, which is older than the Python 3.10
required by SiliconCompiler. Install a newer interpreter from the ``deadsnakes``
PPA, then create the virtual environment with it.

.. code-block:: bash

    sudo apt update                                            # update package information
    sudo apt install software-properties-common               # provides add-apt-repository
    sudo add-apt-repository ppa:deadsnakes/ppa                 # add the deadsnakes PPA
    sudo apt update
    sudo apt install python3.11 python3.11-dev python3.11-venv # install Python 3.11
    python3.11 --version                                       # check for Python 3.10+
    python3.11 -m venv ./venv                                  # create a virtual env
    source ./venv/bin/activate                                 # active virtual env (bash/zsh)

.. note::
   If you plan to generate any docs or create any flowgraphs, you'll also need to install Graphviz.
   You can make sure you have this dependency by running ``sudo apt install graphviz xdot``.

Skip ahead to :ref:`SC Install <sc_install>`.

RHEL (>=RHEL 8)
^^^^^^^^^^^^^^^
Open up a terminal and enter the following command sequence. This also applies to
compatible distributions such as Rocky Linux and AlmaLinux.

.. note::
   SiliconCompiler requires Python 3.10 or newer. The default ``python3`` on RHEL 8
   and RHEL 9 is older than this, so install a newer interpreter (for example,
   ``python3.11``) as shown below.

.. code-block:: bash

   sudo dnf install python3.11 python3.11-pip  # install Python 3.11
   python3.11 --version                        # check for Python 3.10+
   python3.11 -m venv ./venv                   # create a virtual env
   source ./venv/bin/activate                  # active virtual env (bash/zsh)

.. note::
   If you plan to generate any docs or create any flowgraphs, you'll also need to install Graphviz.
   You can make sure you have this dependency by running ``sudo dnf install graphviz xdot``


Skip ahead to :ref:`SC Install <sc_install>`.

macOS
^^^^^
Open up a terminal and enter the following command sequence.

.. note::
   These instructions use `Homebrew <https://brew.sh>`_, which supports only the
   most recent macOS releases. Both Apple Silicon and Intel Macs are supported,
   but they install Homebrew to different prefixes -- the installer prints the
   correct ``shellenv`` line for your machine under "Next steps".

.. code-block:: bash

   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   # /opt/homebrew on Apple Silicon, /usr/local on Intel -- try both
   eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
   brew update
   brew install python
   python3 --version                                      # check for Python 3.10+
   python3 -m venv  ./venv                                # create a virtual env
   source ./venv/bin/activate                             # active virtual env

.. note::
   If you plan to generate any docs or create any flowgraphs, you'll also need to install Graphviz.
   You can make sure you have this dependency by running ``brew install graphviz xdot``


Skip ahead to :ref:`SC Install <sc_install>`.

Windows (>= Windows 10)
^^^^^^^^^^^^^^^^^^^^^^^^

Install the latest Python package from `Python.org <https://www.python.org/downloads>`_ using the Windows installer.
Open up a Windows shell by:

1. Pressing the 'Windows' key
2. Typing 'cmd', and pressing enter.

From the command shell, enter the following sequence to create and activate a virtual environment.
Note that the Python.org installer provides ``python``, not ``python3`` -- on Windows, ``python3`` usually opens the Microsoft Store instead of running the interpreter.

.. code-block:: doscon

  python --version                                       # check for Python 3.10+
  python -m venv  .\venv
  .\venv\Scripts\activate

.. note::
   If you plan to generate any docs or create any flowgraphs, you'll also need to `install Graphviz <https://graphviz.org/download/#windows>`_.


.. _sc_install:

Installing SiliconCompiler
--------------------------

After you've got the python dependencies installed, you will need to install SiliconCompiler.
There are a few different ways to do this:

1. The :ref:`recommended method <install_recommended_method>` is to install the last stable version published to `pypi.org <https://pypi.org/project/siliconcompiler/>`_, or
2. You can install :ref:`directly from the git repository <install_from_git>` (best for developers).

.. _install_recommended_method:

Install from pypi.org
^^^^^^^^^^^^^^^^^^^^^
SiliconCompiler can be installed directly from `pypi.org <https://pypi.org/project/siliconcompiler/>`_ using pip.
Activate your `Python Virtual Environment <https://docs.python.org/3/library/venv.html>`_ and follow the instructions below.

.. code-block:: bash

 (venv) pip install --upgrade siliconcompiler    # install SiliconCompiler in venv
 (venv) pip show siliconcompiler                 # will display SiliconCompiler package information

.. include:: include/installation_confirm_version.inc

Skip to :ref:`asic demo <asic_demo>`.

.. _install_from_git:

Install from GitHub Repo (Linux/MacOS)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
You can also install SiliconCompiler from the latest `SiliconCompiler GitHub Repository <https://github.com/siliconcompiler/siliconcompiler>`_.

**Install SiliconCompiler**

Finally, to clone and install SiliconCompiler, run the following:

.. parsed-literal::

   (venv) git clone -b v\ |release| https\://github.com/siliconcompiler/siliconcompiler
   (venv) cd siliconcompiler
   (venv) pip install --upgrade pip
   (venv) pip install -e .

.. include:: include/installation_confirm_version.inc


.. _asic_demo:

ASIC Demo
---------
Now that you have installed SiliconCompiler, you can test your installation by running a quick demo through the ASIC design flow.
The demo runs the EDA tools in containers with the :ref:`Docker scheduler <docker>`, so nothing beyond Docker and SiliconCompiler needs to be installed -- see :ref:`Using SiliconCompiler with Docker <docker>` if Docker is not running on your machine yet.

.. code-block:: bash

    python -m siliconcompiler.demos.asic_demo -scheduler docker

``python`` rather than ``python3``: a virtual environment provides both on every
platform, and Windows has only ``python``. Outside an activated environment on
Linux or macOS, use ``python3``.

The first run also pulls the container image, so it takes a few minutes.
It should end with a results directory where you can find ``png`` file which displays your results.
It should look something like this:

.. image:: /_screenshots/asic_demo_result.png

See :ref:`Quickstart guide <quickstart_guide>` next to go through the design and run details of the quick demo above.

.. _external_tools:

External Tools
--------------

If you wish to run the tools natively instead of in containers as in the quick :ref:`asic demo <asic_demo>` target above, there will be some tools you need to install first.
You can use the provided :ref:`sc-install <app-sc-install>` application to install the tools or view the scripts directly in the list below.

.. note::

   To install the recommended tools for an asic flow, use: ``sc-install -group asic`` or for an fpga flow ``sc-install -group fpga``.
   To see a full list of supported groups see :ref:`sc-install <app-sc-install>`.
   Links to individual tool installation instructions and platform limitations can be found in the :ref:`pre-defined tool drivers <builtin_tools>`.

   We have provided the following helper install scripts for this minimum toolset for the ASIC flow as well as other external tools, but keep in mind that they are for reference only.
   If you should run into issues, please consult the official download instructions for the tool itself.
   All official tool documentation links can be found in the :ref:`pre-defined tool drivers <builtin_tools>` section.

**Root access.** ``sc-install`` installs into ``~/.local`` by default, which
needs no root of its own, and root is needed only if a tool's prerequisite
packages are missing. Each script asks the package manager what is already
installed -- ``dpkg-query`` on Ubuntu, ``rpm`` on RHEL -- and calls ``sudo`` only
for what is not there. A machine whose prerequisites are already in place -- a
shared server, for instance -- can therefore have its tools installed and updated
by an ordinary user. A handful of scripts still need root regardless, because
they install a system package rather than build into the prefix; KLayout is the
main one.

**Reading the table.** Each row is a tool; each column is a platform. A cell
links to the install script for that combination, and a **blank cell means no
script is provided** -- not that the tool is unavailable. You may still be able
to install it from your distribution's packages or from the tool's own
instructions, linked from the :ref:`pre-defined tool drivers <builtin_tools>`.

Coverage is not uniform, and the gaps matter for the ASIC flow:

* **RHEL 9, Ubuntu 22.04 / 24.04 / 26.04** have scripts for the full ASIC
  toolchain.
* **RHEL 8 and Ubuntu 20.04** have scripts for KLayout only. There are no
  scripts for Yosys, OpenROAD or OpenSTA on those platforms, so the ASIC flow
  cannot be installed this way -- use a newer distribution, the
  :ref:`Docker image <docker>`, or a :ref:`remote run <remote_processing>`.

.. installscripts::

.. note::
   **Windows.** SiliconCompiler itself installs and runs on Windows, and is
   tested there on every commit, but that testing does not cover running EDA
   tools. No install scripts are provided for Windows and the local flows are
   not supported on it.

   To compile a design from Windows, use a :ref:`remote run <remote_processing>`,
   the :ref:`Docker image <docker>`, or WSL. KLayout is the exception worth
   installing natively: it has Windows builds, and :ref:`sc-show <app-sc-show>`
   will use it to view results downloaded from a remote run.

See :ref:`Quickstart guide <quickstart_guide>` next to see how to run locally on your machine with these tools.
