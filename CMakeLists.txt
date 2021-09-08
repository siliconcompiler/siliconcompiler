cmake_minimum_required(VERSION 3.15...3.19)

project(siliconcompiler VERSION "0.0.1")

find_package(PythonLibs REQUIRED)
find_package(PythonInterp REQUIRED)
find_package(PythonExtensions REQUIRED)
find_package(Cython)

add_subdirectory(${CMAKE_CURRENT_LIST_DIR}/siliconcompiler/leflib)
add_cython_target(_leflib ${CMAKE_CURRENT_LIST_DIR}/siliconcompiler/leflib/_leflib.pyx)

add_library(_leflib MODULE ${_leflib})
python_extension_module(_leflib)

target_link_libraries(_leflib lef)
target_link_libraries(_leflib ${PYTHON_LIBRARIES})
target_include_directories(_leflib PRIVATE ${PYTHON_INCLUDE_DIRS})

# ** Stuff to include Si2 LEF library **
set(LEF_DIR ${CMAKE_CURRENT_LIST_DIR}/third_party/tools/openroad/tools/OpenROAD/src/OpenDB/src/lef)

# this lets us include lef headers
INCLUDE_DIRECTORIES(${LEF_DIR}/lef)
# this causes cmake to build lef/
add_subdirectory(${LEF_DIR})

install(TARGETS _leflib DESTINATION .)
