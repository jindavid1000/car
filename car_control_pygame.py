#!/usr/bin/env python3
import time
import serial
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
            print(f"底盘控制错误: {e}")
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

    def control_loop(self):
        try:
            print("\n开始主循环...")
            
            while True:
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
                    self.arduino.write(b'1\n')
                    setBuzzer(1)
                    time.sleep(0.05)
                    setBuzzer(0)
                else:
                    self.arduino.write(b'0\n')
                
                if self.gamepad.get_button(XboxButtons.A):  # A键紧急停止
                    print("紧急停止")
                    self.chassis.reset_motors()
                    self.arduino.write(b'0\n')
                    setBuzzer(1)
                    time.sleep(0.2)
                    setBuzzer(0)
                    self.servo5_pulse = 1500
                    self.servo6_pulse = 1500
                    setPWMServoPulse(SERVO_TILT, self.servo5_pulse, 1000)
                    setPWMServoPulse(SERVO_PAN, self.servo6_pulse, 1000)
                
                time.sleep(0.02)  # 50Hz更新率

        except Exception as e:
            print(f"发生错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("正在退出...")
            self.chassis.reset_motors()
            self.arduino.write(b'0\n')
            self.arduino.close()
            self.gamepad.close()

if __name__ == '__main__':
    controller = GamepadController()
    controller.control_loop() 