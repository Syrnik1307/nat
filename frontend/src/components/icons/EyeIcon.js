import React from 'react';

const EyeIcon = ({ open = false }) => (
  <svg
    width="22"
    height="22"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M2.25 12C3.98 7.96 7.71 5 12 5C16.29 5 20.02 7.96 21.75 12C20.02 16.04 16.29 19 12 19C7.71 19 3.98 16.04 2.25 12Z"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    {open ? (
      <>
        <circle
          cx="12"
          cy="12"
          r="3.2"
          stroke="currentColor"
          strokeWidth="1.6"
        />
        <circle cx="12" cy="12" r="1.2" fill="currentColor" />
      </>
    ) : (
      <>
        <path
          d="M9.5 9.5C8.55 10.45 8 11.67 8 13"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
        <path
          d="M16 11C16 9.62 15.18 8.38 13.95 7.77"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
        <path
          d="M4 4L20 20"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
      </>
    )}
  </svg>
);

export default EyeIcon;
