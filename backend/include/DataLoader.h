//
// Created by akashmaji on 10/4/25.
//

// backend/include/DataLoader.h

#ifndef DATALOADER_H
#define DATALOADER_H

#include <string>
#include "../include/VolumeData.h"

namespace DataLoader {

    /**
     * @brief Loads a series of DICOM slices from a directory.
     *
     * This function scans the specified directory for DICOM files, sorts them based on
     * their spatial position (Image Position Patient tag), and stacks them into a
     * 3D volume.
     *
     * @param directoryPath The path to the directory containing DICOM (.dcm) files.
     * @param volumeData A reference to a VolumeData object to be populated.
     * @return true if loading was successful, false otherwise.
     */
    bool loadDICOM(const std::string& directoryPath, VolumeData& volumeData);

    /**
     * @brief Loads a NIfTI file.
     *
     * This function reads a.nii or.nii.gz file and populates the VolumeData object.
     * NIfTI files store the 3D volume directly, making this process simpler than DICOM.
     *
     * @param filePath The path to the NIfTI file.
     * @param volumeData A reference to a VolumeData object to be populated.
     * @return true if loading was successful, false otherwise.
     */
    bool loadNIFTI(const std::string& filePath, VolumeData& volumeData);

} // namespace DataLoader

#endif // DATALOADER_H