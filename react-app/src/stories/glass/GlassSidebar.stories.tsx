import React from 'react';
import type { Meta, StoryObj } from '@storybook/react';

import GlassSidebar from '../../components/glass/GlassSidebar';

const meta: Meta<typeof GlassSidebar> = {
  title: 'Glass/Sidebar',
  component: GlassSidebar,
};
export default meta;

type Story = StoryObj<typeof GlassSidebar>;

function setMatchMedia(matches: boolean) {
  window.matchMedia = ((query: string) =>
    ({
      matches,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList);
}

export const DesktopOpen: Story = {
  render: () => {
    setMatchMedia(false);
    return <GlassSidebar id="sb" isOpen />;
  },
};

export const DesktopClosed: Story = {
  render: () => {
    setMatchMedia(false);
    return <GlassSidebar id="sb" isOpen={false} />;
  },
};

export const MobileOpen: Story = {
  render: () => {
    setMatchMedia(true);
    return <GlassSidebar isOpen />;
  },
};

export const MobileClosed: Story = {
  render: () => {
    setMatchMedia(true);
    return <GlassSidebar isOpen={false} />;
  },
};
