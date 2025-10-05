//
// Created by akashmaji on 10/4/25.
//

// bindings/src/renderer_bindings.cpp

// bindings/src/renderer_bindings.cpp
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include "../../backend/include/Renderer.h" // From backend/include/
#include "../../backend/include/VTKRenderer.h"
#include "../../backend/include/VTKVolumeData.h"

namespace py = pybind11;

void bind_renderer(py::module_& m) {

    py::class_<VolumeData>(m, "VolumeData")
            .def_readonly("width", &VolumeData::width)
            .def_readonly("height", &VolumeData::height)
            .def_readonly("depth", &VolumeData::depth)
            .def_readonly("spacing_x", &VolumeData::spacing_x)
            .def_readonly("spacing_y", &VolumeData::spacing_y)
            .def_readonly("spacing_z", &VolumeData::spacing_z);


    py::class_<Renderer>(m, "Renderer")

             .def(py::init<>())

             .def("get_volume_width", &Renderer::getVolumeWidth, "Returns the width of the loaded volume")
             .def("get_volume_height", &Renderer::getVolumeHeight, "Returns the height of the loaded volume")
             .def("get_volume_depth", &Renderer::getVolumeDepth, "Returns the depth of the loaded volume")

             .def("get_volume_spacing_x", &Renderer::getVolumeSpacingX, "Returns the X spacing of the loaded volume")
             .def("get_volume_spacing_y", &Renderer::getVolumeSpacingY, "Returns the Y spacing of the loaded volume")
             .def("get_volume_spacing_z", &Renderer::getVolumeSpacingZ, "Returns the Z spacing of the loaded volume")

             .def("load_volume", &Renderer::loadVolume, "Loads a volume from a file path or directory")

             .def("is_volume_loaded", &Renderer::isVolumeLoaded, "Returns true if a volume is loaded")

            // This exposes the C++ getVolume method, returning a pointer.
            // The 'reference_internal' policy is crucial: it tells Python that the
            // lifetime of the returned VolumeData object is managed by the Renderer.
            .def("get_volume", &Renderer::getVolume, py::return_value_policy::reference_internal,
            "Returns a reference to the internal VolumeData object")

            // This is the NEW function that correctly converts the data to a NumPy array.
            // It is implemented as a C++ lambda function right here in the bindings.
            .def("get_volume_as_numpy",[](Renderer &self) -> py::array {

                    VolumeData* vol = self.getVolume();
                    if (!vol || vol->data.empty()) {
                        // Return an empty array if no data is loaded
                        return py::array_t<uint16_t>();
                    }

                    // This creates a NumPy array that is a COPY of the C++ data.
                    // This is the safest and simplest approach.
                    return py::array_t<uint16_t>(
                    {vol->depth, vol->height, vol->width}, // Shape
                    {
                        vol->height * vol->width * sizeof(uint16_t), // Stride for depth
                        vol->width * sizeof(uint16_t),               // Stride for height
                        sizeof(uint16_t)                             // Stride for width
                    },
                    vol->data.data() // Pointer to the data
                    );

            }, "Returns the volume data as a NumPy array (copies data)")
            
            
            // --- Bind new OpenGL and Camera methods ---
            .def("init", &Renderer::init, "Initialize OpenGL context")
            .def("render", &Renderer::render, "Render the scene")
            .def("resize", &Renderer::resize, "Resize the viewport")
            .def("camera_rotate", &Renderer::camera_rotate, "Rotate the camera")
            .def("camera_zoom", &Renderer::camera_zoom, "Zoom the camera")
            .def("set_camera_angles", &Renderer::set_camera_angles, py::arg("azimuthDeg"), py::arg("elevationDeg"),
                 "Set camera azimuth/elevation in degrees (elevation clamped to avoid gimbal lock)")
            // Controls
            .def("set_show_bounding_box", &Renderer::setShowBoundingBox, py::arg("show"), "Show or hide the bounding box")
            .def("set_colormap_preset", &Renderer::setColormapPreset, py::arg("preset_index"), "Set colormap preset (0..9)")
            .def("set_background_color", &Renderer::setBackgroundColor, py::arg("r"), py::arg("g"), py::arg("b"),
                 "Set background clear color as floats in [0,1]")
            .def("set_bounding_box_scale", &Renderer::setBoundingBoxScale, py::arg("scale"),
                 "Set bounding box scale (default 1.0, clamped to [0.1, 5.0])")
            .def("frame_camera_to_box", &Renderer::frameCameraToBox, "Frame camera to volume bounding box")
            .def("set_colormap_mode_custom", &Renderer::setColormapModeCustom, py::arg("use_custom"),
                 "Enable or disable custom transfer function mode")
            .def("set_transfer_function_points",
                 [](Renderer& self, const std::vector<std::tuple<float,float,float,float,float>>& pts){
                     std::vector<Renderer::TFPoint> cpp;
                     cpp.reserve(pts.size());
                     for (auto& t : pts){
                         Renderer::TFPoint p{std::get<0>(t), std::get<1>(t), std::get<2>(t), std::get<3>(t), std::get<4>(t)};
                         cpp.push_back(p);
                     }
                     self.setTransferFunctionPoints(cpp);
                 }, py::arg("points"),
                 "Set custom transfer function points as list of (position,r,g,b,a) with values in [0,1]")
            // Slicer controls
            .def("set_slice_mode", &Renderer::setSliceMode, py::arg("enabled"), "Enable/disable slicer view")
            .def("set_slice_axis", &Renderer::setSliceAxis, py::arg("axis"), "Set slicer axis: 0=Z,1=Y,2=X")
            .def("set_slice_index", &Renderer::setSliceIndex, py::arg("index"), "Set slice index");

    // --- VTKVolumeData bindings ---
    py::class_<VTKVolumeData::Field>(m, "VTKField")
          .def_readonly("name", &VTKVolumeData::Field::name)
          .def_readonly("minVal", &VTKVolumeData::Field::minVal)
          .def_readonly("maxVal", &VTKVolumeData::Field::maxVal);

    py::class_<VTKVolumeData>(m, "VTKVolumeData")
          .def_property_readonly("dim_x", [](const VTKVolumeData& v){ return v.dimensions.x; })
          .def_property_readonly("dim_y", [](const VTKVolumeData& v){ return v.dimensions.y; })
          .def_property_readonly("dim_z", [](const VTKVolumeData& v){ return v.dimensions.z; })
          .def_property_readonly("spacing_x", [](const VTKVolumeData& v){ return v.spacing.x; })
          .def_property_readonly("spacing_y", [](const VTKVolumeData& v){ return v.spacing.y; })
          .def_property_readonly("spacing_z", [](const VTKVolumeData& v){ return v.spacing.z; })
          .def_property_readonly("origin_x", [](const VTKVolumeData& v){ return v.origin.x; })
          .def_property_readonly("origin_y", [](const VTKVolumeData& v){ return v.origin.y; })
          .def_property_readonly("origin_z", [](const VTKVolumeData& v){ return v.origin.z; })
          .def_property_readonly("num_fields", [](const VTKVolumeData& v){ return (int)v.fields.size(); })
          .def("field_name", [](const VTKVolumeData& v, int idx){
               if (idx < 0 || idx >= (int)v.fields.size()) return std::string();
               return v.fields[(size_t)idx].name;
          }, py::arg("index"));

    // --- VTKRenderer bindings ---
    py::class_<VTKRenderer>(m, "VTKRenderer")
            .def(py::init<>())
            .def("load_vtk", &VTKRenderer::loadVTK, py::arg("filename"))
            .def("init", &VTKRenderer::init)
            .def("render", &VTKRenderer::render)
            .def("resize", &VTKRenderer::resize, py::arg("width"), py::arg("height"))
            .def("camera_rotate", &VTKRenderer::camera_rotate, py::arg("dx"), py::arg("dy"))
            .def("camera_zoom", &VTKRenderer::camera_zoom, py::arg("delta"))
            .def("set_camera_angles", &VTKRenderer::set_camera_angles, py::arg("azimuthDeg"), py::arg("elevationDeg"))
            .def("set_colormap_preset", &VTKRenderer::setColormapPreset, py::arg("preset_index"))
            .def("set_bounding_box_scale", &VTKRenderer::setBoundingBoxScale, py::arg("scale"))
            .def("set_show_bounding_box", &VTKRenderer::setShowBoundingBox, py::arg("show"))
            .def("frame_camera_to_box", &VTKRenderer::frameCameraToBox)
            .def("set_colormap_mode_custom", &VTKRenderer::setColormapModeCustom, py::arg("use_custom"))
            .def("set_transfer_function_points",
                 [](VTKRenderer& self, const std::vector<std::tuple<float,float,float,float,float>>& pts){
                     std::vector<VTKRenderer::TFPoint> cpp;
                     cpp.reserve(pts.size());
                     for (auto& t : pts){
                         VTKRenderer::TFPoint p{std::get<0>(t), std::get<1>(t), std::get<2>(t), std::get<3>(t), std::get<4>(t)};
                         cpp.push_back(p);
                     }
                     self.setTransferFunctionPoints(cpp);
                 }, py::arg("points"))
            .def("set_slice_mode", &VTKRenderer::setSliceMode, py::arg("enabled"))
            .def("set_slice_axis", &VTKRenderer::setSliceAxis, py::arg("axis"))
            .def("set_slice_index", &VTKRenderer::setSliceIndex, py::arg("index"))
            .def("is_volume_loaded", &VTKRenderer::isVolumeLoaded)
            .def("get_volume_width", &VTKRenderer::getVolumeWidth)
            .def("get_volume_height", &VTKRenderer::getVolumeHeight)
            .def("get_volume_depth", &VTKRenderer::getVolumeDepth)
            .def("get_spacing_x", &VTKRenderer::getSpacingX)
            .def("get_spacing_y", &VTKRenderer::getSpacingY)
            .def("get_spacing_z", &VTKRenderer::getSpacingZ)
            .def("get_num_fields", &VTKRenderer::getNumFields)
            .def("get_current_field_index", &VTKRenderer::getCurrentFieldIndex)
            .def("set_current_field_index", &VTKRenderer::setCurrentFieldIndex, py::arg("index"))
            .def("get_vtk_volume", &VTKRenderer::getVTKVolume, py::return_value_policy::reference_internal)
            .def("get_current_field_as_numpy", [](VTKRenderer& self) {
                VTKVolumeData* vol = self.getVTKVolume();
                if (!vol || vol->empty() || self.getNumFields() == 0) {
                    return py::array_t<float>();
                }
                int fidx = self.getCurrentFieldIndex();
                auto& field = vol->fields[std::max(0, std::min(fidx, (int)vol->fields.size()-1))];
                if (field.data.empty()) return py::array_t<float>();
                const ssize_t Z = vol->dimensions.z;
                const ssize_t Y = vol->dimensions.y;
                const ssize_t X = vol->dimensions.x;
                return py::array_t<float>(
                    {Z, Y, X},
                    {Y*X*(ssize_t)sizeof(float), X*(ssize_t)sizeof(float), (ssize_t)sizeof(float)},
                    field.data.data()
                );
            }, "Returns current field as NumPy array (view into C++ memory; do not hold after renderer is destroyed)");


}