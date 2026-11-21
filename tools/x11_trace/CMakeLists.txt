# chuds-fg-x11-trace — a development tool (not installed): records the X Present
# completion events of the windows on screen, read-only, and replays a trace
# through the layer's refresh-grid estimator (PresentTimeline).
add_executable(chuds-fg-x11-trace chuds_fg_x11_trace.cpp)
target_include_directories(chuds-fg-x11-trace PRIVATE "${CMAKE_SOURCE_DIR}/layer/src")
target_link_libraries(chuds-fg-x11-trace PRIVATE chuds_fg_core)
target_compile_options(chuds-fg-x11-trace PRIVATE -Wall -Wextra)
find_package(PkgConfig QUIET)
if(PkgConfig_FOUND)
  pkg_check_modules(CHUDS_FG_XCB_PRESENT IMPORTED_TARGET xcb xcb-present)
endif()
if(CHUDS_FG_XCB_PRESENT_FOUND)
  target_link_libraries(chuds-fg-x11-trace PRIVATE PkgConfig::CHUDS_FG_XCB_PRESENT)
  target_compile_definitions(chuds-fg-x11-trace PRIVATE CHUDS_FG_HAVE_XCB_PRESENT)
else()
  message(STATUS "xcb-present not found: chuds-fg-x11-trace built without `watch` (replay only)")
endif()
