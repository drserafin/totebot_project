import { Ros, Topic } from 'roslib';

interface TwistMessage {
  linear:  { x: number; y: number; z: number };
  angular: { x: number; y: number; z: number };
}

class RosService {
  public ros: Ros | null = null;

  // Joystick now publishes to /cmd_vel/joy — the mux forwards it to /cmd_vel
  private cmdVelJoy: Topic | null = null;
  private basketCmd: Topic | null = null;
  private alignCmd:  Topic | null = null;
  private fusionCmd: Topic | null = null;  // ✅ Declared here at the top

  private currentLinear  = 0;
  private currentAngular = 0;
  private publishTimer: ReturnType<typeof setInterval> | null = null;
  private readonly PUBLISH_RATE_MS = 50;

  // ——— Debug helpers ————————————————————————————————————————————————————————
  private publishTickCount = 0;
  private readonly DEBUG_LOG_EVERY_N_TICKS = 10;

  private logDebug(tag: string, msg: string) { console.debug(`[RosService][${tag}] ${msg}`); }
  private logInfo (tag: string, msg: string) { console.info (`[RosService][${tag}] ${msg}`); }
  private logWarn (tag: string, msg: string) { console.warn (`[RosService][${tag}] ${msg}`); }
  private logError(tag: string, msg: string) { console.error(`[RosService][${tag}] ${msg}`); }
  // ——————————————————————————————————————————————————————————————————————————

  connect(url: string, onConnect: () => void, onError: () => void) {
    if (this.ros?.isConnected) {
      this.logWarn('connect', `Already connected – ignoring duplicate connect() call to ${url}`);
      return;
    }

    this.logInfo('connect', `Attempting connection → ${url}`);
    this.ros = new Ros({ url });

    this.ros.on('connection', () => {
      this.logInfo('connect', '✅ Connected to ToteBot');
      this.initTopics();
      this.startPublishLoop();
      onConnect();
    });

    const handleFailure = (reason: string) => {
      this.logWarn('connect', `⚠️ Connection lost (${reason}) – stopping publish loop & resetting velocity`);
      this.stopPublishLoop();
      this.resetVelocity();
      onError();
    };

    this.ros.on('error', (err) => {
      this.logError('ros.error', `❌ ROS bridge error: ${JSON.stringify(err)}`);
      handleFailure('error');
    });

    this.ros.on('close', () => {
      this.logWarn('ros.close', '⚠️ WebSocket closed');
      handleFailure('close');
    });
  }

  private initTopics() {
    if (!this.ros) {
      this.logError('initTopics', 'ros is null – cannot initialise topics');
      return;
    }

    this.cmdVelJoy = new Topic({
      ros: this.ros,
      name: '/cmd_vel/joy',
      messageType: 'geometry_msgs/Twist',
    });
    this.logInfo('initTopics', '📌 Topic advertised: /cmd_vel/joy (geometry_msgs/Twist)');

    this.basketCmd = new Topic({
      ros: this.ros,
      name: '/totebot/basket_cmd',
      messageType: 'std_msgs/Int8',
    });
    this.logInfo('initTopics', '📌 Topic advertised: /totebot/basket_cmd (std_msgs/Int8)');

    this.alignCmd = new Topic({
      ros: this.ros,
      name: '/assist/align_active',
      messageType: 'std_msgs/Bool',
    });
    this.logInfo('initTopics', '📌 Topic advertised: /assist/align_active (std_msgs/Bool)');

    // ✅ Initialized here inside initTopics
    this.fusionCmd = new Topic({
      ros: this.ros,
      name: '/assist/fusion_active',
      messageType: 'std_msgs/Bool',
    });
    this.logInfo('initTopics', '📌 Topic advertised: /assist/fusion_active (std_msgs/Bool)');
  }

  // ——— Public API ———————————————————————————————————————————————————————————

  setBasketState(state: number) {
    if (!this.basketCmd) {
      this.logWarn('setBasketState', 'basketCmd topic not ready – dropping message');
      return;
    }
    this.logDebug('setBasketState', `🧽 Publishing basket state → data: ${state}`);
    this.basketCmd.publish({ data: state });
  }

