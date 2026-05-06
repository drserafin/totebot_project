#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool

class ControlMuxNode(Node):
    def __init__(self):
        super().__init__('control_mux_node')
        self.align_active = False

        self.create_subscription(Twist, '/cmd_vel/joy', self.joy_callback, 10)
        self.create_subscription(Twist, 'camera/alignment/cmd_vel', self.align_callback, 10)
        self.create_subscription(Bool, '/assist/align_active', self.mode_callback, 10)

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.get_logger().info('🚦 Control mux ready — joystick active')

    def mode_callback(self, msg: Bool):
        was_active = self.align_active
        self.align_active = msg.data
        if was_active and not self.align_active:
            self.cmd_pub.publish(Twist())
            self.get_logger().info('🛑 Align released → zero Twist sent, joystick active')
        elif not was_active and self.align_active:
            self.get_logger().info('🎯 Align engaged → ToF commands active')

    def joy_callback(self, msg: Twist):
        if not self.align_active:
            self.cmd_pub.publish(msg)

    def align_callback(self, msg: Twist):
        if self.align_active:
            self.cmd_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = ControlMuxNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
