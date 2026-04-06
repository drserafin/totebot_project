#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from rcl_interfaces.msg import SetParametersResult 
from . import motoron 
import sys

# =====================================================================
# 🚀 TOTEBOT MOTOR DRIVER (motor_driver.py)
# =====================================================================
# 📖 QUICK START: LIVE PARAMETER TUNING
# You can change robot settings (like max speed) while it is driving!
#
# [STEP 1] Keep your main robot launch terminal running.
# [STEP 2] Open a NEW terminal and enter the brain:
#          docker exec -it totebot_brain bash
# [STEP 3] Source ROS 2:
#          source /opt/ros/jazzy/setup.bash
# [STEP 4] Send a new parameter command:
#          ros2 param set /motor_driver <parameter_name> <value>
#
# 🌟 AVAILABLE PARAMETERS:
# - max_speed      (int): 0 to 800 (Absolute speed limit)
# - accel_limit    (int): Lower = smoother ramp-up (Default: 140)
# - decel_limit    (int): Lower = longer braking (Default: 300)
# - cmd_timeout_ms (int): MS before stop if signal lost (Default: 200)
#
# Example: ros2 param set /motor_driver max_speed 800
# =====================================================================

class MotoronRosDriver(Node):
    def __init__(self):
        super().__init__('motoron_driver')
        self.hardware_connected = False
        
        # 🟢 DECLARE ROS 2 PARAMETERS
        self.declare_parameter('dummy_mode', False)
        self.declare_parameter('max_speed', 600)       # Standard: 600, Max: 800
        self.declare_parameter('accel_limit', 140)     # Lower = smoother
        self.declare_parameter('decel_limit', 300)     # Lower = longer braking
        self.declare_parameter('cmd_timeout_ms', 200)  # Stop if signal lost
        self.declare_parameter('min_vin_mv', 4500)     # 4.5V cutoff

        self.is_dummy_mode = self.get_parameter('dummy_mode').value
        
        # 🟢 THE "NO-PANIC" MASK (Fixes 0x2404 Crash)
        self.error_mask = (
            (1 << motoron.STATUS_FLAG_PROTOCOL_ERROR) |
            (1 << motoron.STATUS_FLAG_CRC_ERROR) |
            (1 << motoron.STATUS_FLAG_COMMAND_TIMEOUT))

        # 🟢 REGISTER PARAMETER CALLBACK (Tracks changes in Terminal)
        self.add_on_set_parameters_callback(self.parameter_callback)

        # Initialize the hardware
        self.setup_motoron()

        # Listen for Joystick (via ROS Bridge)
        self.subscription = self.create_subscription(
            Twist, '/cmd_vel', self.listener_callback, 10)
        
        # Health Check Timer (Runs every 100ms)
        self.timer = self.create_timer(0.1, self.health_check_callback)
        
        if self.is_dummy_mode:
            self.get_logger().warn("🚀 TOTEBOT BACKEND READY (DUMMY MODE)")
        else:
            self.get_logger().info("🚀 TOTEBOT BACKEND READY (LIVE HARDWARE MODE)")

    def parameter_callback(self, params):
        """Wakes up whenever 'ros2 param set' is used."""
        for param in params:
            self.get_logger().info(f"⚙️  PARAM UPDATED: {param.name} = {param.value}")
            
            # Sync changes with the physical Motoron board live
            if self.hardware_connected and not self.is_dummy_mode:
                try:
                    if param.name == 'accel_limit':
                        for m in [1,2]: self.mc.set_max_acceleration(m, param.value)
                    elif param.name == 'decel_limit':
                        for m in [1,2]: self.mc.set_max_deceleration(m, param.value)
                    elif param.name == 'cmd_timeout_ms':
                        self.mc.set_command_timeout_milliseconds(param.value)
                except Exception as e:
                    self.get_logger().error(f"❌ Failed to sync param to hardware: {e}")

        return SetParametersResult(successful=True)

    def setup_motoron(self):
        """Attempts to initialize the Motoron I2C hardware."""
        try:
            self.mc = motoron.MotoronI2C()
            self.mc.reinitialize()

            # 🟢 THE DEEP CLEAR (Wipes memory of short circuits/faults)
            self.mc.clear_reset_flag()
            self.mc.clear_latched_status_flags(0xFFFF) 
            self.mc.clear_motor_fault()

            # Apply Safety Settings
            cmd_timeout = self.get_parameter('cmd_timeout_ms').value
            accel = self.get_parameter('accel_limit').value
            decel = self.get_parameter('decel_limit').value

            self.mc.set_error_response(motoron.ERROR_RESPONSE_COAST)
            self.mc.set_error_mask(self.error_mask)
            self.mc.set_command_timeout_milliseconds(cmd_timeout)
            
            for motor in [1, 2]:
                self.mc.set_max_acceleration(motor, accel)
                self.mc.set_max_deceleration(motor, decel)
            
            self.mc.clear_motor_fault()
            self.hardware_connected = True
            
        except Exception as e:
            self.hardware_connected = False
            self.get_logger().error(f"⚠️ MOTORON I2C SETUP FAILED: {e}")
            self.get_logger().warn("🤖 FALLING BACK TO DUMMY MODE")

    def health_check_callback(self):
        """Monitors VIN Voltage and Protocol Errors."""
        if not self.hardware_connected or self.is_dummy_mode:
            return

        try:
            status = self.mc.get_status_flags()
            voltage = self.mc.get_vin_voltage_mv(3300, motoron.VinSenseType.MOTORON_256)
            min_vin = self.get_parameter('min_vin_mv').value
            
            if voltage < min_vin and voltage > 500:
                self.get_logger().error(f"🛑 LOW VOLTAGE: {voltage}mV. SHUTTING DOWN.")
                self.emergency_stop()

            if (status & self.error_mask):
                self.get_logger().error(f"❌ CONTROLLER ERROR: 0x{status:x}. SHUTTING DOWN.")
                self.emergency_stop()

        except Exception as e:
            self.get_logger().error(f"🏥 HEALTH CHECK FAILED: {e}")
            self.emergency_stop()

    def listener_callback(self, msg):
        """Converts Twist messages to L/R motor speeds."""
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
                self.get_logger().warn(f"⚠️ I2C WRITE FAILED: {e}", throttle_duration_sec=1.0)
        else:
            self.get_logger().info(f"🕹️ L: {left} | R: {right}", throttle_duration_sec=0.5)

    def emergency_stop(self):
        """Kills power and exits."""
        if self.hardware_connected:
            try: self.mc.reset()
            except: pass
        self.get_logger().fatal("🛑 Safe node shutdown initiated.")
        self.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    node = MotoronRosDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass 
    finally:
        if node.hardware_connected:
            try: node.mc.reset()
            except: pass
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__ == '__main__':
    main()