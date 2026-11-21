# chuds_fg_capture — the Windows capture product (mode 2 of docs/windows-capture.md):
# capture a game's window with Windows.Graphics.Capture, interop the D3D11
# texture into Vulkan, run the layer's frame-generation engine (framegen.cpp
# and the embedded shaders, unchanged) and present real + generated frames in
# a borderless always-on-top overlay. Console app: logs go to stderr. MSVC
# only (C++/WinRT ships with the Windows SDK).

add_executable(chuds_fg_capture
  src/main.cpp
  src/launcher.cpp
  src/capture.cpp
  src/vkctx.cpp
  src/tray.cpp
  src/injection.cpp
  src/report.cpp
  # The layer's engine and device helpers, shared as source: they only
  # depend on chuds_fg_core and the generated shaders.h. platform.cpp joins for
  # platformConfigPath() (the launcher's config-file save).
  ${CHUDS_FG_ENGINE_SOURCES}
  ../layer/src/platform.cpp
)
add_dependencies(chuds_fg_capture chuds_fg_layer_shaders)
# layer/src before src: the engine's files in layer/src/passes/ include
# "log.h" and must get the layer's (CHUDS_FG_INFO), not the capture app's —
# capture files still find their own log.h first, in their own directory.
target_include_directories(chuds_fg_capture PRIVATE
  "${CMAKE_SOURCE_DIR}/layer/src"
  "${CMAKE_BINARY_DIR}/layer/generated"
  src)
# windowsapp: C++/WinRT activation (RoGetActivationFactory & co.);
# dwmapi: extended frame bounds / cloaked state of the target window.
target_link_libraries(chuds_fg_capture PRIVATE chuds_fg_core Vulkan::Vulkan d3d11 dxgi dwmapi winmm windowsapp shell32 psapi)
target_compile_definitions(chuds_fg_capture PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX CHUDS_FG_VERSION_STR="${PROJECT_VERSION}")
chuds_fg_strict(chuds_fg_capture)
# Only our own sources see the Win32 Vulkan platform header (windows.h in
# tow); the layer sources compile exactly as they do in the DLL.
set_source_files_properties(src/main.cpp src/capture.cpp src/vkctx.cpp
  PROPERTIES COMPILE_DEFINITIONS VK_USE_PLATFORM_WIN32_KHR)
if(MSVC)
  # /Zc:__cplusplus: C++/WinRT checks the real language level; /utf-8: the
  # sources (and the usage text) are UTF-8.
  target_compile_options(chuds_fg_capture PRIVATE /W4 /EHsc /permissive- /Zc:__cplusplus /utf-8 /bigobj)
endif()
install(TARGETS chuds_fg_capture RUNTIME DESTINATION bin)
