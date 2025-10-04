# Medical Volume Renderer [v0]


python3 --version
python3 -m venv .mv
source .mvr/bin/activate


sudo apt install python3
sudo apt install pybind11-dev
sudo apt install dcmtk libdcmtk-dev
sudo apt install libnifti-dev zlib1g-dev libnsl-dev

pip install PyQt6 pyqtgraph numpy


cd ~/Downloads
git clone https://github.com/NIFTI-Imaging/nifti_clib.git
cd nifti_clib



mkdir build && cd build
cmake .. -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DBUILD_SHARED_LIBS=ON
make -j$(nproc)
sudo make install


export PYTHONPATH=$PYTHONPATH:/home/akashmaji/Downloads/MedicalVolumeRenderer/build
