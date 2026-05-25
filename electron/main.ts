import { app, BrowserWindow, ipcMain, dialog, shell } from 'electron'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { getFreePort, startPython, waitForReady, stopPython } from './pythonManager'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

let mainWindow: BrowserWindow | null = null
let pythonPort: number | null = null
let pythonReady = false

// --- IPC Handlers ---

ipcMain.handle('python:getPort', () => pythonPort)
ipcMain.handle('python:isReady', () => pythonReady)

ipcMain.handle('fs:selectDirectory', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory'],
  })
  if (result.canceled || result.filePaths.length === 0) return null
  return result.filePaths[0]
})

ipcMain.handle('fs:selectFile', async (_, filters?: { name: string; extensions: string[] }[]) => {
  const result = await dialog.showOpenDialog({
    properties: ['openFile'],
    filters: filters || [],
  })
  if (result.canceled || result.filePaths.length === 0) return null
  return result.filePaths[0]
})

ipcMain.handle('shell:openPath', async (_, p: string) => {
  return shell.openPath(p)
})

ipcMain.handle('app:getVersion', () => app.getVersion())
ipcMain.handle('app:getDataPath', () => app.getPath('userData'))
ipcMain.handle('app:isDev', () => !app.isPackaged)

// --- App Lifecycle ---

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 600,
    title: 'NiuQI2D',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  // Remove default menu bar
  mainWindow.setMenuBarVisibility(false)

  if (!app.isPackaged) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.on('window-all-closed', () => {
  app.quit()
})

app.on('before-quit', async () => {
  await stopPython()
})

app.whenReady().then(async () => {
  createWindow()

  try {
    pythonPort = await getFreePort()
    console.log(`[Main] Starting Python on port ${pythonPort}`)
    await startPython(pythonPort)
    await waitForReady(pythonPort)
    pythonReady = true
    console.log('[Main] Python backend is ready')
    // Notify renderer that backend is ready
    mainWindow?.webContents.send('python:ready', pythonPort)
  } catch (err) {
    console.error('[Main] Failed to start Python backend:', err)
  }
})
