import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import { ensureBackdropSupport } from './services/glass/supports';
import App from './App';

ensureBackdropSupport();
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
