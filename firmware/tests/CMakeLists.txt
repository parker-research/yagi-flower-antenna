# Host-side unit tests for the hardware-independent firmware modules.
# Built with the native compiler (not the Pico SDK):
#
#   cmake -S firmware/tests -B firmware/tests/build
#   cmake --build firmware/tests/build
#   ctest --test-dir firmware/tests/build --output-on-failure

cmake_minimum_required(VERSION 3.13)
project(yagi_flower_switch_tests C)
set(CMAKE_C_STANDARD 11)
enable_testing()

set(FIRMWARE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/..)
add_compile_options(-Wall -Wextra -Werror)

# The test supplies its own antenna table, so antenna_config.c is not linked.
add_executable(test_antenna_select
    test_antenna_select.c
    ${FIRMWARE_DIR}/antenna_select.c
)
target_include_directories(test_antenna_select PRIVATE ${FIRMWARE_DIR})
target_link_libraries(test_antenna_select m)
add_test(NAME antenna_select COMMAND test_antenna_select)

# The test supplies a fake controller; stubs/ stands in for Pico SDK + build_info.h.
add_executable(test_rotator
    test_rotator.c
    ${FIRMWARE_DIR}/rotator.c
    ${FIRMWARE_DIR}/log.c
)
target_include_directories(test_rotator PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/stubs ${FIRMWARE_DIR})
add_test(NAME rotator COMMAND test_rotator)
