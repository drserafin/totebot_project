import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32 

# docker exec -it totebot_brain bash
# source /opt/ros/jazzy/setup.bash && source /totebot_ws/install/setup.bash
# ros2 run totebot_hardware micro_ros_bridge
# --- Run the Bridge --- 
# Raspberry Pi Terminal 
# docker run -it --rm --net=host -v /dev:/dev --privileged microros/micro-ros-agent:jazzy serial --dev /dev/ttyUSB0


class MicroROSBridge(Node):
    def __init__(self):
        super().__init__('micro_ros_bridge')
        self.subscription = self.create_subscription(
            Int32,
            'encoder_ticks',  # Matches the ESP32 topic name
            self.listener_callback,
            10)
        self.get_logger().info("Bridge online. Waiting for Saturn motor ticks...")

    def listener_callback(self, msg):
        # Displays the real-time integer count
        self.get_logger().info(f'Current Position (Counts): {msg.data}')

def main(args=None):
    rclpy.init(args=args)
    node = MicroROSBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()