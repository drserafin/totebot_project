import { useState, useEffect, useRef, useCallback } from 'react';
import { Topic } from 'roslib';
import { rosService } from '../services/rosService';

// GoBilda 5304 = 5281 PPR per full output shaft rotation
export const TICKS_PER_ROTATION = 5281;

export type LifterState = 'IDLE' | 'EXTENDING' | 'RETRACTING' | 'ERROR';

export interface UseLifterControlReturn {
  lifterState: LifterState;
  currentTicks: number;
  currentRotations: number;
  isConnected: boolean;
  startExtend: () => void;
  startRetract: () => void;
  stop: () => void;
}

export function useLifterControl(): UseLifterControlReturn {
  const [lifterState, setLifterState] = useState<LifterState>('IDLE');
  const [currentTicks, setCurrentTicks] = useState(0);
  const [isConnected, setIsConnected] = useState(false);

  const lifterCmdRef = useRef<Topic | null>(null);
  const encoderSubRef = useRef<Topic | null>(null);

  useEffect(() => {
    // Poll until rosService.ros is connected
    // (it may already be connected by the time this hook mounts)
    const tryInit = () => {
      const ros = rosService.ros;
      if (!ros || !ros.isConnected) return false;

      // ── Publish topic: lifter commands ──────────────────────────
      lifterCmdRef.current = new Topic({
        ros,
        name: '/lifter_cmd',
        messageType: 'std_msgs/Int32',
      });

      // ── Subscribe topic: live encoder ticks ─────────────────────
      encoderSubRef.current = new Topic({
        ros,
        name: '/encoder_ticks',
        messageType: 'std_msgs/Int32',
      });

      encoderSubRef.current.subscribe((msg: any) => {
        setCurrentTicks(msg.data ?? 0);
      });

      setIsConnected(true);
      return true;
    };

    // Try immediately — if already connected this resolves right away
    if (!tryInit()) {
      // Otherwise poll every 500ms until rosService connects
      const interval = setInterval(() => {
        if (tryInit()) clearInterval(interval);
      }, 500);

      return () => {
        clearInterval(interval);
        encoderSubRef.current?.unsubscribe();
      };
    }

    return () => {
      encoderSubRef.current?.unsubscribe();
    };
  }, []);

  // Also track rosService connection state changes
  useEffect(() => {
    const ros = rosService.ros;
    if (!ros) return;

    const onClose = () => {
      setIsConnected(false);
      setLifterState('ERROR');
    };
    const onError = () => {
      setIsConnected(false);
      setLifterState('ERROR');
    };

    ros.on('close', onClose);
    ros.on('error', onError);

    return () => {
      ros.off('close', onClose);
      ros.off('error', onError);
    };
  }, []);

  const publishCmd = useCallback((value: number) => {
    if (!lifterCmdRef.current) {
      console.warn('[useLifterControl] lifterCmd topic not ready');
      return;
    }
    lifterCmdRef.current.publish({ data: value });
  }, []);

  const startExtend  = useCallback(() => { setLifterState('EXTENDING');  publishCmd(1);  }, [publishCmd]);
  const startRetract = useCallback(() => { setLifterState('RETRACTING'); publishCmd(-1); }, [publishCmd]);
  const stop         = useCallback(() => { setLifterState('IDLE');        publishCmd(0);  }, [publishCmd]);

  return {
    lifterState,
    currentTicks,
    currentRotations: currentTicks / TICKS_PER_ROTATION,
    isConnected,
    startExtend,
    startRetract,
    stop,
  };
}