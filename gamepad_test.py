#!/usr/bin/env python3
import pygame
import sys
import time

# 初始化pygame和字体
pygame.init()
pygame.font.init()

# 创建窗口
WINDOW_SIZE = (800, 600)
screen = pygame.display.set_mode(WINDOW_SIZE)
pygame.display.set_caption("手柄测试程序")

# 设置字体
font = pygame.font.SysFont('SimHei', 20)  # 使用黑体，确保能显示中文

class GamepadTester:
    def __init__(self):
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
            
            # 记录初始状态
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
            
        else:
            raise Exception("未检测到手柄设备")

    def draw_text(self, text, pos, color=(255, 255, 255)):
        """在屏幕上绘制文本"""
        text_surface = font.render(text, True, color)
        screen.blit(text_surface, pos)

    def format_trigger_value(self, value):
        """格式化扳机值，从0%到100%"""
        # 将-1到1的值映射到0%到100%
        percentage = (value + 1) * 50  # 从-1到1映射到0到100
        return f"{percentage:.0f}%"

    def run(self):
        try:
            running = True
            while running:
                # 处理事件
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False

                # 清空屏幕
                screen.fill((0, 0, 0))

                # 显示手柄信息
                self.draw_text(f"手柄: {self.joystick.get_name()}", (10, 10))

                # 显示所有轴的值
                y = 50
                for i in range(self.joystick.get_numaxes()):
                    value = self.joystick.get_axis(i)
                    name = self.get_axis_name(i)
                    
                    # 对于扳机，显示百分比
                    if i in [2, 5]:  # LT和RT
                        display_value = self.format_trigger_value(value)
                        color = (0, 255, 0) if value > -0.9 else (255, 255, 255)
                    else:  # 其他轴
                        display_value = f"{value:.2f}"
                        color = (0, 255, 0) if abs(value) > 0.1 else (255, 255, 255)
                    
                    self.draw_text(f"{name}: {display_value}", (10, y), color)
                    y += 30

                # 显示所有按钮的状态
                x = 400
                y = 50
                for i in range(self.joystick.get_numbuttons()):
                    value = self.joystick.get_button(i)
                    name = self.get_button_name(i)
                    color = (0, 255, 0) if value else (255, 255, 255)
                    self.draw_text(f"{name}: {value}", (x, y), color)
                    y += 30

                # 更新显示
                pygame.display.flip()
                time.sleep(0.02)  # 50Hz刷新率

        finally:
            pygame.quit()

    def get_axis_name(self, axis):
        """获取轴的名称"""
        names = {
            0: "左摇杆X",
            1: "左摇杆Y",
            2: "左扳机LT",
            3: "右摇杆X",
            4: "右摇杆Y",
            5: "右扳机RT",
            6: "方向键X",
            7: "方向键Y"
        }
        return names.get(axis, f"轴{axis}")

    def get_button_name(self, button):
        """获取按钮的名称"""
        names = {
            0: "A键",
            1: "B键",
            2: "X键",
            3: "Y键",
            4: "LB键",
            5: "RB键",
            6: "Back键",
            7: "Start键",
            8: "Xbox键",
            9: "左摇杆按下",
            10: "右摇杆按下"
        }
        return names.get(button, f"按钮{button}")

if __name__ == '__main__':
    try:
        tester = GamepadTester()
        tester.run()
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1) 