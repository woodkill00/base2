module.exports = {
  stories: ['../src/**/*.stories.@(js|jsx|ts|tsx)'],
  addons: ['@storybook/addon-essentials'],
  framework: {
    name: '@storybook/react-vite',
    options: {},
  },
  viteFinal(config) {
    // The production budget measures the shipped application, not Storybook's
    // documentation runtime and manager dependencies.
    config.plugins = (config.plugins || []).filter(
      (plugin) => plugin && plugin.name !== 'base2-performance-budget'
    );
    return config;
  },
};
