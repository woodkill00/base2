import React from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import AppShell from '../components/glass/AppShell';
import GlassCard from '../components/glass/GlassCard';

const meta: Meta<typeof AppShell> = {
  title: 'App/AppShell',
  component: AppShell,
  parameters: {
    layout: 'fullscreen',
  },
  argTypes: {
    headerTitle: { control: 'text' },
    sidebarItems: { control: 'object' },
  },
};

export default meta;
type Story = StoryObj<typeof AppShell>;

export const Default: Story = {
  args: {
    headerTitle: 'App Shell',
    sidebarItems: ['Home', 'Dashboard', 'Settings', 'Users', 'Help'],
  },
  render: ({ headerTitle, sidebarItems }) => (
    <AppShell headerTitle={headerTitle} sidebarItems={sidebarItems as string[]}>
      <div style={{ padding: 16, display: 'grid', gap: 16 }}>
        {[0, 1].map((_, i) => (
          <GlassCard key={i}>
            <h3>{i === 0 ? 'Welcome' : 'Content Area'}</h3>
            <p>
              {i === 0
                ? 'This is a calc-driven App Shell using glass components.'
                : 'Resize the viewport to observe sidebar width bounds (320–400px) and content height via calc.'}
            </p>
          </GlassCard>
        ))}
      </div>
    </AppShell>
  ),
};
