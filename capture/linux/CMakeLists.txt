# chuds-fg-capture — frame generation by capture on Linux (X11 / Xwayland): the
# counterpart of the Windows chuds_fg_capture. Built when the X11 libraries
# (Xcomposite, Xdamage, Xext's MIT-SHM, Xfixes) are installed.
add_executable(chuds-fg-capture
  main.cpp
  x11_capture.cpp
  presenter.cpp
  ${CHUDS_FG_ENGINE_SOURCES}
  ../../layer/src/platform.cpp
)
add_dependencies(chuds-fg-capture chuds_fg_layer_shaders)
target_include_directories(chuds-fg-capture PRIVATE
  "${CMAKE_SOURCE_DIR}/layer/src"
  "${CMAKE_BINARY_DIR}/layer/generated"
  "${CMAKE_CURRENT_SOURCE_DIR}")
target_link_libraries(chuds-fg-capture PRIVATE chuds_fg_core Vulkan::Vulkan PkgConfig::CHUDS_FG_X11 Threads::Threads ${CMAKE_DL_LIBS})
target_compile_options(chuds-fg-capture PRIVATE -Wall -Wextra -Wno-missing-field-initializers)
chuds_fg_strict(chuds-fg-capture)
# Native Wayland windows through the screen-cast portal and PipeWire
# (--wayland), when libpipewire and GIO are there.
pkg_check_modules(CHUDS_FG_PW IMPORTED_TARGET libpipewire-0.3 gio-2.0 gio-unix-2.0)
if(CHUDS_FG_PW_FOUND)
  target_sources(chuds-fg-capture PRIVATE pw_capture.cpp)
  target_compile_definitions(chuds-fg-capture PRIVATE CHUDS_FG_PIPEWIRE=1)
  target_link_libraries(chuds-fg-capture PRIVATE PkgConfig::CHUDS_FG_PW)
else()
  message(STATUS "libpipewire-0.3 / gio-2.0 not found: chuds-fg-capture without Wayland capture (--wayland)")
endif()
install(TARGETS chuds-fg-capture RUNTIME DESTINATION bin)
