import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  python: {
    getPort: () => ipcRenderer.invoke('python:getPort'),
    isReady: () => ipcRenderer.invoke('python:isReady'),
  },
  fs: {
    selectDirectory: () => ipcRenderer.invoke('fs:selectDirectory'),
    selectFile: (filters?: { name: string; extensions: string[] }[]) =>
      ipcRenderer.invoke('fs:selectFile', filters),
  },
  shell: {
    openPath: (path: string) => ipcRenderer.invoke('shell:openPath', path),
  },
  app: {
    getVersion: () => ipcRenderer.invoke('app:getVersion'),
    getDataPath: () => ipcRenderer.invoke('app:getDataPath'),
    isDev: () => ipcRenderer.invoke('app:isDev'),
  },
})
