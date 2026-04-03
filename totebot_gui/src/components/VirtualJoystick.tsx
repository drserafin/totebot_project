import React, { useCallback, useRef, useState, useEffect } from 'react';
import { Joystick } from 'lucide-react';

interface VirtualJoystickProps {
  onMove: (x: number, y: number) => void;
  onStop?: () => void; // <-- 1. Added the optional stop command
}

// Control Logic Constants
const DEADZONE = 0.15;
const SLEW_RATE = 0.18; 
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

// 2. Added onStop to the component properties
const VirtualJoystick = ({ onMove, onStop }: VirtualJoystickProps) => {
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  
  // Refs for logic
  const containerRef = useRef<HTMLDivElement>(null);
  const smoothRef = useRef({ x: 0, y: 0 });
  const targetRef = useRef({ x: 0, y: 0 });
  const rafRef = useRef<number | null>(null);

  // 1. Slewing Loop (Smoothing for Robotics)
  const runSlewLoop = useCallback(() => {
    const smooth = smoothRef.current;
    const target = targetRef.current;
    
    const nx = slewLimit(smooth.x, target.x, SLEW_RATE);
    const ny = slewLimit(smooth.y, target.y, SLEW_RATE);
    
    smoothRef.current = { x: nx, y: ny };
    onMove(+nx.toFixed(2), +ny.toFixed(2));

    if (Math.abs(nx - target.x) > 0.001 || Math.abs(ny - target.y) > 0.001) {
      rafRef.current = requestAnimationFrame(runSlewLoop);
    } else {
      rafRef.current = null;
    }
  }, [onMove]);

  const updateTarget = useCallback((x: number, y: number) => {
    targetRef.current = { x, y };
    if (rafRef.current === null) {
      rafRef.current = requestAnimationFrame(runSlewLoop);
    }
  }, [runSlewLoop]);

  // 2. Interaction Handlers
  const handlePointerMove = useCallback((e: PointerEvent) => {
    if (!dragging || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const radius = rect.width / 2; // Assume circular boundary

    // Calculate offset from center
    let dx = e.clientX - (rect.left + centerX);
    let dy = e.clientY - (rect.top + centerY);

    // Clamp to circle
    const distance = Math.sqrt(dx * dx + dy * dy);
    const maxClamp = radius * 0.8; // Leave room for puck radius

    if (distance > maxClamp) {
      dx = (dx / distance) * maxClamp;
      dy = (dy / distance) * maxClamp;
    }

    setPos({ x: dx, y: dy });

    // Normalize (-1 to 1)
    let rawX = dx / maxClamp;
    let rawY = -dy / maxClamp; // Invert Y for robotics (Up is positive)

    // Apply Deadzone & Axis Priority
    let dzX = applyDeadzone(rawX);
    let dzY = applyDeadzone(rawY);

    if (Math.abs(dzY) >= Math.abs(dzX) * AXIS_PRIORITY_RATIO) dzX = 0;
    else if (Math.abs(dzX) >= Math.abs(dzY) * AXIS_PRIORITY_RATIO) dzY = 0;

    updateTarget(dzX, dzY);
  }, [dragging, updateTarget]);

  // 3. Fire the stop command when the user lets go
  const stopDragging = useCallback(() => {
    setDragging(false);
    setPos({ x: 0, y: 0 });
    updateTarget(0, 0);
    
    // Send instant zero velocity to ROS
    if (onStop) onStop();
    
  }, [updateTarget, onStop]);

  // Handle Global Pointer Up (prevents stickiness if mouse leaves window)
  useEffect(() => {
    if (dragging) {
      window.addEventListener('pointermove', handlePointerMove);
      window.addEventListener('pointerup', stopDragging);
    }
    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', stopDragging);
    };
  }, [dragging, handlePointerMove, stopDragging]);

  return (
    <div className="rounded-xl bg-surface-panel border border-border p-4 flex flex-col gap-4 w-full h-full min-h-[280px]">
      {/* Header matching TelemetryPanel */}
      <div className="flex items-center gap-2">
        <Joystick size={16} className="text-hud-green" />
        <h2 className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-hud-green">
          Drive Control
        </h2>
      </div>

      {/* Joystick Boundary */}
      <div className="flex-1 flex items-center justify-center">
        <div
          ref={containerRef}
          onPointerDown={(e) => {
            setDragging(true);
            (e.target as HTMLElement).setPointerCapture(e.pointerId);
          }}
          className="relative aspect-square w-full max-w-[180px] rounded-full border-2 border-border bg-surface-dark/40 select-none touch-none overflow-visible"
        >
          {/* Crosshair Grid */}
          <div className="absolute inset-0 pointer-events-none opacity-20">
            <div className="absolute top-1/2 left-0 right-0 h-px bg-hud-green" />
            <div className="absolute left-1/2 top-0 bottom-0 w-px bg-hud-green" />
          </div>
          {/* The Puck */}
          <div
            className={`absolute w-12 h-12 rounded-full border-2 transition-shadow duration-150
              ${dragging 
                ? 'bg-hud-green shadow-[0_0_20px_rgba(74,222,128,0.5)] border-white/20' 
                : 'bg-hud-green/20 border-hud-green/50 shadow-none'}
            `}
            style={{
              left: `calc(50% + ${pos.x}px)`,
              top: `calc(50% + ${pos.y}px)`,
              transform: 'translate(-50%, -50%)',
              transition: dragging ? 'none' : 'all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
              cursor: dragging ? 'grabbing' : 'grab'
            }}
          >
            {/* Inner Puck Detail */}
            <div className="absolute inset-1 rounded-full border border-white/10 flex items-center justify-center">
               <div className={`w-1 h-1 rounded-full ${dragging ? 'bg-white' : 'bg-hud-green'}`} />
            </div>
          </div>
        </div>
      </div>

      {/* HUD Style Readouts */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2 rounded bg-surface-dark/50 border border-border/50 text-center">
          <p className="font-mono text-[9px] uppercase text-muted-foreground">Vector X</p>
          <p className="font-mono text-sm font-bold text-foreground">{(targetRef.current.x).toFixed(2)}</p>
        </div>
        <div className="p-2 rounded bg-surface-dark/50 border border-border/50 text-center">
          <p className="font-mono text-[9px] uppercase text-muted-foreground">Vector Y</p>
          <p className="font-mono text-sm font-bold text-foreground">{(targetRef.current.y).toFixed(2)}</p>
        </div>
      </div>
    </div>
  );
};

export default VirtualJoystick;