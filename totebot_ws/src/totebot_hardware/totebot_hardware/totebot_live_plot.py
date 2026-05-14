#!/usr/bin/env python3
"""
ToteBot Live Telemetry Dashboard
=================================
Subscribes to:
  /encoder_telemetry  Float32MultiArray  [2]=left_rpm  [3]=right_rpm
  /motor_current_ma   Float32MultiArray  [0]=left_A    [1]=right_A

Run:
  ros2 run totebot_hardware totebot_live_plot
"""

import threading
import collections
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
import matplotlib
matplotlib.use('TkAgg')  # explicit backend — works on Pi with display
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.gridspec import GridSpec

# ── Config ───────────────────────────────────────────────────────────
WINDOW_SECONDS = 30
UPDATE_MS      = 100
MAX_POINTS     = WINDOW_SECONDS * 10

# ── Shared buffers ────────────────────────────────────────────────────
left_rpm   = collections.deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
right_rpm  = collections.deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
left_amps  = collections.deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
right_amps = collections.deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
data_lock  = threading.Lock()


# ── ROS2 node ─────────────────────────────────────────────────────────
class TelemetrySubscriber(Node):
    def __init__(self):
        super().__init__('totebot_live_plot')
        self.create_subscription(
            Float32MultiArray, '/encoder_telemetry', self.rpm_callback, 10)
        self.create_subscription(
            Float32MultiArray, '/motor_current_ma', self.current_callback, 10)
        self.get_logger().info("ToteBot live plot — waiting for data...")

    def rpm_callback(self, msg):
        if len(msg.data) < 4:
            return
        with data_lock:
            left_rpm.append(float(msg.data[2]))
            right_rpm.append(float(msg.data[3]))

    def current_callback(self, msg):
        if len(msg.data) < 2:
            return
        with data_lock:
            left_amps.append(float(msg.data[0]))
            right_amps.append(float(msg.data[1]))


def ros_thread():
    rclpy.init()
    node = TelemetrySubscriber()
    try:
        rclpy.spin(node)
    except Exception:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main():
    # ── Start ROS2 in background ──────────────────────────────────────
    t = threading.Thread(target=ros_thread, daemon=True)
    t.start()

    # ── Build figure ──────────────────────────────────────────────────
    fig = plt.figure(figsize=(12, 7), facecolor='#1a1a2e')
    fig.canvas.manager.set_window_title('ToteBot Live Telemetry')

    gs     = GridSpec(2, 1, figure=fig, hspace=0.45)
    ax_rpm = fig.add_subplot(gs[0])
    ax_cur = fig.add_subplot(gs[1])

    DARK_BG  = '#1a1a2e'
    PANEL_BG = '#16213e'
    GRID_COL = '#2a2a4a'
    TEXT_COL = '#e0e0e0'
    BLUE     = '#4fc3f7'
    GREEN    = '#69f0ae'
    ORANGE   = '#ffb74d'
    RED      = '#ef5350'

    def style_axis(ax, title, ylabel, ylim):
        ax.set_facecolor(PANEL_BG)
        ax.tick_params(colors=TEXT_COL, labelsize=10)
        ax.set_title(title, color=TEXT_COL, fontsize=13, fontweight='bold', pad=10)
        ax.set_ylabel(ylabel, color=TEXT_COL, fontsize=11)
        ax.set_xlabel(f'Last {WINDOW_SECONDS}s', color=TEXT_COL, fontsize=10)
        ax.set_ylim(ylim)
        ax.set_xlim(0, MAX_POINTS)
        ax.grid(True, color=GRID_COL, linewidth=0.6, linestyle='--')
        ax.spines[:].set_color(GRID_COL)
        ax.set_xticks([])

    style_axis(ax_rpm, 'Wheel RPM',         'RPM',  (-250, 250))
    style_axis(ax_cur, 'Motor Current Draw', 'Amps', (0,    16))
    ax_rpm.axhline(0, color=GRID_COL, linewidth=1.0)

    line_lrpm,  = ax_rpm.plot([], [], color=BLUE,   linewidth=1.8, label='Left RPM')
    line_rrpm,  = ax_rpm.plot([], [], color=GREEN,  linewidth=1.8, label='Right RPM')
    line_lamps, = ax_cur.plot([], [], color=ORANGE, linewidth=1.8, label='Left (A)')
    line_ramps, = ax_cur.plot([], [], color=RED,    linewidth=1.8, label='Right (A)')

    rpm_text = ax_rpm.text(
        0.01, 0.95, '', transform=ax_rpm.transAxes,
        color=TEXT_COL, fontsize=10, verticalalignment='top',
        fontfamily='monospace',
        bbox=dict(facecolor=DARK_BG, alpha=0.7, edgecolor=GRID_COL, boxstyle='round,pad=0.4'))

    cur_text = ax_cur.text(
        0.01, 0.95, '', transform=ax_cur.transAxes,
        color=TEXT_COL, fontsize=10, verticalalignment='top',
        fontfamily='monospace',
        bbox=dict(facecolor=DARK_BG, alpha=0.7, edgecolor=GRID_COL, boxstyle='round,pad=0.4'))

    for ax in (ax_rpm, ax_cur):
        ax.legend(loc='upper right', fontsize=10, facecolor=DARK_BG,
                  edgecolor=GRID_COL, labelcolor=TEXT_COL)

    fig.suptitle('ToteBot Live Telemetry', color=TEXT_COL,
                 fontsize=16, fontweight='bold', y=0.98)

    x = list(range(MAX_POINTS))

    def update(_frame):
        with data_lock:
            lr = list(left_rpm)
            rr = list(right_rpm)
            la = list(left_amps)
            ra = list(right_amps)

        line_lrpm.set_data(x, lr)
        line_rrpm.set_data(x, rr)
        line_lamps.set_data(x, la)
        line_ramps.set_data(x, ra)

        rpm_text.set_text(f"L: {lr[-1]:+7.1f} RPM    R: {rr[-1]:+7.1f} RPM")
        cur_text.set_text(f"L:  {la[-1]:5.2f} A       R:  {ra[-1]:5.2f} A")

        return line_lrpm, line_rrpm, line_lamps, line_ramps, rpm_text, cur_text

    ani = animation.FuncAnimation(
        fig, update,
        interval=UPDATE_MS,
        blit=True,
        cache_frame_data=False
    )

    fig.subplots_adjust(top=0.93, hspace=0.45)
    plt.show()


if __name__ == '__main__':
    main()
