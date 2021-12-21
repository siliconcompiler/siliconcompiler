sudo mkdir -p /opt/tools/bsc
sudo chown $USER:$USER /opt/tools/bsc

sudo apt-get install -y ghc libghc-regex-compat-dev libghc-syb-dev \
    libghc-old-time-dev libghc-split-dev tcl-dev build-essential pkg-config \
    autoconf gperf flex bison

mkdir -p deps
cd deps
git clone --recursive https://github.com/B-Lang-org/bsc

cd bsc
git checkout 2021.07
make install-src

# install
BSC_VERSION=$(echo 'puts [lindex [Bluetcl::version] 0]' | inst/bin/bluetcl)
mv inst /opt/tools/bsc/bsc-${BSC_VERSION}
cd /opt/tools/bsc
ln -s bsc-${BSC_VERSION} latest
cd -

cd ../../

echo "Please add \"export PATH=/opt/tools/bsc/latest/bin:\$PATH to your .bashrc"
