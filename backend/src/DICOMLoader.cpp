// backend/src/DICOMLoader.cpp

#include "../include/DataLoader.h"
#include "../include/VolumeData.h"

#include <iostream>
#include <vector>
#include <algorithm>
#include <filesystem>
#include <cmath>

// DCMTK includes
#include "dcmtk/config/osconfig.h"
#include "dcmtk/dcmdata/dctk.h"
#include "dcmtk/dcmimgle/dcmimage.h"

namespace fs = std::filesystem;

namespace DataLoader {

// Helper struct to hold slice information for robust sorting
struct DicomSlice {
    std::string filePath;
    double sortKey; // Can be Z position, slice location, or instance number
};

bool loadDICOM(const std::string& directoryPath, VolumeData& volumeData) {
    volumeData.clear();
    std::vector<DicomSlice> slices;

    std::cout << "      MVR INFO: Scanning directory (non-recursively): " << directoryPath << std::endl;

    // 1. Scan the SPECIFIED directory (non-recursively) for files.
    try {
        for (const auto& entry : fs::directory_iterator(directoryPath)) {
            if (!entry.is_regular_file()){
                std::cout << "      Skipping non-file: " << fs::path(entry.path()).filename().string() << std::endl;
                continue;
            }

            const std::string filePath = entry.path().string();
            
            // --- DEBUG: Print every file being considered ---
            // std::cout << "      Considering file: " << fs::path(filePath).filename().string() << std::endl;

            DcmFileFormat ff;
            
            // --- TOLERANT LOADING ---
            OFCondition status = ff.loadFile(filePath.c_str());
            if (status.bad()) {
                status = ff.loadFile(filePath.c_str(), EXS_Unknown, EGL_noChange, DCM_MaxReadLength, ERM_dataset);
                if (status.bad()) {
                    // --- DEBUG: Print files that fail to load and why ---
                    std::cerr << "        -> FAILED to parse with DCMTK. Error: " << status.text() << std::endl;
                    continue;
                }
            }

            // --- DEBUG: Confirm successful parsing and print dimensions ---
            DicomImage dcmImage(filePath.c_str());
            if (dcmImage.getStatus() == EIS_Normal) {
                std::cout << "        -> OK. Dimensions: " << dcmImage.getWidth() << " x " << dcmImage.getHeight() << std::endl;
            } else {
                std::cerr << "        -> Parsed but could not create DicomImage object. Status: " << DicomImage::getString(dcmImage.getStatus()) << std::endl;
            }

            DcmDataset* ds = ff.getDataset();
            double sortKey = 0.0;
            bool hasKey = false;

            // --- ROBUST SORTING LOGIC ---
            OFString imagePos;
            if (ds->findAndGetOFString(DCM_ImagePositionPatient, imagePos).good()) {
                double z = 0.0;
                if (sscanf(imagePos.c_str(), "%*f\\%*f\\%lf", &z) == 1) {
                    sortKey = z;
                    hasKey = true;
                }
            }

            if (!hasKey) {
                if (ds->findAndGetFloat64(DCM_SliceLocation, sortKey).good()) {
                    hasKey = true;
                }
            }

            if (!hasKey) {
                long instNum = 0;
                if (ds->findAndGetLongInt(DCM_InstanceNumber, instNum).good()) {
                    sortKey = static_cast<double>(instNum);
                }
            }
            
            slices.push_back({filePath, sortKey});
        }
    } catch (const fs::filesystem_error& e) {
        std::cerr << "      MVR ERROR: Cannot access directory: " << directoryPath << " - " << e.what() << std::endl;
        return false;
    }

    if (slices.empty()) {
        std::cerr << "      :MVR ERROR: No valid DICOM files were successfully parsed in: " << directoryPath << std::endl;
        return false;
    }

    // 2. Sort the collected slices.
    std::sort(slices.begin(), slices.end(),[](const DicomSlice& a, const DicomSlice& b) {
        return a.sortKey < b.sortKey;
    });

    std::cout << "      MVR INFO: Found and sorted " << slices.size() << " DICOM slices." << std::endl;

    // 3. Load pixel data from the sorted slices and stack them.
    for (const auto& slice : slices) {
        DicomImage dcmImage(slice.filePath.c_str());

        if (dcmImage.getStatus()!= EIS_Normal) {
            std::cerr << "      MVR WARN: Skipping unreadable DICOM file: " << slice.filePath << std::endl;
            continue;
        }

        const DiPixel* pixelData = dcmImage.getInterData();
        if (!pixelData) {
            std::cerr << "      MVR WARN: Could not get pixel data from " << slice.filePath << std::endl;
            continue;
        }
        
        const uint16_t* slicePixels = static_cast<const uint16_t*>(pixelData->getData());
        if (!slicePixels) {
            std::cerr << "      MVR WARN: Pixel data pointer is null for " << slice.filePath << std::endl;
            continue;
        }

        if (volumeData.width == 0) { // First valid slice: set dimensions and spacing
            volumeData.width = dcmImage.getWidth();
            volumeData.height = dcmImage.getHeight();
            
            DcmFileFormat ff;
            ff.loadFile(slice.filePath.c_str());
            DcmDataset* ds = ff.getDataset();
            OFString spacingStr;
            if (ds->findAndGetOFString(DCM_PixelSpacing, spacingStr).good()) {
                sscanf(spacingStr.c_str(), "%lf\\%lf", &volumeData.spacing_y, &volumeData.spacing_x);
            }
        }

        volumeData.data.insert(volumeData.data.end(), slicePixels, slicePixels + (volumeData.width * volumeData.height));
    }

    if (volumeData.data.empty()) {
        std::cerr << "      MVR ERROR: Failed to decode any slices from the selected directory." << std::endl;
        return false;
    }

    volumeData.depth = volumeData.data.size() / (volumeData.width * volumeData.height);

    // 4. Calculate Z spacing.
    if (slices.size() > 1) {
        volumeData.spacing_z = std::abs(slices[1].sortKey - slices[0].sortKey);
        if (volumeData.spacing_z == 0) {
            DcmFileFormat ff;
            ff.loadFile(slices[0].filePath.c_str());
            ff.getDataset()->findAndGetFloat64(DCM_SliceThickness, volumeData.spacing_z);
        }
    }
    if (volumeData.spacing_z <= 0) {
        volumeData.spacing_z = 1.0; // Final fallback
    }

    std::cout << "      MVR INFO: Loaded DICOM volume: "
              << volumeData.width << "x"
              << volumeData.height << "x"
              << volumeData.depth << std::endl;

    return true;
}

} // namespace DataLoader