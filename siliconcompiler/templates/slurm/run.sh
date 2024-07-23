#!/bin/bash

python3 -m siliconcompiler.scheduler.run_node \
    -cfg {{ cfg_file }} \
    -builddir {{ build_dir }} \
    -step {{ step }} \
    -index {{ index }} \
    -cwd ${PWD} \
    -cachedir {{ cachedir }}
