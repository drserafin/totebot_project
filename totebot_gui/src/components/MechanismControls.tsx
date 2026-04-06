import { useState } from 'react';
import { ChevronsUp, ChevronsDown, ArrowUpDown, StopCircle } from 'lucide-react';
import { rosService } from '../services/rosService';

const MechanismControls = () => {
  const [basketState, setBasketState] = useState<'IDLE' | 'RAISING' | 'LOWERING'>('IDLE');
  const [goTubeState, setGoTubeState] = useState<'IDLE' | 'DEPLOYING' | 'RETRACTING'>('IDLE');

  // ==========================================
  // BASKET ACTUATOR CONTROLS
  // ==========================================
  const startBasketRaise = () => {
    setBasketState('RAISING');
    rosService.setBasketState(1); 
  };

  const startBasketLower = () => {
    setBasketState('LOWERING');
    rosService.setBasketState(-1); 
  };

  const stopBasket = () => {
    setBasketState('IDLE');
    rosService.setBasketState(0); 
  };

  // ==========================================
  // GOTUBES CONTROLS 
  // ==========================================
  const startGoTubeDeploy = () => {
    setGoTubeState('DEPLOYING');
    // rosService.setLiftState(1); // Uncomment when ready
  };

  const startGoTubeRetract = () => {
    setGoTubeState('RETRACTING');
    // rosService.setLiftState(-1); // Uncomment when ready
  };

  const stopGoTubes = () => {
    setGoTubeState('IDLE');
    // rosService.setLiftState(0); // Uncomment when ready
  };

  return (
    <div className="rounded-xl bg-surface-panel border border-border p-5 flex flex-col gap-6">
      <h2 className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-hud-green">
        Mechanism Controls
      </h2>

      {/* Leveling Actuator — BASKET */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ArrowUpDown 
              size={18} 
              className={`transition-colors ${basketState === 'RAISING' ? 'text-hud-amber' : basketState === 'LOWERING' ? 'text-hud-cyan' : 'text-muted-foreground'}`} 
            />
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground font-semibold">
              Basket Lift
            </span>
          </div>
          <span className={`font-mono text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded border transition-colors ${basketState !== 'IDLE' ? 'border-hud-amber text-hud-amber bg-hud-amber/10' : 'border-border text-muted-foreground bg-surface-dark'}`}>
            {basketState}
          </span>
        </div>

        {/* BASKET BUTTONS (Amber / Cyan) - SHRUNK */}
        <div className="grid grid-cols-2 gap-2 mt-1">
          <button
            onPointerDown={startBasketLower}
            onPointerUp={stopBasket}
            onPointerLeave={stopBasket} 
            className="flex flex-col items-center justify-center gap-1.5 bg-surface-dark border border-border rounded-lg py-2.5 active:bg-hud-cyan/20 active:border-hud-cyan transition-all select-none touch-none"
          >
            <ChevronsDown size={20} className={basketState === 'LOWERING' ? 'text-hud-cyan' : 'text-muted-foreground'} />
            <span className="font-mono text-[11px] font-bold text-muted-foreground">HOLD TO LOWER</span>
          </button>

          <button
            onPointerDown={startBasketRaise}
            onPointerUp={stopBasket}
            onPointerLeave={stopBasket} 
            className="flex flex-col items-center justify-center gap-1.5 bg-surface-dark border border-border rounded-lg py-2.5 active:bg-hud-amber/20 active:border-hud-amber transition-all select-none touch-none"
          >
            <ChevronsUp size={20} className={basketState === 'RAISING' ? 'text-hud-amber' : 'text-muted-foreground'} />
            <span className="font-mono text-[11px] font-bold text-muted-foreground">HOLD TO RAISE</span>
          </button>
        </div>
      </div>

      {/* Divider */}
      <div className="h-px bg-border/50" />

      {/* GoTubes — LIFT */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <StopCircle 
              size={18} 
              className={`transition-colors ${goTubeState === 'DEPLOYING' ? 'text-emerald-400' : goTubeState === 'RETRACTING' ? 'text-purple-400' : 'text-muted-foreground'}`} 
            />
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground font-semibold">
              GoTubes
            </span>
          </div>
          <span className={`font-mono text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded border transition-colors ${goTubeState === 'DEPLOYING' ? 'border-emerald-400 text-emerald-400 bg-emerald-400/10' : goTubeState === 'RETRACTING' ? 'border-purple-400 text-purple-400 bg-purple-400/10' : 'border-border text-muted-foreground bg-surface-dark'}`}>
            {goTubeState}
          </span>
        </div>

        {/* GOTUBES BUTTONS (Emerald / Purple) - SHRUNK */}
        <div className="grid grid-cols-2 gap-2 mt-1">
          <button
            onPointerDown={startGoTubeRetract}
            onPointerUp={stopGoTubes}
            onPointerLeave={stopGoTubes}
            className="flex flex-col items-center justify-center gap-1.5 bg-surface-dark border border-border rounded-lg py-2.5 active:bg-purple-400/20 active:border-purple-400 transition-all select-none touch-none"
          >
            <ChevronsDown size={20} className={goTubeState === 'RETRACTING' ? 'text-purple-400' : 'text-muted-foreground'} />
            <span className="font-mono text-[11px] font-bold text-muted-foreground">HOLD RETRACT</span>
          </button>

          <button
            onPointerDown={startGoTubeDeploy}
            onPointerUp={stopGoTubes}
            onPointerLeave={stopGoTubes}
            className="flex flex-col items-center justify-center gap-1.5 bg-surface-dark border border-border rounded-lg py-2.5 active:bg-emerald-400/20 active:border-emerald-400 transition-all select-none touch-none"
          >
            <ChevronsUp size={20} className={goTubeState === 'DEPLOYING' ? 'text-emerald-400' : 'text-muted-foreground'} />
            <span className="font-mono text-[11px] font-bold text-muted-foreground">HOLD DEPLOY</span>
          </button>
        </div>
      </div>

    </div>
  );
};

export default MechanismControls;