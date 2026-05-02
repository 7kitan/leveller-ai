import React from "react";

interface ScanLineLoaderProps {
  size?: number;
  className?: string;
}

export default function ScanLineLoader({ size = 120, className = "" }: ScanLineLoaderProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 56 56"
      role="img"
      aria-label="Scan Line"
      width={size}
      height={size}
      className={className}
    >
      <title>Scan Line</title>
      <desc>A full row sweeps top to bottom like a CRT raster.</desc>
      <defs>
        <circle id="scan-bg" r="2.4" fill="currentColor" opacity="0.07" />
        <circle id="scan-dot" r="3.1" />
      </defs>
      <style>{`
        .scan-dot {
          fill: currentColor;
          opacity: 0;
          animation: scan-pulse 2000ms linear infinite both;
        }
        @keyframes scan-pulse {
          0% { opacity: 0; }
          8% { opacity: 1; }
          36% { opacity: 0.05; }
          100% { opacity: 0; }
        }
        @media (prefers-reduced-motion: reduce) {
          .scan-dot {
            animation: none;
            opacity: 0.45;
          }
        }
        .d00, .d01, .d02, .d03, .d04 { animation-delay: 0ms; }
        .d10, .d11, .d12, .d13, .d14 { animation-delay: 333ms; }
        .d20, .d21, .d22, .d23, .d24 { animation-delay: 667ms; }
        .d30, .d31, .d32, .d33, .d34 { animation-delay: 1000ms; }
        .d40, .d41, .d42, .d43, .d44 { animation-delay: 1333ms; }
      `}</style>
      
      {/* Background dots */}
      <use href="#scan-bg" x="6" y="6" />
      <use href="#scan-bg" x="17" y="6" />
      <use href="#scan-bg" x="28" y="6" />
      <use href="#scan-bg" x="39" y="6" />
      <use href="#scan-bg" x="50" y="6" />
      
      <use href="#scan-bg" x="6" y="17" />
      <use href="#scan-bg" x="17" y="17" />
      <use href="#scan-bg" x="28" y="17" />
      <use href="#scan-bg" x="39" y="17" />
      <use href="#scan-bg" x="50" y="17" />
      
      <use href="#scan-bg" x="6" y="28" />
      <use href="#scan-bg" x="17" y="28" />
      <use href="#scan-bg" x="28" y="28" />
      <use href="#scan-bg" x="39" y="28" />
      <use href="#scan-bg" x="50" y="28" />
      
      <use href="#scan-bg" x="6" y="39" />
      <use href="#scan-bg" x="17" y="39" />
      <use href="#scan-bg" x="28" y="39" />
      <use href="#scan-bg" x="39" y="39" />
      <use href="#scan-bg" x="50" y="39" />
      
      <use href="#scan-bg" x="6" y="50" />
      <use href="#scan-bg" x="17" y="50" />
      <use href="#scan-bg" x="28" y="50" />
      <use href="#scan-bg" x="39" y="50" />
      <use href="#scan-bg" x="50" y="50" />
      
      {/* Animated dots */}
      <use className="scan-dot d00" href="#scan-dot" x="6" y="6" />
      <use className="scan-dot d01" href="#scan-dot" x="17" y="6" />
      <use className="scan-dot d02" href="#scan-dot" x="28" y="6" />
      <use className="scan-dot d03" href="#scan-dot" x="39" y="6" />
      <use className="scan-dot d04" href="#scan-dot" x="50" y="6" />
      
      <use className="scan-dot d10" href="#scan-dot" x="6" y="17" />
      <use className="scan-dot d11" href="#scan-dot" x="17" y="17" />
      <use className="scan-dot d12" href="#scan-dot" x="28" y="17" />
      <use className="scan-dot d13" href="#scan-dot" x="39" y="17" />
      <use className="scan-dot d14" href="#scan-dot" x="50" y="17" />
      
      <use className="scan-dot d20" href="#scan-dot" x="6" y="28" />
      <use className="scan-dot d21" href="#scan-dot" x="17" y="28" />
      <use className="scan-dot d22" href="#scan-dot" x="28" y="28" />
      <use className="scan-dot d23" href="#scan-dot" x="39" y="28" />
      <use className="scan-dot d24" href="#scan-dot" x="50" y="28" />
      
      <use className="scan-dot d30" href="#scan-dot" x="6" y="39" />
      <use className="scan-dot d31" href="#scan-dot" x="17" y="39" />
      <use className="scan-dot d32" href="#scan-dot" x="28" y="39" />
      <use className="scan-dot d33" href="#scan-dot" x="39" y="39" />
      <use className="scan-dot d34" href="#scan-dot" x="50" y="39" />
      
      <use className="scan-dot d40" href="#scan-dot" x="6" y="50" />
      <use className="scan-dot d41" href="#scan-dot" x="17" y="50" />
      <use className="scan-dot d42" href="#scan-dot" x="28" y="50" />
      <use className="scan-dot d43" href="#scan-dot" x="39" y="50" />
      <use className="scan-dot d44" href="#scan-dot" x="50" y="50" />
    </svg>
  );
}
