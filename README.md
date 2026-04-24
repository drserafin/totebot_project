#!/bin/bash

# ==========================================
# TOTEBOT SYSTEM RECOVERY & STARTUP
# ==========================================

# 1. Start and Enter the Container
# Run these on the Raspberry Pi Host
docker start totebot_brain
docker exec -it totebot_brain bash

# 2. Workspace Preparation

cd /totebot_ws/totebot_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch totebot_bringup hardware.launch.py


docker run -it --rm \
  --privileged \
  -v /dev:/dev \
  --net=host \
  microros/micro-ros-agent:jazzy serial --dev /dev/ttyUSB0 -v4

#35. Useful Debugging Commands (Internal)
# Inside the container, you can run:
# ros2 node list
# ros2 topic list
# ros2 topic echo /encoder_telemetry
# ros2 param get /pid_controller Kp