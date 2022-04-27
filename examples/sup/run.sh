#!/bin/bash

export PACKAGE='gcd'
export MANIFEST='build/gcd/job0/gcd.pkg.json'
export REGISTRY='test_registry'

python siliconcompiler/apps/sup.py check $MANIFEST
python siliconcompiler/apps/sup.py publish $MANIFEST -r $REGISTRY
python siliconcompiler/apps/sup.py search $PACKAGE -r $REGISTRY
python siliconcompiler/apps/sup.py info $PACKAGE -r $REGISTRY
python siliconcompiler/apps/sup.py install $PACKAGE -r $REGISTRY
python siliconcompiler/apps/sup.py search $PACKAGE -r $REGISTRY
python siliconcompiler/apps/sup.py uninstall $PACKAGE
