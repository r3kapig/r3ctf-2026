cmake_minimum_required(VERSION 3.16)
project(P1gROXY LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

set(ZLIB_VENDOR_DIR ${CMAKE_CURRENT_SOURCE_DIR}/vendor/zlib)
set(ZLIB_SOURCES
  ${ZLIB_VENDOR_DIR}/adler32.c
  ${ZLIB_VENDOR_DIR}/compress.c
  ${ZLIB_VENDOR_DIR}/crc32.c
  ${ZLIB_VENDOR_DIR}/deflate.c
  ${ZLIB_VENDOR_DIR}/infback.c
  ${ZLIB_VENDOR_DIR}/inffast.c
  ${ZLIB_VENDOR_DIR}/inflate.c
  ${ZLIB_VENDOR_DIR}/inftrees.c
  ${ZLIB_VENDOR_DIR}/trees.c
  ${ZLIB_VENDOR_DIR}/uncompr.c
  ${ZLIB_VENDOR_DIR}/zutil.c
)

add_library(p1groxy_zlib STATIC ${ZLIB_SOURCES})
target_include_directories(p1groxy_zlib PUBLIC ${ZLIB_VENDOR_DIR})
target_compile_definitions(p1groxy_zlib PRIVATE HAVE_HIDDEN)
set_target_properties(p1groxy_zlib PROPERTIES POSITION_INDEPENDENT_CODE ON)

file(GLOB_RECURSE P1GROXY_SOURCES CONFIGURE_DEPENDS
  ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp
)

add_executable(P1gROXY ${P1GROXY_SOURCES})
target_include_directories(P1gROXY PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${ZLIB_VENDOR_DIR}
)
target_link_libraries(P1gROXY PRIVATE p1groxy_zlib pthread)
target_compile_options(P1gROXY PRIVATE
  -Wall -Wextra -Wpedantic -Wconversion -fstack-protector-strong
)
target_compile_definitions(P1gROXY PRIVATE _FORTIFY_SOURCE=2)
target_link_options(P1gROXY PRIVATE -Wl,-z,relro,-z,now)
