import { Ros, Topic } from 'roslib';

interface TwistMessage {
  linear: { x: number; y: number; z: number };
  angular: { x: number; y: number; z: number };
}

class RosService {
  public ros: Ros | null = null;
  
  private cmdVel: Topic | null = null;
  private basketCmd: Topic | null = null; // 1. Declared the new topic here
  
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

    const handleFailure = () => {
      this.stopPublishLoop();
      this.resetVelocity();
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

    // 2. Safely moved the initialization inside the initTopics function
    this.basketCmd = new Topic({
      ros: this.ros,
      name: '/totebot/basket_cmd', // Matches the Python backend
      messageType: 'std_msgs/Int8'
    });
  }

  // 3. Added the function that the React slider will call
  setBasketState(state: number) {
    if (!this.basketCmd) return;
    this.basketCmd.publish({ data: state });
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
    this.basketCmd = null; // Clean up on disconnect
  }
}

export const rosService = new RosService();