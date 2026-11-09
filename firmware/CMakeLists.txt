cmake_minimum_required(VERSION 3.13)

include(pico_sdk_import.cmake)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

project(yagi_flower_switch C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# RP2040-Zero is an RP2040 board.
set(PICO_BOARD pico)

pico_sdk_init()

set(CMAKE_EXECUTABLE_SUFFIX ".elf")
add_executable(yagi_flower_switch
    main.c
    antenna_config.c
    command_line.c
    controller.c
    log.c
    rf_switch.c
    rotator.c
    antenna_select.c
)

# Generate build_info.h at make-time (note: not at cmake configure time).
add_custom_target(generate_build_info ALL
    COMMAND ${CMAKE_COMMAND}
        -DOUTPUT_FILE=${CMAKE_CURRENT_BINARY_DIR}/build_info.h
        -DSOURCE_DIR=${CMAKE_CURRENT_SOURCE_DIR}
        -P ${CMAKE_CURRENT_SOURCE_DIR}/cmake/generate_build_info.cmake
    BYPRODUCTS ${CMAKE_CURRENT_BINARY_DIR}/build_info.h
    COMMENT "Generating build_info.h"
    VERBATIM
)
target_include_directories(yagi_flower_switch PRIVATE ${CMAKE_CURRENT_BINARY_DIR})
add_dependencies(yagi_flower_switch generate_build_info)

# Always force -O3 optimization level.
target_compile_options(yagi_flower_switch PRIVATE -O3)

target_link_libraries(yagi_flower_switch
    pico_stdlib
    hardware_gpio
    hardware_watchdog
)

# USB-CDC for serial; disable UART stdio, apparently so we don't burn pins.
pico_enable_stdio_usb(yagi_flower_switch  1)
pico_enable_stdio_uart(yagi_flower_switch 0)

# Produce .uf2 output to flash.
pico_add_bin_output(yagi_flower_switch)
pico_add_uf2_output(yagi_flower_switch)
