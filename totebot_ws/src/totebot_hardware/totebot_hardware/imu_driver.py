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
        self.publisher_ = self.create_publisher(Imu, '/totebot/imu', 10)

        try:
            self.bus = smbus2.SMBus(1)
            self.address = 0x68
            self.bus.write_byte_data(self.address, PWR_MGMT_1, 0)
            time.sleep(0.1) 
            self.get_logger().info("✅ MPU6050 connected on 0x68")
        except Exception as e:
            self.get_logger().error(f"❌ I2C Connection Error: {e}")
            return

        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.gyro_offset = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.last_time = time.time()
        self.log_counter = 0

        self.calibrate_gyro()
        self.timer = self.create_timer(0.02, self.update) # 50Hz

    def read_raw(self, addr):
        try:
            high = self.bus.read_byte_data(self.address, addr)
            low = self.bus.read_byte_data(self.address, addr + 1)
            val = (high << 8) | low
            return val - 65536 if val > 32768 else val
        except Exception: return 0

    def calibrate_gyro(self, samples=50):
        self.get_logger().info("Calibrating gyro... keep ToteBot still")
        gx_sum = gy_sum = gz_sum = 0.0
        for _ in range(samples):
            gx_sum += self.read_raw(GYRO_XOUT_H) / 131.0
            gy_sum += self.read_raw(GYRO_XOUT_H + 2) / 131.0
            gz_sum += self.read_raw(GYRO_XOUT_H + 4) / 131.0
            time.sleep(0.01)
        self.gyro_offset = {'x': gx_sum/samples, 'y': gy_sum/samples, 'z': gz_sum/samples}
        self.get_logger().info("✅ Calibration complete")

    def update(self):
        try:
            ax = self.read_raw(ACCEL_XOUT_H) / 16384.0
            ay = self.read_raw(ACCEL_XOUT_H + 2) / 16384.0
            az = self.read_raw(ACCEL_XOUT_H + 4) / 16384.0
            gx = (self.read_raw(GYRO_XOUT_H) / 131.0) - self.gyro_offset['x']
            gy = (self.read_raw(GYRO_XOUT_H + 2) / 131.0) - self.gyro_offset['y']
            gz = (self.read_raw(GYRO_XOUT_H + 4) / 131.0) - self.gyro_offset['z']

            dt = time.time() - self.last_time
            self.last_time = time.time()

            accel_pitch = math.atan2(ay, math.sqrt(ax*ax + az*az)) * 180 / math.pi
            accel_roll  = math.atan2(-ax, az) * 180 / math.pi

            alpha = 0.95
            self.pitch = alpha * (self.pitch + gy * dt) + (1 - alpha) * accel_pitch
            self.roll  = alpha * (self.roll  + gx * dt) + (1 - alpha) * accel_roll
            self.yaw  += gz * dt

            msg = Imu()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "imu_link"
            msg.orientation = euler_to_quaternion(self.roll, self.pitch, self.yaw)
            self.publisher_.publish(msg)

            self.log_counter += 1
            if self.log_counter % 50 == 0:
                self.get_logger().info(f"📡 IMU RAW | Pitch: {self.pitch:.1f}°")

        except Exception as e:
            self.get_logger().warning(f"IMU loop failed: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = ImuDriver()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()


