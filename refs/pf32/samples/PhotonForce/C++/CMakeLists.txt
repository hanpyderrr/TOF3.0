#指定项目所需的最低CMake版本为3.0。这告诉CMake运行时需要使用至少这个版本的CMake工具
cmake_minimum_required(VERSION 3.0)

#定义项目的名称为SampleCode。这里指定了项目的名称，用于标识和组织项目。
project(SampleCode)

#添加${CMAKE_SOURCE_DIR}（即CMakeLists.txt文件所在的目录）到项目的包含目录中。这样编译器就能够找到包含在这个目录中的头文件
include_directories(${CMAKE_SOURCE_DIR})
# 添加${CMAKE_SOURCE_DIR}到项目的链接目录中。这样链接器就能够找到链接在这个目录中的库文件
link_directories(${CMAKE_SOURCE_DIR})


#如果系统为Windows（WIN32），则设置C++标准为11 (set (CMAKE_CXX_STANDARD 11))；否则，设置C++编译标志为-std=c++11 -pthread
if(WIN32)
   set (CMAKE_CXX_STANDARD 11)
else ()
   set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -pthread")
endif ()

#用于设置一个名为Example的可执行文件所需的源文件和头文件
#定义了一个变量Example_SOURCES，并将其设置为一个包含Example.cpp的列表。这意味着Example.cpp是构建Example可执行文件所需的源文件之一
set(Example_SOURCES
   Example.cpp
)

#定义了一个变量Example_HEADERS，并将其设置为包含两个头文件API/PF32_API.h和API/PF_types.h的列表
#这些头文件包含了在Example.cpp中使用的函数和数据结构的声明，以便在编译时能够正确引用和使用它们
set(Example_HEADERS
   API/PF32_API.h
   API/PF_types.h
)

#set命令分别定义了不同可执行文件的源文件列表和头文件列表
set(FW_Histogramming_SOURCES
   FW_Histogramming.cpp
)

set(FW_Histogramming_HEADERS
   API/PF32_API.h
   API/PF_types.h
)


set(DualCamera_SOURCES
   DualCamera.cpp
)

set(DualCamera_HEADERS
   API/PF32_API.h
   API/PF_types.h
)




set(Cooled_SOURCES
   Cooled.cpp
)

set(Cooled_HEADERS
   API/PF32_API.h
   API/PF_types.h
)


set(Correlator_SOURCES
   Correlator.cpp
)

set(Correlator_HEADERS
   API/PF32_CORRELATOR_API.h
   API/PF32_API.h
   API/PF_types.h
)

set(Footer_SOURCES
   Footer.cpp
)

set(Footer_HEADERS
   API/PF32_API.h
   API/PF_types.h
)


#根据操作系统的不同，设置了PF32_API和PF32_CORRELATOR_API库文件的名称
if(WIN32)
   set (PF32_API "PF32_API.lib" )
   set (PF32_CORRELATOR_API "PF32_CORRELATOR_API.lib" )
else()
   set (PF32_API "libPF32_API.so" )
   set (PF32_CORRELATOR_API "libPF32_CORRELATOR_API.so" )
endif()


#使用add_executable命令将每个可执行文件与对应的源文件进行关联
#使用target_link_libraries命令将所需的库文件链接到对应的可执行文件上

#添加一个可执行文件目标，名为Example，并且将${Example_SOURCES}中列出的源文件链接到可执行文件上
add_executable(Example ${Example_SOURCES}) #${Example_SOURCES}包含一个名为Example.cpp的源文件
target_link_libraries(Example PF32_API) #将PF32_API库链接到该可执行文件上

add_executable(FW_Histogramming ${FW_Histogramming_SOURCES})
target_link_libraries(FW_Histogramming PF32_API)

add_executable(DualCamera ${DualCamera_SOURCES})
target_link_libraries(DualCamera PF32_API)

add_executable(Cooled ${Cooled_SOURCES})
target_link_libraries(Cooled PF32_API)

add_executable(Correlator ${Correlator_SOURCES})
target_link_libraries(Correlator PF32_API PF32_CORRELATOR_API)

add_executable(Footer ${Footer_SOURCES})
target_link_libraries(Footer PF32_API)

