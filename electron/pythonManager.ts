import { app } from 'electron'
import { spawn, ChildProcess } from 'node:child_process'
import net from 'node:net'
import path from 'node:path'
import http from 'node:http'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

let pythonProcess: ChildProcess | null = null

export function getFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.listen(0, '127.0.0.1', () => {
      const addr = server.address() as net.AddressInfo
      server.close(() => resolve(addr.port))
    })
    server.on('error', reject)
  })
}

function findPythonExe(): { cmd: string; args: string[] } {
  if (app.isPackaged) {
    return {
      cmd: path.join(process.resourcesPath, 'niuqi2d-backend.exe'),
      args: [],
    }
  }
  // Dev: use venv python
  const venvPython = path.resolve(__dirname, '../python/.venv/Scripts/python.exe')
  return {
    cmd: venvPython,
    args: ['-m', 'fastapi_app'],
  }
}

export async function startPython(port: number): Promise<void> {
  const { cmd, args } = findPythonExe()
  const fullArgs = [...args, '--host', '127.0.0.1', '--port', String(port)]

  const env = {
    ...process.env,
    NIUQI2D_PORT: String(port),
    NIUQI2D_HOST: '127.0.0.1',
  } as Record<string, string>

  if (!app.isPackaged) {
    env.NIUQI2D_DEV = '1'
  } else {
    env.NIUQI2D_DATA_DIR = app.getPath('userData')
  }

  pythonProcess = spawn(cmd, fullArgs, {
    env,
    cwd: path.resolve(__dirname, '../python'),
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  })

  pythonProcess.stdout?.on('data', (data: Buffer) => {
    console.log(`[Python] ${data.toString().trimEnd()}`)
  })
  pythonProcess.stderr?.on('data', (data: Buffer) => {
    console.error(`[Python] ${data.toString().trimEnd()}`)
  })

  pythonProcess.on('error', (err) => {
    console.error('[Python] Failed to start:', err)
  })

  pythonProcess.on('exit', (code) => {
    console.log(`[Python] Exited with code ${code}`)
    pythonProcess = null
  })
}

export function waitForReady(port: number, timeoutMs = 30000): Promise<void> {
  const start = Date.now()
  return new Promise((resolve, reject) => {
    const check = () => {
      if (Date.now() - start > timeoutMs) {
        reject(new Error(`Python backend did not become ready within ${timeoutMs}ms`))
        return
      }
      const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
        if (res.statusCode === 200) {
          resolve()
        } else {
          setTimeout(check, 500)
        }
      })
      req.on('error', () => {
        setTimeout(check, 500)
      })
      req.setTimeout(2000, () => {
        req.destroy()
        setTimeout(check, 500)
      })
    }
    // Give Python a moment to start before first check
    setTimeout(check, 1000)
  })
}

export function stopPython(): Promise<void> {
  return new Promise((resolve) => {
    if (!pythonProcess) {
      resolve()
      return
    }
    const pid = pythonProcess.pid
    pythonProcess.on('exit', () => resolve())
    try {
      // On Windows, use taskkill to kill the process tree
      if (process.platform === 'win32') {
        spawn('taskkill', ['/pid', String(pid), '/T', '/F'], { stdio: 'ignore' })
      } else {
        process.kill(pid!, 'SIGTERM')
      }
    } catch {
      // Process already dead
      resolve()
      return
    }
    // Force kill after 5 seconds (non-Windows fallback)
    if (process.platform !== 'win32') {
      setTimeout(() => {
        try {
          process.kill(pid!, 'SIGKILL')
        } catch {
          // Already dead
        }
        resolve()
      }, 5000)
    }
  })
}
