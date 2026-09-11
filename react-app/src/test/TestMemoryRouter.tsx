import React from 'react';
import { MemoryRouter, type MemoryRouterProps } from 'react-router-dom';

export default function TestMemoryRouter(props: MemoryRouterProps) {
  return <MemoryRouter {...props} />;
}
