cmake_minimum_required(VERSION 3.0)
project(TOF)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -pthread")

# PF32 SDK 所在目录（.h 和 .so 文件），根据哪吒实际路径修改
set(PF32_SDK_DIR /home/ding/pf32/c++_sample_linux-1.5.23/PhotonForce/C++)

include_directories(${PF32_SDK_DIR})
link_directories(${PF32_SDK_DIR})

# ExampleTOF 依赖 PF32 SDK，仅当源文件存在时构建
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/ExampleTOF.cpp")
    add_executable(ExampleTOF ExampleTOF.cpp)
    target_link_libraries(ExampleTOF PF32_API)
endif()

# sim_pf32: 纯标准 C 库，不依赖 PF32 SDK，可在任意 Linux 上编译
add_executable(sim_pf32 sim_pf32.cpp)
target_compile_options(sim_pf32 PRIVATE -std=c++11)
