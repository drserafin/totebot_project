import { Ros, Topic } from 'roslib';

// Define the shape of the message for better TypeScript support
interface TwistMessage {
  linear: { x: number; y: number; z: number };
  angular: { x: number; y: number; z: number };
}

class RosService {
  public ros: Ros | null = null;
  
  private cmdVel: Topic | null = null;
  private currentLinear = 0;
  private currentAngular = 0;
  private publishTimer: ReturnType<typeof setInterval> | null = null;
  private readonly PUBLISH_RATE_MS = 50; 

  connect(url: string, onConnect: () => void, onError: () => void) {
    if (this.ros?.isConnected) return;

    this.ros = new Ros({ url });

    this.ros.on('connection', () => {
      console.log('✅ Connected to ToteBot');
      this.initTopics();
      this.startPublishLoop();
      onConnect();
    });

    // Unified cleanup for errors/closing
    const handleFailure = () => {
      this.stopPublishLoop();
      this.resetVelocity(); // Reset memory so robot doesn't "jump" on reconnect
      onError();
    };

    this.ros.on('error', (err) => { console.error('❌ ROS Error:', err); handleFailure(); });
    this.ros.on('close', () => { console.log('⚠️ Connection Closed'); handleFailure(); });
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

  private resetVelocity() {
    this.currentLinear = 0;
    this.currentAngular = 0;
  }

  private startPublishLoop() {
    this.stopPublishLoop();
    
    this.publishTimer = setInterval(() => {
      if (!this.cmdVel) return;

      const twist: TwistMessage = {
        linear: { x: this.currentLinear, y: 0, z: 0 },
        angular: { x: 0, y: 0, z: -this.currentAngular } 
      };

      this.cmdVel.publish(twist);
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