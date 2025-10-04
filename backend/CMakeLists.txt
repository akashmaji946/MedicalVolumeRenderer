cmake_minimum_required(VERSION 3.20)
project(MedicalVolumeRenderer LANGUAGES CXX CUDA)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

enable_language(CUDA)
set(CMAKE_CUDA_ARCHITECTURES native)
set(CMAKE_CUDA_COMPILER /usr/local/cuda-13/bin/nvcc)
find_package(CUDAToolkit REQUIRED)

find_package(OpenGL REQUIRED)
find_package(GLEW REQUIRED)
find_package(glfw3 REQUIRED)
find_package(glm REQUIRED)
find_package(DCMTK REQUIRED)
find_package(pybind11 REQUIRED)
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets OpenGL)

# --- NIFTI / znzlib / nsl ---
find_library(NIFTI_LIB niftiio HINTS /usr/local/lib /usr/lib)
find_library(ZNZ_LIB znz HINTS /usr/local/lib /usr/lib)
find_library(NSL_LIB nsl HINTS /usr/lib /usr/local/lib)

if(NOT NIFTI_LIB)
    message(FATAL_ERROR "Cannot find niftiio library. Please install libnifti-dev or build NIfTI from source.")
endif()

if(NOT ZNZ_LIB)
    message(FATAL_ERROR "Cannot find znz library. Please build NIfTI from source.")
endif()

if(NOT NSL_LIB)
    message(WARNING "Cannot find libnsl. Some network functionality may be missing.")
endif()

message(STATUS "NIFTI_LIB = ${NIFTI_LIB}")
message(STATUS "ZNZ_LIB   = ${ZNZ_LIB}")
message(STATUS "NSL_LIB   = ${NSL_LIB}")

# --- Sources and headers ---
file(GLOB_RECURSE BACKEND_SOURCES "src/*.cpp" "src/*.cu" "glad/*.cpp")
file(GLOB_RECURSE BACKEND_HEADERS "include/*.h" "include/*.hpp" "glad/*.hpp" "glad/*.h")

# --- Core backend library ---
add_library(backend_lib ${BACKEND_SOURCES} ${BACKEND_HEADERS})

target_include_directories(backend_lib PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        /usr/local/include/nifti
)

target_link_libraries(backend_lib PRIVATE
        ${OPENGL_LIBRARIES}
        GLEW::GLEW
        glfw
        glm::glm
        CUDA::cudart
        ${NIFTI_LIB}
        ${ZNZ_LIB}
        DCMTK::dcmdata
        DCMTK::dcmimgle
        DCMTK::ofstd
        ${NSL_LIB} # optional
)

# Provide absolute path to shaders directory as a compile definition
target_compile_definitions(backend_lib PRIVATE SHADERS_DIR="${CMAKE_CURRENT_SOURCE_DIR}/shaders")

# --- Optional standalone executable ---
add_executable(backend_exec
        src/main.cpp
)

target_link_libraries(backend_exec PRIVATE
        backend_lib
        ${NIFTI_LIB}
        ${ZNZ_LIB}
        ${NSL_LIB}
        pybind11::module
)

# --- Additional settings ---
set_target_properties(backend_lib PROPERTIES
        POSITION_INDEPENDENT_CODE ON
)

set_target_properties(backend_exec PROPERTIES
        CXX_STANDARD 17
        CXX_STANDARD_REQUIRED YES
)
