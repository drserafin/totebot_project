import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
from . import motoron
import time

MOTOR_SPEED = 800
STALL_MA    = 6000 # Safety: Still stops if motor pulls too much current

class LifterController(Node):
    def __init__(self):
        super().__init__('lifter_controller')

        self.mc = None
        self.ready = False
        self.current_speed = 0
        self.current_units = None

        # Attempt to find the Motoron at 0x11
        self.init_timer = self.create_timer(2.0, self.try_motoron_init)

        # Listen for movement commands (1, -1, 0)
        self.create_subscription(Int32, '/lifter_cmd', self.cmd_callback, 10)

        # 10Hz Heartbeat to keep the motor driver alive
        self.create_timer(0.1, self.motor_heartbeat)

        self.get_logger().info("🚀 Pure Open-Loop Controller: Targeting Motoron 0x11 CH2")

    def try_motoron_init(self):
        try:
            self.mc = motoron.MotoronI2C(address=0x11)
            self.mc.reinitialize()
            self.mc.disable_crc()
            self.mc.clear_reset_flag()
            self.mc.set_max_acceleration(2, 140)
            self.mc.set_max_deceleration(2, 300)
            
            # Setup current sensing for stall protection
            self.board_type = motoron.CurrentSenseType.MOTORON_18V20
            self.reference_mv = 3300
            self.current_units = motoron.current_sense_units_milliamps(
                self.board_type, self.reference_mv)
            
            self.ready = True
            self.init_timer.cancel()
            self.get_logger().info("✅ Motoron 0x11 CH2 Initialized. Ready for commands.")
        except Exception as e:
            self.get_logger().warn(f"⏳ Motoron 0x11 not found, retrying... ({e})")

    def cmd_callback(self, msg: Int32):
        if not self.ready:
            return

        cmd = int(msg.data)
        if cmd == 1:
            self.current_speed = MOTOR_SPEED
            self.get_logger().info("🔧 Action: EXTENDING")
        elif cmd == -1:
            self.current_speed = -MOTOR_SPEED
            self.get_logger().info("🔧 Action: RETRACTING")
        else:
            self.current_speed = 0
            self.get_logger().info("🔧 Action: STOP")

    def motor_heartbeat(self):
        if not self.ready:
            return

        try:
            # Check for physical stall using Motoron's internal current sense
            current_ma = self.mc.get_current_sense_processed(2) * self.current_units
            if current_ma > STALL_MA:
                self.current_speed = 0
                self.get_logger().error(f"❌ STALL DETECTED ({round(current_ma)} mA). Safety Stop.")
            
            # Push speed to hardware
            self.mc.set_speed(2, self.current_speed)
            
        except Exception as e:
            self.get_logger().error(f"Hardware Error on 0x11: {e}")

    def destroy_node(self):
        if self.mc:
            try:
                self.mc.set_speed(2, 0) # Emergency stop on exit
            except:
                pass
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = LifterController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()