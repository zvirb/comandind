const { defineConfig } = require('cypress')

module.exports = defineConfig({
  projectId: 'aiwfe-webui',
  viewportWidth: 1920,
  viewportHeight: 1080,
  env: {
    TEST_USERNAME: process.env.TEST_USERNAME,
    TEST_PASSWORD: process.env.TEST_PASSWORD,
    TEST_2FA_TOKEN: process.env.TEST_2FA_TOKEN
  },
  experimentalStudio: true,
  e2e: {
    baseUrl: 'https://aiwfe.com',
    specPattern: 'src/tests/e2e/**/*.spec.js',
    supportFile: 'src/tests/support/index.js'
  },
  component: {
    devServer: {
      framework: 'react',
      bundler: 'webpack'
    }
  }
})