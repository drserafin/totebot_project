import { useEffect, useState } from 'react';
import { rosService } from '../services/rosService';

export const useRosConnection = (url: string) => {
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    rosService.connect(
      url,
      () => setIsConnected(true),
      () => setIsConnected(false)
    );
    
    // When the whole app closes, disconnect cleanly
    return () => rosService.disconnect(); 
  }, [url]);

  // It only returns the connection status, nothing else!
  return { isConnected };
};