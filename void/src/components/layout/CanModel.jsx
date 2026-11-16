import React, {
  Component,
  Suspense,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import * as THREE from "three";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useGLTF, Environment } from "@react-three/drei";
import { motion as Motion } from "framer-motion";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const MODEL_URL = "/3d/can5.glb";

// Local environment map (served from /public, works offline).
// For even more detailed reflections, swap in a 2k version, e.g.
// "/3d/studio_small_03_2k.exr". 2k is the sweet spot; 4k is heavy to load.
const ENV_URL = "/3d/studio_small_03_1k.exr";

const VERTICAL_OFFSET = 0.6;
const INTRO_START_OFFSET = -1.2;

// ---------------------------------------------------------------------------
// Error boundary: a failed asset never takes down the page
// ---------------------------------------------------------------------------
class AssetBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    console.error("[CanViewer] asset failed to load:", error);
    this.props.onError?.(error);
  }

  render() {
    return this.state.hasError ? null : this.props.children;
  }
}

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------
function CanModel({ shouldAnimate, onReady }) {
  const { scene } = useGLTF(MODEL_URL);
  const gl = useThree((state) => state.gl);

  const ref = useRef();
  const introDone = useRef(!shouldAnimate);

  // Metallic look + maximum texture sharpness
  useEffect(() => {
    const maxAnisotropy = gl.capabilities.getMaxAnisotropy();

    const textureKeys = [
      "map",
      "normalMap",
      "roughnessMap",
      "metalnessMap",
      "aoMap",
      "emissiveMap",
    ];

    scene.traverse((child) => {
      if (!child.isMesh) return;

      const materials = Array.isArray(child.material)
        ? child.material
        : [child.material];

      materials.forEach((material) => {
        material.metalness = 0.8;
        material.roughness = 0.3;
        material.envMapIntensity = 2;

        textureKeys.forEach((key) => {
          if (material[key]) {
            material[key].anisotropy = maxAnisotropy;
            material[key].needsUpdate = true;
          }
        });

        material.needsUpdate = true;
      });
    });
  }, [scene, gl]);

  // Set the starting position before the first paint
  useLayoutEffect(() => {
    if (shouldAnimate && ref.current) {
      ref.current.position.y = VERTICAL_OFFSET + INTRO_START_OFFSET;
    }
  }, [shouldAnimate]);

  // This component only mounts once the model AND environment have resolved
  // (both live inside the same <Suspense>), so this is the "ready" signal.
  useEffect(() => {
    const id = requestAnimationFrame(() => onReady?.());
    return () => cancelAnimationFrame(id);
  }, [onReady]);

  useFrame((state, delta) => {
    const object = ref.current;
    if (!object) return;

    // ENTRY ANIMATION (frame-rate independent)
    if (!introDone.current) {
      object.position.y = THREE.MathUtils.damp(
        object.position.y,
        VERTICAL_OFFSET,
        3,
        delta
      );

      if (Math.abs(object.position.y - VERTICAL_OFFSET) < 0.005) {
        object.position.y = VERTICAL_OFFSET;
        introDone.current = true;
      }
      return;
    }

    // IDLE FLOATING
    const t = state.clock.getElapsedTime();
    object.position.y = VERTICAL_OFFSET + Math.sin(t * 1.2) * 0.03;

    // POINTER PARALLAX (frame-rate independent smoothing)
    const { pointer } = state;
    const targetY = Math.PI + pointer.x * 0.2;
    const targetX = -pointer.y * 0.2;

    object.rotation.y = THREE.MathUtils.damp(
      object.rotation.y,
      targetY,
      2.5,
      delta
    );
    object.rotation.x = THREE.MathUtils.damp(
      object.rotation.x,
      targetX,
      2.5,
      delta
    );
  });

  return (
    <primitive
      ref={ref}
      object={scene}
      scale={[3, 2.9, 3]}
      rotation={[0, Math.PI, 0]}
      position={[0, VERTICAL_OFFSET, -1]}
    />
  );
}

// ---------------------------------------------------------------------------
// Viewer
// ---------------------------------------------------------------------------
export default function CanViewer() {
  const [ready, setReady] = useState(false);

  // Read once. The write happens in an effect so React StrictMode's
  // double-invoked initializer can't flip the flag before first render.
  const [shouldAnimate] = useState(() => {
    try {
      return !sessionStorage.getItem("canAnimated");
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      sessionStorage.setItem("canAnimated", "true");
    } catch {
      /* storage unavailable, ignore */
    }
  }, []);

  const markReady = () => setReady(true);

  return (
    <Motion.div
      initial={shouldAnimate ? { opacity: 0 } : false}
      animate={{ opacity: ready ? 1 : 0 }}
      transition={{ duration: 1.2, ease: "easeOut" }}
      className="w-full"
    >
      <div className="absolute inset-0 h-screen w-screen pointer-events-none">
        <Canvas
          camera={{ position: [0, 0, 7], fov: 50 }}
          dpr={[1, 2]}
          gl={{
            antialias: true,
            powerPreference: "high-performance",
            toneMapping: THREE.ACESFilmicToneMapping,
            toneMappingExposure: 1,
          }}
        >
          {/* Lighting comes entirely from the environment map */}
          <Suspense fallback={null}>
            {/* If the HDR fails, the can still renders (just less reflective) */}
            <AssetBoundary>
              <Environment files={ENV_URL} />
            </AssetBoundary>

            {/* If the model fails, still fade the canvas in instead of hanging */}
            <AssetBoundary onError={markReady}>
              <CanModel shouldAnimate={shouldAnimate} onReady={markReady} />
            </AssetBoundary>
          </Suspense>
        </Canvas>
      </div>
    </Motion.div>
  );
}

useGLTF.preload(MODEL_URL);
