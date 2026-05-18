#!/bin/bash

cd /home/ding/pf32/c++_sample_linux-1.5.23/PhotonForce/C++

rm -rf CMakeFiles
rm cmake_install.cmake
rm CMakeCache.txt
rm *.o
rm Makefile
rm Example
rm FW_Histogramming
rm Cooled
rm DualCamera
rm Correlator
rm *.log
rm *.dat


cmake .
cmake --build .

should_run=true
    #前面删除了.dat文件，这里必须执行一遍采集数据和分割数据的程序，否则后面出错
    ./Example
    ./cut512
    ./send_exec &
    python3 tsh_image.py &
    
while $should_run
do
    # 数据采集并保存到raw.dat文件
    ./Example
    
    # 提取raw.dat文件数据并保存到cut.dat
    ./cut512
    
    # 显示图像数据
    #后面&符号会将display.py命令放入后台执行，从而允许脚本继续执行接下来的命令。这样，即使display.py在执行期间，脚本也会继续进行数据采集和等待10秒的操作
    #python3 display_clear.py &
    
     # 等待10秒 sleep 10
    sleep 1


done
