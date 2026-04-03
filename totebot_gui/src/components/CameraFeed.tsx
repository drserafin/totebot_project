const CameraFeed = () => {
  return (
    <div className="relative w-full h-full rounded-xl overflow-hidden bg-surface-dark border border-border">
      {/* Live indicator */}
      <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-surface-dark/80 backdrop-blur-sm px-3 py-1.5 rounded-md border border-border">
        <span className="w-2.5 h-2.5 rounded-full bg-hud-green animate-blink" />
        <span className="font-mono text-xs font-semibold text-hud-green tracking-widest uppercase">Live</span>
      </div>

      {/* Timestamp */}
      <div className="absolute top-4 right-4 z-10 font-mono text-xs text-muted-foreground bg-surface-dark/80 backdrop-blur-sm px-3 py-1.5 rounded-md border border-border">
        CAM_01 · 1920×1080 · 30fps
      </div>

      {/* Camera image placeholder */}
      <img
        src=""
        alt="MJPEG Camera Stream"
        className="w-full h-full object-cover"
        style={{ display: 'none' }}
      />

      {/* Placeholder overlay */}
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
        <div className="w-20 h-20 rounded-full border-2 border-hud-green/30 flex items-center justify-center">
          <div className="w-3 h-3 rounded-full bg-hud-green/50" />
        </div>
        <span className="font-mono text-sm text-muted-foreground tracking-wider">
          MJPEG Camera Stream Placeholder
        </span>
        <span className="font-mono text-xs text-muted-foreground/50">
          Replace img src to connect live feed
        </span>
      </div>

      {/* Crosshair overlay */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-0 right-0 h-px bg-hud-green/10" />
        <div className="absolute left-1/2 top-0 bottom-0 w-px bg-hud-green/10" />
        {/* Corner brackets */}
        <div className="absolute top-6 left-6 w-8 h-8 border-t-2 border-l-2 border-hud-green/20 rounded-tl" />
        <div className="absolute top-6 right-6 w-8 h-8 border-t-2 border-r-2 border-hud-green/20 rounded-tr" />
        <div className="absolute bottom-6 left-6 w-8 h-8 border-b-2 border-l-2 border-hud-green/20 rounded-bl" />
        <div className="absolute bottom-6 right-6 w-8 h-8 border-b-2 border-r-2 border-hud-green/20 rounded-br" />
      </div>
    </div>
  );
};

export default CameraFeed;
