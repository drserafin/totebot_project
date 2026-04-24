import { useState, useCallback } from 'react';
import CameraFeed from '@/components/CameraFeed';
import AssistControls from '@/components/AssistControls';
import MechanismControls from '@/components/MechanismControls';
import VirtualJoystick from '@/components/VirtualJoystick';
import { Bot } from 'lucide-react';

// 🟢 IMPORT BOTH OF YOUR NEW HOOKS
import { useRosConnection } from '@/hooks/useRosConnection'; 
import { useMotors } from '@/hooks/useMotors'; 

const Index = () => {
  const [estopActive] = useState(false);

  // 1. THE NERVOUS SYSTEM: Connect to the Pi
  const { isConnected } = useRosConnection(`ws://${window.location.hostname}:9909`);
  
  // 2. THE MUSCLES: Get the drive commands
  const { move, stop } = useMotors();

  // --- LIVE HARDWARE CONTROL ---
  const handleJoystickMove = useCallback((x: number, y: number) => {
    if (estopActive) return; 
    move(x, y);              
  }, [estopActive, move]);

  return (
    <div className={`h-screen w-screen overflow-hidden bg-background p-3 flex flex-col gap-3 transition-all duration-300 ${estopActive ? 'border-4 border-red-600' : ''}`}>
      
      {/* Header bar */}
      <header className="flex items-center justify-between px-4 py-2 rounded-xl bg-surface-panel border border-border shrink-0">
        <div className="flex items-center gap-3">
          <Bot size={20} className={isConnected ? "text-hud-green" : "text-red-500"} />
          <h1 className="font-display font-bold text-sm uppercase tracking-[0.15em] text-foreground">
            ToteBot Command
          </h1>
        </div>
        <div className="flex items-center gap-4 font-mono text-xs text-muted-foreground">
          <span>UNIT-07</span>
          <span className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-hud-green animate-blink' : 'bg-red-500'}`} />
            {isConnected ? 'Connected' : 'Offline'}
          </span>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex flex-col landscape:flex-row sm:flex-row gap-3 min-h-0 overflow-y-auto landscape:overflow-hidden sm:overflow-hidden pb-4 landscape:pb-0 sm:pb-0">
        
        {/* Left: Observation Zone */}
        <div className="w-full landscape:w-[65%] sm:w-[65%] h-[35vh] landscape:h-auto sm:h-auto min-w-0 flex flex-col">
          <div className="flex-1 min-h-0">
             <CameraFeed />
          </div>
        </div>

        {/* Right: Action Strip */}
        <div className="w-full landscape:w-[35%] sm:w-[35%] flex flex-col gap-3 min-w-0 landscape:overflow-y-auto sm:overflow-y-auto pr-1">
  
          {/* Note: Pass isConnected down to MissionControls later when you add the IMU! */}
          <AssistControls /> 
          
          <MechanismControls />

          {/* Joystick Container */}
          <div className="flex-1 min-h-[350px] landscape:min-h-[250px] sm:min-h-0 flex flex-col shrink-0">
            <VirtualJoystick onMove={handleJoystickMove} onStop={stop} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Index;