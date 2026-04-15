from setuptools import find_packages, setup

package_name = 'totebot_hardware'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Kevin Serafin',
    maintainer_email='kevin@example.com', # You can update this
    description='Hardware drivers for ToteBot',
    license='MIT',
    tests_require=['pytest'],
   entry_points={
        'console_scripts': [
            'motor_driver = totebot_hardware.motor_driver:main',
            'imu_driver = totebot_hardware.imu_driver:main',
            'basket_actuator_driver = totebot_hardware.basket_actuator_driver:main',
            'lift_actuator_driver = totebot_hardware.lift_actuator_driver:main',
            'micro_ros_bridge = totebot_hardware.micro_ros_bridge:main',
            'lifter_controller = totebot_hardware.lifter_controller:main'
        ],
    },
)