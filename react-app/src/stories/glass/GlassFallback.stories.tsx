import { Meta, StoryObj } from '@storybook/react';
import GlassCard from '../../components/glass/GlassCard';

const meta: Meta<typeof GlassCard> = {
  title: 'Glass/Fallback',
  component: GlassCard,
};
export default meta;

type Story = StoryObj<typeof GlassCard>;

export const NoBackdrop: Story = { render: () => <GlassCard><p>Fallback mode</p></GlassCard> };
