import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    target: 'esnext', // Support top-level await for @novnc/novnc
    modulePreload: {
      polyfill: false
    }
  }
});