  setAlignActive(isActive: boolean) {
    if (!this.alignCmd) {
      this.logWarn('setAlignActive', 'alignCmd topic not ready – dropping message');
      return;
    }
    this.logDebug('setAlignActive', `🎯 Publishing align active → data: ${isActive}`);
    this.alignCmd.publish({ data: isActive });
  }

  // ✅ Created as a proper class method
  setFusionActive(isActive: boolean) {
    if (!this.fusionCmd) {
      this.logWarn('setFusionActive', 'fusionCmd topic not ready – dropping message');
      return;
    }
    this.logDebug('setFusionActive', `🌪️ Publishing fusion active → data: ${isActive}`);
    this.fusionCmd.publish({ data: isActive });
  }

  /**
   * Called by the React joystick on every pointer/keyboard event.
   * Publishes to /cmd_vel/joy — the mux decides if it reaches /cmd_vel.
   *
   * Axis cross-mapping (intentional – matches React joystick layout):
   * linearX  → Twist.linear.x   (Python reads as target_angular)
   * angularZ → Twist.angular.z  (Python reads as target_linear)
   */
  setVelocity(linearX: number, angularZ: number) {
    this.logDebug(
      'setVelocity',
      `🕹️ React cmd → linearX: ${linearX.toFixed(3)}  angularZ: ${angularZ.toFixed(3)}`,
    );

    const changed = this.currentLinear !== linearX || this.currentAngular !== angularZ;
    this.currentLinear  = linearX;
    this.currentAngular = angularZ;

    if (changed) {
      this.logDebug(
        'setVelocity',
        `📝 Velocity updated → linear: ${this.currentLinear.toFixed(3)}  angular: ${this.currentAngular.toFixed(3)}`,
      );
    }
  }

  // ——— Internal helpers —————————————————————————————————————————————————————

  private resetVelocity() {
    this.logDebug('resetVelocity', '🔄 Resetting velocity to zero');
    this.currentLinear  = 0;
    this.currentAngular = 0;
  }

  private startPublishLoop() {
    this.stopPublishLoop();
    this.publishTickCount = 0;
    this.logInfo('startPublishLoop', `▶️ Publish loop started at ${this.PUBLISH_RATE_MS} ms intervals → /cmd_vel/joy`);

    this.publishTimer = setInterval(() => {
      if (!this.cmdVelJoy) {
        this.logWarn('publishLoop', 'cmdVelJoy topic not ready – skipping tick');
        return;
      }

      const twist: TwistMessage = {
        linear:  { x: this.currentLinear,  y: 0, z: 0 },
        angular: { x: 0, y: 0, z: this.currentAngular },
      };

      if (this.publishTickCount % this.DEBUG_LOG_EVERY_N_TICKS === 0) {
        this.logDebug(
          'publishLoop',
          `📡 Twist → /cmd_vel/joy  linear.x: ${twist.linear.x.toFixed(3)}` +
          `  angular.z: ${twist.angular.z.toFixed(3)}  (tick #${this.publishTickCount})`,
        );
      }
      this.publishTickCount++;

      this.cmdVelJoy.publish(twist);
    }, this.PUBLISH_RATE_MS);
  }

  private stopPublishLoop() {
    if (this.publishTimer) {
      clearInterval(this.publishTimer);
      this.publishTimer = null;
      this.logInfo('stopPublishLoop', '⏸️ Publish loop stopped');
    }
  }

  disconnect() {
    this.logInfo('disconnect', '🔌 Disconnecting from ToteBot…');
    this.stopPublishLoop();
    this.ros?.close();
    this.ros       = null;
    this.cmdVelJoy = null;
    this.basketCmd = null;
    this.alignCmd  = null;
    this.fusionCmd = null; // ✅ Cleaned up here
    this.logInfo('disconnect', '✅ Disconnected and topics cleared');
  }
}

export const rosService = new RosService();


