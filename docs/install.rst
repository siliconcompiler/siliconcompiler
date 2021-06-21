Installation
===================================

To install the current release from PyPI.

::
   
$ pip install siliconcompiler

To install from the active developer repository.

::
   
$ git clone https://github.com/siliconcompiler/siliconcompiler
$ cd siliconcompiler
$ pip install -r requirements.txt
$ python -m pip install -e .

Pre-requisites
---------------

To compile designs using the included open source target flow, you will need to install the follwoing external packages: 

Ubuntu based install scripts can be found in the ./setup directory. These scripts will install dependencies into `siliconcompiler/deps`, and usually build them from source.

- **OpenRoad**
- **Yosys**
- **Verilator**
- **Klayout**

SiliconCompiler have also been tested with commercial EDA tools and PDKs, but these configurations cannot be disclosed due to IP restrictions.

Testing Installation
---------------------

::
   
$ sc examples/gcd/gcd.v -design gcd -target freepdk45_asic -constraint examples/gcd/gcd.sdc
$ sc build/gcd/job1/export/outputs/gcd.gds -display
