import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Quaternion
import smbus2
import math
import time
from threading import Lock

i2c_lock = Lock()

# MPU6050 Registers
PWR_MGMT_1   = 0x6B
ACCEL_XOUT_H = 0x3B


def euler_to_quaternion(roll, pitch, yaw):
    r = math.radians(roll)
    p = math.radians(pitch)
    y = math.radians(yaw)

    cy = math.cos(y * 0.5)
    sy = math.sin(y * 0.5)
    cp = math.cos(p * 0.5)
    sp = math.sin(p * 0.5)
    cr = math.cos(r * 0.5)
    sr = math.sin(r * 0.5)

    q = Quaternion()
    q.w = cy * cp * cr + sy * sp * sr
    q.x = cy * cp * sr - sy * sp * cr
    q.y = sy * cp * sr + cy * sp * cr
    q.z = sy * cp * cr - cy * sp * sr

    return q


class ImuDriver(Node):

    def __init__(self):
        super().__init__('imu_driver')

        self.publisher_ = self.create_publisher(
            Imu,
            '/totebot/imu',
            10
        )

        # I2C Setup
        try:
            self.bus = smbus2.SMBus(1)
            self.address = 0x68

            # Wake MPU6050
            self.bus.write_byte_data(
                self.address,
                PWR_MGMT_1,
                0
            )

            time.sleep(0.1)

            self.get_logger().info(
                "✅ MPU6050 connected on 0x68"
            )

        except Exception as e:
            self.get_logger().error(
                f"❌ I2C Connection Error: {e}"
            )
            raise

        # Orientation state
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0

        # Gyro offsets
        self.gyro_offset = {
            'x': 0.0,
            'y': 0.0,
            'z': 0.0
        }

        self.last_time = time.time()
        self.log_counter = 0

        # Calibrate
        self.calibrate_gyro()

        # 20Hz update rate (much safer for shared I2C bus)
        self.timer = self.create_timer(
            0.25,
            self.update
        )

    def combine_bytes(self, high, low):
        value = (high << 8) | low

        if value > 32767:
            value -= 65536

        return value

    def read_sensor_block(self):
        """
        Reads all accel + gyro data in ONE I2C transaction.
        Much safer and faster than many separate reads.
        """
        with i2c_lock:
            data = self.bus.read_i2c_block_data(
            self.address,
            ACCEL_XOUT_H,
            14
        )

        ax = self.combine_bytes(data[0], data[1])
        ay = self.combine_bytes(data[2], data[3])
        az = self.combine_bytes(data[4], data[5])

        gx = self.combine_bytes(data[8], data[9])
        gy = self.combine_bytes(data[10], data[11])
        gz = self.combine_bytes(data[12], data[13])

        return ax, ay, az, gx, gy, gz

    def calibrate_gyro(self, samples=50):

        self.get_logger().info(
            "Calibrating gyro... keep ToteBot still"
        )

        gx_sum = 0.0
        gy_sum = 0.0
        gz_sum = 0.0

        for _ in range(samples):

            try:
                _, _, _, gx, gy, gz = self.read_sensor_block()

                gx_sum += gx / 131.0
                gy_sum += gy / 131.0
                gz_sum += gz / 131.0

            except Exception as e:
                self.get_logger().warning(
                    f"Calibration read failed: {e}"
                )

            time.sleep(0.05)

        self.gyro_offset['x'] = gx_sum / samples
        self.gyro_offset['y'] = gy_sum / samples
        self.gyro_offset['z'] = gz_sum / samples

        self.get_logger().info(
            "✅ Calibration complete"
        )

    def update(self):

        try:

            # Read all sensor data in ONE transaction
            ax, ay, az, gx, gy, gz = self.read_sensor_block()

            # Convert units
            ax /= 16384.0
            ay /= 16384.0
            az /= 16384.0

            gx = (gx / 131.0) - self.gyro_offset['x']
            gy = (gy / 131.0) - self.gyro_offset['y']
            gz = (gz / 131.0) - self.gyro_offset['z']

            # Delta time
            now = time.time()
            dt = now - self.last_time
            self.last_time = now

            # Accelerometer angles
            accel_pitch = math.atan2(
                ay,
                math.sqrt(ax * ax + az * az)
            ) * 180.0 / math.pi

            accel_roll = math.atan2(
                -ax,
                az
            ) * 180.0 / math.pi

            # Complementary filter
            alpha = 0.95

            self.pitch = (
                alpha * (self.pitch + gy * dt)
                + (1.0 - alpha) * accel_pitch
            )

            self.roll = (
                alpha * (self.roll + gx * dt)
                + (1.0 - alpha) * accel_roll
            )

            self.yaw += gz * dt

            # Create ROS IMU message
            msg = Imu()

            msg.header.stamp = (
                self.get_clock().now().to_msg()
            )

            msg.header.frame_id = "imu_link"

            msg.orientation = euler_to_quaternion(
                self.roll,
                self.pitch,
                self.yaw
            )

            self.publisher_.publish(msg)

            # Log occasionally
            self.log_counter += 1

            if self.log_counter % 20 == 0:
                self.get_logger().info(
                    f"📡 IMU | "
                    f"Roll: {self.roll:.1f}° | "
                    f"Pitch: {self.pitch:.1f}° | "
                    f"Yaw: {self.yaw:.1f}°"
                )

        except Exception as e:

            self.get_logger().warning(
                f"IMU loop failed: {e}"
            )

            # Give I2C bus time to recover
            time.sleep(0.05)

    def destroy_node(self):

        try:
            self.bus.close()
        except Exception:
            pass

        super().destroy_node()


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