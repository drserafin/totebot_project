import rclpy
from rclpy.node import Node
from std_msgs.msg import Int8
from . import motoron 
import time

class BasketActuatorDriver(Node):
    def __init__(self):
        super().__init__('basket_actuator_driver')

        # 1. Initialize the SECOND Motoron Hat
        try:
            self.mc = motoron.MotoronI2C(address=0x11)
            self.mc.reinitialize()
            self.mc.clear_reset_flag()
            
            # Setup acceleration profile
            self.mc.set_max_acceleration(1, 400) 
            self.mc.set_max_deceleration(1, 800) 
            
            self.get_logger().info("✅ ECO-WORTHY Basket Actuator Ready (Motoron Addr 0x11)")
        except Exception as e:
            self.get_logger().error(f"❌ Motoron Hat Connection Failed: {e}")

        # --- STATE MANAGEMENT ---
        # We store the speed here so the timer can access it
        self.current_target_speed = 0

        # 2. Command Subscriber
        self.subscription = self.create_subscription(
            Int8,
            '/totebot/basket_cmd',
            self.listener_callback,
            10
        )

        # 3. Heartbeat Timer (FIXES THE TIMEOUT ISSUE)
        # We send the speed command every 0.1 seconds (10Hz) 
        # This keeps the Motoron 'watchdog' happy while you hold the button.
        self.timer = self.create_timer(0.1, self.motor_heartbeat_callback)

    def listener_callback(self, msg):
        """Updates the stored target speed based on React input."""
        if msg.data == 1:
            self.current_target_speed = 800
            self.get_logger().info("🧺 COMMAND RECEIVED: Raising...")
        elif msg.data == -1:
            self.current_target_speed = -800
            self.get_logger().info("🧺 COMMAND RECEIVED: Lowering...")
        else:
            self.current_target_speed = 0
            self.get_logger().info("🧺 COMMAND RECEIVED: Stopping")

    def motor_heartbeat_callback(self):
        """Continuously feeds the current speed to the hardware."""
        try:
            # Assuming actuator is wired to Motor Channel 1
            self.mc.set_speed(1, self.current_target_speed)
        except Exception as e:
            # We don't want to log this 10 times a second if it fails, 
            # so we use a throttled log or just catch it.
            pass

def main(args=None):
    rclpy.init(args=args)
    node = BasketActuatorDriver()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Keyboard Interrupt (SIGINT)...")
    finally:
        # 🛑 Emergency Stop on exit
        try:
            # Hard stop on exit for safety
            node.mc.set_speed(1, 0)
            node.get_logger().info("Safety stop applied.")
        except:
            pass
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()