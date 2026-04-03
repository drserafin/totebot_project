import { useState, useCallback } from 'react';
import CameraFeed from '@/components/CameraFeed';
import TelemetryPanel from '@/components/TelemetryPanel';
import SafetyControls from '@/components/SafetyControls';
import VirtualJoystick from '@/components/VirtualJoystick';
import { Bot } from 'lucide-react';
import { useRos } from '@/hooks/useRos'; 

const Index = () => {
  const [mode, setMode] = useState<'Manual' | 'Autonomous'>('Manual');
  const [estopActive, setEstopActive] = useState(false);

const { isConnected, move, stop } = useRos(`ws://${window.location.hostname}:9909`);

  const toggleMode = useCallback(() => {
    setMode(m => m === 'Manual' ? 'Autonomous' : 'Manual');
  }, []);

  // --- LIVE HARDWARE CONTROL ---
  const handleJoystickMove = useCallback((x: number, y: number) => {
    if (estopActive) return; // Block movement if E-Stop is active
    move(x, y);              // Send speed directly to the Raspberry Pi memory
  }, [estopActive, move]);

  const handleEStop = useCallback(() => {
    console.log('?? EMERGENCY STOP TRIGGERED');
    setEstopActive(true);
    stop(); // Send 0 speed immediately to lock motors
    
    // Auto-reset UI after 1.5s, but hardware stays safe
    setTimeout(() => setEstopActive(false), 1500);
  }, [stop]);

  return (
    <div className={`h-screen w-screen overflow-hidden bg-background p-3 flex flex-col gap-3 transition-all duration-300 ${estopActive ? 'border-4 border-red-600' : ''}`}>
      
      {/* Header bar (Dynamic Status Lights) */}
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

      {/* Main content - Fully Responsive (Mobile + Landscape + PC) */}
      <div className="flex-1 flex flex-col landscape:flex-row sm:flex-row gap-3 min-h-0 overflow-y-auto landscape:overflow-hidden sm:overflow-hidden pb-4 landscape:pb-0 sm:pb-0">
        
        {/* Left: Observation Zone (65% width on desktop/landscape) */}
        <div className="w-full landscape:w-[65%] sm:w-[65%] h-[35vh] landscape:h-auto sm:h-auto min-w-0 flex flex-col">
          <div className="flex-1 min-h-0">
             <CameraFeed />
          </div>
        </div>

        {/* Right: Action Strip (35% width on desktop/landscape) */}
        <div className="w-full landscape:w-[35%] sm:w-[35%] flex flex-col gap-3 min-w-0 landscape:overflow-y-auto sm:overflow-y-auto pr-1">
          <TelemetryPanel mode={mode} />
          <SafetyControls 
            mode={mode} 
            onModeToggle={toggleMode} 
            onEStop={handleEStop} 
          />
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