import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Quaternion
import smbus2
import math
import time

# MPU6050 Registers
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43

def euler_to_quaternion(roll, pitch, yaw):
    """Convert degrees to a ROS 2 Quaternion (requires radians internally)"""
    r, p, y = math.radians(roll), math.radians(pitch), math.radians(yaw)
    cy, sy = math.cos(y * 0.5), math.sin(y * 0.5)
    cp, sp = math.cos(p * 0.5), math.sin(p * 0.5)
    cr, sr = math.cos(r * 0.5), math.sin(r * 0.5)

    q = Quaternion()
    q.w = cy * cp * cr + sy * sp * sr
    q.x = cy * cp * sr - sy * sp * cr
    q.y = sy * cp * sr + cy * sp * cr
    q.z = sy * cp * cr - cy * sp * sr
    return q

class ImuDriver(Node):
    def __init__(self):
        super().__init__('imu_driver')

        # Standard IMU message publisher
        self.publisher_ = self.create_publisher(Imu, '/totebot/imu', 10)

        # I2C Setup
        try:
            self.bus = smbus2.SMBus(1)
            self.address = 0x68
            self.bus.write_byte_data(self.address, PWR_MGMT_1, 0)
            self.get_logger().info("✅ MPU6050 connected")
        except Exception as e:
            self.get_logger().error(f"I2C Error: {e}")

        # Orientation state
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.gyro_offset = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.last_time = time.time()

        # Run calibration once on startup
        self.calibrate_gyro()
        self.timer = self.create_timer(0.02, self.update) # 50Hz

    def read_raw(self, addr):
        high = self.bus.read_byte_data(self.address, addr)
        low = self.bus.read_byte_data(self.address, addr + 1)
        val = (high << 8) | low
        return val - 65536 if val > 32768 else val

    def calibrate_gyro(self, samples=100):
        self.get_logger().info("Calibrating gyro... keep robot still")
        gx_sum = gy_sum = gz_sum = 0.0

        for _ in range(samples):
            gx_sum += self.read_raw(GYRO_XOUT_H) / 131.0
            gy_sum += self.read_raw(GYRO_XOUT_H + 2) / 131.0
            gz_sum += self.read_raw(GYRO_XOUT_H + 4) / 131.0
            time.sleep(0.01)

        self.gyro_offset['x'] = gx_sum / samples
        self.gyro_offset['y'] = gy_sum / samples
        self.gyro_offset['z'] = gz_sum / samples
        self.get_logger().info(f"Calibration done: {self.gyro_offset}")

    def update(self):
        try:
            # === Read Accelerometer ===
            ax = self.read_raw(ACCEL_XOUT_H) / 16384.0
            ay = self.read_raw(ACCEL_XOUT_H + 2) / 16384.0
            az = self.read_raw(ACCEL_XOUT_H + 4) / 16384.0

            # === Read Gyroscope ===
            gx = (self.read_raw(GYRO_XOUT_H) / 131.0) - self.gyro_offset['x']
            gy = (self.read_raw(GYRO_XOUT_H + 2) / 131.0) - self.gyro_offset['y']
            gz = (self.read_raw(GYRO_XOUT_H + 4) / 131.0) - self.gyro_offset['z']

            # === Accelerometer angles ===
            accel_pitch = math.atan2(ay, math.sqrt(ax*ax + az*az)) * 180 / math.pi
            accel_roll  = math.atan2(-ax, az) * 180 / math.pi

            # === Time delta ===
            current_time = time.time()
            dt = current_time - self.last_time
            self.last_time = current_time

            # === Complementary Filter ===
            alpha = 0.95
            self.pitch = alpha * (self.pitch + gy * dt) + (1 - alpha) * accel_pitch
            self.roll  = alpha * (self.roll  + gx * dt) + (1 - alpha) * accel_roll
            self.yaw  += gz * dt

            # === Publish Standard IMU Message ===
            msg = Imu()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "imu_link"
            
            # Pack the quaternion
            msg.orientation = euler_to_quaternion(self.roll, self.pitch, self.yaw)
            
            # Pack raw data for telemetry
            msg.linear_acceleration.x = ax * 9.81
            msg.linear_acceleration.y = ay * 9.81
            msg.linear_acceleration.z = az * 9.81
            msg.angular_velocity.x = math.radians(gx)
            msg.angular_velocity.y = math.radians(gy)
            msg.angular_velocity.z = math.radians(gz)

            self.publisher_.publish(msg)

        except Exception as e:
            self.get_logger().warning(f"IMU read failed: {e}")

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