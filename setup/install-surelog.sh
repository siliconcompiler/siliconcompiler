sudo apt-get install -y build-essential cmake git pkg-config tclsh swig uuid-dev libgoogle-perftools-dev python3 python3-dev
sudo apt-get install -y default-jre

mkdir -p deps
cd deps
git clone https://github.com/alainmarcel/Surelog.git
cd Surelog
git submodule update --init --recursive
make
make install
cd -
