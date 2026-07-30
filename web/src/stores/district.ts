import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getDistricts } from '@/api/dict'
import type { District } from '@/types'

export const useDistrictStore = defineStore(
  'district',
  () => {
    // 行政区 id -> name 映射
    const districtMap = ref<Record<number, string>>({})
    // 街道 id -> name 映射
    const streetMap = ref<Record<number, string>>({})
    // 是否已加载
    const loaded = ref(false)
    // 加载中
    const loading = ref(false)

    const getDistrictName = computed(() => {
      return (id?: number | null) => {
        if (id == null) return '-'
        return districtMap.value[id] || '-'
      }
    })

    const getStreetName = computed(() => {
      return (id?: number | null) => {
        if (id == null) return '-'
        return streetMap.value[id] || '-'
      }
    })

    async function loadDistricts() {
      if (loaded.value || loading.value) return
      loading.value = true
      try {
        // 1. 获取所有行政区（level=1）
        const districts = await getDistricts({ level: 1 })
        const dMap: Record<number, string> = {}
        districts.forEach((d: District) => {
          dMap[d.id] = d.name
        })
        districtMap.value = dMap

        // 2. 遍历每个行政区，分别获取下属街道（level=2 & parent_id）
        const sMap: Record<number, string> = {}
        const streetPromises = districts.map((d: District) =>
          getDistricts({ level: 2, parent_id: d.id }).then((streets: District[]) => {
            streets.forEach((s: District) => {
              sMap[s.id] = s.name
            })
          })
        )
        await Promise.all(streetPromises)
        streetMap.value = sMap
        loaded.value = true
      } catch {
        // 错误已在 request 拦截器中 toast
      } finally {
        loading.value = false
      }
    }

    function reset() {
      districtMap.value = {}
      streetMap.value = {}
      loaded.value = false
      loading.value = false
    }

    return {
      districtMap,
      streetMap,
      loaded,
      loading,
      getDistrictName,
      getStreetName,
      loadDistricts,
      reset,
    }
  },
  {
    persist: true,
  }
)
