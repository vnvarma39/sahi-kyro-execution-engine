cmake_minimum_required(VERSION 3.22)
project(sahi_cpp_simd_greeks VERSION 3.2.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(sahi_simd_greeks INTERFACE)
target_include_directories(sahi_simd_greeks INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})

if(MSVC)
    target_compile_options(sahi_simd_greeks INTERFACE /O2 /arch:AVX512 /fp:fast)
else()
    target_compile_options(sahi_simd_greeks INTERFACE -O3 -mavx512f -mavx512dq -ffast-math -fopenmp-simd)
endif()
