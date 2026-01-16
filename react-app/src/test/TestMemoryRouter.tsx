import React from 'react';
import { MemoryRouter, type MemoryRouterProps } from 'react-router-dom';

const FUTURE_FLAGS: NonNullable<MemoryRouterProps['future']> = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
};

export default function TestMemoryRouter({ future, ...props }: MemoryRouterProps) {
  return <MemoryRouter {...props} future={{ ...FUTURE_FLAGS, ...future }} />;
}
