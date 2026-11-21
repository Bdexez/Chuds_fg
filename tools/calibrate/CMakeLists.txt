# chuds-fg-calibrate — the engine's cost on this GPU before any game (synthetic
# frames, headless): run by the control panel, the Windows launcher and
# `chuds-fg --calibrate`. Linux and Windows (x64).
add_executable(chuds-fg-calibrate
  chuds_fg_calibrate.cpp
  ${CHUDS_FG_ENGINE_SOURCES}
  ../../layer/src/platform.cpp
)
add_dependencies(chuds-fg-calibrate chuds_fg_layer_shaders)
target_include_directories(chuds-fg-calibrate PRIVATE
  "${CMAKE_SOURCE_DIR}/layer/src"
  "${CMAKE_BINARY_DIR}/layer/generated")
target_link_libraries(chuds-fg-calibrate PRIVATE chuds_fg_core Vulkan::Vulkan)
if(MSVC)
  target_compile_definitions(chuds-fg-calibrate PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX _CRT_SECURE_NO_WARNINGS)
  target_compile_options(chuds-fg-calibrate PRIVATE /W4 /EHsc /permissive- /utf-8 /bigobj)
else()
  target_compile_options(chuds-fg-calibrate PRIVATE -Wall -Wextra -Wno-missing-field-initializers)
endif()
chuds_fg_strict(chuds-fg-calibrate)
if(NOT WIN32)
  install(TARGETS chuds-fg-calibrate RUNTIME DESTINATION bin)
endif()
