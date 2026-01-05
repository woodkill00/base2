// React import not required with the new JSX transform
import { Meta, StoryObj } from '@storybook/react';
import GlassButton from '../../components/glass/GlassButton';

const meta: Meta<typeof GlassButton> = {
  title: 'Glass/Button',
  component: GlassButton,
  args: { children: 'Click me' },
  argTypes: {
    variant: {
      control: { type: 'radio' },
      options: ['primary', 'secondary', 'ghost'],
    },
    disabled: { control: 'boolean' },
    onClick: { action: 'clicked' },
  },
};
export default meta;

type Story = StoryObj<typeof GlassButton>;

export const Primary: Story = { args: { variant: 'primary' } };
export const Secondary: Story = { args: { variant: 'secondary' } };
export const Ghost: Story = { args: { variant: 'ghost' } };
