import os
from launch import LaunchDescription
from launch_ros.actions import Node

# =====================================================================
# 🚀 TOTEBOT MASTER IGNITION FILE
# =====================================================================
# 🛠️ QUICK START COMMANDS (Run these from the Raspberry Pi terminal):
#
# 1. WAKE UP CONTAINER:  docker start totebot_brain
# 2. ENTER CONTAINER:    docker exec -it totebot_brain bash
# 3. SOURCE WORKSPACE:   source /opt/ros/jazzy/setup.bash && source /totebot_ws/install/setup.bash
#
# 4. LAUNCH HARDWARE:    ros2 launch totebot_bringup hardware.launch.py
#
# NOTE: This single command starts the Motors, IMU, and Web Bridge simultaneously.
# =====================================================================

def generate_launch_description():
    return LaunchDescription([
        # 🟢 1. MOTOR DRIVER (Muscles)
        Node(
            package='totebot_hardware',
            executable='motor_driver',
            name='motor_driver',
            output='screen',
            emulate_tty=True
        ),

        # 🟢 2. IMU DRIVER (Balance)
        Node(
            package='totebot_hardware',
            executable='imu_driver',
            name='imu_driver',
            output='screen',
            emulate_tty=True
        ),

        # 🟢 3. ROSBRIDGE (The Web Link)
        # This opens the door for your React HMI to see the data
        Node(
            package='rosbridge_server',
            executable='rosbridge_websocket',
            name='rosbridge',
            parameters=[{'port': 9909}],
            output='screen'
        )
    ])