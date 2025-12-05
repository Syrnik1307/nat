import React from 'react';

// Easy Teaching logo - минималистичный текстовый логотип в едином дизайне
const Logo = ({ size = 40, withText = true }) => {
  return (
    <div className="easy-teaching-logo" style={{ display: 'flex', alignItems: 'center', gap: '10px', height: size }} aria-label="Easy Teaching logo">
      {withText && (
        <span style={{
          fontSize: '22px',
          fontWeight: '700',
          letterSpacing: '-0.5px',
          color: '#1e3a8a',
          fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
          whiteSpace: 'nowrap'
        }}>
          Easy Teaching
        </span>
      )}
    </div>
  );
};

export default Logo;
