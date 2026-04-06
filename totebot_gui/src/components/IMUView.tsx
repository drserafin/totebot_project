import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, RoundedBox } from '@react-three/drei';
import { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useImu } from '../hooks/useImu';

const IMUBoard = ({ quaternion }: { quaternion: THREE.Quaternion }) => {
  const groupRef = useRef<THREE.Group>(null);

  useFrame(() => {
    if (!groupRef.current) return;
    groupRef.current.quaternion.set(
      quaternion.x, 
      quaternion.z, 
      -quaternion.y, 
      quaternion.w
    );
  });

  const pcbColor = useMemo(() => new THREE.Color('hsl(142, 87%, 31%)'), []);
  const chipColor = useMemo(() => new THREE.Color('hsl(222, 47%, 15%)'), []);
  const pinColor = useMemo(() => new THREE.Color('hsl(56, 100%, 50%)'), []);
  const textColor = useMemo(() => new THREE.Color('hsl(0, 0%, 100%)'), []);

  return (
    <group ref={groupRef}>
      {/* PCB Board */}
      <RoundedBox args={[2.4, 0.15, 1.8]} radius={0.05} smoothness={4}>
        <meshStandardMaterial color={pcbColor} roughness={0.6} metalness={0.2} />
      </RoundedBox>

      {/* MPU-6050 Chip */}
      <RoundedBox args={[0.8, 0.12, 0.8]} radius={0.02} smoothness={4} position={new THREE.Vector3(0, 0.13, 0)}>
        <meshStandardMaterial color={chipColor} roughness={0.3} metalness={0.5} />
      </RoundedBox>

      {/* Chip label */}
      <Text
        position={new THREE.Vector3(0, 0.2, 0)}
        rotation={new THREE.Euler(-Math.PI / 2, 0, 0)}
        fontSize={0.12}
        color={textColor}
        font={undefined}
        anchorX="center"
        anchorY="middle"
      >
        MPU-6050
      </Text>

      {/* Pin headers - standard GY-521 8-pin layout on left side, pulled down */}
      {[-0.7, -0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 0.7].map((z, i) => (
        <mesh key={`pin-${i}`} position={new THREE.Vector3(-1.05, -0.1, z)}>
          <boxGeometry args={[0.08, 0.4, 0.08]} />
          <meshStandardMaterial color={pinColor} metalness={0.8} roughness={0.2} />
        </mesh>
      ))}

      {/* X axis - red */}
      <mesh position={new THREE.Vector3(1.6, 0, 0)} rotation={new THREE.Euler(0, 0, -Math.PI / 2)}>
        <coneGeometry args={[0.08, 0.25, 8]} />
        <meshStandardMaterial color="hsl(0, 84%, 60%)" />
      </mesh>
      <mesh position={new THREE.Vector3(1.35, 0, 0)} rotation={new THREE.Euler(0, 0, -Math.PI / 2)}>
        <cylinderGeometry args={[0.02, 0.02, 0.5]} />
        <meshStandardMaterial color="hsl(0, 84%, 60%)" />
      </mesh>

      {/* Y axis - green */}
      <mesh position={new THREE.Vector3(0, 0.55, 0)}>
        <coneGeometry args={[0.08, 0.25, 8]} />
        <meshStandardMaterial color="hsl(142, 71%, 45%)" />
      </mesh>
      <mesh position={new THREE.Vector3(0, 0.35, 0)}>
        <cylinderGeometry args={[0.02, 0.02, 0.5]} />
        <meshStandardMaterial color="hsl(142, 71%, 45%)" />
      </mesh>

      {/* Z axis - blue */}
      <mesh position={new THREE.Vector3(0, 0, 1.2)} rotation={new THREE.Euler(Math.PI / 2, 0, 0)}>
        <coneGeometry args={[0.08, 0.25, 8]} />
        <meshStandardMaterial color="hsl(187, 85%, 53%)" />
      </mesh>
      <mesh position={new THREE.Vector3(0, 0, 0.95)} rotation={new THREE.Euler(Math.PI / 2, 0, 0)}>
        <cylinderGeometry args={[0.02, 0.02, 0.5]} />
        <meshStandardMaterial color="hsl(187, 85%, 53%)" />
      </mesh>
    </group>
  );
};

const IMUView = ({ isConnected = true }: { isConnected?: boolean }) => {
  const { quaternion, eulerDeg } = useImu(isConnected);

  const formatAngle = (angle: number) => {
    return (angle > 0 ? '+' : '') + angle.toFixed(1) + '°';
  };

  return (
    <div className="relative w-full h-full rounded-xl overflow-hidden bg-surface-light border border-border">
      {/* IMU label */}
      <div className="absolute top-4 right-4 z-10 font-mono text-xs text-muted-foreground bg-surface-dark/80 backdrop-blur-sm px-3 py-1.5 rounded-md border border-border">
        MPU-6050 · 3-Axis · 50Hz
      </div>

      {/* Axis legend */}
      <div className="absolute bottom-4 left-4 z-10 flex flex-col gap-1 font-mono text-[10px] bg-surface-dark/80 backdrop-blur-sm px-3 py-2 rounded-md border border-border">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-destructive" />
          <span className="text-muted-foreground">X Roll</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-primary" />
          <span className="text-muted-foreground">Y Pitch</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-hud-cyan" />
          <span className="text-muted-foreground">Z Yaw</span>
        </span>
      </div>

      {/* Telemetry readout */}
      <div className="absolute bottom-4 right-4 z-10 font-mono text-sm text-muted-foreground bg-surface-dark/80 backdrop-blur-sm px-4 py-3 rounded-md border border-border">
        <div className="grid grid-cols-2 gap-x-6 gap-y-1">
          <span>Roll</span><span className="text-foreground font-semibold">{formatAngle(eulerDeg.roll)}</span>
          <span>Pitch</span><span className="text-foreground font-semibold">{formatAngle(eulerDeg.pitch)}</span>
          <span>Yaw</span><span className="text-foreground font-semibold">{formatAngle(eulerDeg.yaw)}</span>
        </div>
      </div>

      <Canvas camera={{ position: new THREE.Vector3(3, 2, 3), fov: 40 }}>
        <ambientLight intensity={0.4} />
        <directionalLight position={new THREE.Vector3(5, 5, 5)} intensity={0.8} />
        <directionalLight position={new THREE.Vector3(-3, 2, -3)} intensity={0.3} />
        
        <IMUBoard quaternion={quaternion} />
        
        <OrbitControls enableZoom={false} enablePan={false} />
        <gridHelper args={[6, 12, "#2aa146", "#475569"]} position={new THREE.Vector3(0, -0.5, 0)} />
      </Canvas>
    </div>
  );
};

export default IMUView;