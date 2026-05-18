cmake_minimum_required(VERSION 3.0)

project(SampleCode)

include_directories(${CMAKE_SOURCE_DIR})
link_directories(${CMAKE_SOURCE_DIR})



if(WIN32)
   set (CMAKE_CXX_STANDARD 11)
else ()
   set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -pthread")
endif ()


set(Example_SOURCES
   Example.cpp
)

set(Example_HEADERS
   API/PF32_API.h
   API/PF_types.h
)

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




if(WIN32)
   set (PF32_API "PF32_API.lib" )
   set (PF32_CORRELATOR_API "PF32_CORRELATOR_API.lib" )
else()
   set (PF32_API "libPF32_API.so" )
   set (PF32_CORRELATOR_API "libPF32_CORRELATOR_API.so" )
endif()



add_executable(Example ${Example_SOURCES})
target_link_libraries(Example PF32_API)

add_executable(FW_Histogramming ${FW_Histogramming_SOURCES})
target_link_libraries(FW_Histogramming PF32_API)

add_executable(DualCamera ${DualCamera_SOURCES})
target_link_libraries(DualCamera PF32_API)

add_executable(Cooled ${Cooled_SOURCES})
target_link_libraries(Cooled PF32_API)

add_executable(Correlator ${Correlator_SOURCES})
target_link_libraries(Correlator PF32_API PF32_CORRELATOR_API)

