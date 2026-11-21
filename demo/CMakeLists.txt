chuds_fg_add_shaders(chuds_fg_demo_shaders
  OUT_HEADER "${CMAKE_CURRENT_BINARY_DIR}/generated/demo_shaders.h"
  SHADERS shaders/fullscreen.vert shaders/scene.frag)

add_executable(chuds_fg_demo main.cpp)
add_dependencies(chuds_fg_demo chuds_fg_demo_shaders)
target_include_directories(chuds_fg_demo PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_link_libraries(chuds_fg_demo PRIVATE Vulkan::Vulkan PkgConfig::GLFW3)
target_compile_options(chuds_fg_demo PRIVATE -Wall -Wextra -Wno-missing-field-initializers)
install(TARGETS chuds_fg_demo RUNTIME DESTINATION bin)
