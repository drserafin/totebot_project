import { useEffect, useState } from 'react';
import { rosService } from '../services/rosService';

export const useRos = (url: string) => {
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    rosService.connect(
      url,
      () => setIsConnected(true),
      () => setIsConnected(false)
    );
    
    // Cleanup when the user completely closes the app
    return () => rosService.disconnect(); 
  }, [url]);

  return {
    isConnected,
    // Just update the memory. The background loop handles the rest!
    move: (x: number, y: number) => rosService.setVelocity(y, x), 
    stop: () => rosService.setVelocity(0, 0)
  };
};