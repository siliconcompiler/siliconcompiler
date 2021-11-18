sudo apt-get install -y build-essential cmake git pkg-config tclsh swig uuid-dev libgoogle-perftools-dev python3 python3-dev
sudo apt-get install -y default-jre

git submodule update --init --recursive third_party/tools/surelog
cd third_party/tools/surelog
make
make install
cd -
