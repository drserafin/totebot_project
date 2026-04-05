import { rosService } from '../services/rosService';

export const useMotors = () => {
  return {
    move: (x: number, y: number) => rosService.setVelocity(y, x),
    stop: () => rosService.setVelocity(0, 0)
  };
};