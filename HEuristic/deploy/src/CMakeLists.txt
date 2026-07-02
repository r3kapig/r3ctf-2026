cmake_minimum_required(VERSION 3.16)

project(HEuristic LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

set(SEAL_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/thirdparty/seal")
if(NOT EXISTS "${SEAL_SOURCE_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "SEAL is missing. Clone it into thirdparty/seal first.")
endif()

set(BUILD_SHARED_LIBS OFF CACHE BOOL "Build shared libraries" FORCE)
set(SEAL_BUILD_DEPS OFF CACHE BOOL "Automatically download and build SEAL dependencies" FORCE)
set(SEAL_USE_MSGSL OFF CACHE BOOL "Use Microsoft GSL" FORCE)
set(SEAL_USE_ZLIB OFF CACHE BOOL "Use ZLIB" FORCE)
set(SEAL_USE_ZSTD OFF CACHE BOOL "Use Zstandard" FORCE)
set(SEAL_USE_INTEL_HEXL OFF CACHE BOOL "Use Intel HEXL" FORCE)
set(SEAL_BUILD_EXAMPLES OFF CACHE BOOL "Build SEAL examples" FORCE)
set(SEAL_BUILD_TESTS OFF CACHE BOOL "Build SEAL tests" FORCE)
set(SEAL_BUILD_BENCH OFF CACHE BOOL "Build SEAL benchmarks" FORCE)
set(SEAL_BUILD_SEAL_C OFF CACHE BOOL "Build SEAL C library" FORCE)

add_subdirectory("${SEAL_SOURCE_DIR}" "${CMAKE_BINARY_DIR}/seal" EXCLUDE_FROM_ALL)

add_executable(he_server server.cc)
set_target_properties(he_server PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)

target_link_libraries(he_server PRIVATE SEAL::seal)
