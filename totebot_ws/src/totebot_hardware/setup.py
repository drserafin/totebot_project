from setuptools import setup
import os
from glob import glob

package_name = 'totebot_hardware'

setup(
    name=package_name,
    version='0.0.0',
    # Explicitly name the package folder instead of using find_packages()
    packages=[package_name], 
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='root@todo.todo',
    description='Motoron Driver for Totebot',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'motor_driver = totebot_hardware.motor_driver:main'
        ],
    },
)