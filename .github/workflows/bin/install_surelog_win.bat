:: Install dependencies
choco install -y make
choco install -y swig --side-by-side --version=3.0.12
vcpkg install zlib zlib:x64-windows

:: Build Surelog
:: Based on Surelog CI script: https://github.com/chipsalliance/Surelog/blob/master/.github/workflows/main.yml
call "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat"

set CMAKE_GENERATOR=Ninja
set CC=cl
set CXX=cl
set NO_TCMALLOC=On
set PREFIX=%GITHUB_WORKSPACE%\siliconcompiler\tools\surelog
set CPU_CORES=%NUMBER_OF_PROCESSORS%

set MAKE_DIR=C:\make\bin
set TCL_DIR=%PROGRAMFILES%\Git\mingw64\bin
set SWIG_DIR=%PROGRMDATA%\chocolatey\lib\swig\tools\install\swigwin-3.0.12
set PATH=%pythonLocation%;%SWIG_DIR%;%JAVA_HOME%\bin;%MAKE_DIR%;%TCL_DIR%;%PATH%
set ADDITIONAL_CMAKE_OPTIONS=-DPython3_ROOT_DIR=%pythonLocation% -DCMAKE_TOOLCHAIN_FILE=%VCPKG_INSTALLATION_ROOT%\scripts\buildsystems\vcpkg.cmake.

set
where cmake && cmake --version
where make && make --version
where swig && swig -version
where java && java -version
where python && python --version
where ninja && ninja --version

:: Required for Surelog
pip3 install orderedmultidict
pip3 install cmake

for /f "tokens=* USEBACKQ" %%i in (`python3 setup/_tools.py --tool surelog --field git-url`) do set GITURL=%%i
for /f "tokens=* USEBACKQ" %%i in (`python3 setup/_tools.py --tool surelog --field git-commit`) do set GITCOMMIT=%%i

git clone %GITURL%
cd Surelog
git checkout %GITCOMMIT%
git submodule update --init --recursive

make
make install
