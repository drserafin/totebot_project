#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from . import motoron 
import sys

# =====================================================================
# 🚀 HOW TO RUN THIS NODE
# 1. Jump into the docker container: docker exec -it totebot_brain /bin/bash
# 2. Run Dummy Mode (Testing):       ros2 run totebot_hardware motor_driver --ros-args -p dummy_mode:=true
# 3. Run Live Mode (Hardware):       ros2 run totebot_hardware motor_driver
#
# 🛠️ HOW TO TUNE PARAMETERS LIVE
# While the node is running, open a SECOND terminal, enter the docker 
# container, and use these commands to change how the robot drives:
#
#   Change Top Speed instantly:      ros2 param set /motoron_driver max_speed 400
#   Change Acceleration limits:      ros2 param set /motoron_driver accel_limit 80
#   Change Braking (Deceleration):   ros2 param set /motoron_driver decel_limit 200
#
# List all available parameters:     ros2 param list
# =====================================================================

class MotoronRosDriver(Node):
    def __init__(self):
        super().__init__('motoron_driver')
        self.hardware_connected = False
        
        # 🟢 DECLARE ROS 2 PARAMETERS (Replaces hardcoded macros)
        self.declare_parameter('dummy_mode', False)
        self.declare_parameter('max_speed', 600)       # Top speed (0 to 800)
        self.declare_parameter('accel_limit', 140)     # Lower = smoother acceleration
        self.declare_parameter('decel_limit', 300)     # Lower = longer braking
        self.declare_parameter('cmd_timeout_ms', 100)  # STOP if no signal
        self.declare_parameter('min_vin_mv', 4500)     # 4.5V Minimum cutoff
        
        self.is_dummy_mode = self.get_parameter('dummy_mode').value
        
        self.error_mask = (
            (1 << motoron.STATUS_FLAG_PROTOCOL_ERROR) |
            (1 << motoron.STATUS_FLAG_CRC_ERROR) |
            (1 << motoron.STATUS_FLAG_COMMAND_TIMEOUT_LATCHED) |
            (1 << motoron.STATUS_FLAG_MOTOR_FAULT_LATCHED) |
            (1 << motoron.STATUS_FLAG_NO_POWER_LATCHED) |
            (1 << motoron.STATUS_FLAG_RESET) |
            (1 << motoron.STATUS_FLAG_COMMAND_TIMEOUT))

        self.setup_motoron()

        self.subscription = self.create_subscription(
            Twist, '/cmd_vel', self.listener_callback, 10)
        
        self.timer = self.create_timer(0.1, self.health_check_callback)
        
        if self.is_dummy_mode:
            self.get_logger().warn("🚀 TOTEBOT BACKEND READY (LAUNCHED IN DUMMY MODE)")
        else:
            self.get_logger().info("🚀 TOTEBOT BACKEND READY (LIVE HARDWARE MODE)")

    def setup_motoron(self):
        try:
            self.mc = motoron.MotoronI2C()
            self.mc.reinitialize()
            self.mc.clear_reset_flag()
            self.mc.clear_latched_status_flags(0xFFFF) 
            self.mc.clear_motor_fault()

            self.mc.set_error_response(motoron.ERROR_RESPONSE_COAST)
            self.mc.set_error_mask(self.error_mask)
            
            # Read hardware parameters once during setup
            cmd_timeout = self.get_parameter('cmd_timeout_ms').value
            accel = self.get_parameter('accel_limit').value
            decel = self.get_parameter('decel_limit').value

            self.mc.set_command_timeout_milliseconds(cmd_timeout)
            
            for motor in [1,2]:
                self.mc.set_max_acceleration(motor, accel)
                self.mc.set_max_deceleration(motor, decel)
            
            self.mc.clear_motor_fault()
            self.hardware_connected = True
            
        except Exception as e:
            self.hardware_connected = False
            self.get_logger().error(f"⚠️ MOTORON I2C NOT FOUND: {e}")

    def health_check_callback(self):
        if not self.hardware_connected:
            return

        try:
            status = self.mc.get_status_flags()
            voltage = self.mc.get_vin_voltage_mv(3300, motoron.VinSenseType.MOTORON_HP)
            min_vin = self.get_parameter('min_vin_mv').value
            
            if self.is_dummy_mode:
                return 

            if voltage < min_vin:
                self.get_logger().error(f"🛑 LOW VOLTAGE: {voltage}mV. SHUTTING DOWN.")
                self.emergency_stop()

            if (status & self.error_mask):
                self.get_logger().error(f"❌ CONTROLLER ERROR: 0x{status:x}. SHUTTING DOWN.")
                self.emergency_stop()

        except Exception as e:
            self.get_logger().error(f"🏥 HEALTH CHECK FAILED: {e}")
            self.emergency_stop()

    def listener_callback(self, msg):
        # 🟢 Live-read the max speed so it can be changed on the fly while driving!
        current_max_speed = self.get_parameter('max_speed').value

        left = int((msg.linear.x - msg.angular.z) * current_max_speed)
        right = int((msg.linear.x + msg.angular.z) * current_max_speed)
        
        left = max(min(left, 800), -800)
        right = max(min(right, 800), -800)

        if self.hardware_connected and not self.is_dummy_mode:
            try:
                self.mc.set_speed(1, left)
                self.mc.set_speed(2, right)
            except Exception as e: 
                # 🟢 Catch and log I2C noise/drops instead of silently passing
                self.get_logger().warn(f"⚠️ I2C WRITE FAILED: {e}", throttle_duration_sec=1.0)
        else:
            self.get_logger().info(f"🕹️ DUMMY MODE -> L: {left} | R: {right}", throttle_duration_sec=0.5)

    def emergency_stop(self):
        if self.hardware_connected:
            try:
                self.mc.reset() # Force motors to coast
            except Exception: 
                pass
        
        # 🟢 Graceful ROS 2 shutdown instead of a raw sys.exit(1)
        self.get_logger().fatal("🛑 Initiating safe node shutdown due to hardware fault.")
        self.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    node = MotoronRosDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass # Handle standard Ctrl+C cleanly
    finally:
        if node.hardware_connected:
            try:
                node.mc.reset()
            except Exception: 
                pass
        # Double check if the node hasn't already been destroyed by emergency_stop
        try:
            node.destroy_node()
        except:
            pass
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()