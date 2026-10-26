import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

interface NeuralNetwork3DProps {
  currentPhase: string; // 'READ' | 'PLAN' | 'TOOL_CALL' | 'EVALUATE' | 'LOG' | 'IDLE' | 'SUSPENDED' | 'BLOCKED'
  isDemo: boolean;
  workerName: string;
}

interface NodeData {
  mesh: THREE.Mesh;
  basePosition: THREE.Vector3;
  layer: number; // 0=Read, 1=Plan, 2=ToolCall, 3=Evaluate, 4=Log
}

export const NeuralNetwork3D: React.FC<NeuralNetwork3DProps> = ({ currentPhase, isDemo, workerName }) => {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    // 1. Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x050811, 0.035);

    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
    camera.position.set(0, 0, 24);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // 2. Build Neural Topology
    const layers = [
      { name: 'READ', count: 4, x: -9, color: 0x00f0ff },
      { name: 'PLAN', count: 6, x: -4.5, color: 0x00d2ff },
      { name: 'TOOL_CALL', count: 5, x: 0, color: 0x8b5cf6 },
      { name: 'EVALUATE', count: 5, x: 4.5, color: 0xf59e0b },
      { name: 'LOG', count: 3, x: 9, color: 0x10b981 },
    ];

    const nodes: NodeData[] = [];
    const nodeGeometry = new THREE.SphereGeometry(0.32, 16, 16);

    layers.forEach((layer, layerIdx) => {
      const ySpacing = 2.4;
      const yOffset = ((layer.count - 1) * ySpacing) / 2;

      for (let i = 0; i < layer.count; i++) {
        const material = new THREE.MeshBasicMaterial({
          color: layer.color,
          transparent: true,
          opacity: 0.85,
        });
        const mesh = new THREE.Mesh(nodeGeometry, material);
        const y = i * ySpacing - yOffset;
        const z = (Math.random() - 0.5) * 3;
        mesh.position.set(layer.x, y, z);

        scene.add(mesh);
        nodes.push({
          mesh,
          basePosition: new THREE.Vector3(layer.x, y, z),
          layer: layerIdx,
        });
      }
    });

    // 3. Connect Nodes with Synaptic Lines
    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0x1c2a47,
      transparent: true,
      opacity: 0.35,
    });

    const activeLineMaterial = new THREE.LineBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.8,
    });

    const linesGroup = new THREE.Group();
    const activeLinesGroup = new THREE.Group();
    scene.add(linesGroup);
    scene.add(activeLinesGroup);

    // Create connections between adjacent layers
    for (let l = 0; l < layers.length - 1; l++) {
      const currentLayerNodes = nodes.filter((n) => n.layer === l);
      const nextLayerNodes = nodes.filter((n) => n.layer === l + 1);

      currentLayerNodes.forEach((src) => {
        nextLayerNodes.forEach((dst) => {
          // Connect with high probability
          if (Math.random() > 0.3) {
            const points = [src.basePosition, dst.basePosition];
            const geometry = new THREE.BufferGeometry().setFromPoints(points);
            const line = new THREE.Line(geometry, lineMaterial);
            linesGroup.add(line);
          }
        });
      });
    }

    // 4. Background Ambient Starfield Particles
    const starCount = 350;
    const starGeometry = new THREE.BufferGeometry();
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i += 3) {
      starPositions[i] = (Math.random() - 0.5) * 60;
      starPositions[i + 1] = (Math.random() - 0.5) * 40;
      starPositions[i + 2] = (Math.random() - 0.5) * 40 - 10;
    }
    starGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    const starMaterial = new THREE.PointsMaterial({
      color: 0x475569,
      size: 0.15,
      transparent: true,
      opacity: 0.45,
    });
    const starField = new THREE.Points(starGeometry, starMaterial);
    scene.add(starField);

    // 5. Interactive Mouse Rotation
    let mouseX = 0;
    let mouseY = 0;
    let targetRotationX = 0;
    let targetRotationY = 0;

    const handleMouseMove = (event: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      mouseX = ((event.clientX - rect.left) / width) * 2 - 1;
      mouseY = -(((event.clientY - rect.top) / height) * 2 - 1);
      targetRotationY = mouseX * 0.35;
      targetRotationX = mouseY * 0.2;
    };
    container.addEventListener('mousemove', handleMouseMove);

    // 6. Animation Loop
    let animationFrameId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Smooth camera/scene tilt
      scene.rotation.y += (targetRotationY - scene.rotation.y) * 0.05;
      scene.rotation.x += (targetRotationX - scene.rotation.x) * 0.05;

      // Subtle node pulsation and phase response
      const isSuspended = currentPhase === 'SUSPENDED';
      const isBlocked = currentPhase === 'BLOCKED';

      nodes.forEach((node) => {
        const layerMeta = layers[node.layer];
        const isActiveLayer = layerMeta.name === currentPhase;

        let scale = 1.0;
        let opacity = 0.5;

        if (isBlocked) {
          (node.mesh.material as THREE.MeshBasicMaterial).color.setHex(0xef4444);
          scale = 0.9 + Math.sin(elapsedTime * 6) * 0.2;
          opacity = 0.9;
        } else if (isSuspended) {
          (node.mesh.material as THREE.MeshBasicMaterial).color.setHex(0x334155);
          scale = 0.7;
          opacity = 0.3;
        } else if (isActiveLayer) {
          scale = 1.4 + Math.sin(elapsedTime * 8) * 0.25;
          opacity = 1.0;
          (node.mesh.material as THREE.MeshBasicMaterial).color.setHex(layerMeta.color);
        } else {
          scale = 1.0 + Math.sin(elapsedTime * 2 + node.layer) * 0.08;
          opacity = 0.45;
          (node.mesh.material as THREE.MeshBasicMaterial).color.setHex(layerMeta.color);
        }

        node.mesh.scale.set(scale, scale, scale);
        (node.mesh.material as THREE.MeshBasicMaterial).opacity = opacity;
      });

      // Subtle starfield drift
      starField.rotation.y = elapsedTime * 0.02;

      renderer.render(scene, camera);
    };

    animate();

    // 7. Handle Resize
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId);
      container.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [currentPhase]);

  return (
    <div className="relative w-full h-full min-h-[320px] bg-gradient-to-b from-[#070b14] to-[#04060a] rounded-xl overflow-hidden border border-[#172238] shadow-2xl">
      {/* 3D Canvas Mount */}
      <div ref={mountRef} className="absolute inset-0 z-0" />

      {/* Top Banner Overlays */}
      <div className="absolute top-3 left-4 right-4 flex items-center justify-between z-10 pointer-events-none">
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-[#0a101d]/90 border border-cyan-500/30 backdrop-blur-md">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-xs font-mono font-semibold tracking-wider text-cyan-300 uppercase">
              Neural Activity: {currentPhase || 'IDLE'}
            </span>
          </div>

          <span className="text-xs font-mono text-slate-400 px-2 py-0.5 rounded bg-slate-900/80 border border-slate-800">
            Worker: {workerName}
          </span>
        </div>

        {/* DEMO or LIVE Mode Badge */}
        {isDemo ? (
          <div className="px-3 py-1 rounded-md bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs font-mono font-bold tracking-wider uppercase animate-pulse">
            DEMO — SIMULATED EVENTS
          </div>
        ) : (
          <div className="px-3 py-1 rounded-md bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-mono font-bold tracking-wider uppercase">
            LIVE BACKEND CONNECTED
          </div>
        )}
      </div>

      {/* Bottom Stage Legend */}
      <div className="absolute bottom-3 left-4 right-4 flex items-center justify-between z-10 pointer-events-none text-[11px] font-mono text-slate-400">
        <div className="flex items-center space-x-4">
          <span className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-[#00f0ff]" />
            <span>Read</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-[#00d2ff]" />
            <span>Plan</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-[#8b5cf6]" />
            <span>Tool Call</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-[#f59e0b]" />
            <span>Evaluate</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-[#10b981]" />
            <span>Log</span>
          </span>
        </div>

        <div className="text-[10px] text-slate-500">
          Visual topology abstraction • Zero internal claim
        </div>
      </div>
    </div>
  );
};
