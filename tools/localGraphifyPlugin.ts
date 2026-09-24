import { createHash } from 'node:crypto'
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import type { Plugin } from 'vite'

const projectRoot = path.resolve(__dirname, '..')
const defaultRoot = process.env.WRF_SOURCE_ROOT || 'E:\\QWRF\\WRF'
const indexPath = path.join(projectRoot, 'public', 'data', 'local', 'graphify-search.json')
const signatureFiles = ['main/wrf.F', 'Registry/Registry.EM_COMMON'] as const

type Job = {
  id: string
  state: 'idle' | 'running' | 'complete' | 'failed'
  folder: string
  message: string
  log: string
}

const isLoopback = (address: string | undefined) => Boolean(address && (
  address === '::1' || address === '::ffff:127.0.0.1' || /^127\./.test(address)
))

const isLocalHost = (host: string | undefined) => {
  if (!host) return false
  try {
    return ['localhost', '127.0.0.1', '[::1]'].includes(new URL(`http://${host}`).hostname)
  } catch {
    return false
  }
}

const fileDigest = (file: string) => createHash('sha256').update(fs.readFileSync(file)).digest('hex')

export const localGraphifyPlugin = (): Plugin => {
  let job: Job = { id: '', state: 'idle', folder: '', message: '', log: '' }

  return {
    name: 'local-graphify-runner',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use('/api/graphify', (req, res) => {
        const reply = (status: number, body: object) => {
          res.statusCode = status
          res.setHeader('Content-Type', 'application/json; charset=utf-8')
          res.setHeader('Cache-Control', 'no-store')
          res.end(JSON.stringify(body))
        }

        // Never expose a process-launching endpoint through a LAN-bound Vite server.
        if (!isLoopback(req.socket.remoteAddress) || !isLocalHost(req.headers.host)) {
          reply(403, { error: 'Graphify can only be started from this computer on localhost.' })
          return
        }

        if (req.method === 'GET' && req.url === '/status') {
          reply(200, { ...job, configuredRoot: defaultRoot })
          return
        }
        if (req.method !== 'POST' || req.url !== '/run') {
          reply(404, { error: 'Unknown Graphify endpoint.' })
          return
        }

        const origin = req.headers.origin
        let sameOrigin = false
        try { sameOrigin = Boolean(origin && new URL(origin).host === req.headers.host) } catch { /* Reject invalid Origin. */ }
        if (!sameOrigin || req.headers['content-type']?.split(';')[0] !== 'application/json') {
          reply(403, { error: 'Start Graphify from the local Atlas page.' })
          return
        }
        if (job.state === 'running') {
          reply(409, { error: 'An index is already running.' })
          return
        }

        let body = ''
        req.on('data', chunk => {
          body += chunk
          if (body.length > 4096) req.destroy()
        })
        req.on('end', () => {
          try {
            const input = JSON.parse(body) as { root?: unknown; folderName?: unknown; signatures?: Record<string, string> }
            if (typeof input.root !== 'string' || !path.isAbsolute(input.root) || typeof input.folderName !== 'string') {
              reply(400, { error: 'Enter the absolute path of the selected WRF folder.' })
              return
            }
            const root = fs.realpathSync(input.root)
            if (!fs.statSync(root).isDirectory() || path.basename(root).toLowerCase() !== input.folderName.toLowerCase()) {
              reply(400, { error: 'The server path does not name the selected WRF folder.' })
              return
            }
            if (!signatureFiles.every(file => {
              const candidate = path.join(root, file)
              return fs.statSync(candidate).isFile() && fileDigest(candidate) === input.signatures?.[file]
            })) {
              reply(409, { error: 'The selected browser folder and server path do not match. Enter that folder’s absolute path.' })
              return
            }

            const folder = path.basename(root)
            const scopeKey = createHash('sha256').update(root).digest('hex').slice(0, 12)
            const workDir = path.join(projectRoot, '.graphify-work', `local-${scopeKey}`)
            const temporaryIndex = path.join(projectRoot, 'public', 'data', 'local', `graphify-${scopeKey}.tmp`)
            const python = process.env.PYTHON || 'python'
            const args = [
              '-u', path.join(projectRoot, 'tools', 'graphify_pipeline.py'),
              '--wrf-root', root, '--work-dir', workDir, '--output', temporaryIndex,
            ]
            job = { id: `${Date.now()}`, state: 'running', folder, message: 'Starting Graphify…', log: '' }
            const child = spawn(python, args, { cwd: projectRoot, shell: false, windowsHide: true })
            const append = (chunk: Buffer) => {
              job.log = (job.log + chunk.toString()).slice(-6000)
              const lines = job.log.trim().split(/\r?\n/)
              job.message = lines.at(-1) || 'Indexing WRF source…'
            }
            child.stdout.on('data', append)
            child.stderr.on('data', append)
            child.on('error', error => {
              job = { ...job, state: 'failed', message: error.message }
            })
            child.on('close', code => {
              if (code === 0) {
                try {
                  fs.copyFileSync(temporaryIndex, indexPath)
                  fs.rmSync(temporaryIndex, { force: true })
                  job = { ...job, state: 'complete', message: `Indexed ${folder}.` }
                } catch (error) {
                  job = { ...job, state: 'failed', message: error instanceof Error ? error.message : 'Could not publish the local index.' }
                }
              } else if (job.state !== 'failed') {
                job = { ...job, state: 'failed', message: job.message || `Graphify exited with code ${code ?? 'unknown'}.` }
              }
              if (job.state === 'failed') fs.rmSync(temporaryIndex, { force: true })
            })
            reply(202, { ...job })
          } catch (error) {
            reply(400, { error: error instanceof Error ? error.message : 'Invalid WRF folder.' })
          }
        })
      })
    },
  }
}
