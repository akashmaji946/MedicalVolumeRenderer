
## MedicalVolumeRenderer/CMakeLists.txt
#cmake_minimum_required(VERSION 3.2)
#project(MedicalVolumeRenderer LANGUAGES CXX CUDA)

## set these using -D options
#set(CMAKE_CUDA_ARCHITECTURES native)
#set(CMAKE_CUDA_COMPILER  /usr/local/cuda-13/bin/nvcc)
#find_package(CUDAToolkit REQUIRED)

## Find Python and PyBind11
#set(Python_EXECUTABLE /home/akashmaji/Downloads/MedicalVolumeRenderer/.mvr/bin/python)
#find_package(Python 3.13.5 EXACT COMPONENTS Interpreter Development REQUIRED)
#find_package(pybind11 CONFIG REQUIRED)


# MedicalVolumeRenderer/CMakeLists.txt
cmake_minimum_required(VERSION 3.22)
project(MedicalVolumeRenderer LANGUAGES CXX CUDA)

# CUDA settings (use defaults unless overridden)
enable_language(CUDA)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Detect CUDA (compiler + toolkit)
find_package(CUDAToolkit REQUIRED)

# Find Python and PyBind11 (use global installation if available)
# sudo apt-get install python3 pybind11-dev
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

# Add the C++ backend as a subdirectory.
# This will create the 'backend_lib' target.
add_subdirectory(backend)

# Create the Python extension module
pybind11_add_module(volumerenderer
        bindings/src/main.cpp
        bindings/src/renderer_bindings.cpp
)

# Link the Python module against our C++ backend library
target_link_libraries(volumerenderer PRIVATE backend_lib)

# Include directories for the binding code
target_include_directories(volumerenderer PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/backend/include"
)
