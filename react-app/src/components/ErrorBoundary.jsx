import React from 'react';
import { siteManifest } from '../config/siteRuntime';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div role="alert" style={{ padding: 24 }}>
          <h1>{siteManifest.name} encountered a problem</h1>
          <p>Please try refreshing the page. If the problem persists, contact support.</p>
          <a href="/">Return home</a>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
