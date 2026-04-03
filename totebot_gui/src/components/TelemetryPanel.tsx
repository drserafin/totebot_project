import { Battery, Cpu, Package, Joystick } from 'lucide-react';

interface TelemetryItemProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  unit?: string;
  color?: string;
}

const TelemetryItem = ({ icon, label, value, unit }: TelemetryItemProps) => (
  <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-dark/50 border border-border/50">
    <div className="text-hud-green/70">{icon}</div>
    <div className="flex-1 min-w-0">
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">{label}</p>
      <p className="font-mono text-sm font-semibold text-foreground">
        {value}
        {unit && <span className="text-muted-foreground ml-1 text-xs">{unit}</span>}
      </p>
    </div>
  </div>
);

interface TelemetryPanelProps {
  mode: 'Manual' | 'Autonomous';
}

const TelemetryPanel = ({ mode }: TelemetryPanelProps) => {
  return (
    <div className="rounded-xl bg-surface-panel border border-border p-4 flex flex-col gap-3">
      <h2 className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-hud-green">
        System Status
      </h2>
      <div className="grid grid-cols-2 gap-2">
        <TelemetryItem icon={<Battery size={16} />} label="Battery" value="85" unit="%" />
        <TelemetryItem icon={<Cpu size={16} />} label="CPU Temp" value="45" unit="°C" />
        <TelemetryItem icon={<Package size={16} />} label="Payload" value="12 / 50" unit="lbs" />
        <TelemetryItem icon={<Joystick size={16} />} label="Mode" value={mode} />
      </div>
    </div>
  );
};

export default TelemetryPanel;
