import React, { useState } from 'react';
import { Meta, StoryObj } from '@storybook/react';
import { userEvent, within, expect } from '@storybook/test';
import GlassTabs from '../../components/glass/GlassTabs';

const meta: Meta<typeof GlassTabs> = {
  title: 'Glass/Tabs',
  component: GlassTabs,
};
export default meta;

type Story = StoryObj<typeof GlassTabs>;

function TabsStory() {
  const tabs = [
    { id: 'one', label: 'One' },
    { id: 'two', label: 'Two' },
  ];
  const [active, setActive] = useState('one');
  return <GlassTabs tabs={tabs} activeTab={active} onChange={setActive} />;
}

export const Basic: Story = { render: () => <TabsStory /> };

export const KeyboardNavigation: Story = {
  render: () => <TabsStory />,
  play: async ({ canvasElement }) => {
    const c = within(canvasElement);
    const tabs = await c.getAllByRole('tab');
    await userEvent.click(tabs[0]);
    await userEvent.keyboard('{ArrowRight}');
    // Expect second tab selected
    expect(tabs[1]).toHaveAttribute('aria-selected', 'true');
  },
};
