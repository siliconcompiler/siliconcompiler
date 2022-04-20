#!/bin/bash

export PACKAGE='gcd'
export MANIFEST='gcd/job0/gcd.pkg.json'
export REGISTRY='test_registry'

python siliconcompiler/apps/sup.py check $MANIFEST
python siliconcompiler/apps/sup.py publish $MANIFEST -registry $REGISTRY
python siliconcompiler/apps/sup.py show $PACKAGE -registry $REGISTRY
python siliconcompiler/apps/sup.py index -registry $REGISTRY
python siliconcompiler/apps/sup.py install $PACKAGE
python siliconcompiler/apps/sup.py list
