import { useCallback, useRef, useState, useEffect } from 'react';
import { Joystick, AlertTriangle } from 'lucide-react';

interface VirtualJoystickProps {
  onMove: (linearX: number, angularZ: number) => void;
  onStop?: () => void;
  maxLinearSpeed?: number;   // e.g., meters per second (m/s)
  maxAngularSpeed?: number;  // e.g., radians per second (rad/s)
  obstacleDetected?: boolean; // Disables driving if the edge-detection lasers trip
  publishRateMs?: number;    // Network throttle (50ms = 20Hz, ideal for ROS 2)
}

const DEADZONE = 0.15;
const SLEW_RATE = 0.15; // Increased to 0.15 for fast but smooth braking
const AXIS_PRIORITY_RATIO = 2.0;

const applyDeadzone = (v: number): number => {
  const abs = Math.abs(v);
  if (abs < DEADZONE) return 0;
  return ((abs - DEADZONE) / (1 - DEADZONE)) * Math.sign(v);
};

const slewLimit = (current: number, target: number, maxDelta: number): number => {
  const diff = target - current;
  if (Math.abs(diff) <= maxDelta) return target;
  return current + maxDelta * Math.sign(diff);
};

const VirtualJoystick = ({ 
  onMove, 
  onStop, 
  maxLinearSpeed = 1.0, 
  maxAngularSpeed = 1.0,
  obstacleDetected = false,
  publishRateMs = 50
}: VirtualJoystickProps) => {
  
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [output, setOutput] = useState({ linear: 0, angular: 0 });

  const containerRef = useRef<HTMLDivElement>(null);
  const smoothRef = useRef({ linear: 0, angular: 0 });
  const targetRef = useRef({ linear: 0, angular: 0 });
  const rafRef = useRef<number | null>(null);
  const lastPublishRef = useRef<number>(0);

  // Force stop if an obstacle is detected while driving
  useEffect(() => {
    if (obstacleDetected && dragging) {
      stopDragging();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [obstacleDetected]);

  const runSlewLoop = useCallback(() => {
    const smooth = smoothRef.current;
    const target = targetRef.current;

    const nLinear = slewLimit(smooth.linear, target.linear, SLEW_RATE);
    const nAngular = slewLimit(smooth.angular, target.angular, SLEW_RATE);

    smoothRef.current = { linear: nLinear, angular: nAngular };
    
    // Scale normalized values (-1 to 1) to physical speeds for ROS 2
    const finalLinear = +(nLinear * maxLinearSpeed).toFixed(2);
    const finalAngular = +(nAngular * maxAngularSpeed).toFixed(2);
    
    setOutput({ linear: finalLinear, angular: finalAngular });

    // Determine if the UI puck has fully reached its target
    const isFinished = Math.abs(nLinear - target.linear) < 0.001 && Math.abs(nAngular - target.angular) < 0.001;

    // Network Throttling: Send data at defined Hz, OR if we just finished decelerating to guarantee the stop command sends
    const now = performance.now();
    if (now - lastPublishRef.current >= publishRateMs || isFinished) {
      onMove(finalLinear, finalAngular);
      lastPublishRef.current = now;
    }

    if (!isFinished) {
      rafRef.current = requestAnimationFrame(runSlewLoop);
    } else {
      rafRef.current = null;
    }
  }, [onMove, maxLinearSpeed, maxAngularSpeed, publishRateMs]);

  const updateTarget = useCallback((linear: number, angular: number) => {
    targetRef.current = { linear, angular };
    if (rafRef.current === null) {
      rafRef.current = requestAnimationFrame(runSlewLoop);
    }
  }, [runSlewLoop]);

  const handlePointerMove = useCallback((e: PointerEvent) => {
    if (!dragging || !containerRef.current || obstacleDetected) return;

    const rect = containerRef.current.getBoundingClientRect();
    const radius = rect.width / 2;
    const maxClamp = radius * 0.8;

    let dx = e.clientX - (rect.left + radius);
    let dy = e.clientY - (rect.top + radius);

    const distance = Math.sqrt(dx * dx + dy * dy);
    if (distance > maxClamp) {
      dx = (dx / distance) * maxClamp;
      dy = (dy / distance) * maxClamp;
    }

    setPos({ x: dx, y: dy });

    const rawX = dx / maxClamp;  // Left/Right -> Angular Z
    const rawY = -dy / maxClamp; // Up/Down -> Linear X (inverted so up is positive)

    let dzAngular = applyDeadzone(rawX);
    let dzLinear = applyDeadzone(rawY);

    // Axis Priority (Lock to straight lines or pure rotation)
    if (Math.abs(dzLinear) >= Math.abs(dzAngular) * AXIS_PRIORITY_RATIO) dzAngular = 0;
    else if (Math.abs(dzAngular) >= Math.abs(dzLinear) * AXIS_PRIORITY_RATIO) dzLinear = 0;

    updateTarget(dzLinear, -dzAngular); // Invert angular if needed based on your robot's kinematics
  }, [dragging, obstacleDetected, updateTarget]);

  const stopDragging = useCallback(() => {
    setDragging(false);
    setPos({ x: 0, y: 0 });
    
    // Set target to 0,0 and let the runSlewLoop ramp it down perfectly
    updateTarget(0, 0); 
    
    if (onStop) onStop();
  }, [updateTarget, onStop]);

  // Window/Tab focus safety listener (Deadman's switch)
  useEffect(() => {
    const handleVisibilityChange = () => { if (document.hidden) stopDragging(); };
    const handleBlur = () => stopDragging();

    window.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('blur', handleBlur);

    if (dragging) {
      window.addEventListener('pointermove', handlePointerMove);
      window.addEventListener('pointerup', stopDragging);
    }
    return () => {
      window.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('blur', handleBlur);
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', stopDragging);
    };
  }, [dragging, handlePointerMove, stopDragging]);

  return (
    <div className={`rounded-xl border p-4 flex flex-col gap-4 w-full h-full min-h-[360px] select-none transition-colors
      ${obstacleDetected ? 'bg-red-950/40 border-red-800' : 'bg-slate-900 border-slate-700'}
    `}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {obstacleDetected ? (
            <AlertTriangle size={20} className="text-red-500 animate-pulse" />
          ) : (
            <Joystick size={20} className="text-emerald-400" />
          )}
          <h2 className={`font-mono text-sm font-bold uppercase tracking-[0.2em] 
            ${obstacleDetected ? 'text-red-500' : 'text-emerald-400'}`}>
            {obstacleDetected ? 'Drive Locked' : 'Drive Control'}
          </h2>
        </div>
        {dragging && !obstacleDetected && <span className="text-xs font-mono text-emerald-500 animate-pulse">LIVE</span>}
      </div>

      <div className="flex-1 flex items-center justify-center">
        <div
          ref={containerRef}
          onPointerDown={(e) => {
            if (obstacleDetected) return;
            setDragging(true);
            (e.target as HTMLElement).setPointerCapture(e.pointerId);
          }}
          className={`relative aspect-square w-full max-w-[240px] rounded-full border-2 touch-none
            ${obstacleDetected ? 'border-red-900/50 bg-red-950/20' : 'border-slate-700 bg-slate-950/50'}
          `}
        >
          {/* Deadzone Visualization */}
          <div 
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-white/5"
            style={{ width: `${DEADZONE * 100}%`, height: `${DEADZONE * 100}%` }}
          />

          {/* Crosshair Grid */}
          <div className="absolute inset-0 pointer-events-none opacity-10">
            <div className={`absolute top-1/2 left-0 right-0 h-px ${obstacleDetected ? 'bg-red-500' : 'bg-emerald-400'}`} />
            <div className={`absolute left-1/2 top-0 bottom-0 w-px ${obstacleDetected ? 'bg-red-500' : 'bg-emerald-400'}`} />
          </div>

          {/* The Puck */}
          <div
            className={`absolute w-16 h-16 rounded-full border-2 transition-shadow duration-150 flex items-center justify-center
              ${dragging 
                ? 'bg-emerald-500 shadow-[0_0_25px_rgba(16,185,129,0.4)] border-emerald-300' 
                : obstacleDetected 
                  ? 'bg-red-500/10 border-red-500/40' 
                  : 'bg-emerald-500/10 border-emerald-500/40 shadow-none'}
            `}
            style={{
              left: `calc(50% + ${pos.x}px)`,
              top: `calc(50% + ${pos.y}px)`,
              transform: 'translate(-50%, -50%)',
              transition: dragging ? 'none' : 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
              cursor: obstacleDetected ? 'not-allowed' : dragging ? 'grabbing' : 'grab'
            }}
          >
            <div className={`w-2 h-2 rounded-full 
              ${dragging ? 'bg-white' : obstacleDetected ? 'bg-red-500/50' : 'bg-emerald-500'}`} 
            />
          </div>
        </div>
      </div>

      {/* Real-time Output Readouts (Enlarged for Accessibility) */}
      <div className="grid grid-cols-2 gap-3">
        <div className={`p-3 rounded border text-center transition-colors
          ${obstacleDetected ? 'bg-red-950/50 border-red-900/50' : 'bg-black/40 border-slate-800'}`}>
          <p className="font-mono text-xs uppercase text-slate-400 mb-1">Linear X (m/s)</p>
          <p className={`font-mono text-xl font-bold 
            ${obstacleDetected ? 'text-red-500' : output.linear !== 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
            {output.linear.toFixed(2)}
          </p>
        </div>
        <div className={`p-3 rounded border text-center transition-colors
          ${obstacleDetected ? 'bg-red-950/50 border-red-900/50' : 'bg-black/40 border-slate-800'}`}>
          <p className="font-mono text-xs uppercase text-slate-400 mb-1">Angular Z (rad/s)</p>
          <p className={`font-mono text-xl font-bold 
            ${obstacleDetected ? 'text-red-500' : output.angular !== 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
            {output.angular.toFixed(2)}
          </p>
        </div>
      </div>
    </div>
  );
};

export default VirtualJoystick;