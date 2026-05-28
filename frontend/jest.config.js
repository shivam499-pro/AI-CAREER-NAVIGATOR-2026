process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';

const nextJest = require('next/jest')

const createJestConfig = nextJest({
  dir: './',
})

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  testEnvironmentOptions: {
    customExportConditions: [' '],
  },
  globals: {
    'process.env.NEXT_PUBLIC_API_URL': 'http://localhost:8000',
  },
}

module.exports = createJestConfig(customJestConfig)