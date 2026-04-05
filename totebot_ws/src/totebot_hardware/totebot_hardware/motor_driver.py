#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from rcl_interfaces.msg import SetParametersResult 
from . import motoron 
import sys

# =====================================================================
# 🚀 TOTEBOT MOTOR DRIVER - FINAL PRODUCTION STACK (2026)
# =====================================================================
# ⚙️ LIVE PARAMETER TUNING GUIDE
# IMPORTANT: You must use TWO separate terminals to tune parameters.
# You cannot set a parameter if the robot is not currently running!
#
# --- TERMINAL 1 (The Engine Room) ---
# This terminal runs the master switch and keeps the robot alive.
# 1. Enter container:  docker exec -it totebot_brain bash
# 2. Source ROS:       source /opt/ros/jazzy/setup.bash && source /totebot_ws/install/setup.bash
# 3. Start Robot:      ros2 launch totebot_bringup hardware.launch.py
# 
# --- TERMINAL 2 (The Control Room) ---
# Open a second terminal to the Raspberry Pi to send commands.
# 1. Enter container:  docker exec -it totebot_brain bash
# 2. Source ROS:       source /opt/ros/jazzy/setup.bash
# 3. Change param:     ros2 param set /motor_driver <parameter> <value>
#
# EXAMPLE COMMANDS:
# ros2 param set /motor_driver max_speed 800
# ros2 param set /motor_driver accel_limit 100
#
# WHY "/motor_driver"? 
# Even though the Python class is 'motoron_driver', our hardware.launch.py 
# file intentionally renames the node to '/motor_driver' for cleaner networking.
#
# AVAILABLE PARAMETERS:
# - max_speed      (int):  0 to 800 (Absolute limit).
# - accel_limit    (int):  Lower value = smoother ramp-up.
# - decel_limit    (int):  Lower value = longer braking.
# - cmd_timeout_ms (int):  MS before stop if signal lost.
# - min_vin_mv     (int):  Voltage cutoff (4500 = 4.5V).
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
                        for m in: self.mc.set_max_acceleration(m, param.value)
                    elif param.name == 'decel_limit':
                        for m in: self.mc.set_max_deceleration(m, param.value)
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
            self.