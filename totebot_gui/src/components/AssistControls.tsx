import { useCallback, useEffect, useRef, useState } from 'react';
import { Combine, Power, Crosshair } from 'lucide-react';
// Make sure this relative path matches where you saved the hook!
import { useAutoAlign } from '../hooks/useAutoAlign';

interface AssistControlsProps {
  cameraOn?: boolean;
  onToggleCamera?: (next: boolean) => void;
  fusionOn?: boolean;
  onToggleFusion?: (next: boolean) => void;
  onAlignActive?: (active: boolean) => void;
}

const ALIGN_TICK_MS = 100;

const AssistControls = ({
  cameraOn = false,
  onToggleCamera,
  fusionOn = false,
  onToggleFusion,
  onAlignActive,
}: AssistControlsProps) => {
  // Local UI state
  const [isCameraOn, setIsCameraOn] = useState(cameraOn);
  const [isFusionOn, setIsFusionOn] = useState(fusionOn);
  const [aligning, setAligning] = useState(false);
  const tickRef = useRef<number | null>(null);

  // Initialize the ROS Auto Align hook
  const { triggerStartAlign, triggerStopAlign } = useAutoAlign();

  // Sync with parent if the parent forces a change
  useEffect(() => setIsCameraOn(cameraOn), [cameraOn]);
  useEffect(() => setIsFusionOn(fusionOn), [fusionOn]);

  const handleToggleCamera = () => {
    const next = !isCameraOn;
    setIsCameraOn(next);
    if (onToggleCamera) onToggleCamera(next);
  };

  const handleToggleFusion = () => {
    const next = !isFusionOn;
    setIsFusionOn(next);
    if (onToggleFusion) onToggleFusion(next);
  };

  const stopTick = useCallback(() => {
    if (tickRef.current !== null) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, []);

  const startAlign = useCallback(() => {
    if (aligning) return;
    setAligning(true);
    
    // Fire the ROS command to start aligning the ToF sensor
    triggerStartAlign();

    if (onAlignActive) onAlignActive(true);
    stopTick();
    tickRef.current = window.setInterval(() => {
      console.log('[Assist] align tick');
    }, ALIGN_TICK_MS);
  }, [aligning, onAlignActive, stopTick, triggerStartAlign]);

  const stopAlign = useCallback(() => {
    if (!aligning) return;
    setAligning(false);
    
    // Fire the ROS command to stop aligning and return control to joystick
    triggerStopAlign();

    if (onAlignActive) onAlignActive(false);
    stopTick();
  }, [aligning, onAlignActive, stopTick, triggerStopAlign]);

  useEffect(() => () => stopTick(), [stopTick]);

  const baseBtn =
    'flex flex-col items-center justify-center gap-1.5 py-4 px-2 rounded-xl border-2 transition-all duration-150 select-none touch-none active:scale-[0.97]';

  return (
    <div className="rounded-xl bg-surface-panel border border-border p-4 flex flex-col gap-3">
      <h2 className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-hud-green">
        Assist
      </h2>

      <div className="grid grid-cols-3 gap-2.5">
        {/* Camera Power */}
        <button
          onClick={handleToggleCamera}
          aria-pressed={isCameraOn}
          className={`${baseBtn} ${
            isCameraOn
              ? 'bg-hud-cyan/15 border-hud-cyan text-hud-cyan shadow-[0_0_10px_hsl(var(--hud-cyan)/0.25)]'
              : 'bg-surface-dark/60 border-border text-muted-foreground hover:text-foreground hover:border-border'
          }`}
        >
          <Power size={22} strokeWidth={2.2} />
          <span className="font-mono text-[10px] font-bold uppercase tracking-wider">
            Camera {isCameraOn ? 'On' : 'Off'}
          </span>
        </button>

        {/* Sensor Fusion */}
        <button
          onClick={handleToggleFusion}
          aria-pressed={isFusionOn}
          className={`${baseBtn} ${
            isFusionOn
              ? 'bg-hud-green/15 border-hud-green text-hud-green shadow-[0_0_10px_hsl(var(--hud-green)/0.25)]'
              : 'bg-surface-dark/60 border-border text-muted-foreground hover:text-foreground'
          }`}
        >
          <Combine size={22} strokeWidth={2.2} />
          <span className="font-mono text-[10px] font-bold uppercase tracking-wider">
            Fusion {isFusionOn ? 'On' : 'Off'}
          </span>
        </button>

        {/* Laser Align — hold to engage */}
        <button
          onPointerDown={(e) => {
            e.preventDefault();
            (e.currentTarget as HTMLButtonElement).setPointerCapture(e.pointerId);
            startAlign();
          }}
          onPointerUp={(e) => {
            (e.currentTarget as HTMLButtonElement).releasePointerCapture(e.pointerId);
            stopAlign();
          }}
          onPointerCancel={stopAlign}
          onPointerLeave={() => aligning && stopAlign()}
          onContextMenu={(e) => e.preventDefault()}
          aria-pressed={aligning}
          className={`${baseBtn} ${
            aligning
              ? 'bg-hud-amber/20 border-hud-amber text-hud-amber shadow-[0_0_14px_hsl(var(--hud-amber)/0.45)] scale-[0.97]'
              : 'bg-surface-dark/60 border-hud-amber/40 text-hud-amber hover:bg-hud-amber/10'
          }`}
        >
          <Crosshair size={22} strokeWidth={2.2} className={aligning ? 'animate-spin' : ''} />
          <span className="font-mono text-[10px] font-bold uppercase tracking-wider">
            {aligning ? 'Aligning…' : 'Hold Align'}
          </span>
        </button>
      </div>

      <p className="font-mono text-[10px] text-muted-foreground leading-snug px-0.5">
        Align uses left + right lasers — release instantly to stop rotation.
      </p>
    </div>
  );
};

export default AssistControls;