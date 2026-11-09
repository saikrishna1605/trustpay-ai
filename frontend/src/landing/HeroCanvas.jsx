import React, {Suspense, useMemo, useRef} from 'react';
import {Canvas, useFrame} from '@react-three/fiber';
import {Float, MeshDistortMaterial, Environment} from '@react-three/drei';
import * as THREE from 'three';

function Shield({reduced}){
  const group=useRef();
  useFrame((_,dt)=>{if(!reduced&&group.current)group.current.rotation.y+=dt*0.22;});
  return (
    <group ref={group} position={[0,0.55,0]} rotation={[0.35,0.25,0]}>
      <mesh castShadow>
        <cylinderGeometry args={[0.95,1.15,0.22,6]}/>
        <meshStandardMaterial color="#2f4f8c" metalness={0.55} roughness={0.28}/>
      </mesh>
      <mesh position={[0,0.14,0]} castShadow>
        <cylinderGeometry args={[0.72,0.88,0.18,6]}/>
        <meshStandardMaterial color="#4269df" metalness={0.4} roughness={0.22} emissive="#1a3a7a" emissiveIntensity={0.28}/>
      </mesh>
      <mesh position={[0,0.28,0]} rotation={[Math.PI/2,0,0]}>
        <torusGeometry args={[0.38,0.04,16,48]}/>
        <meshStandardMaterial color="#7eb8ff" metalness={0.6} roughness={0.2} emissive="#4674ee" emissiveIntensity={0.4}/>
      </mesh>
      <mesh position={[0,0.28,0]}>
        <sphereGeometry args={[0.16,24,24]}/>
        <meshStandardMaterial color="#e8f0ff" metalness={0.2} roughness={0.15} emissive="#9ec0ff" emissiveIntensity={0.45}/>
      </mesh>
    </group>
  );
}

function ScanRings({reduced}){
  const a=useRef(),b=useRef();
  useFrame((state)=>{
    if(reduced)return;
    const t=state.clock.elapsedTime;
    if(a.current){a.current.rotation.z=t*0.35;a.current.scale.setScalar(1+Math.sin(t*1.2)*0.03);}
    if(b.current){b.current.rotation.z=-t*0.22;b.current.scale.setScalar(1+Math.cos(t)*0.04);}
  });
  return (
    <group>
      <mesh ref={a} rotation={[Math.PI/2.4,0.2,0]}>
        <torusGeometry args={[1.85,0.02,12,96]}/>
        <meshBasicMaterial color="#6ea0ff" transparent opacity={0.55}/>
      </mesh>
      <mesh ref={b} rotation={[Math.PI/2.1,-0.35,0.4]}>
        <torusGeometry args={[2.25,0.015,12,96]}/>
        <meshBasicMaterial color="#22ac8e" transparent opacity={0.4}/>
      </mesh>
    </group>
  );
}

function Card({position,rotation,color,label}){
  return (
    <Float speed={1.2} rotationIntensity={0.25} floatIntensity={0.55}>
      <group position={position} rotation={rotation}>
        <mesh castShadow>
          <boxGeometry args={[1.15,0.72,0.06]}/>
          <meshStandardMaterial color={color} metalness={0.15} roughness={0.35}/>
        </mesh>
        <mesh position={[0,0,0.035]}>
          <planeGeometry args={[0.95,0.52]}/>
          <meshStandardMaterial color="#f7f9fc" roughness={0.55}/>
        </mesh>
        <mesh position={[-0.28,0.12,0.04]}>
          <planeGeometry args={[0.28,0.12]}/>
          <meshBasicMaterial color={label}/>
        </mesh>
        <mesh position={[0.2,-0.08,0.04]}>
          <planeGeometry args={[0.48,0.06]}/>
          <meshBasicMaterial color="#d5deee"/>
        </mesh>
      </group>
    </Float>
  );
}

