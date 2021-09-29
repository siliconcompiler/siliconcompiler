#!/bin/sh
# Install core dependencies.
sudo apt-get install -y build-essential gcc g++ cmake automake autoconf bison flex git libblas-dev liblapack-dev liblapack64-dev libfftw3-dev libsuitesparse-dev libopenmpi-dev libboost-all-dev libnetcdf-dev libmatio-dev

mkdir -p deps
cd deps

# Download and build Trilinos.
wget --content-disposition https://github.com/trilinos/Trilinos/archive/refs/tags/trilinos-release-12-12-1.tar.gz
tar -xf Trilinos-trilinos-release-12-12-1.tar.gz
cd Trilinos-trilinos-release-12-12-1/
mkdir build
cd build
pwd=$(pwd)
SRCDIR=$pwd/..
ARCHDIR=$HOME/XyceLibs/Parallel
FLAGS="-O3 -fPIC"
cmake \
-G "Unix Makefiles" \
-DCMAKE_C_COMPILER=mpicc \
-DCMAKE_CXX_COMPILER=mpic++ \
-DCMAKE_Fortran_COMPILER=mpif77 \
-DCMAKE_CXX_FLAGS="$FLAGS" \
-DCMAKE_C_FLAGS="$FLAGS" \
-DCMAKE_Fortran_FLAGS="$FLAGS" \
-DCMAKE_INSTALL_PREFIX=$ARCHDIR \
-DCMAKE_MAKE_PROGRAM="make" \
-DTrilinos_ENABLE_NOX=ON \
-DNOX_ENABLE_LOCA=ON \
-DTrilinos_ENABLE_EpetraExt=ON \
-DEpetraExt_BUILD_BTF=ON \
-DEpetraExt_BUILD_EXPERIMENTAL=ON \
-DEpetraExt_BUILD_GRAPH_REORDERINGS=ON \
-DTrilinos_ENABLE_TrilinosCouplings=ON \
-DTrilinos_ENABLE_Ifpack=ON \
-DTrilinos_ENABLE_Isorropia=ON \
-DTrilinos_ENABLE_AztecOO=ON \
-DTrilinos_ENABLE_Belos=ON \
-DTrilinos_ENABLE_Teuchos=ON \
-DTeuchos_ENABLE_COMPLEX=ON \
-DTrilinos_ENABLE_Amesos=ON \
-DAmesos_ENABLE_KLU=ON \
-DTrilinos_ENABLE_Amesos2=ON \
-DAmesos2_ENABLE_KLU2=ON \
-DAmesos2_ENABLE_Basker=ON \
-DTrilinos_ENABLE_Sacado=ON \
-DTrilinos_ENABLE_Stokhos=ON \
-DTrilinos_ENABLE_Kokkos=ON \
-DTrilinos_ENABLE_Zoltan=ON \
-DTrilinos_ENABLE_ALL_OPTIONAL_PACKAGES=OFF \
-DTrilinos_ENABLE_CXX11=ON \
-DTPL_ENABLE_AMD=ON \
-DAMD_LIBRARY_DIRS="/usr/lib" \
-DTPL_AMD_INCLUDE_DIRS="/usr/include/suitesparse" \
-DTPL_ENABLE_BLAS=ON \
-DTPL_ENABLE_LAPACK=ON \
-DTPL_ENABLE_MPI=ON \
$SRCDIR
make -j2
sudo make install
cd -

# Download and build Xyce.
wget https://github.com/Xyce/Xyce/archive/refs/tags/Release-7.3.0.tar.gz
tar -xf Release-7.3.0.tar.gz
cd Xyce-Release-7.3.0/
./bootstrap
mkdir build
cd build
../configure CXXFLAGS="-O3 -std=c++11" ARCHDIR=$ARCHDIR CPPFLAGS="-I/usr/include/suitesparse" CXX=mpic++ CC=mpicc F77=mpif77 --enable-mpi --enable-stokhos --enable-amesos2
make -j2
sudo make install
cd -
