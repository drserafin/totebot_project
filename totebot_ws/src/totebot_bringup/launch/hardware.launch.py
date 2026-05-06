import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import TimerAction

def generate_launch_description():

    # -----------------------------------------------------------------
    # CORE HARDWARE NODES (Boot Immediately)
    # -----------------------------------------------------------------

    imu_node = Node(
        package='totebot_hardware',
        executable='imu_driver',
        name='imu_driver',
        output='screen',
        emulate_tty=True
    )

    encoder_telemetry_node = Node(
        package='totebot_hardware',
        executable='encoder_telemetry',
        name='encoder_telemetry',
        output='screen',
        emulate_tty=True
    )

    control_mux_node = Node(
        package='totebot_hardware',
        executable='control_mux_node',
        name='control_mux_node',
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
            'cmd_timeout_ms': 500,
            'min_vin_mv': 4500,
            'dummy_mode': False,
        }]
    )

    basket_actuator_node = Node(
        package='totebot_hardware',
        executable='basket_actuator_driver',
        name='basket_actuator_driver',
        output='screen',
        emulate_tty=True
    )

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

    # -----------------------------------------------------------------
    # HEAVY SENSOR NODES (Delayed 5s to prevent I2C/Serial choking)
    # -----------------------------------------------------------------

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
        # imu_node,
        encoder_telemetry_node,
        control_mux_node,
        open_loop_motor_driver_node,
        # basket_actuator_node,
        lifter_controller_node,
        rosbridge_node,
        #delayed_camera_nodes,
    ])