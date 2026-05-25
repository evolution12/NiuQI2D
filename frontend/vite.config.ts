import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import electron from 'vite-plugin-electron'
import renderer from 'vite-plugin-electron-renderer'
import path from 'node:path'

const isElectron = !!process.env.ELECTRON

export default defineConfig({
  plugins: [
    react(),
    ...(isElectron
      ? [
          electron([
            {
              entry: path.resolve(__dirname, '../electron/main.ts'),
              vite: {
                build: {
                  outDir: path.resolve(__dirname, '../dist-electron'),
                },
              },
            },
            {
              entry: path.resolve(__dirname, '../electron/preload.ts'),
              onstart({ reload }) {
                reload()
              },
              vite: {
                build: {
                  outDir: path.resolve(__dirname, '../dist-electron'),
                  lib: {
                    entry: path.resolve(__dirname, '../electron/preload.ts'),
                    formats: ['cjs'],
                    fileName: () => '[name].js',
                  },
                },
              },
            },
          ]),
          renderer(),
        ]
      : []),
  ],
})
