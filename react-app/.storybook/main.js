module.exports = {
  stories: ["../src/**/*.stories.@(js|jsx|ts|tsx)"],
  addons: [
    "@storybook/addon-essentials",
    // Ensure CRA Babel/Webpack config is applied for JSX/TSX
    "@storybook/preset-create-react-app",
  ],
  framework: {
    // Use the Webpack 5 framework package for Storybook 8
    name: "@storybook/react-webpack5",
    options: {},
  },
};