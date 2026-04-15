import os
from launch import LaunchDescription
from launch_ros.actions import Node

# =====================================================================
# 🚀 TOTEBOT MASTER IGNITION FILE (hardware.launch.py)
# =====================================================================
# 📖 QUICK START GUIDE FOR TEAMMATES & USERS
# Open a terminal on the Raspberry Pi and run these commands in order:
#
# [STEP 1] Wake up the Docker Container (The Robot's Brain)
#          docker start totebot_brain
#
# [STEP 2] Enter the Container Environment
#          docker exec -it totebot_brain bash
#
# [STEP 3] 🛠️ THE UPDATE RITUAL (Run this every time you edit code!)
#          cd /totebot_ws && colcon build --symlink-install
#
# [STEP 4] Load the ROS 2 Paths & ToteBot Workspace
#          source /opt/ros/jazzy/setup.bash && source /totebot_ws/install/setup.bash
#
# [STEP 5] Fire up the Master Switch!
#          ros2 launch totebot_bringup hardware.launch.py
#
# 🌟 WHAT THIS SCRIPT DOES:
# This central nervous system handles the coordination of:
# 1. Motor Driver:     Drive motors for tracks.
# 2. IMU Driver:       (DISABLED) MPU6050 Balance/Pitch/Roll.
# 3. Basket Actuator:  Connects to Motoron #2 (Addr 17) for linear motion.
# 4. Web Bridge:       Opens Port 9909 for the React Web Dashboard.
# =====================================================================

def generate_launch_description():
    return LaunchDescription([
        # 🟢 1. MOTOR DRIVER (Muscles) - Now Active!
        Node(
            package='totebot_hardware',
            executable='motor_driver',
            name='motor_driver',
            output='screen',
            emulate_tty=True
        ),

        # 🟡 2. IMU DRIVER (Balance) - Commented out for Basket Testing
        # Node(
        #     package='totebot_hardware',
        #     executable='imu_driver',
        #     name='imu_driver',
        #     output='screen',
        #     emulate_tty=True
        # ),

        # 🟢 3. BASKET ACTUATOR (The Lift)
        # Connects to the second Motoron hat for the linear actuator
        #Node(
        #    package='totebot_hardware',
        #    executable='basket_actuator_driver',
        #    name='basket_actuator',
        #    output='screen',
        #    emulate_tty=True
        #),

        # 🟢 4. ROSBRIDGE (The Web Link)
        Node(
            package='rosbridge_server',
            executable='rosbridge_websocket',
            name='rosbridge',
            parameters=[{'port': 9909}],
            output='screen'
        )
    ])