#!/bin/sh
sudo apt-get install -y python3-pip
pip3 install -r requirements.txt
python3 -m pip install -e .

echo 'export PATH=~/.local/bin:$PATH' >> ~/.bashrc
