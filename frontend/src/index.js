import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const BUILD_STAMP = '2025-12-06T00:30Z';
if (typeof console !== 'undefined') {
  console.info('Frontend build', BUILD_STAMP);
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
