//
// Created by akashmaji on 10/4/25.
//

// bindings/src/main.cpp

#include <pybind11/pybind11.h>

// Forward declaration of the function that will define our bindings.
// This keeps the binding code for different classes in separate, organized files.
void bind_renderer(pybind11::module_& m);

// The PYBIND11_MODULE macro creates the entry point that will be called when
// the Python interpreter imports the module.
// - The first argument, 'volumerenderer', is the name of the Python module.
//   This MUST match the target name given in the pybind11_add_module command
//   in your root CMakeLists.txt.
// - The second argument, 'm', is a variable of type py::module_ which is the
//   main interface for creating bindings.
PYBIND11_MODULE(volumerenderer, m) {
    m.doc() = "Python bindings for the C++ Volume Renderer"; // Optional module docstring

    // Call the function to bind the Renderer class
    bind_renderer(m);

    // In the future, you would add calls to other binding functions here:
    // bind_camera(m);
    // bind_transfer_function(m);
}