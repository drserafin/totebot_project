import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32, String


import ArducamDepthCamera as ac




class TofAlignmentNode(Node):
    def __init__(self):
        super().__init__("tof_alignment_node")


        self.declare_parameter("fps", 15.0)
        self.declare_parameter("max_distance_mm", 4000)
        self.declare_parameter("confidence_threshold", 30)
        self.declare_parameter("alignment_deadband_mm", 5.0)
        self.declare_parameter("kp", 0.002)
        self.declare_parameter("max_turn", 0.6)
        self.declare_parameter("show_preview", False)
        self.declare_parameter("publish_cmd_vel", True)
        self.declare_parameter("frame_id", "tof_camera")
        self.declare_parameter("roi_y_min_ratio", 0.45)
        self.declare_parameter("roi_y_max_ratio", 0.55)
        self.declare_parameter("roi_side_margin_ratio", 0.10)


        self.fps = float(self.get_parameter("fps").value)
        self.max_distance_mm = int(self.get_parameter("max_distance_mm").value)
        self.confidence_threshold = int(self.get_parameter("confidence_threshold").value)
        self.alignment_deadband_mm = float(self.get_parameter("alignment_deadband_mm").value)
        self.kp = float(self.get_parameter("kp").value)
        self.max_turn = float(self.get_parameter("max_turn").value)
        self.show_preview = bool(self.get_parameter("show_preview").value)
        self.publish_cmd_vel = bool(self.get_parameter("publish_cmd_vel").value)
        self.frame_id = str(self.get_parameter("frame_id").value)
        self.roi_y_min_ratio = float(self.get_parameter("roi_y_min_ratio").value)
        self.roi_y_max_ratio = float(self.get_parameter("roi_y_max_ratio").value)
        self.roi_side_margin_ratio = float(self.get_parameter("roi_side_margin_ratio").value)


        self.bridge = CvBridge()
        self.camera_ready = False
        self.range_val = float(self.max_distance_mm)
        self.last_warn_ns = 0


        self.depth_publisher = self.create_publisher(Image, "camera/depth/image_color", 10)
        self.conf_publisher = self.create_publisher(Image, "camera/confidence/image_raw", 10)
        self.turn_publisher = self.create_publisher(Float32, "camera/alignment/turn", 10)
        self.error_publisher = self.create_publisher(Float32, "camera/alignment/error_mm", 10)
        self.status_publisher = self.create_publisher(String, "camera/alignment/status", 10)
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


        info = self.cam.getCameraInfo()
        self.width = int(info.width)
        self.height = int(info.height)


        if self.show_preview:
            cv2.namedWindow("tof_alignment_preview", cv2.WINDOW_AUTOSIZE)


        self.camera_ready = True
        self.timer = self.create_timer(1.0 / max(self.fps, 1.0), self.timer_callback)
        self.get_logger().info("ToF alignment node started.")


    def build_preview(self, depth: np.ndarray, confidence: np.ndarray) -> np.ndarray:
        preview = np.nan_to_num(depth, nan=0.0, posinf=0.0, neginf=0.0)
        preview = np.clip(preview * (255.0 / max(self.range_val, 1.0)), 0, 255).astype(np.uint8)
        preview = cv2.applyColorMap(preview, cv2.COLORMAP_RAINBOW)
        preview[confidence < self.confidence_threshold] = (0, 0, 0)
        return preview


    def compute_alignment(self, depth: np.ndarray, confidence: np.ndarray):
        y_start = int(self.height * self.roi_y_min_ratio)
        y_end = int(self.height * self.roi_y_max_ratio)
        x_mid = self.width // 2
        margin = int(self.width * self.roi_side_margin_ratio)


        left_roi = (slice(y_start, y_end), slice(margin, x_mid - margin))
        right_roi = (slice(y_start, y_end), slice(x_mid + margin, self.width - margin))


        valid = confidence >= self.confidence_threshold
        left_vals = depth[left_roi][valid[left_roi]]
        right_vals = depth[right_roi][valid[right_roi]]


        left_dist = float(np.median(left_vals)) if left_vals.size else 0.0
        right_dist = float(np.median(right_vals)) if right_vals.size else 0.0


        have_both_sides = left_vals.size > 0 and right_vals.size > 0
        if not have_both_sides:
            return {
                "left_dist": left_dist,
                "right_dist": right_dist,
                "error": 0.0,
                "delta": 0.0,
                "turn": 0.0,
                "status": "NO DATA",
                "y_start": y_start,
                "y_end": y_end,
                "margin": margin,
                "x_mid": x_mid,
            }


        error = left_dist - right_dist
        delta = abs(error)


        if delta <= self.alignment_deadband_mm:
            turn = 0.0
            status = "ALIGNED"
        else:
            turn = max(min(self.kp * error, self.max_turn), -self.max_turn)
            status = "TURN RIGHT" if turn < 0.0 else "TURN LEFT"


        return {
            "left_dist": left_dist,
            "right_dist": right_dist,
            "error": error,
            "delta": delta,
            "turn": turn,
            "status": status,
            "y_start": y_start,
            "y_end": y_end,
            "margin": margin,
            "x_mid": x_mid,
        }


    def annotate_preview(self, preview: np.ndarray, result: dict) -> np.ndarray:
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.45
        thickness = 1


        cv2.rectangle(
            preview,
            (result["margin"], result["y_start"]),
            (result["x_mid"] - result["margin"], result["y_end"]),
            (0, 255, 0),
            2,
        )
        cv2.rectangle(
            preview,
            (result["x_mid"] + result["margin"], result["y_start"]),
            (self.width - result["margin"], result["y_end"]),
            (255, 0, 0),
            2,
        )


        cv2.putText(preview, f"L:{result['left_dist']:.0f}", (10, 20), font, font_scale, (0, 255, 0), thickness)
        cv2.putText(preview, f"R:{result['right_dist']:.0f}", (10, 40), font, font_scale, (255, 0, 0), thickness)
        cv2.putText(preview, f"E:{result['error']:.0f}", (10, 60), font, font_scale, (0, 255, 255), thickness)
        cv2.putText(preview, f"T:{result['turn']:.3f}", (10, 80), font, font_scale, (255, 255, 255), thickness)
        cv2.putText(
            preview,
            result["status"],
            (10, 110),
            font,
            font_scale,
            (0, 255, 0) if result["status"] == "ALIGNED" else (0, 0, 255),
            thickness,
        )
        return preview


    def publish_images(self, preview: np.ndarray, confidence: np.ndarray, stamp):
        depth_msg = self.bridge.cv2_to_imgmsg(preview, encoding="bgr8")
        depth_msg.header.stamp = stamp
        depth_msg.header.frame_id = self.frame_id


        conf_img = np.nan_to_num(confidence, nan=0.0, posinf=0.0, neginf=0.0)
        conf_img = cv2.normalize(conf_img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        conf_msg = self.bridge.cv2_to_imgmsg(conf_img, encoding="mono8")
        conf_msg.header.stamp = stamp
        conf_msg.header.frame_id = self.frame_id


        self.depth_publisher.publish(depth_msg)
        self.conf_publisher.publish(conf_msg)


    def publish_alignment(self, result: dict):
        error_msg = Float32()
        error_msg.data = float(result["error"])
        self.error_publisher.publish(error_msg)


        turn_msg = Float32()
        turn_msg.data = float(result["turn"])
        self.turn_publisher.publish(turn_msg)


        status_msg = String()
        status_msg.data = result["status"]
        self.status_publisher.publish(status_msg)


        if self.publish_cmd_vel:
            cmd = Twist()
            cmd.angular.z = float(result["turn"])
            self.cmd_vel_publisher.publish(cmd)


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
            depth = frame.depth_data
            confidence = frame.confidence_data


            result = self.compute_alignment(depth, confidence)
            preview = self.build_preview(depth, confidence)
            preview = self.annotate_preview(preview, result)


            stamp = self.get_clock().now().to_msg()
            self.publish_images(preview, confidence, stamp)
            self.publish_alignment(result)


            self.get_logger().debug(
                f"L:{result['left_dist']:.1f} R:{result['right_dist']:.1f} "
                f"E:{result['error']:.1f} T:{result['turn']:.3f} {result['status']}"
            )


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




