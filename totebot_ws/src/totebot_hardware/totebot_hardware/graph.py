import tkinter as tk
import rclpy
from matplotlib.backends import FigureCanvasTkAgg
from matplotlib.figure import Figure

class motorGUI(tk.Tk):
    def __init__(self,ros_node):
        super().__init__()
        self.title("Robot Current v. Weight")
        self.ros_node=ros_node

        self.fig=Figure(figsize=(5, 4), dpi=100)
        self.ax=self.fig.add_subplot(111)
        self.ax.set_xlabel('Weight (kg)')
        self.ax.set_ylabel('Current (A)')
        self.data_buffer=[]

        self.canvas = FigureCanvasTkAgg(self.fig,master=self)
        self.canvas.get_tk_widget().pack(side=tk.TOP,fill=tk.BOTH,expand=1)
    def update_plot(self):
        if self.ros_node.current_data:
            self.data_buffer.append(self.ros_node.current_data)
            if len(self.data_buffer)>50:
                self.data_buffer.pop(0)

            self.ax.clear()
            self.ax.plot(self.data_buffer,label='Current (A)')
            self.ax.set_xlabel('Time')
            self.ax.set_ylabel('Current (A)')
            self.ax.legend()
            self.canvas.draw()

        self.after(100, self.update_plot)

def subscriber_A(Node):
    def __init__(self):
        super().__init__("subscriber_node")
        self.subscription=self.create_subscription(
            Float64,'motor_data',self.listener_callback,10)
        self.current_data=None
    def listener_callback(self,msg):
        self.current_data=msg.data

def main():
    rclpy.init()
    ros_node=subscriber_A()
    app=motorGUI(ros_node)
    app.mainloop()
    ros_node.destroy_node()
    rclpy.shutdown()