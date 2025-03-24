#!/usr/bin/env python3
import time
import serial
import cv2
import numpy as np
from sys import path
import glob
path.append('/home/pi/MasterPi/')
from HiwonderSDK.Board import setPWMServoPulse, setBuzzer
from HiwonderSDK.mecanum import MecanumChassis
from gamepad import Gamepad, XboxButtons, XboxAxes

def find_arduino_port():
    ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
    return ports[0] if ports else None

ARDUINO_PORT = find_arduino_port() or '/dev/ttyUSB0'

# 硬件配置
SERVO_PAN = 6  # 水平舵机（编号6）
SERVO_TILT = 5 # 垂直舵机（编号5）

class GamepadController:
    def __init__(self):
        # 初始化手柄
        self.gamepad = Gamepad()
        
        # 初始化麦克纳姆轮底盘
        self.chassis = MecanumChassis()
        
        # 初始化硬件
        self.arduino = serial.Serial(ARDUINO_PORT, 115200, timeout=0.1)
        self.chassis.reset_motors()
        
        # 初始化舵机位置
        self.servo5_pulse = 1500
        self.servo6_pulse = 1500
        setPWMServoPulse(SERVO_TILT, self.servo5_pulse, 1000)
        setPWMServoPulse(SERVO_PAN, self.servo6_pulse, 1000)
        time.sleep(1)

        # 初始化摄像头
        self.cap = cv2.VideoCapture('http://127.0.0.1:8080?action=stream')
        
        # 添加发射按钮状态追踪
        self.b_button_pressed = False
        
        # 添加鼠标位置追踪
        self.mouse_x = 0
        self.mouse_y = 0

    def map_axis(self, value, deadzone=0.1):
        """摇杆轴值处理（带死区）"""
        if abs(value) < deadzone:
            return 0.0
        return round(value, 2)

    def control_chassis(self, x, y, turn_rate):
        """麦克纳姆轮移动控制（包含转向）"""
        max_speed = 50  # 降低最大速度方便测试
        max_turn = 50   # 降低最大转向速度
        
        # 使用translation方法控制移动，反转y轴方向
        vx = x * max_speed
        vy = -y * max_speed  # 反转Y轴方向
        turn = turn_rate * max_turn
        
        try:
            if abs(turn) > 0.1:  # 如果有转向，使用set_velocity
                self.chassis.set_velocity(0, 0, turn/max_turn)  # 归一化转向速度
            else:  # 没有转向，使用translation进行平移
                self.chassis.translation(vx, vy)
        except Exception as e:
            self.chassis.reset_motors()

    def control_servos(self, rx, ry):
        """云台舵机控制"""
        servo_speed = 10  # 舵机移动速度
        
        # 水平方向控制6号舵机（反转方向）
        if abs(rx) > 0.1:
            self.servo6_pulse -= int(rx * servo_speed)  # 反转方向
            self.servo6_pulse = max(500, min(2500, self.servo6_pulse))
            setPWMServoPulse(SERVO_PAN, self.servo6_pulse, 20)
        
        # 垂直方向控制5号舵机（反转方向）
        if abs(ry) > 0.1:
            self.servo5_pulse -= int(ry * servo_speed)  # 反转方向
            self.servo5_pulse = max(500, min(2500, self.servo5_pulse))
            setPWMServoPulse(SERVO_TILT, self.servo5_pulse, 20)

    def mouse_callback(self, event, x, y, flags, param):
        """鼠标事件回调函数"""
        self.mouse_x = x
        self.mouse_y = y

    def create_debug_frame(self):
        """创建调试帧，用于在摄像头不可用时显示"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, "Camera Disconnected", (180, 240),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        return frame

    def control_loop(self):
        cv2.namedWindow('Robot Control', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Robot Control', 960, 480)  # 增加窗口宽度以容纳参数显示
        cv2.setMouseCallback('Robot Control', self.mouse_callback)  # 设置鼠标回调
        
        while True:
            try:
                # 更新手柄状态
                self.gamepad.update()
                
                # 读取摇杆值
                lx = self.map_axis(self.gamepad.get_axis(XboxAxes.LEFT_X))
                ly = self.map_axis(self.gamepad.get_axis(XboxAxes.LEFT_Y))
                rx = self.map_axis(self.gamepad.get_axis(XboxAxes.RIGHT_X))
                ry = self.map_axis(self.gamepad.get_axis(XboxAxes.RIGHT_Y))
                
                # 读取扳机值（用于转向）
                lt = self.gamepad.get_axis(XboxAxes.LEFT_TRIGGER)
                rt = self.gamepad.get_axis(XboxAxes.RIGHT_TRIGGER)
                
                # 计算转向值
                turn_rate = 0
                if lt > -0.9:  # 左扳机按下，左转
                    lt_value = self.gamepad.format_trigger_value(lt) / 100.0
                    turn_rate = -lt_value
                if rt > -0.9:  # 右扳机按下，右转
                    rt_value = self.gamepad.format_trigger_value(rt) / 100.0
                    turn_rate = rt_value
                
                # 控制底盘移动和转向
                if abs(lx) > 0.1 or abs(ly) > 0.1 or abs(turn_rate) > 0.1:
                    self.control_chassis(lx, ly, turn_rate)
                else:
                    self.chassis.reset_motors()
                
                # 控制云台舵机
                self.control_servos(rx, ry)
                
                # 处理按钮
                if self.gamepad.get_button(XboxButtons.B):  # B键控制发射
                    if not self.b_button_pressed:  # 只在第一次按下时发送1
                        self.arduino.write(b'1\n')
                        setBuzzer(1)
                        time.sleep(0.05)
                        setBuzzer(0)
                        self.b_button_pressed = True
                else:
                    if self.b_button_pressed:  # 松开按钮时发送0
                        self.arduino.write(b'0\n')
                        self.b_button_pressed = False
                
                if self.gamepad.get_button(XboxButtons.A):  # A键紧急停止
                    self.chassis.reset_motors()
                    self.arduino.write(b'0\n')
                    setBuzzer(1)
                    time.sleep(0.2)
                    setBuzzer(0)
                    self.servo5_pulse = 1500
                    self.servo6_pulse = 1500
                    setPWMServoPulse(SERVO_TILT, self.servo5_pulse, 1000)
                    setPWMServoPulse(SERVO_PAN, self.servo6_pulse, 1000)

                # 读取并显示摄像头画面
                ret, frame = self.cap.read()
                if not ret:
                    frame = self.create_debug_frame()

                # 在画面上画准心
                center = (264, 386)
                size = 20  # 准心大小
                color = (0, 255, 0)  # 绿色
                thickness = 2
                # 画十字准心
                cv2.line(frame, (center[0] - size, center[1]), (center[0] + size, center[1]), color, thickness)  # 水平线
                cv2.line(frame, (center[0], center[1] - size), (center[0], center[1] + size), color, thickness)  # 垂直线

                # 创建信息显示区域
                info_panel = np.zeros((480, 320, 3), dtype=np.uint8)
                
                # 准备显示信息
                info_text = [
                    f"Mouse Position: ({self.mouse_x}, {self.mouse_y})",
                    f"Left Stick: ({lx:.2f}, {ly:.2f})",
                    f"Right Stick: ({rx:.2f}, {ry:.2f})",
                    f"Left Trigger: {lt:.2f}",
                    f"Right Trigger: {rt:.2f}",
                    f"PTZ Position: ({self.servo6_pulse}, {self.servo5_pulse})",
                    "Press ESC to Exit",
                    "Press A for Emergency Stop",
                    "Press B to Fire"
                ]
                
                # 在信息面板上显示文本
                y = 30
                for text in info_text:
                    cv2.putText(info_panel, text, (10, y), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                              (0, 255, 0), 2)
                    y += 30
                
                # 合并摄像头画面和信息面板
                display = np.hstack((frame, info_panel))
                
                # 显示画面
                cv2.imshow('Robot Control', display)
                
                # 按ESC退出
                key = cv2.waitKey(1)
                if key == 27:  # ESC
                    break

            except Exception:
                pass
            
            time.sleep(0.02)  # 50Hz更新率

        # 清理资源
        self.chassis.reset_motors()
        self.arduino.write(b'0\n')
        self.arduino.close()
        self.gamepad.close()
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    controller = GamepadController()
    controller.control_loop() 