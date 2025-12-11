import React from 'react';

// Lectio Space logo - Premium SaaS брендинг
const Logo = ({ size = 40, withText = true }) => {
  return (
    <div className="lectio-space-logo" style={{ display: 'flex', alignItems: 'center', gap: '10px', height: size }} aria-label="Lectio Space logo">
      {withText && (
        <span style={{
          fontSize: '22px',
          fontWeight: '800',
          fontStyle: 'normal',
          letterSpacing: '-0.02em',
          fontFamily: "'Inter', -apple-system, sans-serif",
          whiteSpace: 'nowrap',
          background: 'linear-gradient(135deg, #4338ca 0%, #6366f1 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text'
        }}>
          Lectio Space
        </span>
      )}
    </div>
  );
};

export default Logo;
