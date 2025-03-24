#!/usr/bin/env python3
import pygame
import time

class Gamepad:
    def __init__(self):
        """初始化手柄"""
        pygame.init()
        pygame.joystick.init()
        
        # 连接手柄
        joystick_count = pygame.joystick.get_count()
        print(f"检测到 {joystick_count} 个游戏手柄")
        
        if joystick_count > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"已连接手柄: {self.joystick.get_name()}")
            print(f"轴数量: {self.joystick.get_numaxes()}")
            print(f"按钮数量: {self.joystick.get_numbuttons()}")
            
            # 等待用户按下并释放两个扳机进行校准
            print("请按下并释放两个扳机（LT和RT）以校准...")
            self._calibrate_triggers()
        else:
            raise Exception("未检测到手柄设备")

    def _calibrate_triggers(self):
        """等待两个扳机都被按下并释放"""
        lt_pressed = rt_pressed = False
        lt_released = rt_released = False
        
        while not (lt_released and rt_released):
            lt = self.joystick.get_axis(2)
            rt = self.joystick.get_axis(5)
            
            # 检测按下
            if not lt_pressed and lt > -0.5:
                lt_pressed = True
            if not rt_pressed and rt > -0.5:
                rt_pressed = True
                
            # 检测释放
            if lt_pressed and lt < -0.9:
                lt_released = True
            if rt_pressed and rt < -0.9:
                rt_released = True
            
            # 显示当前状态
            status = []
            if not lt_pressed:
                status.append("等待按下LT")
            elif not lt_released:
                status.append("等待释放LT")
            if not rt_pressed:
                status.append("等待按下RT")
            elif not rt_released:
                status.append("等待释放RT")
            print(f"\r当前状态: {', '.join(status)}", end="")
            
            pygame.event.pump()
            time.sleep(0.02)
        
        print("\n校准完成！")

    def get_axis(self, axis):
        """获取指定轴的值"""
        return self.joystick.get_axis(axis)

    def get_button(self, button):
        """获取指定按钮的状态"""
        return self.joystick.get_button(button)

    def update(self):
        """更新手柄状态"""
        pygame.event.pump()

    def format_trigger_value(self, value):
        """格式化扳机值，从0%到100%"""
        percentage = (value + 1) * 50  # 从-1到1映射到0%到100%
        return percentage

    def close(self):
        """关闭手柄"""
        pygame.quit()

# Xbox 360手柄按键映射
class XboxButtons:
    A = 0
    B = 1
    X = 2
    Y = 3
    LB = 4
    RB = 5
    BACK = 6
    START = 7
    GUIDE = 8
    LEFT_STICK = 9
    RIGHT_STICK = 10

# Xbox 360手柄轴映射
class XboxAxes:
    LEFT_X = 0
    LEFT_Y = 1
    LEFT_TRIGGER = 2
    RIGHT_X = 3
    RIGHT_Y = 4
    RIGHT_TRIGGER = 5
    DPAD_X = 6
    DPAD_Y = 7 