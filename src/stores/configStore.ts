import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useConfigStore = defineStore('config', () => {
  const config = ref<Record<string, any>>({
    sf_surface_physics: 2, // Default Noah LSM
    mp_physics: 8,         // Thompson
    ra_lw_physics: 4,      // RRTMG
    ra_sw_physics: 4,      // RRTMG
    bl_pbl_physics: 1,     // YSU
    cu_physics: 1,         // Kain-Fritsch
    sf_sfclay_physics: 1   // Revised MM5
  })

  const setConfig = (key: string, value: any) => {
    config.value[key] = value
  }

  const getConfig = (key: string) => {
    return config.value[key]
  }

  const activePhysicsOptions = computed(() => {
    return Object.entries(config.value).filter(([k]) => k.includes('physics'))
  })

  return {
    config,
    setConfig,
    getConfig,
    activePhysicsOptions
  }
})
