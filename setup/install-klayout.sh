#!/bin/sh
sudo apt-get install -y klayout
export QT_QPA_PLATFORM=offscreen
echo 'export QT_QPA_PLATFORM=offscreen' >> ~/.bashrc
