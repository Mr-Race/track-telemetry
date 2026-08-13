import { execSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The product version lives in a single root VERSION file, not in
// package.json - the Python side ships from the same repo and has no
// package.json to read.
const version = readFileSync(new URL('../VERSION', import.meta.url), 'utf8').trim()

// The short commit is what actually answers "which build am I looking
// at" - a version alone can't distinguish two deploys of the same
// release. Falls back gracefully: a build from a tarball with no git
// history should not fail.
function commit(): string {
  try {
    return execSync('git rev-parse --short HEAD', { encoding: 'utf8' }).trim()
  } catch {
    return 'unknown'
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(version),
    __APP_COMMIT__: JSON.stringify(commit()),
  },
  server: {
    // Mirrors the same-origin /api/* proxy Azure Static Web Apps provides
    // in production for a linked Function App backend.
    proxy: {
      '/api': 'http://localhost:7071',
    },
  },
})
