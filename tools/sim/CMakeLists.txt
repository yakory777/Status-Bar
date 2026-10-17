# Симулятор прошивки: тот же UI-код (firmware/main), LVGL 9.2, без железа.
#
#   cmake -S tools/sim -B build/sim && cmake --build build/sim -j
#   build/sim/agent_sim tools/sim/scenarios/demo.txt out.rgb565
#
# Готовые исходники LVGL и cJSON можно подсунуть: -DLVGL_DIR=... -DCJSON_DIR=...
cmake_minimum_required(VERSION 3.16)
project(agent_status_sim C)

set(CMAKE_C_STANDARD 11)
set(FW ${CMAKE_CURRENT_SOURCE_DIR}/../../firmware/main)

include(FetchContent)

if(NOT LVGL_DIR)
    FetchContent_Declare(lvgl GIT_REPOSITORY https://github.com/lvgl/lvgl.git
                         GIT_TAG v9.2.2 GIT_SHALLOW TRUE)
    FetchContent_Populate(lvgl)
    set(LVGL_DIR ${lvgl_SOURCE_DIR})
endif()
if(NOT CJSON_DIR)
    FetchContent_Declare(cjson GIT_REPOSITORY https://github.com/DaveGamble/cJSON.git
                         GIT_TAG v1.7.18 GIT_SHALLOW TRUE)
    FetchContent_Populate(cjson)
    set(CJSON_DIR ${cjson_SOURCE_DIR})
endif()

set(LV_CONF_PATH ${CMAKE_CURRENT_SOURCE_DIR}/lv_conf.h CACHE STRING "" FORCE)
set(CONFIG_LV_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(CONFIG_LV_BUILD_DEMOS OFF CACHE BOOL "" FORCE)
add_subdirectory(${LVGL_DIR} lvgl EXCLUDE_FROM_ALL)
target_include_directories(lvgl PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# Шрифты встраиваются так же, как EMBED_FILES в ESP-IDF: символы _binary_<имя>_start/_end
file(GLOB FONT_FILES CONFIGURE_DEPENDS RELATIVE ${FW}/fonts ${FW}/fonts/*.ttf)
set(FONT_OBJS)
foreach(f ${FONT_FILES})
    string(MAKE_C_IDENTIFIER ${f} id)
    set(obj ${CMAKE_CURRENT_BINARY_DIR}/font_${id}.o)
    add_custom_command(OUTPUT ${obj}
        COMMAND ${CMAKE_LINKER} -r -b binary -o ${obj} ${f}
        WORKING_DIRECTORY ${FW}/fonts
        DEPENDS ${FW}/fonts/${f})
    list(APPEND FONT_OBJS ${obj})
endforeach()

file(GLOB FW_UI_SOURCES CONFIGURE_DEPENDS ${FW}/ui_*.c)   # всё, что рисует, — тот же код, что на плате
add_executable(agent_sim
    sim_main.c
    sim_platform.c
    ${FW}/protocol.c
    ${FW_UI_SOURCES}
    ${CJSON_DIR}/cJSON.c
    ${FONT_OBJS})
target_include_directories(agent_sim PRIVATE ${FW} ${CJSON_DIR})
target_compile_definitions(agent_sim PRIVATE AGENT_SIM=1)
target_compile_options(agent_sim PRIVATE -Wall -Wextra -Wno-unused-parameter)
target_link_libraries(agent_sim PRIVATE lvgl m)
if(NOT APPLE)
    target_link_options(agent_sim PRIVATE -Wl,-z,noexecstack)
endif()
