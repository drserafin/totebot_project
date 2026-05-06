import { useCallback, useEffect, useRef, useState } from 'react';
import { Combine, Power, Crosshair } from 'lucide-react';
import { useAutoAlign } from '../hooks/useAutoAlign';
import { rosService } from '../services/rosService'; // ✅ Import the service

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
  const [isCameraOn, setIsCameraOn] = useState(cameraOn);
  const [isFusionOn, setIsFusionOn] = useState(fusionOn);
  const [aligning, setAligning] = useState(false);
  const tickRef = useRef<number | null>(null);

  const { triggerStartAlign, triggerStopAlign } = useAutoAlign();

  useEffect(() => setIsCameraOn(cameraOn), [cameraOn]);
  useEffect(() => setIsFusionOn(fusionOn), [fusionOn]);

  const handleToggleCamera = () => {
    const next = !isCameraOn;
    setIsCameraOn(next);
    if (onToggleCamera) onToggleCamera(next);
    // Add rosService.setCameraPower(next) here if you have that topic!
  };

  const handleToggleFusion = () => {
    const next = !isFusionOn;
    setIsFusionOn(next);
    
    // ✅ THIS IS THE MISSING LINK:
    console.log(`[Assist] Toggling Fusion: ${next}`);
    rosService.setFusionActive(next); 
    
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
        <button
          onClick={handleToggleCamera}
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

        <button
          onClick={handleToggleFusion}
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
          onContextMenu={(e) => e.preventDefault()}
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
    </div>
  );
};

export default AssistControls;


