import rclpy
from rclpy.node import Node
from std_msgs.msg import Int8
from . import motoron

# =====================================================================
# 🧺 TOTEBOT BASKET ACTUATOR
# Motoron 0x11 — Channel 1
# Linear actuator, no encoder, just hold to move
# Topic: /totebot/basket_cmd (Int8: 1 = raise | -1 = lower | 0 = stop)
# =====================================================================

class BasketActuatorDriver(Node):
    def __init__(self):
        super().__init__('basket_actuator_driver')

        self.current_target_speed = 0

        try:
            self.mc = motoron.MotoronI2C(address=0x11)  # same board as GoTubes
            self.mc.reinitialize()
            self.mc.clear_reset_flag()
            self.mc.set_max_acceleration(1, 400)  # channel 1
            self.mc.set_max_deceleration(1, 800)  # channel 1
            self.get_logger().info("✅ Basket Actuator Ready (Motoron 0x11 CH1)")
        except Exception as e:
            self.get_logger().error(f"❌ Motoron init failed: {e}")
            raise

        self.create_subscription(
            Int8, '/totebot/basket_cmd', self.basket_callback, 10)

        # Heartbeat keeps Motoron watchdog alive while button is held
        self.create_timer(0.1, self.heartbeat)

    def basket_callback(self, msg: Int8):
        if msg.data == 1:
            self.current_target_speed = 800
            self.get_logger().info("🧺 RAISING")
        elif msg.data == -1:
            self.current_target_speed = -800
            self.get_logger().info("🧺 LOWERING")
        else:
            self.current_target_speed = 0
            self.get_logger().info("🧺 STOP")

    def heartbeat(self):
        try:
            self.mc.set_speed(1, self.current_target_speed)  # channel 1
        except Exception:
            pass

    def destroy_node(self):
        try:
            self.mc.set_speed(1, 0)
            self.get_logger().info("🛑 Basket safety stop on shutdown")
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = BasketActuatorDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()