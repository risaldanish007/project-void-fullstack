import { useAppStartup } from "../components/common/AppStartupContext";
import { LottieSvg } from "lottie-react";
import animationData from "../assets/animations/void-loader.json";

const rendererSettings = { preserveAspectRatio: "xMidYMid meet" };

const VoidLoader = ({
  fullScreen = false,
  fadeOut = false,
  fadeDuration = 500,
  label = "Loading",
  className = "",
}) => {
  const appIsStarting = useAppStartup();
  if (appIsStarting) return null;

  return (
    <div
    className={`${
      fullScreen
        ? "fixed inset-0 z-[9999] min-h-dvh bg-[#050507]"
        : "flex min-h-[35vh] w-full"
    } flex flex-col items-center justify-center overflow-hidden transition-opacity duration-500 ease-out ${
      fadeOut ? "opacity-0" : "opacity-100"
    } ${className}`}
    style={fadeOut ? { transitionDuration: `${fadeDuration}ms` } : undefined}
    role="status"
    aria-live="polite"
    aria-busy="true"
  >
    <div className="aspect-square w-[min(43.2vw,12rem)]" aria-hidden="true">
      <LottieSvg
        src={animationData}
        loop
        autoplay
        className="h-full w-full"
        rendererSettings={rendererSettings}
      />
    </div>
    {label && !fullScreen && (
      <span className="-mt-5 font-mono text-[10px] uppercase tracking-[0.45em] text-white/60">
        {label}
      </span>
    )}
    {label && fullScreen && (
      <span className="absolute bottom-[12vh] font-mono text-[10px] uppercase tracking-[0.45em] text-white/60">
        {label}
      </span>
    )}
    </div>
  );
};

export default VoidLoader;
