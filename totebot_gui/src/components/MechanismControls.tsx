import { useState } from 'react';
import { Slider } from '@/components/ui/slider';
import { ChevronsUp, ChevronsDown, ArrowUpDown } from 'lucide-react';

const MechanismControls = () => {
  const [goTubePosition, setGoTubePosition] = useState(0);
  const [actuatorPosition, setActuatorPosition] = useState(50);

  const handleGoTubeChange = (value: number[]) => {
    setGoTubePosition(value[0]);
    // console.log(`GoTubes → Position: ${value[0]}%`);
  };

  const handleActuatorChange = (value: number[]) => {
    setActuatorPosition(value[0]);
    // console.log(`Leveling Actuator → Position: ${value[0]}%`);
  };

  const goTubeDeployed = goTubePosition > 50;
  const goTubeLabel = goTubePosition === 0 ? 'RETRACTED' : goTubePosition === 100 ? 'DEPLOYED' : `${goTubePosition}%`;

  return (
    <div className="rounded-xl bg-surface-panel border border-border p-5 flex flex-col gap-5">
      <h2 className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-hud-green">
        Mechanism Controls
      </h2>

      {/* GoTubes — LIFT */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {goTubeDeployed ? (
              <ChevronsUp size={18} className="text-hud-amber" />
            ) : (
              <ChevronsDown size={18} className="text-muted-foreground" />
            )}
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground font-semibold">
              Lift — GoTubes
            </span>
          </div>
          <span className={`font-mono text-sm font-bold ${goTubeDeployed ? 'text-hud-amber' : 'text-hud-green'}`}>
            {goTubeLabel}
          </span>
        </div>
        <Slider
          value={[goTubePosition]}
          onValueChange={handleGoTubeChange}
          max={100}
          step={1}
          className="w-full [&_[role=slider]]:h-6 [&_[role=slider]]:w-6"
        />
        <div className="flex justify-between">
          <span className="font-mono text-[10px] text-muted-foreground flex items-center gap-1">
            <ChevronsDown size={10} /> RETRACT
          </span>
          <span className="font-mono text-[10px] text-muted-foreground flex items-center gap-1">
            DEPLOY <ChevronsUp size={10} />
          </span>
        </div>
      </div>

      {/* Divider */}
      <div className="h-px bg-border/50" />

      {/* Leveling Actuator — BASKET */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ArrowUpDown size={18} className="text-hud-cyan" />
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground font-semibold">
              Basket — Actuator
            </span>
          </div>
          <span className="font-mono text-sm font-bold text-hud-cyan">
            {actuatorPosition}%
          </span>
        </div>
        <Slider
          value={[actuatorPosition]}
          onValueChange={handleActuatorChange}
          max={100}
          step={1}
          className="w-full [&_[role=slider]]:h-6 [&_[role=slider]]:w-6"
        />
        <div className="flex justify-between">
          <span className="font-mono text-[10px] text-muted-foreground">DOWN</span>
          <span className="font-mono text-[10px] text-muted-foreground">UP</span>
        </div>
      </div>
    </div>
  );
};

export default MechanismControls;
