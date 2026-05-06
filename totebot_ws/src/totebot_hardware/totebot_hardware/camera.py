import os
import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32, String, Bool

import ArducamDepthCamera as ac

# =====================================================================
# 🚀 TOTEBOT TOF ALIGNMENT NODE (camera.py)
# =====================================================================

class TofAlignmentNode(Node):
    def __init__(self):
        super().__init__("tof_alignment_node")

        self.declare_parameter("fps", 15.0)
        self.declare_parameter("max_distance_mm", 4000)
        self.declare_parameter("confidence_threshold", 30)
        self.declare_parameter("alignment_deadband_mm", 5.0)
        
        self.declare_parameter("ema_alpha", 0.3) 
        self.declare_parameter("max_turn", 0.20)

        self.declare_parameter("show_preview", False)
        self.declare_parameter("publish_cmd_vel", True)
        self.declare_parameter("frame_id", "tof_camera")
        self.declare_parameter("roi_y_min_ratio", 0.45)
        self.declare_parameter("roi_y_max_ratio", 0.55)
        self.declare_parameter("roi_side_margin_ratio", 0.10)
        self.declare_parameter("calibration_offset_mm", -13.0)

        self.fps                  = float(self.get_parameter("fps").value)
        self.max_distance_mm      = int(self.get_parameter("max_distance_mm").value)
        self.confidence_threshold = int(self.get_parameter("confidence_threshold").value)
        self.alignment_deadband_mm= float(self.get_parameter("alignment_deadband_mm").value)
        self.ema_alpha            = float(self.get_parameter("ema_alpha").value)
        self.max_turn             = float(self.get_parameter("max_turn").value)
        
        self.show_preview         = bool(self.get_parameter("show_preview").value)
        self.publish_cmd_vel      = bool(self.get_parameter("publish_cmd_vel").value)
        self.frame_id             = str(self.get_parameter("frame_id").value)
        self.roi_y_min_ratio      = float(self.get_parameter("roi_y_min_ratio").value)
        self.roi_y_max_ratio      = float(self.get_parameter("roi_y_max_ratio").value)
        self.roi_side_margin_ratio= float(self.get_parameter("roi_side_margin_ratio").value)
        self.calibration_offset_mm= float(self.get_parameter("calibration_offset_mm").value)

        # --- State Variables ---
        self.ema_left   = None
        self.ema_right  = None
        
        # --- Latching System ---
        self.align_active = False
        self.has_aligned  = False
        self.create_subscription(Bool, '/assist/align_active', self.mode_callback, 10)

        self.bridge       = CvBridge()
        self.camera_ready = False
        self.range_val    = float(self.max_distance_mm)
        self.last_warn_ns = 0

        self.depth_publisher   = self.create_publisher(Image,   "camera/depth/image_color",    10)
        self.conf_publisher    = self.create_publisher(Image,   "camera/confidence/image_raw", 10)
        self.turn_publisher    = self.create_publisher(Float32, "camera/alignment/turn",       10)
        self.error_publisher   = self.create_publisher(Float32, "camera/alignment/error_mm",   10)
        self.status_publisher  = self.create_publisher(String,  "camera/alignment/status",     10)
        self.cmd_vel_publisher = self.create_publisher(Twist, "camera/alignment/cmd_vel", 10)

        self.cam = ac.ArducamCamera()
        if self.cam.open(ac.Connection.CSI, 0) != 0:
            self.get_logger().error("Failed to open Arducam ToF camera.")
            return

        if self.cam.start(ac.FrameType.DEPTH) != 0:
            self.get_logger().error("Failed to start Arducam ToF camera.")
            self.cam.close()
            return

        self.cam.setControl(ac.Control.RANGE, self.max_distance_mm)
        self.range_val = float(self.cam.getControl(ac.Control.RANGE))

        info        = self.cam.getCameraInfo()
        self.width  = int(info.width)
        self.height = int(info.height)

        if self.show_preview:
            cv2.namedWindow("tof_alignment_preview", cv2.WINDOW_AUTOSIZE)

        self.camera_ready = True
        self.timer = self.create_timer(1.0 / max(self.fps, 1.0), self.timer_callback)

        self.get_logger().info(
            f"ToF alignment node started — max_turn={self.max_turn:.3f} "
            f"({int(self.max_turn * 800)}/800 speed units) — LATCHING ACTIVE"
        )

    def mode_callback(self, msg: Bool):
        if msg.data and not self.align_active:
            self.has_aligned = False
        self.align_active = msg.data

    def build_preview(self, depth: np.ndarray, confidence: np.ndarray) -> np.ndarray:
        preview = np.nan_to_num(depth, nan=0.0, posinf=0.0, neginf=0.0)
        preview = np.clip(preview * (255.0 / max(self.range_val, 1.0)), 0, 255).astype(np.uint8)
        preview = cv2.applyColorMap(preview, cv2.COLORMAP_RAINBOW)
        preview[confidence < self.confidence_threshold] = (0, 0, 0)
        return preview

    def compute_alignment(self, depth: np.ndarray, confidence: np.ndarray):
        y_start = int(self.height * self.roi_y_min_ratio)
        y_end   = int(self.height * self.roi_y_max_ratio)
        x_mid   = self.width // 2
        margin  = int(self.width * self.roi_side_margin_ratio)

        left_roi  = (slice(y_start, y_end), slice(margin, x_mid - margin))
        right_roi = (slice(y_start, y_end), slice(x_mid + margin, self.width - margin))

        valid      = confidence >= self.confidence_threshold
        left_vals  = depth[left_roi][valid[left_roi]]
        right_vals = depth[right_roi][valid[right_roi]]

        raw_left  = float(np.median(left_vals))  if left_vals.size  else None
        raw_right = float(np.median(right_vals)) if right_vals.size else None

        # --- 1. EMA FILTER ---
        if raw_left is not None:
            self.ema_left = raw_left if self.ema_left is None else (self.ema_alpha * raw_left + (1 - self.ema_alpha) * self.ema_left)
        
        if raw_right is not None:
            self.ema_right = raw_right if self.ema_right is None else (self.ema_alpha * raw_right + (1 - self.ema_alpha) * self.ema_right)

        if self.ema_left is None or self.ema_right is None:
            return {
                "left_dist": 0.0, "right_dist": 0.0,
                "error": 0.0, "delta": 0.0, "turn": 0.0,
                "status": "WAITING FOR DATA",
                "y_start": y_start, "y_end": y_end,
                "margin": margin, "x_mid": x_mid,
            }

        # --- 2. CONSTANT SPEED CONTROLLER WITH LATCH ---
        error = self.ema_left - self.ema_right - self.calibration_offset_mm
        delta = abs(error)

        # First, calculate what the screen SHOULD say, regardless of the button
        if delta <= self.alignment_deadband_mm:
            screen_text = "ALIGNED"
            ideal_turn  = 0.0
        elif error > 0:
            screen_text = "TURN RIGHT"
            ideal_turn  = -self.max_turn
        else:
            screen_text = "TURN LEFT"
            ideal_turn  = self.max_turn

        # Second, apply the button rules to the ACTUAL motors
        if not self.align_active:
            turn   = 0.0
            status = f"{screen_text} (IDLE)"
            
        elif delta <= self.alignment_deadband_mm:
            turn   = 0.0
            status = "ALIGNED (LOCKED)"
            self.has_aligned = True
            
        elif self.has_aligned:
            turn   = 0.0
            status = "ALIGNED (LOCKED)"
            
        else:
            turn   = ideal_turn
            status = f"{screen_text} (MOVING)"

        return {
            "left_dist": self.ema_left, "right_dist": self.ema_right,
            "error": error, "delta": delta, "turn": turn,
            "status": status,
            "y_start": y_start, "y_end": y_end,
            "margin": margin, "x_mid": x_mid,
        }

    def annotate_preview(self, preview: np.ndarray, result: dict) -> np.ndarray:
        font       = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.45
        thickness  = 1

        cv2.rectangle(preview,
            (result["margin"], result["y_start"]),
            (result["x_mid"] - result["margin"], result["y_end"]),
            (0, 255, 0), 2)
        cv2.rectangle(preview,
            (result["x_mid"] + result["margin"], result["y_start"]),
            (self.width - result["margin"], result["y_end"]),
            (255, 0, 0), 2)

        cv2.putText(preview, f"L:{result['left_dist']:.0f}",  (10, 20),  font, font_scale, (0, 255, 0),   thickness)
        cv2.putText(preview, f"R:{result['right_dist']:.0f}", (10, 40),  font, font_scale, (255, 0, 0),   thickness)
        cv2.putText(preview, f"E:{result['error']:.0f}",      (10, 60),  font, font_scale, (0, 255, 255), thickness)
        cv2.putText(preview, f"T:{result['turn']:.3f}",       (10, 80),  font, font_scale, (255, 255, 255), thickness)
        
        # Make the status text larger and bolder
        status_color = (0, 255, 0) if "ALIGNED" in result["status"] else (0, 255, 255) # Yellow for turning, Green for aligned
        cv2.putText(preview, result["status"], (10, 110), font, 0.55, status_color, 2)
        return preview

    def publish_images(self, preview: np.ndarray, confidence: np.ndarray, stamp):
        depth_msg = self.bridge.cv2_to_imgmsg(preview, encoding="bgr8")
        depth_msg.header.stamp    = stamp
        depth_msg.header.frame_id = self.frame_id

        conf_img = np.nan_to_num(confidence, nan=0.0, posinf=0.0, neginf=0.0)
        conf_img = cv2.normalize(conf_img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        conf_msg = self.bridge.cv2_to_imgmsg(conf_img, encoding="mono8")
        conf_msg.header.stamp    = stamp
        conf_msg.header.frame_id = self.frame_id

        self.depth_publisher.publish(depth_msg)
        self.conf_publisher.publish(conf_msg)

    def publish_alignment(self, result: dict):
        error_msg      = Float32()
        error_msg.data = float(result["error"])
        self.error_publisher.publish(error_msg)

        turn_msg      = Float32()
        turn_msg.data = float(result["turn"])
        self.turn_publisher.publish(turn_msg)

        status_msg      = String()
        status_msg.data = result["status"]
        self.status_publisher.publish(status_msg)

        if self.publish_cmd_vel:
            cmd           = Twist()
            cmd.linear.x  = float(result["turn"])   
            cmd.angular.z = 0.0
            self.cmd_vel_publisher.publish(cmd)

            if self.align_active:
                self.get_logger().debug(
                    f"[ALIGN CMD] status={result['status']}  "
                    f"L={result['left_dist']:.1f}  R={result['right_dist']:.1f}  "
                    f"error={result['error']:.1f}mm  linear.x={result['turn']:.3f}  "
                    f"(~{int(result['turn'] * 800)} speed units)"
                )

    def timer_callback(self):
        if not self.camera_ready:
            return

        frame = self.cam.requestFrame(2000)
        if frame is None or not isinstance(frame, ac.DepthData):
            now_ns = self.get_clock().now().nanoseconds
            if now_ns - self.last_warn_ns > 2_000_000_000:
                self.get_logger().warning("Failed to capture frame from ToF camera.")
                self.last_warn_ns = now_ns
            return

        try:
            depth      = frame.depth_data
            confidence = frame.confidence_data

            result  = self.compute_alignment(depth, confidence)
            preview = self.build_preview(depth, confidence)
            preview = self.annotate_preview(preview, result)

            stamp = self.get_clock().now().to_msg()
            self.publish_images(preview, confidence, stamp)
            self.publish_alignment(result)

            if self.show_preview:
                cv2.imshow("tof_alignment_preview", preview)
                cv2.waitKey(1)
        finally:
            self.cam.releaseFrame(frame)

    def shutdown(self):
        if self.publish_cmd_vel:
            self.cmd_vel_publisher.publish(Twist())

        if self.show_preview:
            cv2.destroyAllWindows()

        if getattr(self, "camera_ready", False):
            self.get_logger().info("Shutting down ToF hardware...")
            self.cam.stop()
            self.cam.close()
            self.camera_ready = False

def main(args=None):
    rclpy.init(args=args)
    node = TofAlignmentNode()

    try:
        if node.camera_ready:
            rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()


