//
// backend/src/DICOMLoader.cpp
//
#include "../include/DataLoader.h"
#include "../include/VolumeData.h"

#include <iostream>
#include <vector>
#include <algorithm>
#include <filesystem>

// DCMTK includes
#include "dcmtk/config/osconfig.h"
#include "dcmtk/dcmdata/dctk.h"
#include "dcmtk/dcmimgle/dcmimage.h"

namespace fs = std::filesystem;

namespace DataLoader {

struct DicomSlice {
    std::string filePath;
    double imagePositionZ;
};

bool loadDICOM(const std::string& directoryPath, VolumeData& volumeData) {
    volumeData.clear();
    std::vector<DicomSlice> slices;

    // 1. Scan directory for .dcm files
    for (const auto& entry : fs::directory_iterator(directoryPath)) {
        if (entry.is_regular_file()) {
            std::string filePath = entry.path().string();
            DcmFileFormat fileformat;
            if (fileformat.loadFile(filePath.c_str()).good()) {
                DcmDataset* dataset = fileformat.getDataset();
                OFString imagePos;
                if (dataset->findAndGetOFString(DCM_ImagePositionPatient, imagePos).good()) {
                    double z = 0.0;
                    sscanf(imagePos.c_str(), "%*f\\%*f\\%lf", &z);
                    slices.push_back({filePath, z});
                }
            }
        }
    }

    if (slices.empty()) {
        std::cerr << "      MVR ERROR: No valid DICOM slices found in directory: " << directoryPath << std::endl;
        return false;
    }

    // 2. Sort slices by Z position
    std::sort(slices.begin(), slices.end(),
              [](const DicomSlice& a, const DicomSlice& b) {
                  return a.imagePositionZ < b.imagePositionZ;
              });

    // 3. Load pixel data
    for (const auto& slice : slices) {
        DicomImage dcmImage(slice.filePath.c_str());
        if (dcmImage.getStatus() != EIS_Normal) {
            std::cerr << "      MVR ERROR: Processing DICOM file: " << slice.filePath << std::endl;
            continue;
        }

        const DiPixel* pixelData = dcmImage.getInterData();
        if (!pixelData) {
            std::cerr << "      MVR ERROR: Could not get pixel data from " << slice.filePath << std::endl;
            return false;
        }

        const uint16_t* slicePixels = static_cast<const uint16_t*>(pixelData->getData());
        if (!slicePixels) {
            std::cerr << "      MVR ERROR: Pixel data pointer is null for " << slice.filePath << std::endl;
            return false;
        }

        if (volumeData.width == 0) { // first slice
            volumeData.width = dcmImage.getWidth();
            volumeData.height = dcmImage.getHeight();

            // Extract pixel spacing (0028,0030)
            DcmFileFormat ff;
            ff.loadFile(slice.filePath.c_str());
            DcmDataset* ds = ff.getDataset();
            OFString spacingStr;
            if (ds->findAndGetOFString(DCM_PixelSpacing, spacingStr).good()) {
                double sx, sy;
                sscanf(spacingStr.c_str(), "%lf\\%lf", &sy, &sx);
                volumeData.spacing_x = sx;
                volumeData.spacing_y = sy;
            } else {
                volumeData.spacing_x = 1.0;
                volumeData.spacing_y = 1.0;
            }
        }

        // append slice data
        volumeData.data.insert(volumeData.data.end(),
                               slicePixels,
                               slicePixels + (volumeData.width * volumeData.height));
    }

    volumeData.depth = slices.size();

    // 4. Z spacing
    if (slices.size() > 1) {
        volumeData.spacing_z = std::abs(slices[1].imagePositionZ - slices[0].imagePositionZ);
    } else {
        DcmFileFormat ff;
        ff.loadFile(slices[0].filePath.c_str());
        if (ff.getDataset()->findAndGetFloat64(DCM_SliceThickness, volumeData.spacing_z).bad()) {
            volumeData.spacing_z = 1.0; // fallback
        }
    }

    std::cout << "      MVR INFO: Loaded DICOM volume: "
              << volumeData.width << "x"
              << volumeData.height << "x"
              << volumeData.depth << std::endl;

    return true;
}

} // namespace DataLoader
