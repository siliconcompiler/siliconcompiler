#!/usr/bin/env bash
echo "{{ title }}"
echo "see README.txt for more information"
echo "executing in {{ exec_dir }}"
cd {{ exec_dir }}
./replay.sh
