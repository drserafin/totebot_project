#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
from . import motoron
from threading import Lock

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
i2c_lock = Lock()

MOTOR_SPEED = 800

STALL_MA = 6000
STALL_CONFIRM_COUNT = 5   # ~0.5s at 10Hz

UPDATE_RATE = 0.1         # 10 Hz

# ─────────────────────────────────────────────
# NODE
# ─────────────────────────────────────────────
class LifterController(Node):

    def __init__(self):
        super().__init__('lifter_controller')

        self.mc = None
        self.ready = False

        self.current_speed = 0

        # safety filtering
        self.filtered_current = 0.0
        self.stall_counter = 0

        # init retry timer
        self.init_timer = self.create_timer(2.0, self.try_motoron_init)

        # command input
        self.create_subscription(Int32, '/lifter_cmd', self.cmd_callback, 10)

        # heartbeat
        self.create_timer(UPDATE_RATE, self.motor_heartbeat)

        self.get_logger().info("🚀 Lifter Controller Ready (Safe Mode)")

    # ─────────────────────────────────────────────
    # INIT MOTORON (RETRY SAFE)
    # ─────────────────────────────────────────────
    def try_motoron_init(self):
        if self.ready:
            return

        try:
            with i2c_lock:
                self.mc = motoron.MotoronI2C(address=0x10)
                self.mc.reinitialize()
                self.mc.disable_crc()
                self.mc.clear_reset_flag()

                self.mc.set_max_acceleration(2, 140)
                self.mc.set_max_deceleration(2, 300)

            self.ready = True
            self.init_timer.cancel()

            self.get_logger().info("✅ Motoron initialized safely")

        except Exception as e:
            self.get_logger().warn(f"Motoron init retry: {e}")

    # ─────────────────────────────────────────────
    # COMMANDS
    # ─────────────────────────────────────────────
    def cmd_callback(self, msg: Int32):

        if not self.ready:
            return

        if msg.data == 1:
            self.current_speed = MOTOR_SPEED
        elif msg.data == -1:
            self.current_speed = -MOTOR_SPEED
        else:
            self.current_speed = 0

    # ─────────────────────────────────────────────
    # HEARTBEAT + SAFETY LOOP
    # ─────────────────────────────────────────────
    def motor_heartbeat(self):

        if not self.ready:
            return

        try:
            with i2c_lock:

                # ── READ CURRENT (SAFE) ──
                try:
                    raw_current = self.mc.get_current_sense_processed(2)
                except Exception:
                    self.get_logger().warn("I2C read failed (skipping)")
                    return

                # ── FILTER SPIKES ──
                if raw_current < 0 or raw_current > 20000:
                    self.get_logger().warn(f"Bad current ignored: {raw_current}")
                    return

                # exponential smoothing
                self.filtered_current = (
                    0.8 * self.filtered_current +
                    0.2 * raw_current
                )

                # ── STALL DETECTION (STABLE) ──
                if self.filtered_current > STALL_MA:
                    self.stall_counter += 1
                else:
                    self.stall_counter = 0

                if self.stall_counter >= STALL_CONFIRM_COUNT:
                    self.current_speed = 0
                    self.get_logger().error(
                        f"STALL CONFIRMED → STOP ({int(self.filtered_current)} mA)"
                    )
                else:
                    # normal operation
                    self.mc.set_speed(2, self.current_speed)

        except Exception as e:
            self.get_logger().error(f"I2C ERROR (non-fatal): {e}")
            self.ready = False  # allow re-init instead of crash

    # ─────────────────────────────────────────────
    # CLEAN SHUTDOWN
    # ─────────────────────────────────────────────
    def destroy_node(self):

        if self.mc:
            try:
                self.mc.set_speed(2, 0)
            except:
                pass

        super().destroy_node()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main(args=None):
    rclpy.init(args=args)

    node = LifterController()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()