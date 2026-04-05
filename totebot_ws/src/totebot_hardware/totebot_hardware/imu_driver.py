import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Vector3
import smbus2
import math
import time

class ImuDriver(Node):
    def __init__(self):
        super().__init__('imu_driver')
        # Publisher for the React Web Remote
        self.publisher_ = self.create_publisher(Vector3, '/totebot/imu', 10)
        
        # MPU6050 Hardware Init
        try:
            self.bus = smbus2.SMBus(1)
            self.address = 0x68
            self.bus.write_byte_data(self.address, 0x6B, 0) # Wake up sensor
            self.get_logger().info("✅ MPU6050 connected at 0x68")
        except Exception as e:
            self.get_logger().error(f"❌ I2C Connection Failed: {e}")

        # Filter Vars
        self.last_time = time.time()
        self.timer = self.create_timer(0.05, self.publish_data) # 20 Hz update rate

    def read_raw(self, addr):
        high = self.bus.read_byte_data(self.address, addr)
        low = self.bus.read_byte_data(self.address, addr + 1)
        val = (high << 8) | low
        return val - 65536 if val > 32768 else val

    def publish_data(self):
        try:
            # Read Accelerometer Raw
            ax = self.read_raw(0x3B) / 16384.0
            ay = self.read_raw(0x3D) / 16384.0
            az = self.read_raw(0x3F) / 16384.0
            
            # Calculate Euler Angles (Degrees)
            # Pitch: Tilt forward/backward
            pitch = math.atan2(ay, math.sqrt(ax*ax + az*az)) * 180 / math.pi
            # Roll: Leaning side to side
            roll = math.atan2(-ax, az) * 180 / math.pi
            
            msg = Vector3()
            msg.x = float(roll)   # X = Roll
            msg.y = float(pitch)  # Y = Pitch
            msg.z = 0.0           # Z = Yaw 
            
            self.publisher_.publish(msg)
        except Exception as e:
            self.get_logger().warning(f"Failed to read IMU: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = ImuDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()