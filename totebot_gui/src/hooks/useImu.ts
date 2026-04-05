import { useState, useEffect } from 'react';
import { rosService } from '../services/rosService';
import { Topic } from 'roslib';

// We pass 'isConnected' as a prop so the hook knows when it's safe to listen
export const useImu = (isConnected: boolean) => {
  const [pitch, setPitch] = useState<number>(0);
  const [roll, setRoll] = useState<number>(0);

  useEffect(() => {
    // If the main App hasn't connected to the Pi yet, don't try to subscribe
    if (!isConnected || !rosService.ros) return;

    // 1. Create the Topic object using the shared ROS connection
    const imuTopic = new Topic({
      ros: rosService.ros,
      name: '/totebot/imu',
      messageType: 'geometry_msgs/Vector3'
    });

    // 2. Subscribe and update React State
    imuTopic.subscribe((message: any) => {
      // Vector3 uses x, y, z. Our Python driver sends Roll on X and Pitch on Y.
      setRoll(message.x);
      setPitch(message.y);
    });

    // 3. Cleanup: Unsubscribe when the component unmounts
    return () => {
      imuTopic.unsubscribe();
    };
  }, [isConnected]); // Re-run this effect if the connection status changes

  return { pitch, roll };
};