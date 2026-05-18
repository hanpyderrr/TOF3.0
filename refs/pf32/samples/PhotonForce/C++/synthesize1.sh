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

while $should_run
do
    # 数据采集并保存到raw.dat文件
    ./Example
    #./exec
    # 提取数据文件并保存到cut.dat
    ./cut512
    
    # 显示图像数据
    #后面&符号会将display.py命令放入后台执行，从而允许脚本继续执行接下来的命令。这样，即使display.py在执行期间，脚本也会继续进行数据采集和等待10秒的操作
    python3 display_clear.py &
    
    # 等待10秒 sleep 10
    sleep 5
    # 检查是否有用户输入并选择是否停止脚本
    if [[ -t 0 && ! -t 1 ]]; then
        read -t 5 -p "Press 'q' to stop the script and close the display window: " input
        if [ "$input" = "q" ]; then
            pkill -f "python display_clear.py"
            should_run=false
        fi
    fi
done
