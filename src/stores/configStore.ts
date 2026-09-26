import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useGraphStore } from '@/stores/graphStore'
import { getNamelistValue, parseNamelist, unquoteNamelist, updateNamelistValue } from '@/lib/namelist'

export const useConfigStore = defineStore('config', () => {
  const graphStore = useGraphStore()
  const config = ref<Record<string, any>>({
    sf_surface_physics: 2, // Example configuration, not a WRF default
    mp_physics: 8,         // Thompson
    ra_lw_physics: 4,      // RRTMG
    ra_sw_physics: 4,      // RRTMG
    bl_pbl_physics: 1,     // YSU
    cu_physics: 1,         // Kain-Fritsch
    sf_sfclay_physics: 1   // Revised MM5
  })
  const namelistText = ref<string | null>(null)
  const activeDomain = ref(1)
  const parsedNamelist = computed(() => namelistText.value === null ? null : parseNamelist(namelistText.value))
  const maxDomain = computed(() => parsedNamelist.value?.maxDomain || 1)
  const physicsSuite = computed(() => unquoteNamelist(
    parsedNamelist.value ? getNamelistValue(parsedNamelist.value, 'physics', 'physics_suite') : undefined
  )?.toLowerCase())

  const setNamelistText = (text: string, resetDomain = true) => {
    namelistText.value = text
    if (resetDomain) activeDomain.value = 1
    else activeDomain.value = Math.min(activeDomain.value, parseNamelist(text).maxDomain)
  }

  const clearNamelist = () => {
    namelistText.value = null
    activeDomain.value = 1
  }

  const suiteSetting = (key: string) => physicsSuite.value
    ? graphStore.getSuiteSettings(physicsSuite.value).find(edge => edge.target === `namelist:${key}`)
    : undefined
  const registryDefault = (key: string) => graphStore.getNodeById(`namelist:${key}`)?.data?.default

  const getRawConfig = (key: string, domain = activeDomain.value) => parsedNamelist.value
    ? getNamelistValue(parsedNamelist.value, 'physics', key, domain)
    : undefined

  const getConfigOrigin = (key: string, domain = activeDomain.value): 'example' | 'namelist' | 'suite' | 'registry-default' | 'unresolved' => {
    if (!parsedNamelist.value) return 'example'
    const raw = getRawConfig(key, domain)
    if (raw !== undefined && raw.trim() !== '-1') return 'namelist'
    const defaultIsUnset = raw === '-1' || (raw === undefined && String(registryDefault(key)).trim() === '-1')
    if (defaultIsUnset && suiteSetting(key)?.data?.value != null) return 'suite'
    if (raw === undefined && registryDefault(key) !== undefined && Number(registryDefault(key)) >= 0) return 'registry-default'
    return 'unresolved'
  }

  const setConfig = (key: string, value: any) => {
    if (namelistText.value !== null) {
      namelistText.value = updateNamelistValue(namelistText.value, 'physics', key, activeDomain.value, String(value))
      return
    }
    config.value[key] = value
  }

  const getConfig = (key: string) => {
    if (parsedNamelist.value) {
      const raw = getRawConfig(key)
      if (raw !== undefined && raw.trim() !== '-1') {
        const numeric = Number(raw)
        return Number.isFinite(numeric) ? numeric : unquoteNamelist(raw)
      }
      const defaultValue = registryDefault(key)
      const defaultIsUnset = raw === '-1' || (raw === undefined && String(defaultValue).trim() === '-1')
      const suiteValue = defaultIsUnset ? suiteSetting(key)?.data?.value : undefined
      if (suiteValue !== undefined && suiteValue !== null) return Number(suiteValue)
      if (raw === undefined && defaultValue !== undefined && Number(defaultValue) >= 0) return Number(defaultValue)
      return undefined
    }
    return config.value[key]
  }

  const activePhysicsOptions = computed(() => {
    return Object.entries(config.value).filter(([k]) => k.includes('physics'))
  })

  return {
    config,
    namelistText,
    parsedNamelist,
    activeDomain,
    maxDomain,
    physicsSuite,
    setNamelistText,
    clearNamelist,
    getRawConfig,
    getConfigOrigin,
    setConfig,
    getConfig,
    activePhysicsOptions
  }
})
