import { useState } from 'react';
import { ChevronsUp, ChevronsDown, ArrowUpDown, StopCircle, AlertTriangle } from 'lucide-react';
import { rosService } from '../services/rosService';
import { useLifterControl } from '../hooks/useLifterControl';

const MechanismControls = () => {
  const [basketState, setBasketState] = useState<'IDLE' | 'RAISING' | 'LOWERING'>('IDLE');

  const {
    lifterState,
    currentTicks,
    currentRotations,
    isConnected,
    startExtend,
    startRetract,
    stop,
  } = useLifterControl();

  const startBasketRaise = () => { setBasketState('RAISING');  rosService.setBasketState(1);  };
  const startBasketLower = () => { setBasketState('LOWERING'); rosService.setBasketState(-1); };
  const stopBasket       = () => { setBasketState('IDLE');     rosService.setBasketState(0);  };

  const goTubeBadgeClass =
    lifterState === 'EXTENDING'  ? 'border-emerald-400 text-emerald-400 bg-emerald-400/10' :
    lifterState === 'RETRACTING' ? 'border-purple-400  text-purple-400  bg-purple-400/10'  :
    lifterState === 'ERROR'      ? 'border-red-500     text-red-500     bg-red-500/10'      :
    'border-border text-muted-foreground bg-surface-dark';

  return (
    <div className="rounded-xl bg-surface-panel border border-border p-5 flex flex-col gap-6">
      <h2 className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-hud-green">
        Mechanism Controls
      </h2>

      {/* ── Basket Lift ───────────────────────────────────────────── */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ArrowUpDown size={18} className={`transition-colors ${
              basketState === 'RAISING'  ? 'text-hud-amber' :
              basketState === 'LOWERING' ? 'text-hud-cyan'  : 'text-muted-foreground'
            }`} />
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground font-semibold">
              Basket Lift
            </span>
          </div>
          <span className={`font-mono text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded border transition-colors ${
            basketState !== 'IDLE'
              ? 'border-hud-amber text-hud-amber bg-hud-amber/10'
              : 'border-border text-muted-foreground bg-surface-dark'
          }`}>
            {basketState}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2 mt-1">
          <button
            onPointerDown={startBasketLower} onPointerUp={stopBasket} onPointerLeave={stopBasket}
            className="flex flex-col items-center justify-center gap-1.5 bg-surface-dark border border-border rounded-lg py-2.5 active:bg-hud-cyan/20 active:border-hud-cyan transition-all select-none touch-none"
          >
            <ChevronsDown size={20} className={basketState === 'LOWERING' ? 'text-hud-cyan' : 'text-muted-foreground'} />
            <span className="font-mono text-[11px] font-bold text-muted-foreground">MOVE BASKET UP</span>
          </button>
          <button
            onPointerDown={startBasketRaise} onPointerUp={stopBasket} onPointerLeave={stopBasket}
            className="flex flex-col items-center justify-center gap-1.5 bg-surface-dark border border-border rounded-lg py-2.5 active:bg-hud-amber/20 active:border-hud-amber transition-all select-none touch-none"
          >
            <ChevronsUp size={20} className={basketState === 'RAISING' ? 'text-hud-amber' : 'text-muted-foreground'} />
            <span className="font-mono text-[11px] font-bold text-muted-foreground">MOVE BASKET DOWN</span>
          </button>
        </div>
      </div>

      <div className="h-px bg-border/50" />

      {/* ── GoTubes ───────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <StopCircle size={18} className={`transition-colors ${
              lifterState === 'EXTENDING'  ? 'text-emerald-400' :
              lifterState === 'RETRACTING' ? 'text-purple-400'  :
              lifterState === 'ERROR'      ? 'text-red-500'      : 'text-muted-foreground'
            }`} />
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground font-semibold">
              GoTubes
            </span>
            <span className={`w-1.5 h-1.5 rounded-full ${
              isConnected ? 'bg-emerald-400' : 'bg-red-500 animate-pulse'
            }`} />
          </div>
          <span className={`font-mono text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded border transition-colors ${goTubeBadgeClass}`}>
            {lifterState}
          </span>
        </div>

        {/* Live position readout */}
        <div className="flex items-center justify-between px-1 py-1 rounded-lg bg-surface-dark border border-border/50">
          <span className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest pl-2">
            Position
          </span>
          <div className="flex items-center gap-3 pr-2">
            <span className="font-mono text-[11px] text-hud-green tabular-nums">
              {currentTicks.toLocaleString()} ticks
            </span>
            <span className="font-mono text-[10px] text-muted-foreground tabular-nums">
              {currentRotations.toFixed(2)} rot
            </span>
          </div>
        </div>

        {/* Hold to retract / extend */}
        <div className="grid grid-cols-2 gap-2 mt-1">
          <button
            onPointerDown={startRetract} onPointerUp={stop} onPointerLeave={stop}
            disabled={!isConnected}
            className="flex flex-col items-center justify-center gap-1.5 bg-surface-dark border border-border rounded-lg py-2.5 active:bg-purple-400/20 active:border-purple-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all select-none touch-none"
          >
            <ChevronsDown size={20} className={lifterState === 'RETRACTING' ? 'text-purple-400' : 'text-muted-foreground'} />
            <span className="font-mono text-[11px] font-bold text-muted-foreground">HOLD RETRACT</span>
          </button>
          <button
            onPointerDown={startExtend} onPointerUp={stop} onPointerLeave={stop}
            disabled={!isConnected}
            className="flex flex-col items-center justify-center gap-1.5 bg-surface-dark border border-border rounded-lg py-2.5 active:bg-emerald-400/20 active:border-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all select-none touch-none"
          >
            <ChevronsUp size={20} className={lifterState === 'EXTENDING' ? 'text-emerald-400' : 'text-muted-foreground'} />
            <span className="font-mono text-[11px] font-bold text-muted-foreground">HOLD EXTEND</span>
          </button>
        </div>

        {/* E-Stop */}
        <button
          onClick={stop}
          disabled={!isConnected}
          className="flex items-center justify-center gap-2 bg-surface-dark border border-red-500/40 rounded-lg py-2 active:bg-red-500/20 active:border-red-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all select-none touch-none"
        >
          <AlertTriangle size={16} className="text-red-500" />
          <span className="font-mono text-[11px] font-bold text-red-500 uppercase tracking-widest">E-Stop</span>
        </button>
      </div>
    </div>
  );
};

export default MechanismControls;