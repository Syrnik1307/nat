import React from 'react';

const StudentIcon = () => (
  <svg
    width="48"
    height="48"
    viewBox="0 0 48 48"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    {/* Шапка */}
    <path
      d="M24 8L8 16V18C8 22.4 10.8 26.2 15 28.2V32C15 33.1 15.9 34 17 34H31C32.1 34 33 33.1 33 32V28.2C37.2 26.2 40 22.4 40 18V16L24 8Z"
      fill="#2563eb"
    />
    
    {/* Лицо */}
    <circle cx="24" cy="20" r="3" fill="white" />
    
    {/* Глаза */}
    <circle cx="20" cy="18" r="1.2" fill="white" />
    <circle cx="28" cy="18" r="1.2" fill="white" />
    
    {/* Улыбка */}
    <path
      d="M21 22C22 23 23 23.5 24 23.5C25 23.5 26 23 27 22"
      stroke="white"
      strokeWidth="1"
      strokeLinecap="round"
    />
  </svg>
);

export default StudentIcon;
