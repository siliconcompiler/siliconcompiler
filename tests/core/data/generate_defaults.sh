#!/usr/bin/env bash

src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)
schema_cfg=${src_path}/../../../siliconcompiler/schema_obj.py

python3 $schema_cfg > ${src_path}/defaults.json
