# chuds_fg_options: layer/options_ui.conf + the option registry -> options_ui.json,
# read by the GTK panel (installed next to it). Run at every build, so a UI
# line naming an option the engine does not know fails the build.
# A cross build cannot run it: it installs the JSON of a native build instead
# (CHUDS_FG_OPTIONS_JSON; the file does not depend on the architecture).
set(CHUDS_FG_OPTIONS_JSON "" CACHE FILEPATH "A prebuilt options_ui.json to install (cross builds, where chuds_fg_options cannot run)")
if(CHUDS_FG_OPTIONS_JSON)
  install(FILES "${CHUDS_FG_OPTIONS_JSON}" DESTINATION share/chuds-fg)
  return()
endif()
if(CMAKE_CROSSCOMPILING AND NOT CMAKE_CROSSCOMPILING_EMULATOR)
  message(WARNING "Cross build without CHUDS_FG_OPTIONS_JSON: the control panel's options_ui.json is not generated")
  return()
endif()
add_executable(chuds_fg_options chuds_fg_options.cpp)
target_link_libraries(chuds_fg_options PRIVATE chuds_fg_core)
set(CHUDS_FG_OPTIONS_UI_JSON "${CMAKE_BINARY_DIR}/options_ui.json")
add_custom_command(
  OUTPUT "${CHUDS_FG_OPTIONS_UI_JSON}"
  COMMAND chuds_fg_options "${CMAKE_SOURCE_DIR}/layer/options_ui.conf" "${CMAKE_SOURCE_DIR}/layer/options_ui.en.conf"
          "${CHUDS_FG_OPTIONS_UI_JSON}"
  DEPENDS chuds_fg_options "${CMAKE_SOURCE_DIR}/layer/options_ui.conf" "${CMAKE_SOURCE_DIR}/layer/options_ui.en.conf"
  COMMENT "Generating options_ui.json")
add_custom_target(chuds_fg_options_ui ALL DEPENDS "${CHUDS_FG_OPTIONS_UI_JSON}")
install(FILES "${CHUDS_FG_OPTIONS_UI_JSON}" DESTINATION share/chuds-fg)
