import React from 'react';

// Lectio Space logo - Premium SaaS брендинг
const Logo = ({ size = 40, withText = true }) => {
  return (
    <div className="lectio-space-logo" style={{ display: 'flex', alignItems: 'center', gap: '10px', height: size }} aria-label="Lectio Space logo">
      {withText && (
        <span style={{
          fontSize: '22px',
          fontWeight: '800', /* ExtraBold */
          fontStyle: 'italic',
          letterSpacing: '-0.02em', /* Tight, professional */
          fontFamily: "'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif",
          whiteSpace: 'nowrap'
        }}>
          <span style={{ color: '#4F46E5' }}>Easy</span>
          {' '}
          <span style={{ color: '#1E293B' }}>Teaching</span>
        </span>
      )}
    </div>
  );
};

export default Logo;
