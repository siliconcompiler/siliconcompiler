#!/bin/sh

mkdir -p deps
cd deps

pkg_version="0.27.8-1"
version=$(lsb_release -sr)

if [ "$version" = "18.04" ]; then
    url=https://www.klayout.org/downloads/Ubuntu-18/klayout_${pkg_version}_amd64.deb
elif [ "$version" = "20.04" ]; then
    url=https://www.klayout.org/downloads/Ubuntu-20/klayout_${pkg_version}_amd64.deb
else
    echo "Script doesn't support Ubuntu version $version."
fi

# Fetch package
wget $url
# Install dependencies
sudo apt-get install -y libqt5core5a libqt5designer5 libqt5gui5 libqt5multimedia5 \
       libqt5multimediawidgets5 libqt5network5 libqt5opengl5 libqt5printsupport5 \
       libqt5sql5 libqt5svg5 libqt5widgets5 libqt5xml5 libqt5xmlpatterns5 libruby2.7
# Install package
sudo dpkg -i klayout_${pkg_version}_amd64.deb

echo "Please add \"export QT_QPA_PLATFORM=offscreen\" to your .bashrc"

cd -
