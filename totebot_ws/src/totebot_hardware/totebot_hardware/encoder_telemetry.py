#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32MultiArray, Float32MultiArray
import math

# =====================================================================
# 🤖 TOTEBOT ENCODER TELEMETRY NODE (encoder_telemetry.py)
# =====================================================================
# Sits between the ESP32 and the rest of the system.
# Converts raw hardware counts into meaningful telemetry.
# Deliberately knows NOTHING about motors or PID — reusable anywhere.
#
# SUBSCRIBES:  encoder_array      (Int32MultiArray  — from ESP32)
# PUBLISHES:   /encoder_telemetry (Float32MultiArray — to PID + anyone)
#
# Float32MultiArray layout:
#   [0] left_raw_counts
#   [1] right_raw_counts
#   [2] left_rpm
#   [3] right_rpm
#   [4] left_delta_counts
#   [5] right_delta_counts
#   [6] left_velocity_ms
#   [7] right_velocity_ms
#   [8] linear_velocity_ms     (robot center)
#   [9] angular_velocity_rads
#
# MONITOR LIVE:
#   ros2 topic echo /encoder_telemetry
# =====================================================================

CPR                   = 1993.6
WHEEL_DIAMETER_M      = 0.0927
WHEEL_CIRCUMFERENCE_M = math.pi * WHEEL_DIAMETER_M
WHEELBASE_M           = 0.635
GEAR_RATIO            = 2.0   

class EncoderTelemetryNode(Node):
    def __init__(self):
        super().__init__('encoder_telemetry')

        self.prev_left_counts  = 0
        self.prev_right_counts = 0
        self.prev_time         = self.get_clock().now()
        self.first_message     = True

        self.subscription = self.create_subscription(
            Int32MultiArray,
            'encoder_array',
            self.encoder_callback,
            10)

        self.telemetry_publisher = self.create_publisher(
            Float32MultiArray,
            '/encoder_telemetry',
            10)

        self.get_logger().info("📡 ENCODER TELEMETRY NODE READY")
        self.get_logger().info(
            f"   CPR: {CPR} | Wheel: {WHEEL_DIAMETER_M*1000:.1f}mm "
            f"| Wheelbase: {WHEELBASE_M*1000:.0f}mm "
            f"| Circumference: {WHEEL_CIRCUMFERENCE_M*1000:.1f}mm"
        )

    def encoder_callback(self, msg):
        if len(msg.data) < 2:
            self.get_logger().warn(
                f"encoder_array has {len(msg.data)} value(s), expected at least 2. Skipping.",
                throttle_duration_sec=2.0)
            return

        left_counts  = -msg.data[0]
        right_counts = msg.data[1]
        

        now  = self.get_clock().now()
        dt_s = (now - self.prev_time).nanoseconds / 1e9

        # Seed state on first message — don't publish garbage deltas
        if self.first_message:
            self.prev_left_counts  = left_counts
            self.prev_right_counts = right_counts
            self.prev_time         = now
            self.first_message     = False
            return

        if dt_s <= 0.0:
            return

        # --- Delta counts ---
        delta_left  = left_counts  - self.prev_left_counts
        delta_right = right_counts - self.prev_right_counts

        # --- RPM ---
        left_rpm  = (delta_left  / CPR) / dt_s * 60.0 / GEAR_RATIO
        right_rpm = (delta_right / CPR) / dt_s * 60.0 / GEAR_RATIO

        # --- Velocity (m/s) ---
        left_vel  = (delta_left  / CPR) * WHEEL_CIRCUMFERENCE_M / dt_s / GEAR_RATIO
        right_vel = (delta_right / CPR) * WHEEL_CIRCUMFERENCE_M / dt_s / GEAR_RATIO

        # --- Robot-level kinematics ---
        linear_vel  = (left_vel + right_vel) / 2.0
        angular_vel = (right_vel - left_vel) / WHEELBASE_M

        # --- Update state ---
        self.prev_left_counts  = left_counts
        self.prev_right_counts = right_counts
        self.prev_time         = now

        # --- Terminal log (throttled to 5Hz) ---
        # self.get_logger().info(
        #     f"[ENC] "
        #     f"L: {left_counts:8d}  R: {right_counts:8d} cnt | "
        #     f"L: {left_rpm:+7.2f}  R: {right_rpm:+7.2f} RPM | "
        #     f"lin: {linear_vel:+6.3f} m/s  ang: {angular_vel:+6.3f} rad/s",
        #     throttle_duration_sec=2
        # )

        # --- Publish ---
        telemetry = Float32MultiArray()
        telemetry.data = [
            float(left_counts),   # [0]
            float(right_counts),  # [1]
            float(left_rpm),      # [2]
            float(right_rpm),     # [3]
            float(delta_left),    # [4]
            float(delta_right),   # [5]
            float(left_vel),      # [6]
            float(right_vel),     # [7]
            float(linear_vel),    # [8]
            float(angular_vel),   # [9]
        ]
        self.telemetry_publisher.publish(telemetry)

def main(args=None):
    rclpy.init(args=args)
    node = EncoderTelemetryNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()

    