function CoreOrb({reduced}){
  const ref=useRef();
  useFrame((s)=>{if(!reduced&&ref.current)ref.current.rotation.y=s.clock.elapsedTime*0.15;});
  return (
    <mesh ref={ref} position={[0,-0.05,0]}>
      <icosahedronGeometry args={[0.55,2]}/>
      <MeshDistortMaterial color="#1c2d4b" speed={reduced?0:1.4} distort={reduced?0:0.25} roughness={0.2} metalness={0.55} emissive="#243c64" emissiveIntensity={0.3}/>
    </mesh>
  );
}

function Nodes({reduced}){
  const points=useMemo(()=>[[-2.1,1.1,-0.4],[-1.8,-1.0,0.6],[2.0,0.9,-0.5],[1.9,-0.9,0.3],[0.2,1.7,-0.8]].map(p=>new THREE.Vector3(...p)),[]);
  const line=useMemo(()=>{
    const geo=new THREE.BufferGeometry().setFromPoints([points[0],new THREE.Vector3(0,0.2,0),points[1],new THREE.Vector3(0,0.2,0),points[2],new THREE.Vector3(0,0.2,0),points[3],new THREE.Vector3(0,0.2,0),points[4]]);
    return geo;
  },[points]);
  const group=useRef();
  useFrame((s)=>{if(!reduced&&group.current)group.current.rotation.y=Math.sin(s.clock.elapsedTime*0.2)*0.08;});
  return (
    <group ref={group}>
      <line geometry={line}>
        <lineBasicMaterial color="#7aa2ef" transparent opacity={0.35}/>
      </line>
      {points.map((p,i)=>(
        <mesh key={i} position={p}>
          <sphereGeometry args={[0.07,12,12]}/>
          <meshStandardMaterial color={i%2?'#22ac8e':'#4269df'} emissive={i%2?'#0f6b57':'#2a4eb0'} emissiveIntensity={0.45}/>
        </mesh>
      ))}
    </group>
  );
}

function Scene({reduced}){
  return (
    <>
      <color attach="background" args={['#0f1b2e']}/>
      <ambientLight intensity={0.55}/>
      <directionalLight castShadow position={[4,6,3]} intensity={1.25} color="#e8f0ff" shadow-mapSize={[1024,1024]}/>
      <pointLight position={[-3,2,-2]} intensity={0.7} color="#5f8dff"/>
      <pointLight position={[3,-1,2]} intensity={0.45} color="#2bb89a"/>
      <Suspense fallback={null}>
        <Environment preset="city"/>
        <CoreOrb reduced={reduced}/>
        <Shield reduced={reduced}/>
        <ScanRings reduced={reduced}/>
        <Nodes reduced={reduced}/>
        <Card position={[-2.35,0.55,0.4]} rotation={[0.15,-0.55,0.1]} color="#27406a" label="#4269df"/>
        <Card position={[2.25,0.35,0.55]} rotation={[-0.1,0.6,-0.08]} color="#1f3a58" label="#22ac8e"/>
        <Card position={[0.15,-1.45,0.9]} rotation={[0.35,0.15,0]} color="#243852" label="#e6ad45"/>
        <mesh rotation={[-Math.PI/2,0,0]} position={[0,-1.85,0]} receiveShadow>
          <circleGeometry args={[3.4,64]}/>
          <meshStandardMaterial color="#152338" metalness={0.3} roughness={0.85}/>
        </mesh>
      </Suspense>
    </>
  );
}

export default function HeroCanvas({reducedMotion=false}){
  return (
    <div className="hero-canvas" aria-hidden="true">
      <Canvas
        dpr={reducedMotion?[1]:[1,1.6]}
        camera={{position:[0.35,1.35,5.6],fov:36}}
        gl={{antialias:true,alpha:false,powerPreference:'high-performance'}}
        shadows={!reducedMotion}
      >
        <Scene reduced={reducedMotion}/>
      </Canvas>
    </div>
  );
}
