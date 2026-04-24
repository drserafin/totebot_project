import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32, Int32MultiArray
from . import motoron
import time

SOFT_LIMIT_TICKS    = 999999
RETRACT_LIMIT_TICKS = 0
MOTOR_SPEED         = 800
STALL_MA            = 2000
ENCODER_TIMEOUT_SEC = 2.0  # if no encoder data for 2s → open loop mode


class LifterController(Node):
    def __init__(self):
        super().__init__('lifter_controller')

        self.current_position = 0
        self.command = 0
        self.mc = None
        self.current_units = None
        self.ready = False
        self.current_speed = 0

        # Tracks when we last got encoder data
        self.last_encoder_time = None
        self.encoder_online = False

        self.init_timer = self.create_timer(2.0, self.try_motoron_init)

        self.create_subscription(
            Int32MultiArray, '/encoder_array', self.encoder_callback, 10)

        self.create_subscription(
            Int32, '/lifter_cmd', self.cmd_callback, 10)

        self.ticks_pub = self.create_publisher(Int32, '/encoder_ticks', 10)

        # 10Hz — drives motor + checks encoder timeout
        self.create_timer(0.1, self.motor_heartbeat)

        self.get_logger().info("Lifter Controller starting — waiting for Motoron 0x11 CH2...")

    def try_motoron_init(self):
        try:
            time.sleep(0.5)
            self.mc = motoron.MotoronI2C(address=0x11)
            self.mc.set_max_acceleration(2, 140)
            self.mc.set_max_deceleration(2, 300)
            self.board_type = motoron.CurrentSenseType.MOTORON_18V20
            self.reference_mv = 3300
            self.current_units = motoron.current_sense_units_milliamps(
                self.board_type, self.reference_mv)
            self.ready = True
            self.init_timer.cancel()
            self.get_logger().info(
                f"✅ GoTubes Lifter Ready (Motoron 0x11 CH2) | "
                f"Soft limit: {SOFT_LIMIT_TICKS} ticks "
                f"({SOFT_LIMIT_TICKS / 5281:.2f} rot)"
            )
        except Exception as e:
            self.get_logger().warn(f"⏳ Motoron init retry — {e}")

    def cmd_callback(self, msg: Int32):
        if not self.ready:
            self.get_logger().warn("GoTubes not ready yet — command ignored")
            return

        self.command = int(msg.data)
        direction = {1: "EXTEND", -1: "RETRACT", 0: "STOP"}.get(self.command, "?")
        mode = "📡 w/ encoder" if self.encoder_online else "⚠️  OPEN LOOP (no ESP32)"
        self.get_logger().info(f"🔧 GoTubes: {direction} {mode}")

        if self.command == 1:
            self.current_speed = MOTOR_SPEED
        elif self.command == -1:
            self.current_speed = -MOTOR_SPEED
        else:
            self.current_speed = 0

    def motor_heartbeat(self):
        """
        10Hz — drives motor unconditionally.
        Also checks if encoder has timed out and switches mode accordingly.
        """
        if not self.ready:
            return

        # ── Check encoder timeout ─────────────────────────────────────
        if self.last_encoder_time is not None:
            elapsed = self.get_clock().now().nanoseconds / 1e9 - self.last_encoder_time
            was_online = self.encoder_online
            self.encoder_online = elapsed < ENCODER_TIMEOUT_SEC

            # Log mode transitions
            if was_online and not self.encoder_online:
                self.get_logger().warn(
                    "⚠️  ESP32 disconnected — running OPEN LOOP, soft limits disabled")
            elif not was_online and self.encoder_online:
                self.get_logger().info(
                    "📡 ESP32 reconnected — soft limits active")

        # ── Drive motor regardless of encoder state ───────────────────
        try:
            self.mc.set_speed(2, self.current_speed)
        except Exception as e:
            self.get_logger().warn(f"heartbeat error: {e}")

    def encoder_callback(self, msg: Int32MultiArray):
        """
        Only used for limits + tick display.
        Motor runs from heartbeat so this being absent doesn't stop movement.
        """
        if len(msg.data) < 3:
            return

        # Mark encoder as alive
        self.last_encoder_time = self.get_clock().now().nanoseconds / 1e9
        self.encoder_online = True

        self.current_position = msg.data[2]

        # Publish ticks for web dashboard
        out = Int32()
        out.data = self.current_position
        self.ticks_pub.publish(out)

        if not self.ready or self.current_speed == 0:
            return

        # Stall detection
        try:
            current_ma = self.mc.get_current_sense_processed(2) * self.current_units
            if current_ma > STALL_MA:
                self.current_speed = 0
                self.command = 0
                self.get_logger().warn(f"⚠️  STALL: {round(current_ma)} mA — killed")
                return
        except Exception:
            pass

        # Soft limit — only enforced when encoder is online
        if self.current_speed > 0 and self.current_position >= SOFT_LIMIT_TICKS:
            self.current_speed = 0
            self.command = 0
            self.get_logger().info(
                f"🛑 EXTEND LIMIT: {self.current_position} ticks "
                f"({self.current_position / 5281:.2f} rot)"
            )
            return

        # Home limit
        if self.current_speed < 0 and self.current_position <= RETRACT_LIMIT_TICKS:
            self.current_speed = 0
            self.command = 0
            self.get_logger().info(f"🏠 HOME: {self.current_position} ticks")
            return

    def stop_motor(self):
        self.current_speed = 0
        try:
            if self.mc:
                self.mc.set_speed(2, 0)
        except Exception as e:
            self.get_logger().warn(f"stop_motor failed: {e}")

    def destroy_node(self):
        try:
            self.stop_motor()
            self.get_logger().info("🛑 Safety stop on shutdown")
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = LifterController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()