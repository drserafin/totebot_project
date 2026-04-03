import { Ros, Topic } from 'roslib';

class RosService {
  private ros: Ros | null = null;
  private cmdVel: Topic | null = null;
  
  // --- MEMORY & HEARTBEAT VARIABLES ---
  private currentLinear: number = 0;
  private currentAngular: number = 0;
  private publishTimer: ReturnType<typeof setInterval> | null = null;
  private readonly PUBLISH_RATE_MS = 50; 

  connect(url: string, onConnect: () => void, onError: () => void) {
    if (this.ros?.isConnected) return;

    this.ros = new Ros({ url });

    this.ros.on('connection', () => {
      console.log('? Connected to ToteBot Bridge');
      this.initTopics();
      this.startPublishLoop();
      onConnect();
    });

    this.ros.on('error', (error) => {
      console.error('? ROS Bridge Error:', error);
      this.stopPublishLoop();
      onError();
    });

    this.ros.on('close', () => {
      console.log('?? Connection to ToteBot Closed');
      this.stopPublishLoop();
      onError();
    });
  }

  private initTopics() {
    if (!this.ros) return;
    this.cmdVel = new Topic({
      ros: this.ros,
      name: '/cmd_vel',
      messageType: 'geometry_msgs/Twist'
    });
  }

  setVelocity(linearX: number, angularZ: number) {
    this.currentLinear = linearX;
    this.currentAngular = angularZ;
  }
  
private startPublishLoop() {
    if (this.publishTimer) clearInterval(this.publishTimer);
    
    this.publishTimer = setInterval(() => {
      if (!this.cmdVel) return;

      // 1. Just create a plain object instead of a new Message()
      const twist = {
        linear: { x: this.currentLinear, y: 0, z: 0 },
        angular: { x: 0, y: 0, z: -this.currentAngular }
      };

      // 2. Use "as any" to force TypeScript to accept it
      this.cmdVel.publish(twist as any);
      
    }, this.PUBLISH_RATE_MS);
  }

  private stopPublishLoop() {
    if (this.publishTimer) {
      clearInterval(this.publishTimer);
      this.publishTimer = null;
    }
  }

  disconnect() {
    this.stopPublishLoop();
    this.ros?.close();
    this.ros = null;
    this.cmdVel = null;
  }
}

export const rosService = new RosService();