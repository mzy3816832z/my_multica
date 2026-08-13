<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getNearbyPOIs } from '@/api/apartment'
import type { NearbyPOI } from '@/types'

const props = defineProps<{
  apartmentId: number
  longitude: number | null
  latitude: number | null
}>()

const pois = ref<NearbyPOI[]>([])
const staticMapUrl = ref('')
const loading = ref(false)

const groupedPois = ref<Record<string, NearbyPOI[]>>({
  '地铁站': [],
  '公交站': [],
  '超市/便利店': [],
})

async function fetchNearby() {
  if (props.longitude == null || props.latitude == null) return

  loading.value = true
  try {
    const data = await getNearbyPOIs(props.apartmentId)
    pois.value = data.pois || []
    staticMapUrl.value = data.static_map_url || ''

    const groups: Record<string, NearbyPOI[]> = {
      '地铁站': [],
      '公交站': [],
      '超市/便利店': [],
    }
    for (const p of pois.value) {
      if (groups[p.type]) {
        groups[p.type].push(p)
      }
    }
    groupedPois.value = groups
  } catch {
    pois.value = []
  } finally {
    loading.value = false
  }
}

function formatDistance(meters: number): string {
  if (meters >= 1000) {
    return (meters / 1000).toFixed(1) + 'km'
  }
  return meters + 'm'
}

function openFullMap() {
  if (props.longitude != null && props.latitude != null) {
    const url = `https://uri.amap.com/marker?position=${props.longitude},${props.latitude}&name=房源位置`
    window.open(url, '_blank')
  }
}

onMounted(() => {
  if (props.longitude != null && props.latitude != null) {
    fetchNearby()
  }
})
</script>

<template>
  <div v-if="longitude != null && latitude != null" class="location-module bg-white mt-3 p-4">
    <h2 class="text-base font-bold text-gray-900 mb-3">位置及周边</h2>

    <div
      v-if="staticMapUrl"
      class="static-map mb-3 rounded-lg overflow-hidden cursor-pointer"
      @click="openFullMap"
    >
      <van-image
        :src="staticMapUrl"
        fit="cover"
        class="w-full h-full"
        alt="位置地图"
      />
      <div class="map-overlay">
        <span class="text-xs">点击查看大地图</span>
      </div>
    </div>
    <div v-else-if="loading" class="py-4 text-center">
      <van-loading size="20px" />
      <span class="text-sm text-gray-400 ml-2">加载周边信息...</span>
    </div>

    <div v-if="pois.length > 0" class="poi-list">
      <div
        v-for="(items, typeName) in groupedPois"
        :key="typeName"
      >
        <div v-if="items.length > 0" class="poi-group mb-3">
          <div class="text-sm font-medium text-gray-700 mb-2">
            <van-icon :name="typeName === '地铁站' ? 'guide-o' : typeName === '公交站' ? 'bus-o' : 'shop-o'" class="mr-1" />
            {{ typeName }}
          </div>
          <div class="space-y-1">
            <div
              v-for="(poi, idx) in items"
              :key="idx"
              class="flex items-center justify-between text-sm"
            >
              <span class="text-gray-600 truncate flex-1 mr-2">{{ poi.name }}</span>
              <span class="text-gray-400 text-xs flex-shrink-0">{{ formatDistance(poi.distance) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-else-if="!loading" class="text-sm text-gray-400 py-2">
      暂无周边信息
    </div>
  </div>
</template>

<style scoped lang="scss">
.location-module {
  border-radius: 0;
}

.static-map {
  position: relative;
  width: 100%;
  height: 180px;
  background-color: #f0f0f0;
}

.map-overlay {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  padding: 2px 8px;
  border-radius: 4px;
}

@media (min-width: 768px) {
  .location-module {
    max-width: 1200px;
    margin-left: auto;
    margin-right: auto;
    border-radius: 12px;
  }
}
</style>
