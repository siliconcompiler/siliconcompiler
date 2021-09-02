cmake_minimum_required(VERSION 3.15...3.19)

project(siliconcompiler VERSION "0.0.1")

if(SKBUILD)
  # Scikit-Build does not add your site-packages to the search path automatically,
  # so we need to add it _or_ the pybind11 specific directory here.
  execute_process(
    COMMAND
      "${PYTHON_EXECUTABLE}" -c
      "import pybind11; print(pybind11.get_cmake_dir())"
    OUTPUT_VARIABLE _tmp_dir
    OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ECHO STDOUT)
  list(APPEND CMAKE_PREFIX_PATH "${_tmp_dir}")
endif()

# Now we can find pybind11
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_core MODULE siliconcompiler/leflib/main.cpp)

# ** Stuff to include Si2 LEF library **

set(LEF_DIR ${CMAKE_CURRENT_LIST_DIR}/third_party/tools/openroad/tools/OpenROAD/src/OpenDB/src/lef)

# this lets us include lef headers
INCLUDE_DIRECTORIES(${LEF_DIR}/lef)
# this causes cmake to build lef/
add_subdirectory(${LEF_DIR})

target_compile_definitions(_core PRIVATE VERSION_INFO=${PROJECT_VERSION})
target_link_libraries(_core PRIVATE lef)

add_dependencies(_core lef)

install(TARGETS _core DESTINATION .)
