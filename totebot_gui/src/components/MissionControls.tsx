import { Target, Activity, ZapOff, ShieldAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';

const MissionControls = () => {
  return (
    <div className="rounded-xl bg-surface-panel border border-border p-4 flex flex-col gap-3 shadow-lg shadow-black/20">
      
      {/* 🟢 HEADER SECTION - Slimmed down gap */}
      <div className="flex items-center justify-between">
        <h2 className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-hud-green">
            Mission Controls
        </h2>

        
        {/* Connection Status Badge - Compact version */}
        <div className="flex items-center gap-2 border border-hud-green/20 px-2 py-0.5 rounded-full bg-hud-green/5">
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-hud-green opacity-75"></span>
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-hud-green"></span>
          </span>
          <span className="font-mono text-[8px] text-hud-green uppercase tracking-wider font-bold">
            Ready
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        
        {/* 🟡 AMBER ACTION (Auto Mode) */}
        <Button
          variant="outline"
          className="h-12 border-hud-amber/30 bg-hud-amber/5 text-hud-amber hover:bg-hud-amber/15 hover:border-hud-amber hover:text-white justify-between px-3 group transition-all"
          onClick={() => console.log("HMI COMMAND: Init Stair Alignment")}
        >
          <div className="flex items-center gap-3">
            <Target size={20} className="group-active:scale-90 transition-transform text-hud-amber/80 group-hover:text-white" />
            <div className="text-left">
              <p className="font-bold text-[11px] tracking-tight uppercase">Align to Stairs</p>
              <p className="font-mono text-[8px] text-muted-foreground/60 uppercase leading-none group-hover:text-white">Autonomous</p>
            </div>
          </div>
          <div className="font-mono text-[8px] border border-hud-amber/30 px-1.5 py-0.5 rounded bg-hud-amber/10 font-bold">
            AUTO
          </div>
        </Button>

        {/* 🔵 CYAN ACTION (IMU Stabilization) */}
        <Button
          variant="outline"
          className="h-12 border-hud-cyan/30 bg-hud-cyan/5 text-hud-cyan hover:bg-hud-cyan/15 hover:border-hud-cyan hover:text-white justify-between px-3 group transition-all"
          onClick={() => console.log("HMI COMMAND: Init Basket Leveling")}
        >
          <div className="flex items-center gap-3">
            <Activity size={20} className="group-hover:animate-pulse text-hud-cyan/80 group-hover:text-white" />
            <div className="text-left">
              <p className="font-bold text-[11px] tracking-tight uppercase">Auto-Level Basket</p>
              <p className="font-mono text-[8px] text-muted-foreground/60 uppercase leading-none group-hover:text-white">IMU Active</p>
            </div>
          </div>
          <div className="font-mono text-[8px] border border-hud-cyan/30 px-1.5 py-0.5 rounded bg-hud-cyan/10 font-bold">
            STAB
          </div>
        </Button>

        {/* 🔴 UTILITY ROW */}
        <div className="grid grid-cols-2 gap-2 mt-1">
          <Button 
            variant="ghost" 
            className="text-[9px] h-9 border border-hud-white/10 text-hud-white/50 gap-2 hover:bg-white/5 hover:text-white transition-colors uppercase font-mono tracking-tighter"
            onClick={() => console.log("HMI COMMAND: Init Climb Mode")} // 👈 ADDED ONCLICK HERE
          >
            <ShieldAlert size={12} /> Climb Mode
          </Button>
          
          <Button
            variant="destructive"
            className="text-[9px] h-9 bg-red-950/20 border border-red-500/40 text-red-500 hover:bg-red-500/80 hover:text-white gap-2 uppercase font-bold transition-all group"
            onClick={() => console.log("HMI COMMAND: Reset Calibration")}
          >
            <ZapOff size={12} className="group-active:scale-95"/> Reset Calibration
          </Button>
        </div>
      </div>
    </div>
  );
};

export default MissionControls;