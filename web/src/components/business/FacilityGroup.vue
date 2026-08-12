<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getDicts } from '@/api/dict'
import type { DictItem } from '@/types'
import { facilityMap } from '@/utils/dictMaps'

const props = defineProps<{
  facilities: string[]
}>()

const groupLabels = ref<Record<string, string>>({})
const loading = ref(false)

function getFacilityGroup(code: string): string {
  const groupMap: Record<string, string> = {
    air_conditioner: 'basic',
    washing_machine: 'basic',
    refrigerator: 'basic',
    water_heater: 'basic',
    wifi: 'basic',
    tv: 'basic',
    bed: 'basic',
    wardrobe: 'basic',
    desk: 'basic',
    sofa: 'basic',
    private_bathroom: 'bathroom',
    broadband: 'basic',
    kitchen: 'kitchen',
    balcony: 'public',
    elevator: 'public',
    parking: 'public',
    gym: 'public',
  }
  return groupMap[code] || 'basic'
}

function getFacilityLabel(code: string): string {
  return facilityMap[code] || code
}

const groupedFacilities = computed(() => {
  const groups: Record<string, string[]> = {}
  for (const f of props.facilities) {
    const group = getFacilityGroup(f)
    if (!groups[group]) {
      groups[group] = []
    }
    groups[group].push(f)
  }
  const order = ['basic', 'bathroom', 'kitchen', 'public']
  return order.filter(g => groups[g]).map(g => ({
    group: g,
    groupLabel: groupLabels.value[g] || g,
    facilities: groups[g].map(f => ({ code: f, label: getFacilityLabel(f) })),
  }))
})

async function fetchGroupLabels() {
  loading.value = true
  try {
    const items: DictItem[] = await getDicts('facility_group')
    const map: Record<string, string> = {}
    for (const item of items) {
      map[item.code] = item.label
    }
    groupLabels.value = map
  } catch {
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchGroupLabels()
})
</script>

<template>
  <div v-if="facilities.length > 0" class="bg-white p-4 mt-3">
    <h2 class="text-base font-bold text-gray-900 mb-3">配套设施</h2>

    <div v-if="loading" class="py-4 text-center text-sm text-gray-400">加载中...</div>

    <template v-else>
      <div v-for="group in groupedFacilities" :key="group.group" class="mb-3 last:mb-0">
        <div class="text-xs text-gray-400 mb-2">{{ group.groupLabel }}</div>
        <div class="flex flex-wrap gap-2">
          <van-tag
            v-for="fac in group.facilities"
            :key="fac.code"
            type="primary"
            size="medium"
          >{{ fac.label }}</van-tag>
        </div>
      </div>
    </template>
  </div>
</template>
