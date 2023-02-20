# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

# Install Haskell build tools
sudo add-apt-repository -y ppa:hvr/ghc
sudo apt-get update
sudo apt-get install -y cabal-install ghc

sudo apt-get install -y ghc libghc-regex-compat-dev libghc-syb-dev \
    libghc-old-time-dev libghc-split-dev tcl-dev build-essential pkg-config \
    autoconf gperf flex bison

sudo mkdir -p /opt/tools/bsc
sudo chown $USER:$USER /opt/tools/bsc

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool bsc --field git-url) bsc
cd bsc
git checkout $(python3 ${src_path}/_tools.py --tool bsc --field git-commit)
git submodule update --init --recursive

make install-src

# install
BSC_VERSION=$(echo 'puts [lindex [Bluetcl::version] 0]' | inst/bin/bluetcl)
mv inst /opt/tools/bsc/bsc-${BSC_VERSION}
ln -s /opt/tools/bsc/bsc-${BSC_VERSION} /opt/tools/bsc/latest

cd -

echo "Please add \"export PATH=/opt/tools/bsc/latest/bin:\$PATH to your .bashrc"
