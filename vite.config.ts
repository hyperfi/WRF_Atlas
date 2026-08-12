import { defineConfig, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import fs from 'fs'

const wrfSourcePlugin = (): Plugin => ({
  name: 'wrf-source-plugin',
  configureServer(server) {
    server.middlewares.use('/api/source', (req, res) => {
      try {
        const url = new URL(req.url || '', `http://${req.headers.host}`)
        const relPath = url.searchParams.get('file')
        if (!relPath) {
          res.statusCode = 400
          res.end('Missing file parameter')
          return
        }

        const wrfRoot = process.env.WRF_SOURCE_ROOT || 'E:\\QWRF\\WRF'
        const fullPath = path.resolve(wrfRoot, relPath)

        // Ensure path stays within WRF root
        if (!fullPath.startsWith(path.resolve(wrfRoot))) {
          res.statusCode = 403
          res.end('Access denied')
          return
        }

        if (fs.existsSync(fullPath) && fs.statSync(fullPath).isFile()) {
          res.setHeader('Content-Type', 'text/plain; charset=utf-8')
          fs.createReadStream(fullPath).pipe(res)
        } else {
          res.statusCode = 404
          res.end(`File not found: ${relPath}`)
        }
      } catch (e: any) {
        res.statusCode = 500
        res.end(`Server error: ${e.message}`)
      }
    })
  }
})

export default defineConfig({
  plugins: [vue(), wrfSourcePlugin()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
