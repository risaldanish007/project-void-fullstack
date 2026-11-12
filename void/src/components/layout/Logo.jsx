// const Logo = ({ isWhite = true }) => {
//   return (
//     <div className="relative inline-flex items-center justify-center wifit ">
      
//       {/* VOID (slightly smaller now) */}
//       <h1 className={`text-3xl md:text-5xl font-black uppercase tracking-tighter leading-none select-none ${
//         isWhite ? 'text-white' : 'text-black'
//       }`}>
//         VOID
//       </h1>

//       {/* energy (manually positioned overlap) */}
//       <span className="absolute 
//                         drop-shadow-lg
//                        left-1/2 top-1/2 
//                        -translate-x-1/2 -translate-y-1/3
//                        text-3xl md:text-5xl 
//                        text-cyan-400 font-script 
//                        lowercase italic
//                        drop-shadow-[0_0_15px_rgba(34,211,238,0.4)]
//                        z-10 pointer-events-none
//                        pb-9">
//         energy
//       </span>
      
//     </div>
//   );
// };

// export default Logo;

const Logo = ({ isWhite = true }) => {
  return (
    <div className="relative inline-flex h-10 w-24 shrink-0 items-center justify-center sm:h-12 sm:w-32 group cursor-pointer leading-none">
      
      <h1 className={`m-0 p-0 text-[2rem] sm:text-[2.6rem] font-black uppercase tracking-tighter leading-none select-none transition-all duration-300 ${
        isWhite ? 'text-white' : 'text-black'
      } group-hover:text-green-300 group-hover:drop-shadow-[0_0_25px_rgba(34,211,238,0.8)]`}>
        VOID
      </h1>

      <span className="absolute left-1/2 top-1/2 z-10 whitespace-nowrap p-0 text-[1.75rem] sm:text-[2.25rem] leading-none drop-shadow-lg
                       text-green-400 [font-family:'Mr_De_Haviland',cursive]
                       lowercase italic
                       transition-all duration-200
                       group-hover:scale-110
                       group-hover:drop-shadow-[0_0_30px_rgba(34,211,238,1)]
                       group-hover:text-cyan-200
                       group-hover:animate-pulse
                       pointer-events-none"
        style={{ transform: "translate(-50%, -25%) rotate(-5deg)" }}>
        energy
      </span>
      
    </div>
  );
};

export default Logo;
