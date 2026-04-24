import { useCallback } from 'react';
import { rosService } from '../services/rosService';

export const useAutoAlign = () => {
  const triggerStartAlign = useCallback(() => {
    // Tells the ROS Mux Node that the user is holding the Align button
    rosService.setAlignActive(true);
  }, []);

  const triggerStopAlign = useCallback(() => {
    // Tells the ROS Mux Node that the user released the button (return to joystick control)
    rosService.setAlignActive(false);
  }, []);

  return { triggerStartAlign, triggerStopAlign };
};