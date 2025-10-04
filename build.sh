#!/usr/bin/env bash
set -e

# Clean build dir if --clean is passed
if [ "$1" == "--clean" ]; then
  echo "[INFO] Cleaning build directory..."
  rm -rf build
fi

# Create build directory
mkdir -p build
cd build

# Run CMake configure
cmake .. \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_CUDA_ARCHITECTURES=native \
  -DCMAKE_CUDA_COMPILER=$(which nvcc) \
  -DPython_EXECUTABLE=$(which python3)

# Build project (uses system default generator, e.g. make)
cmake --build . -j4


################################################################################
## USAGE:
#./build.sh        # configure + build
#./build.sh clean  # clean build directory