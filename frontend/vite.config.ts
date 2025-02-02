import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import wasmPlugin from 'vite-plugin-wasm';

import { visualizer } from 'rollup-plugin-visualizer';

// https://vitejs.dev/config/
export default defineConfig({
  base: "./",
  plugins: [
    vue(),
    wasmPlugin()
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    target: ['es2022', 'edge89', 'firefox89', 'chrome89', 'safari15'],
    rollupOptions: {
      plugins: [
        visualizer(),
      ],
      output: {
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith('.css')) return 'assets/css/style.[hash].css';
          return assetInfo.name && assetInfo.name.endsWith('.svg')
            ? 'assets/img/[name].[hash].[ext]'
            : 'assets/[name].[hash].[ext]';
        },
        chunkFileNames: 'assets/js/[name].[hash].js',
        entryFileNames: 'assets/js/[name].[hash].js',
        manualChunks: {
          'vendor': ['vue', 'pinia', 'vue-router' ],
          'third-party': [
            'tiktoken', 
            'localforage', 
            'markdown-it',
            'floating-vue',
            'dompurify',
            'highlight.js',
            '@fortawesome/fontawesome-svg-core', 
            '@fortawesome/free-regular-svg-icons', 
            '@fortawesome/free-solid-svg-icons', 
            '@fortawesome/vue-fontawesome'
          ],
          'tiktoken-assets': ['@/assets/claude.json']
        },
      },  
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173
  },
  define: {
    'process.env': {},
    // VITE_API_BASE_URL: process.env.VITE_API_BASE_URL
  }
})

