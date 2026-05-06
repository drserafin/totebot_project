// hooks/useAutoAlign.ts
import { rosService } from '../services/rosService';

export function useAutoAlign() {
  return {
    triggerStartAlign: () => rosService.setAlignActive(true),
    triggerStopAlign:  () => rosService.setAlignActive(false),
  };
}