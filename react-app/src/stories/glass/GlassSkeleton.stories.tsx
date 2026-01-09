import { Meta, StoryObj } from '@storybook/react';
import GlassSkeleton from '../../components/glass/GlassSkeleton';

const meta: Meta<typeof GlassSkeleton> = {
  title: 'Glass/Skeleton',
  component: GlassSkeleton,
  argTypes: {
    width: { control: { type: 'number', min: 24, max: 600, step: 4 } },
    height: { control: { type: 'number', min: 16, max: 200, step: 2 } },
    rounded: { control: 'boolean' },
  },
};
export default meta;

type Story = StoryObj<typeof GlassSkeleton>;

export const Basic: Story = { args: { width: 120, height: 24, rounded: true } };
