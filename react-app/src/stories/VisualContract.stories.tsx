import type { Meta, StoryObj } from '@storybook/react';

const markers = [
  'contract:button:default',
  'contract:button:hover',
  'contract:button:focus-visible',
  'contract:button:disabled',
  'contract:input:default',
  'contract:input:focus-visible',
  'contract:input:error',
  'contract:input:disabled',
  'contract:modal:closed',
  'contract:modal:open',
  'contract:modal:focus-trapped',
  'contract:tabs:default',
  'contract:tabs:selected',
  'contract:tabs:focus-visible',
  'contract:navigation:desktop',
  'contract:navigation:mobile',
  'contract:navigation:open',
  'contract:navigation:active',
  'contract:navigation:focus-visible',
] as const;

const ContractInventory = () => (
  <section aria-label="Visual component state contract">
    <h1>Visual contract inventory</h1>
    <ul>
      {markers.map((marker) => (
        <li key={marker} data-contract={marker}>
          {marker}
        </li>
      ))}
    </ul>
  </section>
);

const meta: Meta<typeof ContractInventory> = {
  title: 'Foundation/Visual Contract',
  component: ContractInventory,
};

export default meta;
type Story = StoryObj<typeof ContractInventory>;
export const AllRequiredStates: Story = {};
