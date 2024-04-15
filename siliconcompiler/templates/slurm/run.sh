#!/bin/bash

sc \
    -cfg {{ cfg_file }} \
    -builddir {{ build_dir }} \
    -arg_step {{ step }} \
    -arg_index {{ index }}
