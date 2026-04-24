import { Ros, Topic } from 'roslib';

interface TwistMessage {
  linear: { x: number; y: number; z: number };
  angular: { x: number; y: number; z: number };
}

class RosService {
  public ros: Ros | null = null;

  private cmdVel: Topic | null = null;
  private basketCmd: Topic | null = null;
  private alignCmd: Topic | null = null;

  private currentLinear = 0;
  private currentAngular = 0;
  private publishTimer: ReturnType<typeof setInterval> | null = null;
  private readonly PUBLISH_RATE_MS = 50;

  // ─── Debug helpers ────────────────────────────────────────────────
  private publishTickCount = 0;
  private readonly DEBUG_LOG_EVERY_N_TICKS = 10; // ~500 ms at 50 ms rate

  private logDebug(tag: string, msg: string) {
    console.debug(`[RosService][${tag}] ${msg}`);
  }

  private logInfo(tag: string, msg: string) {
    console.info(`[RosService][${tag}] ${msg}`);
  }

  private logWarn(tag: string, msg: string) {
    console.warn(`[RosService][${tag}] ${msg}`);
  }

  private logError(tag: string, msg: string) {
    console.error(`[RosService][${tag}] ${msg}`);
  }
  // ──────────────────────────────────────────────────────────────────

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
    
    this.cmdVel = new Topic({
      ros: this.ros,
      name: '/cmd_vel',
      messageType: 'geometry_msgs/Twist',
    });
    this.logInfo('initTopics', `📌 Topic advertised: /cmd_vel (geometry_msgs/Twist)`);

    this.basketCmd = new Topic({
      ros: this.ros,
      name: '/totebot/basket_cmd',
      messageType: 'std_msgs/Int8',
    });
    this.logInfo('initTopics', `📌 Topic advertised: /totebot/basket_cmd  (std_msgs/Int8)`);

    this.alignCmd = new Topic({
      ros: this.ros,
      name: '/assist/align_active',
      messageType: 'std_msgs/Bool',
    });
    this.logInfo('initTopics', `📌 Topic advertised: /assist/align_active  (std_msgs/Bool)`);
  }

  // ─── Public API ───────────────────────────────────────────────────

  setBasketState(state: number) {
    if (!this.basketCmd) {
      this.logWarn('setBasketState', 'basketCmd topic not ready – dropping message');
      return;
    }
    this.logDebug('setBasketState', `🧺 Publishing basket state → data: ${state}`);
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

  /**
   * Called by the React joystick component on every pointer/keyboard event.
   * linearX  → goes into Twist.linear.x  (read by Python as msg.linear.x  → target_angular)
   * angularZ → goes into Twist.angular.z (read by Python as msg.angular.z → target_linear)
   *
   * NOTE: The Python driver intentionally cross-maps these axes:
   *   target_linear  = msg.angular.z
   *   target_angular = msg.linear.x
   * The logs below make that pipeline fully traceable.
   */
  setVelocity(linearX: number, angularZ: number) {
    // 🐛 DEBUG – log every React command coming in
    this.logDebug(
      'setVelocity',
      `🕹️  React cmd → linearX: ${linearX.toFixed(3)}  angularZ: ${angularZ.toFixed(3)}` +
        `  (will map to Twist: linear.x=${linearX.toFixed(3)}, angular.z=${angularZ.toFixed(3)})`,
    );

    const changed =
      this.currentLinear !== linearX || this.currentAngular !== angularZ;

    this.currentLinear = linearX;
    this.currentAngular = angularZ;

    if (changed) {
      this.logDebug(
        'setVelocity',
        `📝 Velocity updated → linear: ${this.currentLinear.toFixed(3)}  angular: ${this.currentAngular.toFixed(3)}`,
      );
    }
  }

  // ─── Internal helpers ─────────────────────────────────────────────

  private resetVelocity() {
    this.logDebug('resetVelocity', '🔄 Resetting velocity to zero');
    this.currentLinear = 0;
    this.currentAngular = 0;
  }

  private startPublishLoop() {
    this.stopPublishLoop();
    this.publishTickCount = 0;
    this.logInfo('startPublishLoop', `▶️  Publish loop started at ${this.PUBLISH_RATE_MS} ms intervals`);

    this.publishTimer = setInterval(() => {
      if (!this.cmdVel) {
        this.logWarn('publishLoop', 'cmdVel topic not ready – skipping tick');
        return;
      }

      const twist: TwistMessage = {
        linear:  { x: this.currentLinear,  y: 0, z: 0 },
        angular: { x: 0, y: 0, z: this.currentAngular },
      };

      // 🐛 DEBUG – throttled publish log (~every 500 ms)
      if (this.publishTickCount % this.DEBUG_LOG_EVERY_N_TICKS === 0) {
        this.logDebug(
          'publishLoop',
          `📡 Twist published → linear.x: ${twist.linear.x.toFixed(3)}` +
            `  angular.z: ${twist.angular.z.toFixed(3)}` +
            `  (tick #${this.publishTickCount})`,
        );
      }
      this.publishTickCount++;

      this.cmdVel.publish(twist);
    }, this.PUBLISH_RATE_MS);
  }

  private stopPublishLoop() {
    if (this.publishTimer) {
      clearInterval(this.publishTimer);
      this.publishTimer = null;
      this.logInfo('stopPublishLoop', '⏹️  Publish loop stopped');
    }
  }

  disconnect() {
    this.logInfo('disconnect', '🔌 Disconnecting from ToteBot…');
    this.stopPublishLoop();
    this.ros?.close();
    this.ros = null;
    this.cmdVel = null;
    this.basketCmd = null;
    this.alignCmd = null;
    this.logInfo('disconnect', '✅ Disconnected and topics cleared');
  }
}

export const rosService = new RosService();