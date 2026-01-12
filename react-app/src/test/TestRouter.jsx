import React from 'react';
import { MemoryRouter } from 'react-router-dom';

/**
 * Test-only router wrapper that opts into React Router v7 future flags.
 * Use in tests to remove deprecation warnings while preserving production behavior.
 */
const TestRouter = ({ children }) => (
  <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    {children}
  </MemoryRouter>
);

export default TestRouter;
