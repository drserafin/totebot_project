import { useState } from 'react';
import IMUView from './IMUView';
import { Camera, Box, Eye, Layers } from 'lucide-react';

type ViewMode = 'camera' | 'imu';
type TofMode = 'confidence' | 'depth';

// CHANGE THIS TO YOUR RASPBERRY PI'S IP ADDRESS
const ROS_VIDEO_SERVER = `http://${window.location.hostname}:8081`;

const CameraFeed = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('camera');
  const [tofMode, setTofMode] = useState<TofMode>('depth');

  return (
    <div className="relative w-full h-full">
      {/* Mode switcher - top-left overlay */}
      <div className="absolute top-4 left-4 z-20 flex bg-surface-dark/90 backdrop-blur-sm rounded-lg border border-border overflow-hidden">
        <button
          onClick={() => setViewMode('camera')}
          className={`flex items-center gap-1.5 px-3 py-1.5 font-mono text-xs font-semibold tracking-wider uppercase transition-all duration-200 ${
            viewMode === 'camera'
              ? 'bg-primary/20 text-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Camera size={14} />
          ToF Camera
        </button>
        <button
          onClick={() => setViewMode('imu')}
          className={`flex items-center gap-1.5 px-3 py-1.5 font-mono text-xs font-semibold tracking-wider uppercase transition-all duration-200 ${
            viewMode === 'imu'
              ? 'bg-primary/20 text-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Box size={14} />
          IMU 3D
        </button>
      </div>

      {viewMode === 'camera' ? (
        <div className="relative w-full h-full rounded-xl overflow-hidden bg-surface-dark border border-border">
          {/* ToF mode switcher - top-right */}
          <div className="absolute top-4 right-4 z-20 flex flex-col gap-2 items-end">
            <span className="font-mono text-[10px] text-muted-foreground tracking-widest uppercase bg-surface-dark/80 backdrop-blur-sm px-2 py-0.5 rounded border border-border">
              Arducam ToF Â· ROS 2
            </span>
            <div className="flex bg-surface-dark/90 backdrop-blur-sm rounded-lg border border-border overflow-hidden">
              <button
                onClick={() => setTofMode('confidence')}
                className={`flex items-center gap-1.5 px-3 py-1.5 font-mono text-xs font-semibold tracking-wider uppercase transition-all duration-200 ${
                  tofMode === 'confidence'
                    ? 'bg-hud-amber/20 text-hud-amber'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Eye size={14} />
                Confidence
              </button>
              <button
                onClick={() => setTofMode('depth')}
                className={`flex items-center gap-1.5 px-3 py-1.5 font-mono text-xs font-semibold tracking-wider uppercase transition-all duration-200 ${
                  tofMode === 'depth'
                    ? 'bg-hud-cyan/20 text-hud-cyan'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Layers size={14} />
                Depth
              </button>
            </div>
          </div>

          {/* STREAM VIEWS */}
          {tofMode === 'confidence' && (
            <div className="absolute inset-0">
              <img
                src={`${ROS_VIDEO_SERVER}/stream?topic=/camera/confidence/image_raw&type=mjpeg`}
                alt="ROS Confidence Stream"
                className="w-full h-full object-contain bg-black"
              />
              <div className="absolute bottom-4 left-0 right-0 flex flex-col items-center justify-center gap-1 pointer-events-none">
                <span className="font-mono text-sm text-hud-amber tracking-wider uppercase bg-surface-dark/80 px-3 py-1 rounded">Confidence Map</span>
                <span className="font-mono text-xs text-muted-foreground bg-surface-dark/80 px-2 py-0.5 rounded">High = bright Â· Low = dark</span>
              </div>
            </div>
          )}

          {tofMode === 'depth' && (
            <div className="absolute inset-0">
              <img
                src={`${ROS_VIDEO_SERVER}/stream?topic=/camera/depth/image_color&type=mjpeg`}
                alt="ROS Depth Stream"
                className="w-full h-full object-contain bg-black"
              />
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 flex flex-col items-center justify-center gap-3 pointer-events-none opacity-20">
                <Layers className="text-hud-cyan" size={48} strokeWidth={1.2} />
              </div>

              <div className="absolute bottom-4 left-4 flex items-center gap-2 bg-surface-dark/80 backdrop-blur-sm px-3 py-1.5 rounded-md border border-border">
                <span className="font-mono text-[10px] text-muted-foreground">0.2m</span>
                <div
                  className="w-32 h-2 rounded-sm"
                  style={{
                    background:
                      'linear-gradient(90deg, hsl(var(--hud-red)), hsl(var(--hud-amber)), hsl(var(--hud-green)), hsl(var(--hud-cyan)), hsl(217 80% 35%))',
                  }}
                />
                <span className="font-mono text-[10px] text-muted-foreground">4.0m</span>
              </div>
            </div>
          )}

          {/* Crosshair overlay */}
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute top-1/2 left-0 right-0 h-px bg-primary/10" />
            <div className="absolute left-1/2 top-0 bottom-0 w-px bg-primary/10" />
            <div className="absolute top-6 left-6 w-8 h-8 border-t-2 border-l-2 border-primary/20 rounded-tl" />
            <div className="absolute top-6 right-6 w-8 h-8 border-t-2 border-r-2 border-primary/20 rounded-tr" />
            <div className="absolute bottom-6 left-6 w-8 h-8 border-b-2 border-l-2 border-primary/20 rounded-bl" />
            <div className="absolute bottom-6 right-6 w-8 h-8 border-b-2 border-r-2 border-primary/20 rounded-br" />
          </div>
        </div>
      ) : (
        <IMUView />
      )}
    </div>
  );
};

export default CameraFeed;



