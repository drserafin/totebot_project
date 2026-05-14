import rclpy
from rclpy.node import Node
from std_msgs.msg import Int8, Bool
from sensor_msgs.msg import Imu
import math
from . import motoron
from threading import Lock

i2c_lock = Lock()

# =====================================================================
# 🧽 TOTEBOT BASKET ACTUATOR (with IMU Fusion & Status Feedback)
# Motoron 0x11 — Channel 1
# =====================================================================

class BasketActuatorDriver(Node):
    def __init__(self):
        super().__init__('basket_actuator_driver')

        # --- State Variables ---
        self.fusion_active = False
        self.manual_speed = 0
        self.current_pitch = 0.0
        self.DEADZONE = 1.5  # degrees
        self.debug_tick = 0 

        try:
            self.mc = motoron.MotoronI2C(address=0x10)  
            self.mc.reinitialize()
            self.mc.clear_reset_flag()
            self.mc.set_max_acceleration(1, 400)  
            self.mc.set_max_deceleration(1, 800)  
            self.get_logger().info("✅ BASKET HARDWARE INITIALIZED (Motoron 0x10 CH1)")
        except Exception as e:
            self.get_logger().error(f"❌ Motoron init failed: {e}")
            raise

        # --- Subscriptions ---
        self.create_subscription(Int8, '/totebot/basket_cmd', self.basket_callback, 10)
        self.create_subscription(Bool, '/assist/fusion_active', self.fusion_callback, 10)
        self.create_subscription(Imu, '/totebot/imu', self.imu_callback, 10)

        # Heartbeat executes 10 times a second
        self.create_timer(0.1, self.heartbeat)

    def basket_callback(self, msg: Int8):
        # We only update manual_speed if fusion is OFF
        if not self.fusion_active:
            if msg.data == 1:
                self.manual_speed = 800
            elif msg.data == -1:
                self.manual_speed = -800
            else:
                self.manual_speed = 0

    def fusion_callback(self, msg: Bool):
        self.fusion_active = msg.data
        if self.fusion_active:
            self.get_logger().info("🚀 FUSION MODE: [ENABLED] - IMU Auto-Leveling is now WORKNG")
        else:
            self.get_logger().info("🎮 FUSION MODE: [DISABLED] - Switching back to Manual Control")
            self.manual_speed = 0 # Safety reset
            self.mc.set_speed(1, 0) 

    def imu_callback(self, msg: Imu):
            # Extract the quaternion
            w, x, y, z = msg.orientation.w, msg.orientation.x, msg.orientation.y, msg.orientation.z
            
            # Convert to pitch
            sinp = 2.0 * (w * y - z * x)
            if abs(sinp) >= 1:
                pitch_rad = math.copysign(math.pi / 2.0, sinp)
            else:
                pitch_rad = math.asin(sinp)
                
            self.current_pitch = math.degrees(pitch_rad)
            # ? This will now print the REAL pitch in your logs!

    def heartbeat(self):
        target_speed = 0
        mode_label = ""

        if self.fusion_active:
            # --- AUTO-LEVELING MODE ---
            if self.current_pitch > self.DEADZONE:
                target_speed = 200  # Retract
                mode_label = "WORKING (Leveling Up)"
            elif self.current_pitch < -self.DEADZONE:
                target_speed = -200   # Extend
                mode_label = "WORKING (Leveling Down)"
            else:
                target_speed = 0     # Already Level
                mode_label = "STABLE (Aligned to Horizon)"
                
            # Log Fusion performance once per second
            self.debug_tick += 1
            if self.debug_tick % 10 == 0:
                self.get_logger().info(
                    f"🌪️ Fusion Status: {mode_label} | Pitch: {self.current_pitch:.1f}°"
                )
        else:
            # --- MANUAL MODE ---
            target_speed = self.manual_speed
            self.debug_tick = 0 

        try:
            self.mc.set_speed(1, target_speed)
        except Exception:
            self.get_logger().error(f"⚠️ I2C WRITE FAILED: {e}")

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


