import { Meta, StoryObj } from '@storybook/react';
import { userEvent, within, expect } from '@storybook/test';
import ThemeToggle from '../components/glass/ThemeToggle';

const meta: Meta<typeof ThemeToggle> = {
  title: 'Glass/ThemeToggle',
  component: ThemeToggle,
};
export default meta;

type Story = StoryObj<typeof ThemeToggle>;

export const Default: Story = {
  render: () => <ThemeToggle />,
  play: async ({ canvasElement }) => {
    const c = within(canvasElement);
    const button = await c.findByRole('button');
    await userEvent.click(button);
    // Verify that dark class is applied on toggle
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  },
};
