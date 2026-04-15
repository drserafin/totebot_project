import sys
import select
import tty
import termios
import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32 
from . import motoron
# =====================================================================
# 🚀 TOTEBOT LIFTER PID TEST (Docker Safe)
# Run command inside container: 
# colcon build --packages-select totebot_hardware
# source install/setup.bash
# ros2 run totebot_hardware lifter_controller
# =====================================================================

class LifterPIDController(Node):
    def __init__(self):
        super().__init__('lifter_pid_controller')
        
        # --- 1. PID Tuning & Targets ---
        self.target_position = 0  
        self.current_position = 0
        self.Kp = 0.5   
        self.Ki = 0.0   
        self.Kd = 0.1   

        self.prev_error = 0
        self.integral_sum = 0
        self.tolerance = 15  

        # --- 2. Motoron Initialization (From your driver) ---
        self.mc = motoron.MotoronI2C()
        self.stall_threshold_ma = 2000  # 2 Amp limit for lifting mechanism
        self.reference_mv = 3300 
        self.vin_type = motoron.VinSenseType.MOTORON_256
        
        # The "No-Panic" Mask
        self.error_mask = (
            (1 << motoron.STATUS_FLAG_PROTOCOL_ERROR) |
            (1 << motoron.STATUS_FLAG_CRC_ERROR) |
            (1 << motoron.STATUS_FLAG_COMMAND_TIMEOUT))

        self.setup_motoron()

        # --- 3. Start Listening to the ESP32 ---
        self.subscription = self.create_subscription(
            Int32,
            'encoder_ticks',
            self.pid_loop_callback,
            10)
        
        self.get_logger().info("Lifter PID Online. Waiting for ticks...")

    def setup_motoron(self):
        self.mc.reinitialize()
        self.mc.clear_reset_flag()
        self.mc.clear_latched_status_flags(0xFFFF) 
        self.mc.clear_motor_fault()

        self.mc.set_error_response(motoron.ERROR_RESPONSE_COAST)
        self.mc.set_error_mask(self.error_mask)
        self.mc.set_command_timeout_milliseconds(200)
        self.mc.set_max_acceleration(1, 140)
        self.mc.set_max_deceleration(1, 300)
        
        while self.mc.get_motor_driving_flag(): pass
        self.mc.clear_motor_fault()

        self.board_type = motoron.CurrentSenseType.MOTORON_18V20
        self.current_units = motoron.current_sense_units_milliamps(self.board_type, self.reference_mv)

    def set_target(self, new_target):
        if self.target_position != new_target:
            self.target_position = new_target
            self.integral_sum = 0 # Reset integral windup on new command
            # Clear line and print new target
            sys.stdout.write("\033[K") 
            print(f"\r🎯 Target Updated: {self.target_position}")

    def emergency_brake(self):
        self.target_position = self.current_position
        self.mc.set_speed(1, 0)
        sys.stdout.write("\033[K") 
        print("\r🛑 E-BRAKE: Target locked to current position.")

    def pid_loop_callback(self, msg):
        self.current_position = msg.data

        # --- Safety First: Read Current ---
        processed_reading = self.mc.get_current_sense_processed(1)
        current_ma = processed_reading * self.current_units

        if current_ma > self.stall_threshold_ma:
            self.mc.set_speed(1, 0)
            self.target_position = self.current_position 
            sys.stdout.write("\033[K")
            print(f"\r⚠️ LIMIT REACHED! {round(current_ma)} mA. Motor Killed.")
            return

        # --- The PID Math ---
        error = self.target_position - self.current_position

        if abs(error) <= self.tolerance:
            self.mc.set_speed(1, 0)
            return

        p_term = self.Kp * error
        self.integral_sum += error
        i_term = self.Ki * self.integral_sum
        d_term = self.Kd * (error - self.prev_error)

        raw_speed = int(p_term + i_term + d_term)
        motor_speed = max(-800, min(800, raw_speed))

        self.mc.set_speed(1, motor_speed)
        self.prev_error = error

        # Live terminal update
        sys.stdout.write(f"\rPos: {self.current_position} | Tgt: {self.target_position} | Spd: {motor_speed} | mA: {round(current_ma)}   ")
        sys.stdout.flush()

# =====================================================================
# ⌨️ DOCKER-SAFE KEYBOARD THREAD
# =====================================================================
def keyboard_loop(node):
    settings = termios.tcgetattr(sys.stdin)
    print("\n--- LIFTER PID TEST ---")
    print("[w] : Deloy (Target: 5281)")
    print("[s] : Restract (Target: 0)")
    print("[SPACE] : Emergency Brake")
    print("[q] : Quit\n")
    
    try:
        tty.setraw(sys.stdin.fileno())
        while rclpy.ok():
            # Non-blocking read
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
            if rlist:
                key = sys.stdin.read(1)
                if key == 'w':
                    node.set_target(5281)
                elif key == 's':
                    node.set_target(0)
                elif key == ' ':
                    node.emergency_brake()
                elif key == 'q' or key == '\x03': # q or Ctrl+C
                    break
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node.mc.set_speed(1, 0)
        rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    node = LifterPIDController()
    
    # Run ROS spin in the background, keep keyboard in the main thread
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    keyboard_loop(node)

    node.destroy_node()

if __name__ == '__main__':
    main()