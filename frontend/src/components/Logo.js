import React from 'react';

// Easy Teaching logo - минималистичная иконка книги с современным текстом
const Logo = ({ size = 40, withText = true }) => {
  return (
    <div className="easy-teaching-logo" style={{ display: 'flex', alignItems: 'center', gap: '10px', height: size }} aria-label="Easy Teaching logo">
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        style={{ flexShrink: 0 }}
      >
        <defs>
          <linearGradient id="bookGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#3b82f6', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#2563eb', stopOpacity: 1 }} />
          </linearGradient>
        </defs>
        {/* Стилизованная открытая книга */}
        <path 
          d="M20 8 C15 8, 10 10, 6 13 L6 32 C10 29, 15 27, 20 27 M20 8 C25 8, 30 10, 34 13 L34 32 C30 29, 25 27, 20 27 M20 8 L20 27" 
          fill="none"
          stroke="url(#bookGradient)"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Закладка */}
        <path 
          d="M20 8 L20 18" 
          stroke="#3b82f6"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
      {withText && (
        <span style={{
          fontSize: '20px',
          fontWeight: '700',
          letterSpacing: '0.3px',
          background: 'linear-gradient(135deg, #1e293b 0%, #3b82f6 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          whiteSpace: 'nowrap'
        }}>
          Easy Teaching
        </span>
      )}
    </div>
  );
};

export default Logo;
