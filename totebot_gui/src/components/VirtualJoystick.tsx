import { useCallback, useRef, useState, useEffect } from 'react';
import { Joystick } from 'lucide-react';

interface VirtualJoystickProps {
  onMove: (x: number, y: number) => void;
  onStop?: () => void;
}

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

const VirtualJoystick = ({ onMove, onStop }: VirtualJoystickProps) => {
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [output, setOutput] = useState({ x: 0, y: 0 });

  const containerRef = useRef<HTMLDivElement>(null);
  const smoothRef = useRef({ x: 0, y: 0 });
  const targetRef = useRef({ x: 0, y: 0 });
  const rafRef = useRef<number | null>(null);

  const runSlewLoop = useCallback(() => {
    const smooth = smoothRef.current;
    const target = targetRef.current;

    const nx = slewLimit(smooth.x, target.x, SLEW_RATE);
    const ny = slewLimit(smooth.y, target.y, SLEW_RATE);

    smoothRef.current = { x: nx, y: ny };
    setOutput({ x: nx, y: ny }); // Update UI readouts
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

  const handlePointerMove = useCallback((e: PointerEvent) => {
    if (!dragging || !containerRef.current) return;

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

    const rawX = dx / maxClamp;
    const rawY = -dy / maxClamp;

    let dzX = applyDeadzone(rawX);
    let dzY = applyDeadzone(rawY);

    if (Math.abs(dzY) >= Math.abs(dzX) * AXIS_PRIORITY_RATIO) dzX = 0;
    else if (Math.abs(dzX) >= Math.abs(dzY) * AXIS_PRIORITY_RATIO) dzY = 0;

    updateTarget(dzX, dzY);
  }, [dragging, updateTarget]);

  const stopDragging = useCallback(() => {
    setDragging(false);
    setPos({ x: 0, y: 0 });
    updateTarget(0, 0);

    if (onStop) onStop();
  }, [updateTarget, onStop]);

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
    <div className="rounded-xl bg-slate-900 border border-slate-700 p-4 flex flex-col gap-4 w-full h-full min-h-[320px] select-none">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Joystick size={16} className="text-emerald-400" />
          <h2 className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-emerald-400">
            Drive Control
          </h2>
        </div>
        {dragging && <span className="text-[10px] font-mono text-emerald-500 animate-pulse">LIVE</span>}
      </div>

      <div className="flex-1 flex items-center justify-center">
        <div
          ref={containerRef}
          onPointerDown={(e) => {
            setDragging(true);
            (e.target as HTMLElement).setPointerCapture(e.pointerId);
          }}
          className="relative aspect-square w-full max-w-[180px] rounded-full border-2 border-slate-700 bg-slate-950/50 touch-none"
        >
          {/* Deadzone Visualization */}
          <div 
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-white/5"
            style={{ width: `${DEADZONE * 100}%`, height: `${DEADZONE * 100}%` }}
          />

          {/* Crosshair Grid */}
          <div className="absolute inset-0 pointer-events-none opacity-10">
            <div className="absolute top-1/2 left-0 right-0 h-px bg-emerald-400" />
            <div className="absolute left-1/2 top-0 bottom-0 w-px bg-emerald-400" />
          </div>

          {/* The Puck */}
          <div
            className={`absolute w-12 h-12 rounded-full border-2 transition-shadow duration-150 flex items-center justify-center
              ${dragging 
                ? 'bg-emerald-500 shadow-[0_0_25px_rgba(16,185,129,0.4)] border-emerald-300' 
                : 'bg-emerald-500/10 border-emerald-500/40 shadow-none'}
            `}
            style={{
              left: `calc(50% + ${pos.x}px)`,
              top: `calc(50% + ${pos.y}px)`,
              transform: 'translate(-50%, -50%)',
              transition: dragging ? 'none' : 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
              cursor: dragging ? 'grabbing' : 'grab'
            }}
          >
            <div className={`w-1.5 h-1.5 rounded-full ${dragging ? 'bg-white' : 'bg-emerald-500'}`} />
          </div>
        </div>
      </div>

      {/* Real-time Output Readouts */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2 rounded bg-black/40 border border-slate-800 text-center">
          <p className="font-mono text-[9px] uppercase text-slate-500">Linear X</p>
          <p className={`font-mono text-sm font-bold ${output.x !== 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
            {output.x.toFixed(2)}
          </p>
        </div>
        <div className="p-2 rounded bg-black/40 border border-slate-800 text-center">
          <p className="font-mono text-[9px] uppercase text-slate-500">Angular Z</p>
          <p className={`font-mono text-sm font-bold ${output.y !== 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
            {output.y.toFixed(2)}
          </p>
        </div>
      </div>
    </div>
  );
};

export default VirtualJoystick;