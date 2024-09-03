Docker
======

To use the docker based running image SiliconCompiler provides, you will need to ensure that docker is installed on your machine.
If you need to install docker, please follow the instructions for your OS: :ref:`linux`, :ref:`Windows`, or :ref:`macOS`.

Linux
-----

Download and Install Docker Desktop for Linux as detailed in `dockers installation instructions <https://docs.docker.com/desktop/install/linux-install/>`__.
After installation, start Docker Desktop and use recommended settings if possible

On a terminal, run the following commands:

.. code-block:: bash

    $ python3 -m venv .venv
    $ source .venv/bin/activate

    $ python3 -m pip install siliconcompiler

    $ sc -target asic_demo -scheduler docker


Windows
-------

Download and Install Docker Desktop for Windows as detailed in `dockers installation instructions <https://docs.docker.com/desktop/install/windows-install/>`__.
After installation, start docker.

On powershell terminal, run the following commands:

.. code-block:: bash

    $ python3 -m venv .venv
    $ .venv/Script/activate

    $ python3 -m pip install siliconcompiler

    $ siliconcompiler -target asic_demo -scheduler docker


macOS
-----

Download and Install Docker Desktop for macOS as detailed in `dockers installation instructions <https://docs.docker.com/desktop/install/mac-install/>`_.
After installation, start Docker Desktop and use recommended settings if possible

On a Mac terminal, run the following commands:

.. code-block:: bash

    $ python -m venv .venv
    $ source .venv/bin/activate

    $ python -m pip install siliconcompiler

    $ sc -target asic_demo -scheduler docker
