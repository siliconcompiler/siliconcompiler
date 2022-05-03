# KLayout Python multi-script.
# We want to run OpenROAD's "def2stream.py" file, followed by a "gds2svg.py"
# script. Both scripts use KLayout's pya module, so they must be run in
# KLayout's interpreter. That means we need to use 'exec', not 'subprocess'.

import os

mydir = os.path.dirname(__file__)
script = os.path.join(mydir, 'def2stream.py')
with open(script, 'r') as py:
  exec(py.read())
