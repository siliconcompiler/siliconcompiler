:: Install dependencies
choco install -y make
choco install -y ninja
vcpkg install zlib:x64-windows-static

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
set PATH=%pythonLocation%;%JAVA_HOME%\bin;%MAKE_DIR%;%PATH%
set ADDITIONAL_CMAKE_OPTIONS=-DPython3_ROOT_DIR=%pythonLocation% -DSURELOG_WITH_TCMALLOC=Off -DCMAKE_TOOLCHAIN_FILE=%VCPKG_INSTALLATION_ROOT%\scripts\buildsystems\vcpkg.cmake. -DVCPKG_TARGET_TRIPLET=x64-windows-static

set
where cmake && cmake --version
where make && make --version
where swig && swig -version
where java && java -version
where python && python --version
where ninja && ninja --version

:: Required for Surelog
pip3 install orderedmultidict
pip3 install psutil

git config --global core.autocrlf input

for /f "tokens=* USEBACKQ" %%i in (`python3 setup/_tools.py --tool surelog --field git-url`) do set GITURL=%%i
for /f "tokens=* USEBACKQ" %%i in (`python3 setup/_tools.py --tool surelog --field git-commit`) do set GITCOMMIT=%%i

git clone %GITURL%
cd Surelog
git checkout %GITCOMMIT%
git submodule update --init --recursive

make release
make install
