#!/usr/bin/env bash
# SiliconCompiler Replay Setup
# From {{ source }}
# Jobname: {{ jobname }}

if [ "$(python3 -V)" != "Python {{ pythonversion }}" ]; then
    echo "Python version mismatch: $(python3 -V) != {{ pythonversion }}"
fi

python3 -m venv {{ design }}_venv --clear
echo "*" > gcd_venv/.gitignore

. {{ design }}_venv/bin/activate
pip3 install -r requirements.txt

echo "To enable run environment: . {{ design }}_venv/bin/activate"
echo "To replay: ./run.py"
