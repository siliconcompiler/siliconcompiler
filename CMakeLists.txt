cmake_minimum_required(VERSION 3.15...3.19)

project(siliconcompiler VERSION "0.0.1")

if(APPLE)
    # Seems to be required for MacOS build to work, but may break Windows build...
    set (CMAKE_CXX_STANDARD 11)
endif()

find_package(PythonLibs REQUIRED)
find_package(PythonInterp REQUIRED)
find_package(PythonExtensions REQUIRED)
find_package(Cython)

# Needed to find *.pxd file
include_directories(${CMAKE_CURRENT_LIST_DIR}/siliconcompiler/leflib)

add_subdirectory(${CMAKE_CURRENT_LIST_DIR}/siliconcompiler/leflib)
add_cython_target(_leflib ${CMAKE_CURRENT_LIST_DIR}/siliconcompiler/leflib/_leflib.pyx CXX)

add_library(_leflib MODULE ${_leflib})
python_extension_module(_leflib)

target_link_libraries(_leflib lef)
target_link_libraries(_leflib ${PYTHON_LIBRARIES})
target_include_directories(_leflib PRIVATE ${PYTHON_INCLUDE_DIRS})

# We want to be extra strict about error checking -- enable all warnings and
# treat them as errors. We only apply this to the _leflib target since the LEF
# parser library has warnings under -Wall -pedantic, but there's not much we can
# do about those.
# 
# We exempt deprecated-declarations since Cython uses something deprecated in at
# least one of the Python versions we support, and there's not much we can do
# about that either.
#
# Microsoft's compiler uses a totally different set of flags, so we just set
# these for MacOS/Linux (which will be using GCC or clang).
if(NOT WIN32)
    target_compile_options(_leflib PRIVATE -Wall -pedantic -Werror -Wno-error=deprecated-declarations)
endif()

# ** Stuff to include Si2 LEF library **
set(LEF_DIR ${CMAKE_CURRENT_LIST_DIR}/third_party/tools/openroad/tools/OpenROAD/src/OpenDB/src/lef)

# this lets us include lef headers
INCLUDE_DIRECTORIES(${LEF_DIR}/lef)
# this causes cmake to build lef/
add_subdirectory(${LEF_DIR})

install(TARGETS _leflib DESTINATION .)
