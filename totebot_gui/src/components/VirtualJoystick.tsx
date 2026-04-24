import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowDown,
  ArrowDownLeft,
  ArrowDownRight,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  ArrowUpLeft,
  ArrowUpRight,
  Joystick,
  Square,
} from 'lucide-react';

interface VirtualJoystickProps {
  onMove: (linearX: number, angularZ: number) => void;
  onStop?: () => void;
  maxLinearSpeed?: number;
  maxAngularSpeed?: number;
  obstacleDetected?: boolean;
  publishRateMs?: number;
}

const SPEED_STEPS = [25, 40, 55, 70, 85, 100];
const DEFAULT_SPEED = 70;
const HOLD_REPEAT_MS = 100;
const SLEW_RATE = 0.15;
const CURVE_X = 0.5;

type Dir = {
  linear: number;
  angular: number;
  key: string;
  label: string;
  Icon: typeof ArrowUp;
};

const DIRS: Dir[] = [
  { linear: 1, angular: CURVE_X, key: 'ul', label: 'Forward Left', Icon: ArrowUpLeft },
  { linear: 1, angular: 0, key: 'u', label: 'Forward', Icon: ArrowUp },
  { linear: 1, angular: -CURVE_X, key: 'ur', label: 'Forward Right', Icon: ArrowUpRight },
  { linear: 0, angular: 1, key: 'l', label: 'Rotate Left', Icon: ArrowLeft },
  { linear: 0, angular: 0, key: 'stop', label: 'Stop', Icon: Square },
  { linear: 0, angular: -1, key: 'r', label: 'Rotate Right', Icon: ArrowRight },
  { linear: -1, angular: CURVE_X, key: 'dl', label: 'Reverse Left', Icon: ArrowDownLeft },
  { linear: -1, angular: 0, key: 'd', label: 'Reverse', Icon: ArrowDown },
  { linear: -1, angular: -CURVE_X, key: 'dr', label: 'Reverse Right', Icon: ArrowDownRight },
];

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
  publishRateMs = 50,
}: VirtualJoystickProps) => {
  const [speedPercent, setSpeedPercent] = useState(DEFAULT_SPEED);
  const [activeKey, setActiveKey] = useState<string>('stop');

  const activePointerRef = useRef<number | null>(null);
  const activeDirRef = useRef<Dir | null>(null);
  const holdTimerRef = useRef<number | null>(null);
  const targetRef = useRef({ linear: 0, angular: 0 });
  const smoothRef = useRef({ linear: 0, angular: 0 });
  const rafRef = useRef<number | null>(null);
  const lastPublishRef = useRef(0);
  const speedRef = useRef(speedPercent);

  useEffect(() => {
    speedRef.current = speedPercent;
  }, [speedPercent]);

  const emitCurrentOutput = useCallback(
    (linearNorm: number, angularNorm: number, force = false) => {
      const speedScale = speedRef.current / 100;
      const finalLinear = +(linearNorm * speedScale * maxLinearSpeed).toFixed(2);
      const finalAngular = +(angularNorm * speedScale * maxAngularSpeed).toFixed(2);
      const now = performance.now();

      if (force || now - lastPublishRef.current >= publishRateMs) {
        onMove(finalLinear, finalAngular);
        lastPublishRef.current = now;
      }
    },
    [maxAngularSpeed, maxLinearSpeed, onMove, publishRateMs],
  );

  const runSlewLoop = useCallback(() => {
    const smooth = smoothRef.current;
    const target = targetRef.current;

    const nextLinear = slewLimit(smooth.linear, target.linear, SLEW_RATE);
    const nextAngular = slewLimit(smooth.angular, target.angular, SLEW_RATE);

    smoothRef.current = { linear: nextLinear, angular: nextAngular };

    const isFinished =
      Math.abs(nextLinear - target.linear) < 0.001 &&
      Math.abs(nextAngular - target.angular) < 0.001;

    emitCurrentOutput(nextLinear, nextAngular, isFinished);

    if (!isFinished) {
      rafRef.current = requestAnimationFrame(runSlewLoop);
    } else {
      rafRef.current = null;
    }
  }, [emitCurrentOutput]);

  const updateTarget = useCallback(
    (linear: number, angular: number) => {
      targetRef.current = { linear, angular };
      if (rafRef.current === null) {
        rafRef.current = requestAnimationFrame(runSlewLoop);
      }
    },
    [runSlewLoop],
  );

  const stopHoldTimer = useCallback(() => {
    if (holdTimerRef.current !== null) {
      clearInterval(holdTimerRef.current);
      holdTimerRef.current = null;
    }
  }, []);

  const startHeartbeat = useCallback(() => {
    stopHoldTimer();
    holdTimerRef.current = window.setInterval(() => {
      const cur = activeDirRef.current;
      if (cur && cur.key !== 'stop') {
        updateTarget(cur.linear, cur.angular);
      }
    }, HOLD_REPEAT_MS);
  }, [stopHoldTimer, updateTarget]);

  const setDir = useCallback(
    (dir: Dir) => {
      if (obstacleDetected) return;
      activeDirRef.current = dir;
      setActiveKey(dir.key);
      updateTarget(dir.linear, dir.angular);
    },
    [obstacleDetected, updateTarget],
  );

  const release = useCallback(() => {
    stopHoldTimer();
    activePointerRef.current = null;
    activeDirRef.current = null;
    setActiveKey('stop');
    updateTarget(0, 0);
    if (onStop) onStop();
  }, [onStop, stopHoldTimer, updateTarget]);

  const dirFromPoint = useCallback((clientX: number, clientY: number): Dir | null => {
    const el = document.elementFromPoint(clientX, clientY) as HTMLElement | null;
    const btn = el?.closest('[data-dir-key]') as HTMLElement | null;
    if (!btn) return null;
    const key = btn.dataset.dirKey;
    return DIRS.find((dir) => dir.key === key) ?? null;
  }, []);

  const press = useCallback(
    (dir: Dir, pointerId: number) => {
      if (obstacleDetected) return;
      activePointerRef.current = pointerId;
      setDir(dir);
      startHeartbeat();
    },
    [obstacleDetected, setDir, startHeartbeat],
  );

  useEffect(() => {
    if (obstacleDetected) {
      release();
    }
  }, [obstacleDetected, release]);

  useEffect(() => {
    const activeDir = activeDirRef.current;
    if (activeDir && activeDir.key !== 'stop') {
      emitCurrentOutput(smoothRef.current.linear, smoothRef.current.angular, true);
    }
  }, [emitCurrentOutput, speedPercent]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) release();
    };
    const handleBlur = () => release();

    window.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('blur', handleBlur);

    return () => {
      window.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('blur', handleBlur);
    };
  }, [release]);

  useEffect(() => {
    return () => {
      stopHoldTimer();
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [stopHoldTimer]);

  return (
    <div
      className={`rounded-xl border p-4 flex flex-col gap-4 w-full h-full min-h-[360px] select-none transition-colors ${
        obstacleDetected ? 'bg-red-950/40 border-red-800' : 'bg-slate-900 border-slate-700'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {obstacleDetected ? (
            <AlertTriangle size={20} className="text-red-500 animate-pulse" />
          ) : (
            <Joystick size={20} className="text-emerald-400" />
          )}
          <h2
            className={`font-mono text-sm font-bold uppercase tracking-[0.2em] ${
              obstacleDetected ? 'text-red-500' : 'text-emerald-400'
            }`}
          >
            {obstacleDetected ? 'Drive Locked' : 'Drive Control'}
          </h2>
        </div>
        {!obstacleDetected && activeKey !== 'stop' && (
          <span className="text-xs font-mono text-emerald-500 animate-pulse">LIVE</span>
        )}
      </div>

      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div
            className="grid grid-cols-3 grid-rows-3 gap-2 touch-none"
            onPointerDown={(e) => {
              e.preventDefault();
              const dir = dirFromPoint(e.clientX, e.clientY);
              if (!dir) return;
              (e.currentTarget as HTMLDivElement).setPointerCapture(e.pointerId);
              press(dir, e.pointerId);
            }}
            onPointerMove={(e) => {
              if (activePointerRef.current !== e.pointerId) return;
              const dir = dirFromPoint(e.clientX, e.clientY);
              if (dir) setDir(dir);
            }}
            onPointerUp={(e) => {
              if (activePointerRef.current !== e.pointerId) return;
              (e.currentTarget as HTMLDivElement).releasePointerCapture(e.pointerId);
              release();
            }}
            onPointerCancel={(e) => {
              if (activePointerRef.current !== e.pointerId) return;
              release();
            }}
            onContextMenu={(e) => e.preventDefault()}
          >
            {DIRS.map((dir) => {
              const isActive = activeKey === dir.key;
              const isStop = dir.key === 'stop';
              const baseClass =
                'w-16 h-16 flex items-center justify-center rounded-xl border-2 transition-all duration-75 touch-none';
              const stateClass = isStop
                ? isActive
                  ? 'bg-red-500 text-white border-red-300 shadow-[0_0_20px_rgba(239,68,68,0.35)]'
                  : 'bg-red-500/10 text-red-400 border-red-500/40'
                : obstacleDetected
                  ? 'bg-red-950/20 text-red-500 border-red-900/40'
                  : isActive
                    ? 'bg-emerald-500 text-slate-950 border-emerald-300 shadow-[0_0_20px_rgba(16,185,129,0.35)] scale-95'
                    : 'bg-slate-950/60 text-emerald-400 border-slate-700 hover:border-emerald-500/60';

              return (
                <button
                  key={dir.key}
                  type="button"
                  data-dir-key={dir.key}
                  aria-label={dir.label}
                  disabled={obstacleDetected && !isStop}
                  className={`${baseClass} ${stateClass}`}
                >
                  <dir.Icon size={22} strokeWidth={2.4} />
                </button>
              );
            })}
          </div>

          <div className="w-full max-w-[260px] flex flex-col gap-2">
            <div className="flex items-center justify-between font-mono text-xs uppercase tracking-wider">
              <span className="text-slate-400">Speed</span>
              <span className={obstacleDetected ? 'text-red-500' : 'text-emerald-400'}>
                {speedPercent}%
              </span>
            </div>
            <input
              type="range"
              min={SPEED_STEPS[0]}
              max={SPEED_STEPS[SPEED_STEPS.length - 1]}
              step={5}
              value={speedPercent}
              disabled={obstacleDetected}
              onChange={(e) => setSpeedPercent(Number(e.target.value))}
              className="w-full accent-emerald-500 h-1.5 cursor-pointer"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default VirtualJoystick;


