import React, { useState } from 'react';
import { Meta, StoryObj } from '@storybook/react';
import GlassInput from '../../components/glass/GlassInput';

const meta: Meta<typeof GlassInput> = {
  title: 'Glass/Input',
  component: GlassInput,
  argTypes: {
    label: { control: 'text' },
    placeholder: { control: 'text' },
    error: { control: 'text' },
  },
};
export default meta;

type Story = StoryObj<typeof GlassInput>;

function InputStory(args: Partial<React.ComponentProps<typeof GlassInput>>) {
  const [v, setV] = useState('');
  return <GlassInput id="email" label={args.label ?? 'Email'} placeholder={args.placeholder} error={args.error} value={v} onChange={(e) => setV(e.target.value)} />;
}

export const Basic: Story = { args: { label: 'Email' }, render: (args) => <InputStory {...args} /> };

export const ErrorState: Story = { render: () => <GlassInput id="email" label="Email" value="" onChange={() => {}} error="Required" /> };
