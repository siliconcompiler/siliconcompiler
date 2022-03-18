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

wget $url
sudo dpkg -i klayout_${pkg_version}_amd64.deb

echo "Please add \"export QT_QPA_PLATFORM=offscreen\" to your .bashrc"

cd -
