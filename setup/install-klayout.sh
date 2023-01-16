#!/bin/sh

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

mkdir -p deps
cd deps

pkg_version=$(python3 ${src_path}/_tools.py --tool klayout --field version)
version=$(lsb_release -sr)

if [ "$version" = "18.04" ]; then
    url=https://www.klayout.org/downloads/Ubuntu-18/klayout_${pkg_version}_amd64.deb
elif [ "$version" = "20.04" ]; then
    url=https://www.klayout.org/downloads/Ubuntu-20/klayout_${pkg_version}_amd64.deb
elif [ "$version" = "22.04" ]; then
    url=https://www.klayout.org/downloads/Ubuntu-22/klayout_${pkg_version}_amd64.deb
else
    echo "Script doesn't support Ubuntu version $version."
fi

# Fetch package
wget -O klayout.deb $url
# Install dependencies
sudo apt-get install -y libqt5core5a libqt5designer5 libqt5gui5 libqt5multimedia5 \
       libqt5multimediawidgets5 libqt5network5 libqt5opengl5 libqt5printsupport5 \
       libqt5sql5 libqt5svg5 libqt5widgets5 libqt5xml5 libqt5xmlpatterns5 libruby2.7
# Install package
sudo dpkg -i klayout.deb

cd -
