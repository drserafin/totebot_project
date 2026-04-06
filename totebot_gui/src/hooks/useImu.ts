import { useState, useEffect } from 'react';
import { rosService } from '../services/rosService';
import { Topic } from 'roslib';
import * as THREE from 'three';

export const useImu = (isConnected: boolean) => {
  // State for the 3D Model (Quaternion)
  const [quaternion, setQuaternion] = useState<THREE.Quaternion>(new THREE.Quaternion());
  
  // State for the UI Text (Degrees)
  const [eulerDeg, setEulerDeg] = useState({ roll: 0, pitch: 0, yaw: 0 });

  useEffect(() => {
    if (!isConnected || !rosService.ros) return;

    const imuTopic = new Topic({
      ros: rosService.ros,
      name: '/totebot/imu',
      messageType: 'sensor_msgs/Imu' 
    });

    imuTopic.subscribe((message: any) => {
      const qMsg = message.orientation;
      
      const q = new THREE.Quaternion(qMsg.x, qMsg.y, qMsg.z, qMsg.w);
      setQuaternion(q);

      const euler = new THREE.Euler().setFromQuaternion(q, 'XYZ');
      setEulerDeg({
        roll: THREE.MathUtils.radToDeg(euler.x),
        pitch: THREE.MathUtils.radToDeg(euler.y),
        yaw: THREE.MathUtils.radToDeg(euler.z)
      });
    });

    return () => {
      imuTopic.unsubscribe();
    };
  }, [isConnected]);

  return { quaternion, eulerDeg };
};