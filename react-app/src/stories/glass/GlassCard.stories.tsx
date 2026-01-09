import { Meta, StoryObj } from '@storybook/react';
import GlassCard from '../../components/glass/GlassCard';

const meta: Meta<typeof GlassCard> = {
  title: 'Glass/Card',
  component: GlassCard,
  argTypes: {
    variant: {
      control: { type: 'radio' },
      options: ['default', 'elevated', 'subtle'],
    },
    interactive: { control: 'boolean' },
  },
};
export default meta;

type Story = StoryObj<typeof GlassCard>;

export const Default: Story = { args: { variant: 'default', children: <p>Content</p> } };
export const Elevated: Story = { args: { variant: 'elevated', children: <p>Content</p> } };
export const Subtle: Story = { args: { variant: 'subtle', children: <p>Content</p> } };
