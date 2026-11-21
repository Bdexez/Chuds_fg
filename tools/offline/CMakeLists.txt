# chuds_fg_offline — the frame-generation engine on a PPM sequence, headless (no
# window, surface or layer). Feeds tools/eval_sequence.py; see CONTRIBUTING.md.
add_executable(chuds_fg_offline
  chuds_fg_offline.cpp
  ${CHUDS_FG_ENGINE_SOURCES}
)
add_dependencies(chuds_fg_offline chuds_fg_layer_shaders)
target_include_directories(chuds_fg_offline PRIVATE
  "${CMAKE_BINARY_DIR}/layer/generated"
  "${CMAKE_SOURCE_DIR}/layer/src")
target_link_libraries(chuds_fg_offline PRIVATE chuds_fg_core Vulkan::Vulkan)
target_compile_options(chuds_fg_offline PRIVATE -Wall -Wextra -Wno-missing-field-initializers)
