import { OctagonX, ToggleLeft, ToggleRight } from 'lucide-react';

interface SafetyControlsProps {
  mode: 'Manual' | 'Autonomous';
  onModeToggle: () => void;
  onEStop: () => void;
}

const SafetyControls = ({ mode, onModeToggle, onEStop }: SafetyControlsProps) => {
  return (
    <div className="rounded-xl bg-surface-panel border border-border p-4 flex flex-col gap-4">
      <h2 className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-hud-green">
        Safety & Controls
      </h2>

      {/* E-Stop */}
      <button
        onClick={onEStop}
        className="group relative w-full py-5 rounded-xl bg-hud-red text-foreground font-display font-black text-lg uppercase tracking-wider 
          transition-all duration-150 hover:brightness-110 active:scale-[0.97] animate-pulse-ring
          border-2 border-hud-red/50 shadow-[0_0_20px_hsl(var(--hud-red)/0.3)]"
      >
        <div className="flex items-center justify-center gap-3">
          <OctagonX size={24} />
          <span>Emergency Stop</span>
        </div>
      </button>

      {/* Mode Toggle */}
      <div className="flex items-center justify-between p-3 rounded-lg bg-surface-dark/50 border border-border/50">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Drive Mode</p>
          <p className="font-mono text-sm font-semibold text-foreground">{mode}</p>
        </div>
        <button
          onClick={onModeToggle}
          className="text-hud-green hover:text-hud-green/80 transition-colors"
        >
          {mode === 'Manual' ? <ToggleLeft size={36} /> : <ToggleRight size={36} />}
        </button>
      </div>
    </div>
  );
};

export default SafetyControls;
