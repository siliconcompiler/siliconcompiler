#!/bin/sh
wget -q https://github.com/zachjs/sv2v/releases/download/v0.0.7/sv2v-Linux.zip
unzip sv2v-Linux
sudo mv sv2v-Linux/sv2v /usr/bin
rm -rf sv2v-Linux
