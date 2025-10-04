//
// Created by akashmaji on 10/4/25.
//

// bindings/src/renderer_bindings.cpp

// bindings/src/renderer_bindings.cpp
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include "../../backend/include/Renderer.h" // From backend/include/

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
            // Controls
            .def("set_show_bounding_box", &Renderer::setShowBoundingBox, py::arg("show"), "Show or hide the bounding box")
            .def("set_colormap_preset", &Renderer::setColormapPreset, py::arg("preset_index"), "Set colormap preset (0..9)");

}