import React from 'react';

// Lectio Space logo - Premium SaaS брендинг (двухцветный как на AuthPage)
const Logo = ({ size = 40, withText = true }) => {
  const fontSize = size * 0.55; // Пропорциональный размер текста
  
  return (
    <div className="lectio-space-logo" style={{ display: 'flex', alignItems: 'center', gap: '10px', height: size }} aria-label="Lectio Space logo">
      {withText && (
        <span style={{
          fontSize: `${fontSize}px`,
          fontWeight: '800',
          fontStyle: 'normal',
          letterSpacing: '-0.02em',
          fontFamily: "'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif",
          whiteSpace: 'nowrap',
          display: 'inline-flex',
          alignItems: 'baseline',
          gap: '0.15em'
        }}>
          <span style={{ color: '#4f46e5', fontWeight: 800 }}>Lectio</span>
          <span style={{ color: '#94a3b8', fontWeight: 600 }}>Space</span>
        </span>
      )}
    </div>
  );
};

export default Logo;
