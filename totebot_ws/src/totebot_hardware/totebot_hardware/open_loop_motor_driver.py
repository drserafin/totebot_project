#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from rcl_interfaces.msg import SetParametersResult
from . import motoron
import sys

# =====================================================================
# 🚀 TOTEBOT OPEN LOOP MOTOR DRIVER (open_loop_motor_driver.py)
# =====================================================================


class MotoronRosDriver(Node):
    def __init__(self):
        super().__init__('open_loop_motor_driver')
        self.hardware_connected = False

        # 🟢 DECLARE ROS 2 PARAMETERS
        self.declare_parameter('dummy_mode', False)
        self.declare_parameter('max_speed', 800)       # Max: 800
        self.declare_parameter('accel_limit', 140)     # Lower = smoother
        self.declare_parameter('decel_limit', 300)     # Lower = longer braking
        self.declare_parameter('cmd_timeout_ms', 100)  # Stop if signal lost
        self.declare_parameter('min_vin_mv', 4500)     # 4.5V cutoff

        self.is_dummy_mode = self.get_parameter('dummy_mode').value

        # Internal speed trackers for the heartbeat timer
        self.current_left_speed = 0
        self.current_right_speed = 0

        # 🟢 THE "NO-PANIC" MASK (Fixes 0x2404 Crash)
        self.error_mask = (
            (1 << motoron.STATUS_FLAG_PROTOCOL_ERROR) |
            (1 << motoron.STATUS_FLAG_CRC_ERROR) |
            (1 << motoron.STATUS_FLAG_COMMAND_TIMEOUT))

        # 🟢 REGISTER PARAMETER CALLBACK
        self.add_on_set_parameters_callback(self.parameter_callback)

        # Initialize the hardware
        self.setup_motoron()

        # Listen for Joystick directly (Bypassing PID)
        self.subscription = self.create_subscription(
            Twist, '/cmd_vel', self.listener_callback, 10)

        # Health Check & Heartbeat Timer (Runs every 100ms)
        self.timer = self.create_timer(0.1, self.health_check_callback)

        if self.is_dummy_mode:
            self.get_logger().warn("🚀 TOTEBOT OPEN LOOP READY (DUMMY MODE)")
        else:
            self.get_logger().info("🚀 TOTEBOT OPEN LOOP READY (LIVE HARDWARE MODE)")

        # 🐛 DEBUG – summarise active configuration at startup
        self.get_logger().debug(
            f"[INIT] Parameters → "
            f"dummy_mode={self.is_dummy_mode}, "
            f"max_speed={self.get_parameter('max_speed').value}, "
            f"accel_limit={self.get_parameter('accel_limit').value}, "
            f"decel_limit={self.get_parameter('decel_limit').value}, "
            f"cmd_timeout_ms={self.get_parameter('cmd_timeout_ms').value}, "
            f"min_vin_mv={self.get_parameter('min_vin_mv').value}"
        )

    # ─── Parameter callback ──────────────────────────────────────────

    def parameter_callback(self, params):
        for param in params:
            self.get_logger().info(f"⚙️  PARAM UPDATED: {param.name} = {param.value}")
            if self.hardware_connected and not self.is_dummy_mode:
                try:
                    if param.name == 'accel_limit':
                        for m in [1, 2]:
                            self.mc.set_max_acceleration(m, param.value)
                        self.get_logger().debug(
                            f"[PARAM] accel_limit synced to hardware: {param.value}"
                        )
                    elif param.name == 'decel_limit':
                        for m in [1, 2]:
                            self.mc.set_max_deceleration(m, param.value)
                        self.get_logger().debug(
                            f"[PARAM] decel_limit synced to hardware: {param.value}"
                        )
                    elif param.name == 'cmd_timeout_ms':
                        self.mc.set_command_timeout_milliseconds(param.value)
                        self.get_logger().debug(
                            f"[PARAM] cmd_timeout_ms synced to hardware: {param.value}"
                        )
                except Exception as e:
                    self.get_logger().error(f"❌ Failed to sync param to hardware: {e}")
        return SetParametersResult(successful=True)

    # ─── Hardware setup ──────────────────────────────────────────────

    def setup_motoron(self):
        try:
            self.get_logger().debug("[SETUP] Initialising Motoron I2C controller…")
            self.mc = motoron.MotoronI2C()
            self.mc.reinitialize()
            self.mc.clear_reset_flag()
            self.mc.clear_latched_status_flags(0xFFFF)
            self.mc.clear_motor_fault()

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

            self.get_logger().debug(
                f"[SETUP] Hardware ready → "
                f"error_mask=0x{self.error_mask:04x}, "
                f"cmd_timeout={cmd_timeout} ms, "
                f"accel={accel}, decel={decel}"
            )

        except Exception as e:
            self.hardware_connected = False
            self.get_logger().error(f"⚠️ MOTORON I2C SETUP FAILED: {e}")
            self.get_logger().warn("🤖 FALLING BACK TO DUMMY MODE")

    # ─── Health check / heartbeat ─────────────────────────────────────

    def health_check_callback(self):
        if not self.hardware_connected or self.is_dummy_mode:
            return

        try:
            # --- THE HEARTBEAT (Fixes 0x2404 Timeout) ---
            self.mc.set_speed(1, self.current_left_speed)
            self.mc.set_speed(2, self.current_right_speed)

            # --- HEALTH MONITORING ---
            status = self.mc.get_status_flags()
            voltage = self.mc.get_vin_voltage_mv(3300, motoron.VinSenseType.MOTORON_256)
            min_vin = self.get_parameter('min_vin_mv').value

            # 🐛 DEBUG – log voltage & status periodically (throttled)
            self.get_logger().debug(
                f"[HEALTH] voltage={voltage} mV  status=0x{status:04x}  "
                f"L={self.current_left_speed:+4d}  R={self.current_right_speed:+4d}",
                throttle_duration_sec=1.0
            )

            if voltage < min_vin and voltage > 500:
                self.get_logger().error(
                    f"🛑 LOW VOLTAGE: {voltage} mV (threshold={min_vin} mV). SHUTTING DOWN."
                )
                self.emergency_stop()

            if status & self.error_mask:
                self.get_logger().error(
                    f"❌ CONTROLLER ERROR: 0x{status:x} "
                    f"(error_mask=0x{self.error_mask:x}). SHUTTING DOWN."
                )
                self.emergency_stop()

        except Exception as e:
            self.get_logger().error(f"🏥 HEALTH CHECK FAILED: {e}")
            self.emergency_stop()

    # ─── /cmd_vel subscriber ──────────────────────────────────────────

    def listener_callback(self, msg):
        """
        Receives Twist messages published by the React web remote via rosService.ts.

        Axis cross-mapping (intentional – matches React joystick layout):
          React sets  → Twist.linear.x   = linearX  (left/right joystick axis)
          React sets  → Twist.angular.z  = angularZ (forward/back joystick axis)

          Python reads:
            target_linear  ← msg.angular.z   (forward/back becomes drive speed)
            target_angular ← msg.linear.x    (left/right becomes turn rate)
        """
        current_max_speed = self.get_parameter('max_speed').value

        # ── 🐛 DEBUG LAYER 1: raw Twist fields from the web remote ──
        self.get_logger().debug(
            f"[CMD_VEL] Incoming Twist → "
            f"linear.x={msg.linear.x:.3f}  linear.y={msg.linear.y:.3f}  linear.z={msg.linear.z:.3f}  "
            f"angular.x={msg.angular.x:.3f}  angular.y={msg.angular.y:.3f}  angular.z={msg.angular.z:.3f}"
        )

        # ── Axis remap ───────────────────────────────────────────────
        target_linear  = -msg.linear.x    # forward/back
        target_angular = msg.angular.z   # left/right turn

        # ── Differential drive math ──────────────────────────────────
        raw_left  = int((target_linear + target_angular) * current_max_speed)
        raw_right = int((target_linear - target_angular) * current_max_speed)

        # Clamp and store for the heartbeat timer
        self.current_left_speed  = max(min(raw_left,   800), -800)
        self.current_right_speed = max(min(raw_right,  800), -800)


    # ─── Emergency stop ──────────────────────────────────────────────

    def emergency_stop(self):
        self.get_logger().fatal(
            f"[EMERGENCY_STOP] Triggered → hardware_connected={self.hardware_connected}"
        )
        if self.hardware_connected:
            try:
                self.mc.reset()
                self.get_logger().debug("[EMERGENCY_STOP] mc.reset() succeeded")
            except Exception as e:
                self.get_logger().error(f"[EMERGENCY_STOP] mc.reset() failed: {e}")
        self.get_logger().fatal("🛑 Safe node shutdown initiated.")
        self.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


# ─── Entry point ──────────────────────────────────────────────────────

def main(args=None):
    rclpy.init(args=args)
    node = MotoronRosDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("[MAIN] KeyboardInterrupt received – shutting down gracefully")
    finally:
        if node.hardware_connected:
            try:
                node.mc.reset()
                node.get_logger().debug("[MAIN] mc.reset() on shutdown succeeded")
            except Exception as e:
                node.get_logger().error(f"[MAIN] mc.reset() on shutdown failed: {e}")
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()