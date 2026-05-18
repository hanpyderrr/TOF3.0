# -*- coding: utf-8 -*-

import numpy as np
import cv2

# 创建一个显示窗口
cv2.namedWindow("Image", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Image", cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

# 获取显示屏幕的宽度和高度
screen_width = 800  # 设置为您的显示屏幕宽度
screen_height = 480  # 设置为您的显示屏幕高度

while True:
    # 从 raw.dat 文件中读取数据
    with open("cutzhong.dat", "r") as file:
        data = file.readlines()

    frames = []

    # 遍历每一行数据，将数据转换为图像数据并存储到frames列表中
    for line in data:
        # 读取每一行数据并以空格分割
        values = line.strip().split(' ')

        # 转换每个数字为整数并存储在frame_data中
        frame_data = []
        for value in values:
            try:
                frame_data.append(int(value))
            except ValueError:
                continue

        # 将数据转换为 numpy 数组，并重塑为 32x32 的灰度图像
        frame = np.array(frame_data, dtype=np.uint8).reshape(32, 32)
        frames.append(frame)

    for frame in frames:
        # 获取图像的大小
        height, width = frame.shape

        # 计算缩放比例
        scale = min(screen_width / width, screen_height / height)

        # 调整图像大小，使用最近邻插值算法
        frame_resized = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)  # 使用 cv2.INTER_NEAREST 表示最近邻插值算法

        # 旋转图像180度
        rotated_frame = cv2.rotate(frame_resized, cv2.ROTATE_180)  # 旋转180度

        # 显示图像
        cv2.imshow("Image", rotated_frame)
        key = cv2.waitKey(500)  # 等待 0.5 秒

    #等待按键事件，检查是否需要退出循环
    # key = cv2.waitKey(1)
    # if key == 27:  # 按下ESC键
        # break
        
      # 检查是否按下 ESC 键，如果是则退出循环
        if key == 27:  # 检查键值是否是 ASCII 中的 27（ESC 键）
            break

    # 如果按下 ESC 键则跳出外层循环，关闭窗口
    if key == 27:
        break
                
cv2.destroyAllWindows()
