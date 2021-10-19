#!/bin/sh
mkdir -p deps
cd deps
wget -q https://github.com/zachjs/sv2v/releases/download/v0.0.9/sv2v-Linux.zip
unzip sv2v-Linux
sudo mv sv2v-Linux/sv2v /usr/bin
rm -rf sv2v-Linux
