#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray
from rcl_interfaces.msg import SetParametersResult
from . import motoron
import time
from threading import Lock

i2c_lock = Lock()

MOTOR_SPEED = 800

# M2H18v18 current sense type (3.3V system)
CURRENT_SENSE_TYPE = motoron.CurrentSenseType.MOTORON_18V20
REFERENCE_MV       = 3300


class MotoronRosDriver(Node):

    def __init__(self):
        super().__init__('open_loop_motor_driver')

        self.hardware_connected = False

        self.declare_parameter('dummy_mode',    False)
        self.declare_parameter('max_speed',     800)
        self.declare_parameter('accel_limit',   140)
        self.declare_parameter('decel_limit',   300)
        self.declare_parameter('cmd_timeout_ms',500)
        self.declare_parameter('min_vin_mv',    4500)

        self.is_dummy_mode = self.get_parameter('dummy_mode').value

        self.current_left_speed  = 0
        self.current_right_speed = 0

        # Pre-calculate milliamp conversion factor once (not every loop)
        self.current_units_ma = motoron.current_sense_units_milliamps(
            CURRENT_SENSE_TYPE, REFERENCE_MV
        )

        self.error_mask = (
            (1 << motoron.STATUS_FLAG_PROTOCOL_ERROR) |
            (1 << motoron.STATUS_FLAG_CRC_ERROR)      |
            (1 << motoron.STATUS_FLAG_COMMAND_TIMEOUT)
        )

        self.add_on_set_parameters_callback(self.parameter_callback)

        self.setup_motoron()

        # /cmd_vel subscriber
        self.subscription = self.create_subscription(
            Twist, '/cmd_vel', self.listener_callback, 10)

        # Current publisher — Float32MultiArray [left_ma, right_ma]
        self.current_publisher = self.create_publisher(
            Float32MultiArray, '/motor_current_ma', 10)

        # 200ms heartbeat (5Hz) — safe for I2C bus
        self.timer = self.create_timer(0.2, self.health_check_callback)

        self.get_logger().info("Open Loop Motor Driver Ready")
        self.get_logger().info(
            f"Current sense units: {self.current_units_ma:.4f} mA/unit"
        )

    # -----------------------------
    # Safe I2C wrapper
    # -----------------------------
    def safe_i2c(self, fn, retries=3):
        for _ in range(retries):
            try:
                with i2c_lock:
                    return fn()
            except Exception:
                time.sleep(0.01)
        raise Exception("I2C failed after retries")

    # -----------------------------
    # Setup motor controller
    # -----------------------------
    def setup_motoron(self):
        try:
            self.mc = motoron.MotoronI2C(address=0x11)

            with i2c_lock:
                self.mc.reinitialize()
                self.mc.clear_reset_flag()
                self.mc.clear_latched_status_flags(0xFFFF)
                self.mc.clear_motor_fault()

                # Set current sense minimum divisor so readings are valid at low speeds
                # (without this, current reads 0 below a speed threshold)
                self.mc.set_current_sense_minimum_divisor(1, 0)
                self.mc.set_current_sense_minimum_divisor(2, 0)

            self.hardware_connected = True

        except Exception as e:
            self.hardware_connected = False
            self.get_logger().error(f"Motoron init failed: {e}")

    # -----------------------------
    # cmd_vel callback
    # -----------------------------
    def listener_callback(self, msg):
        max_speed = self.get_parameter('max_speed').value

        target_linear  = -msg.linear.x
        target_angular =  msg.angular.z

        self.current_left_speed  = int((target_linear + target_angular) * max_speed)
        self.current_right_speed = int((target_linear - target_angular) * max_speed)

        self.current_left_speed  = max(min(self.current_left_speed,  800), -800)
        self.current_right_speed = max(min(self.current_right_speed, 800), -800)

    # -----------------------------
    # Heartbeat — runs at 5Hz
    # -----------------------------
    def health_check_callback(self):
        if not self.hardware_connected:
            return

        try:
            # --- Motor speed writes ---
            self.safe_i2c(lambda: self.mc.set_speed(1, self.current_left_speed))
            self.safe_i2c(lambda: self.mc.set_speed(2, self.current_right_speed))

            # --- Status + voltage ---
            status  = self.safe_i2c(lambda: self.mc.get_status_flags())
            voltage = self.safe_i2c(
                lambda: self.mc.get_vin_voltage_mv(3300, motoron.VinSenseType.MOTORON_256)
            )

            # --- Current sense (built-in to M2H18v18) ---
            raw_left  = self.safe_i2c(lambda: self.mc.get_current_sense_processed(1))
            raw_right = self.safe_i2c(lambda: self.mc.get_current_sense_processed(2))

            # Convert raw units → milliamps → amps
            left_ma  = raw_left  * self.current_units_ma
            right_ma = raw_right * self.current_units_ma
            left_a   = round(left_ma  / 1000.0, 3)
            right_a  = round(right_ma / 1000.0, 3)

            # Publish current
            cur_msg      = Float32MultiArray()
            cur_msg.data = [left_a, right_a]
            self.current_publisher.publish(cur_msg)

            # --- Voltage safety ---
            if voltage < self.get_parameter('min_vin_mv').value:
                self.get_logger().error("LOW VOLTAGE → STOP")
                self.current_left_speed  = 0
                self.current_right_speed = 0

            # --- Error safety ---
            if status & self.error_mask:
                self.get_logger().error("MOTOR ERROR → STOP")
                self.current_left_speed  = 0
                self.current_right_speed = 0

        except Exception as e:
            self.get_logger().error(f"HEALTH CHECK FAILED: {e}")

    # -----------------------------
    # Emergency stop
    # -----------------------------
    def emergency_stop(self):
        self.current_left_speed  = 0
        self.current_right_speed = 0

        try:
            self.safe_i2c(lambda: self.mc.reset())
        except Exception:
            pass

        self.get_logger().fatal("EMERGENCY STOP TRIGGERED")

    # -----------------------------
    def parameter_callback(self, params):
        return SetParametersResult(successful=True)


def main(args=None):
    rclpy.init(args=args)
    node = MotoronRosDriver()

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