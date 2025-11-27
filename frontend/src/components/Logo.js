import React from 'react';

// Новый логотип (книга + планшет + шапочка) адаптирован в SVG.
// size управляет высотой блока; ширина масштабируется пропорционально.
const Logo = ({ size = 36, withText = false }) => {
  const width = withText ? Math.round(size * 4.4) : size; // пропорция ширины для варианта с текстом
  return (
    <div className="tp-logo" style={{ height: size, width }} aria-label="Teaching Panel logo">
      <svg
        width={width}
        height={size}
        viewBox={withText ? '0 0 160 48' : '0 0 60 48'}
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        aria-hidden={false}
      >
        <style>
          {`.tp-stroke{stroke:#1d4ed8;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;} .tp-fill{fill:#1d4ed8;} @media (prefers-color-scheme:dark){ .tp-stroke{stroke:#3b82f6;} .tp-fill{fill:#3b82f6;} }`}
        </style>
        {/* Книга */}
        <path className="tp-stroke" d="M6 14h18v20c-6-3-12-3-18 0V14Z" fill="#eef3ff" />
        <path className="tp-stroke" d="M24 14h18v20c-6-3-12-3-18 0V14Z" fill="#ffffff" />
        {/* Планшет */}
        <rect className="tp-stroke" x="36" y="8" width="22" height="28" rx="4" fill="#fff" />
        <rect className="tp-stroke" x="41" y="14" width="12" height="16" rx="2" />
        <path className="tp-stroke" d="M47 34h4" />
        {/* Шапочка */}
        <path className="tp-fill" d="M30 8 20 12l10 4 10-4-10-4Z" />
        <path className="tp-fill" d="M25.5 13.2v4.2c0 .9 1.2 1.6 2.5 1.6s2.5-.7 2.5-1.6v-4.2" fill="none" stroke="#1d4ed8" strokeWidth="1.6" strokeLinecap="round" />
        <path className="tp-fill" d="M34 12v6" stroke="#1d4ed8" strokeWidth="1.6" strokeLinecap="round" />
        {withText && (
          <g fill="#1d4ed8" fontFamily="system-ui,Segoe UI,Roboto,Arial" fontSize="18" fontWeight="600">
            <text x="64" y="24" letterSpacing=".5">Teaching</text>
            <text x="64" y="42" letterSpacing=".5">Panel</text>
          </g>
        )}
      </svg>
    </div>
  );
};

export default Logo;
