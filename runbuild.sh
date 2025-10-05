# runbuild.sh  
# runs the executable 'renderer-x86_64'
# run 'createbuild.sh' script first to create the executable

__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia QT_XCB_GL_INTEGRATION=xcb_glx ./renderer-x86_64
