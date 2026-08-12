import { computed, ref, shallowRef } from 'vue'
import { defineStore } from 'pinia'

type PermissionState = 'granted' | 'denied' | 'prompt'

interface AtlasFileHandle {
  kind: 'file'
  getFile(): Promise<File>
}

interface AtlasDirectoryHandle {
  kind: 'directory'
  name: string
  getDirectoryHandle(name: string): Promise<AtlasDirectoryHandle>
  getFileHandle(name: string): Promise<AtlasFileHandle>
  queryPermission(options?: { mode: 'read' }): Promise<PermissionState>
  requestPermission(options?: { mode: 'read' }): Promise<PermissionState>
}

interface DirectoryPickerWindow extends Window {
  showDirectoryPicker?: (options?: { id?: string; mode?: 'read' }) => Promise<AtlasDirectoryHandle>
}

const DB_NAME = 'wrf-atlas-local-source'
const STORE_NAME = 'handles'
const HANDLE_KEY = 'wrf-root'

const openHandleDatabase = () => new Promise<IDBDatabase>((resolve, reject) => {
  const request = indexedDB.open(DB_NAME, 1)
  request.onupgradeneeded = () => {
    if (!request.result.objectStoreNames.contains(STORE_NAME)) {
      request.result.createObjectStore(STORE_NAME)
    }
  }
  request.onsuccess = () => resolve(request.result)
  request.onerror = () => reject(request.error)
})

const loadSavedHandle = async () => {
  const db = await openHandleDatabase()
  return new Promise<AtlasDirectoryHandle | undefined>((resolve, reject) => {
    const request = db.transaction(STORE_NAME, 'readonly').objectStore(STORE_NAME).get(HANDLE_KEY)
    request.onsuccess = () => resolve(request.result as AtlasDirectoryHandle | undefined)
    request.onerror = () => reject(request.error)
    request.transaction.oncomplete = () => db.close()
  })
}

const saveHandle = async (handle: AtlasDirectoryHandle | null) => {
  const db = await openHandleDatabase()
  return new Promise<void>((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, 'readwrite')
    const store = transaction.objectStore(STORE_NAME)
    if (handle) store.put(handle, HANDLE_KEY)
    else store.delete(HANDLE_KEY)
    transaction.oncomplete = () => { db.close(); resolve() }
    transaction.onerror = () => { db.close(); reject(transaction.error) }
  })
}

const validateWrfRoot = async (handle: AtlasDirectoryHandle) => {
  try {
    await handle.getDirectoryHandle('Registry')
    await handle.getDirectoryHandle('main')
  } catch {
    throw new Error('Choose the WRF repository root containing the Registry and main folders.')
  }
}

export const useLocalSourceStore = defineStore('localSource', () => {
  const directoryHandle = shallowRef<AtlasDirectoryHandle | null>(null)
  const folderName = ref('')
  const error = ref<string | null>(null)
  const restoring = ref(false)
  const supported = typeof window !== 'undefined' && Boolean((window as DirectoryPickerWindow).showDirectoryPicker)
  const connected = computed(() => directoryHandle.value !== null)

  const restore = async () => {
    if (!supported || restoring.value || directoryHandle.value) return
    restoring.value = true
    try {
      const saved = await loadSavedHandle()
      if (saved && await saved.queryPermission({ mode: 'read' }) === 'granted') {
        await validateWrfRoot(saved)
        directoryHandle.value = saved
        folderName.value = saved.name
      }
    } catch {
      // A stale or unavailable handle is harmless; the user can choose again.
    } finally {
      restoring.value = false
    }
  }

  const chooseFolder = async () => {
    error.value = null
    const picker = (window as DirectoryPickerWindow).showDirectoryPicker
    if (!picker) {
      error.value = 'Direct folder access requires a Chromium browser on localhost or HTTPS.'
      return false
    }
    try {
      const handle = await picker({ id: 'wrf-source-root', mode: 'read' })
      await validateWrfRoot(handle)
      const permission = await handle.requestPermission({ mode: 'read' })
      if (permission !== 'granted') throw new Error('Read permission was not granted.')
      directoryHandle.value = handle
      folderName.value = handle.name
      await saveHandle(handle)
      return true
    } catch (cause: any) {
      if (cause?.name !== 'AbortError') error.value = cause?.message || 'Could not open the selected folder.'
      return false
    }
  }

  const disconnect = async () => {
    directoryHandle.value = null
    folderName.value = ''
    error.value = null
    await saveHandle(null)
  }

  const readTextFile = async (relativePath: string) => {
    const root = directoryHandle.value
    if (!root) throw new Error('No local WRF folder is connected.')
    const parts = relativePath.replaceAll('\\', '/').split('/').filter(Boolean)
    if (!parts.length || parts.some(part => part === '..')) throw new Error('Invalid source path.')
    let directory = root
    for (const part of parts.slice(0, -1)) directory = await directory.getDirectoryHandle(part)
    const fileHandle = await directory.getFileHandle(parts.at(-1)!)
    return (await fileHandle.getFile()).text()
  }

  return { connected, directoryHandle, folderName, error, restoring, supported, restore, chooseFolder, disconnect, readTextFile }
})
