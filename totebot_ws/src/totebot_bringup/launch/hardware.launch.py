import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import TimerAction

# =====================================================================
# 🚀 TOTEBOT MASTER IGNITION FILE (hardware.launch.py)
# =====================================================================
# 📖 QUICK START GUIDE
#
# [STEP 1] Wake up the Docker Container
#          docker start totebot_brain
#
# [STEP 2] Enter the Container
#          docker exec -it totebot_brain bash
#
# [STEP 3] Build (run every time you edit code)
#          cd /totebot_ws && colcon build --symlink-install
#
# [STEP 4] Source
#          source /opt/ros/jazzy/setup.bash && source /totebot_ws/install/setup.bash
#
# [STEP 5] Launch
#          ros2 launch totebot_bringup hardware.launch.py
#
# All at once:
#   docker start totebot_brain && \
#   docker exec -it totebot_brain bash -c \
#   "cd /totebot_ws && colcon build --symlink-install && \
#    source /opt/ros/jazzy/setup.bash && \
#    source /totebot_ws/install/setup.bash && \
#    ros2 launch totebot_bringup hardware.launch.py"
#
# 🌟 NODE MAP:
# ┌─────────────────────────────────────────────────────────────┐
# │  ESP32 (hardware)                                           │
# │    └── micro_ros_agent  →  /encoder_array                   │
# │                                 ↓                           │
# │  encoder_telemetry  →  /encoder_telemetry (stats only)      │
# │                                                             │
# │  Web Dashboard  →  /cmd_vel  →  open_loop_motor_driver      │
# │                                       ↓                     │
# │                              Motoron M2H18v20 (drive)       │
# │                                                             │
# │  Web Dashboard  →  /totebot/basket_cmd  →  basket_actuator  │
# │                                       ↓                     │
# │                              Motoron 0x11 (basket)          │
# │                                                             │
# │  Web Dashboard  →  /lifter_cmd  →  lifter_controller        │
# │                       ↑                  ↓                  │
# │                /encoder_ticks    Motoron 0x?? (GoTubes)     │
# └─────────────────────────────────────────────────────────────┘
# =====================================================================

def generate_launch_description():

    # ─────────────────────────────────────────────────────────────
    # CORE HARDWARE NODES (Boot Immediately)
    # ─────────────────────────────────────────────────────────────

    encoder_telemetry_node = Node(
        package='totebot_hardware',
        executable='encoder_telemetry',
        name='encoder_telemetry',
        output='screen',
        emulate_tty=True
    )

    open_loop_motor_driver_node = Node(
        package='totebot_hardware',
        executable='open_loop_motor_driver',
        name='open_loop_motor_driver',
        output='screen',
        emulate_tty=True,
        parameters=[{
            'max_speed': 800,
            'accel_limit': 140,
            'decel_limit': 300,
            'cmd_timeout_ms': 100,
            'min_vin_mv': 4500,
            'dummy_mode': False,
        }]
    )

    # ── NEW: Basket actuator (Motoron 0x11) ──────────────────────
    basket_actuator_node = Node(
        package='totebot_hardware',
        executable='basket_actuator_driver',
        name='basket_actuator_driver',
        output='screen',
        emulate_tty=True
    )

    # ── NEW: GoTubes lifter (open loop + soft limit) ──────────────
    lifter_controller_node = Node(
        package='totebot_hardware',
        executable='lifter_controller',
        name='lifter_controller',
        output='screen',
        emulate_tty=True
    )

    rosbridge_node = Node(
        package='rosbridge_server',
        executable='rosbridge_websocket',
        name='rosbridge',
        parameters=[{'port': 9909}],
        output='screen'
    )

    # ─────────────────────────────────────────────────────────────
    # HEAVY SENSOR NODES (Delayed 5s to prevent I2C/Serial choking)
    # ─────────────────────────────────────────────────────────────

    tof_camera_node = Node(
        package='totebot_hardware',
        executable='camera',
        name='tof_camera',
        output='screen',
        emulate_tty=True
    )

    web_video_server_node = Node(
        package='web_video_server',
        executable='web_video_server',
        name='web_video_server',
        parameters=[{'port': 8081}],
        output='screen',
        emulate_tty=True
    )

    delayed_camera_nodes = TimerAction(
        period=5.0,
        actions=[tof_camera_node, web_video_server_node]
    )

    return LaunchDescription([
        encoder_telemetry_node,
        open_loop_motor_driver_node,
        basket_actuator_node,       # ← basket
        lifter_controller_node,     # ← GoTubes
        rosbridge_node,
        delayed_camera_nodes,
    ])