cmake_minimum_required(VERSION 3.0)
project(TOF)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -pthread")

# PF32 SDK 所在目录（.h 和 .so 文件）。
# 用 1.5.21 而非 1.5.23：1.5.23 的 libPF32_API.so 需 GLIBCXX_3.4.32（GCC 13+），
# 哪吒系统 g++ 11.4（libstdc++ 3.4.30）链接失败；1.5.21 仅需 3.4.21，匹配。
set(PF32_SDK_DIR /home/ding/pf32/c++_sample_linux-1.5.21/PhotonForce/Linux)

include_directories(${PF32_SDK_DIR})
link_directories(${PF32_SDK_DIR})

# ExampleTOF 依赖 PF32 SDK，仅当源文件存在时构建。
# rpath 让二进制运行时直接找到 SDK 的 .so，无需 LD_LIBRARY_PATH。
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/ExampleTOF.cpp")
    add_executable(ExampleTOF ExampleTOF.cpp)
    target_link_libraries(ExampleTOF PF32_API)
    set_target_properties(ExampleTOF PROPERTIES
        BUILD_RPATH "${PF32_SDK_DIR}"
        INSTALL_RPATH "${PF32_SDK_DIR}")
endif()

# sim_pf32: 纯标准 C 库，不依赖 PF32 SDK，可在任意 Linux 上编译
add_executable(sim_pf32 sim_pf32.cpp)
target_compile_options(sim_pf32 PRIVATE -std=c++11)
