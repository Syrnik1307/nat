import React from 'react';

const TeacherIcon = () => (
  <svg
    width="48"
    height="48"
    viewBox="0 0 48 48"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    {/* Голова */}
    <circle cx="24" cy="14" r="6" fill="#2563eb" />
    
    {/* Туловище */}
    <path
      d="M24 20C19 20 15 23 15 27V38H33V27C33 23 29 20 24 20Z"
      fill="#2563eb"
    />
    
    {/* Рубашка/галстук */}
    <rect x="22" y="24" width="4" height="8" fill="#1d4ed8" />
    
    {/* Левая рука */}
    <path
      d="M15 24C12 24 10 26 10 28V35C10 36 9 37 8 37"
      stroke="#2563eb"
      strokeWidth="2.5"
      strokeLinecap="round"
    />
    
    {/* Правая рука с указкой */}
    <path
      d="M33 24C36 24 38 26 38 28V35C38 36 39 37 40 37"
      stroke="#2563eb"
      strokeWidth="2.5"
      strokeLinecap="round"
    />
    
    {/* Указка */}
    <line x1="36" y1="28" x2="42" y2="20" stroke="#fbbf24" strokeWidth="2" strokeLinecap="round" />
    <circle cx="42" cy="20" r="1.5" fill="#fbbf24" />
  </svg>
);

export default TeacherIcon;
