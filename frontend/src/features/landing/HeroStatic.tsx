import React from "react";

export const HeroStatic: React.FC = () => {
  return (
    <div className="relative w-full h-[380px] sm:h-[460px] flex items-center justify-center overflow-hidden rounded-2xl border border-slate-800/80 bg-gradient-to-b from-slate-900/60 to-slate-950/80">
      {/* Background glow and orbital rings */}
      <div className="absolute w-72 h-72 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />
      <div className="absolute w-96 h-96 rounded-full border border-cyan-500/10 animate-[spin_40s_linear_infinite] pointer-events-none" />
      <div className="absolute w-[450px] h-[450px] rounded-full border border-teal-500/10 animate-[spin_60s_linear_infinite_reverse] pointer-events-none" />

      {/* SVG Evidence Observatory Lens & Floating Paper Nodes */}
      <svg
        className="relative z-10 w-full h-full max-w-[500px]"
        viewBox="0 0 500 380"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Central Evidence Hub */}
        <circle cx="250" cy="190" r="48" fill="url(#coreGlow)" stroke="#8db4d9" strokeWidth="2" strokeDasharray="4 2" />
        <circle cx="250" cy="190" r="24" fill="#2f5f8f" fillOpacity="0.4" stroke="#8db4d9" strokeWidth="1.5" />
        <circle cx="250" cy="190" r="8" fill="#e9cf93" />

        {/* Orbiting Paper Records */}
        <g className="transition-transform duration-700 hover:scale-105">
          {/* Node 1: PubMed Record */}
          <rect x="90" y="80" width="105" height="65" rx="8" fill="#0e131d" fillOpacity="0.85" stroke="#8db4d9" strokeWidth="1" />
          <line x1="105" y1="98" x2="165" y2="98" stroke="#7c8696" strokeWidth="2" strokeLinecap="round" />
          <line x1="105" y1="110" x2="180" y2="110" stroke="#3b4556" strokeWidth="2" strokeLinecap="round" />
          <line x1="105" y1="122" x2="145" y2="122" stroke="#3b4556" strokeWidth="2" strokeLinecap="round" />
          <circle cx="100" cy="80" r="4" fill="#8db4d9" />
          <line x1="195" y1="120" x2="225" y2="165" stroke="#8db4d9" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" />
        </g>

        <g className="transition-transform duration-700 hover:scale-105">
          {/* Node 2: Europe PMC Record */}
          <rect x="305" y="65" width="115" height="70" rx="8" fill="#0e131d" fillOpacity="0.85" stroke="#d8b46a" strokeWidth="1" />
          <line x1="320" y1="85" x2="385" y2="85" stroke="#7c8696" strokeWidth="2" strokeLinecap="round" />
          <line x1="320" y1="97" x2="400" y2="97" stroke="#3b4556" strokeWidth="2" strokeLinecap="round" />
          <line x1="320" y1="109" x2="365" y2="109" stroke="#3b4556" strokeWidth="2" strokeLinecap="round" />
          <circle cx="420" cy="65" r="4" fill="#d8b46a" />
          <line x1="305" y1="120" x2="275" y2="165" stroke="#d8b46a" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" />
        </g>

        <g className="transition-transform duration-700 hover:scale-105">
          {/* Node 3: PICO Extraction */}
          <rect x="180" y="260" width="140" height="75" rx="8" fill="#0e131d" fillOpacity="0.85" stroke="#b79ce6" strokeWidth="1" />
          <text x="195" y="282" fill="#cdb8ef" fontSize="10" fontFamily="monospace" fontWeight="bold">PICO ENTITIES</text>
          <rect x="195" y="292" width="22" height="12" rx="3" fill="#8db4d9" fillOpacity="0.25" />
          <text x="202" y="301" fill="#b9d2ea" fontSize="8" fontFamily="monospace">P</text>
          <rect x="223" y="292" width="22" height="12" rx="3" fill="#b79ce6" fillOpacity="0.25" />
          <text x="231" y="301" fill="#d9cbf3" fontSize="8" fontFamily="monospace">I</text>
          <rect x="251" y="292" width="22" height="12" rx="3" fill="#d8b46a" fillOpacity="0.25" />
          <text x="258" y="301" fill="#f1dcab" fontSize="8" fontFamily="monospace">C</text>
          <rect x="279" y="292" width="22" height="12" rx="3" fill="#7cc49b" fillOpacity="0.25" />
          <text x="286" y="301" fill="#bfe3cd" fontSize="8" fontFamily="monospace">O</text>
          <line x1="250" y1="238" x2="250" y2="260" stroke="#b79ce6" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" />
        </g>

        {/* Gradients */}
        <defs>
          <radialGradient id="coreGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(250 190) scale(48)">
            <stop stopColor="#2f5f8f" stopOpacity="0.8" />
            <stop offset="1" stopColor="#2f5f8f" stopOpacity="0.1" />
          </radialGradient>
        </defs>
      </svg>

      <div className="absolute bottom-3 left-4 text-[11px] text-slate-500 font-mono">
        Evidence Observatory • Procedural Lens Fallback
      </div>
    </div>
  );
};
