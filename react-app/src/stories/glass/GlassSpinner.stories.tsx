import { Meta, StoryObj } from '@storybook/react';
import GlassSpinner from '../../components/glass/GlassSpinner';

const meta: Meta<typeof GlassSpinner> = {
  title: 'Glass/Spinner',
  component: GlassSpinner,
  argTypes: {
    size: {
      control: { type: 'radio' },
      options: ['sm', 'md', 'lg'],
    },
  },
};
export default meta;

type Story = StoryObj<typeof GlassSpinner>;

export const Small: Story = { args: { size: 'sm' } };
export const Medium: Story = { args: { size: 'md' } };
export const Large: Story = { args: { size: 'lg' } };
