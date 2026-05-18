import numpy as np  
import matplotlib.pyplot as plt  
import os  
import tkinter as tk  # 用于获取屏幕尺寸  

def get_screen_size():  
    """获取屏幕尺寸，返回宽度和高度（以像素为单位）"""  
    root = tk.Tk()  
    root.withdraw()  # 隐藏主窗口  
    screen_width = root.winfo_screenwidth()  # 屏幕宽度  
    screen_height = root.winfo_screenheight()  # 屏幕高度  
    return screen_width, screen_height  

def read_and_display_images(filename, image_size=(32, 32)):  
    plt.ion()  # 开启交互模式  

    screen_width, screen_height = get_screen_size()  # 获取屏幕尺寸  
    # 将像素转换为英寸，假设屏幕分辨率为 100 像素/英寸（DPI）  
    dpi = 100  
    window_size = (screen_width / dpi, screen_height / dpi)  # 计算窗口大小（英寸）  

    fig = plt.figure(figsize=window_size)  # 设置图形窗口的大小  

    while True:  
        # 检查文件是否存在  
        if not os.path.exists(filename):  
            print(f"File {filename} not found!")  
            return  

        try:  
            # 读取文件数据  
            with open(filename, 'r') as f:  
                data = f.readlines()  

            # 确保文件有20行  
            if len(data) != 20:  
                print("The file does not contain exactly 20 lines.")  
                return  

            # 处理每一行数据  
            images = []  
            for line in data:  
                # 将每行数据转换为 numpy 数组  
                numbers = list(map(float, line.split()))  
                if len(numbers) != image_size[0] * image_size[1]:  
                    print(f"Each line must contain exactly {image_size[0] * image_size[1]} ({image_size[0]}x{image_size[1]}) numbers.")  
                    return  
                # 转换为指定大小的数组并添加到图像列表  
                image = np.array(numbers).reshape(image_size)  
                images.append(image)  

            # 显示图像  
            for i, image in enumerate(images):  
                plt_flipped = np.flipud(image)#图像垂直翻转
                plt.imshow(plt_flipped, cmap='gray', vmin=0, vmax=255)  
                plt.axis('off')  # 关闭坐标轴显示  
                plt.pause(0.01)  # 每幅图像显示 50ms  
                plt.clf()  # 清空当前图像为下一幅图像做准备  

        except Exception as e:  
            print(f"An error occurred: {e}")  

if __name__ == "__main__":  
    filename = "cut.dat"  # 文件名  
    image_size = (32, 32)  # 每幅图像的大小为 32x32  
    read_and_display_images(filename, image_size)
